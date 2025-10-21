import os
import pytz
import requests
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from kbrs_api.models import DiscordProfile

from kbrs_api.ai.congratulations import generate_birthday_en
from kbrs_api.ai.translate import translate_multi
from kbrs_api.ai.formatting import format_multilang_birthday


MAX_DISCORD_LEN = 2000
SAFE_DISCORD_LEN = 1900  # запас для JSON


# перечитываем конфиг на каждый запуск (вдруг .env изменился)
token = os.getenv("DISCORD_BOT_TOKEN") or getattr(settings, "DISCORD_BOT_TOKEN", "")

main_channel_id = int(os.getenv("BIRTHDAY_CHANNEL_ID", getattr(settings, "BIRTHDAY_CHANNEL_ID", "0")))
ja_channel_id = int(os.getenv("BIRTHDAY_JA_CHANNEL_ID", "1429104455617351821"))
ko_channel_id = int(os.getenv("BIRTHDAY_KO_CHANNEL_ID", "1429104494448214078"))
zh_channel_id = int(os.getenv("BIRTHDAY_ZH_CHANNEL_ID", "1429104528258764860"))

if not token or not main_channel_id:
    raise RuntimeError("DISCORD_BOT_TOKEN / BIRTHDAY_CHANNEL_ID not configured")

# ---------- helpers ----------

def _chunk_text(s: str, limit: int = SAFE_DISCORD_LEN) -> list[str]:
    """Режет текст на куски, если он длиннее лимита Discord."""
    s = s or ""
    if len(s) <= limit:
        return [s]
    chunks, buf = [], []
    for line in s.splitlines(keepends=True):
        if len("".join(buf)) + len(line) <= limit:
            buf.append(line)
        else:
            chunks.append("".join(buf))
            buf = [line]
    if buf:
        chunks.append("".join(buf))
    return chunks


def _log_discord_error(prefix: str, resp: requests.Response):
    try:
        detail = resp.json()
    except Exception:
        detail = resp.text
    print(f"{prefix} status={resp.status_code}, resp={detail}")


def _send_discord_message(channel_id: int, content: str, token: str):
    """Отправка текста в Discord с защитой от 400 (слишком длинно)."""
    if not channel_id:
        return
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}"}
    for i, part in enumerate(_chunk_text((content or "").strip()), 1):
        if not part:
            continue
        resp = requests.post(url, json={"content": part}, headers=headers, timeout=15)
        if resp.status_code >= 400:
            _log_discord_error("[Birthday SEND] Bad request", resp)
            resp.raise_for_status()


# ---------- main task ----------

@shared_task
def send_birthday_congratulations() -> dict:
    """
    Ежедневная таска поздравлений:
    - ищет пользователей с сегодняшним birthday_date
    - генерирует EN (2-3 предложения, одно 😊) + переводы JA/KO/ZH-CN
    - шлёт мульти-язычный пост в основной канал
    - шлёт каждый перевод в свой языковой канал
    """

    sent = 0
    qs = (
        DiscordProfile.objects
        .filter(birthday_enabled=True)
        .exclude(birthday_date__isnull=True)
    )

    for profile in qs:
        try:
            tz = pytz.timezone(profile.birthday_tz or "UTC")
            today_local = timezone.now().astimezone(tz).date()
            bdate = profile.birthday_date

            # пропускаем, если дата не сегодня или уже поздравляли
            if not bdate or (bdate.month != today_local.month or bdate.day != today_local.day):
                continue
            if profile.birthday_last_congrats == today_local:
                continue

            mention = f"<@{profile.discord_id}>"

            # --- 1) EN (2–3 предложения, одна 😊)
            try:
                en = (generate_birthday_en(profile) or "").strip()
                if not en:
                    raise ValueError("empty EN")
            except Exception as e:
                print(f"[Birthday EN] fallback for {profile.discord_id}: {e}")
                en = "Happy Birthday! Wishing you a warm and joyful day. 😊"

            # --- 2) Переводы (строгие, без think-блоков)
            try:
                trs = translate_multi(en)  # {"JA": "...", "KO": "...", "ZH-CN": "..."}
                ja = trs.get("JA", "お誕生日おめでとう！素敵な一日になりますように。😊")
                ko = trs.get("KO", "생일 축하해요! 멋진 하루 되길 바라요. 😊")
                zh = trs.get("ZH-CN", "生日快乐！祝你度过美好的一天。😊")
            except Exception as e:
                print(f"[Birthday TR] translate_multi error for {profile.discord_id}: {e}")
                ja = "お誕生日おめでとう！素敵な一日になりますように。😊"
                ko = "생일 축하해요! 멋진 하루 되길 바라요. 😊"
                zh = "生日快乐！祝你度过美好的一天。😊"

            # --- 3) Основное многоязычное в главный канал
            main_message = format_multilang_birthday(mention, en, ja, ko, zh)
            _send_discord_message(main_channel_id, main_message, token)

            # --- 4) Отдельно в языковые каналы (как самостоятельные сообщения)
            # здесь без флажков и без подписи "JA/KO/ZH-CN", просто упоминание + перевод
            if ja_channel_id:
                _send_discord_message(ja_channel_id, f"{mention} {ja}", token)
            if ko_channel_id:
                _send_discord_message(ko_channel_id, f"{mention} {ko}", token)
            if zh_channel_id:
                _send_discord_message(zh_channel_id, f"{mention} {zh}", token)

            # --- 5) отметим, что поздравили сегодня
            profile.birthday_last_congrats = today_local
            profile.save(update_fields=["birthday_last_congrats"])
            sent += 1

        except requests.HTTPError as e:
            print(f"[Birthday SEND] HTTP error for {profile.discord_id}: {e} (status={getattr(e.response, 'status_code', '?')})")
        except Exception as e:
            print(f"[Birthday] unexpected error for {profile.discord_id}: {e}")

    return {"sent": sent}