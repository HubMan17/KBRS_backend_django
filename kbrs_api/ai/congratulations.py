import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()
DEEP_URL = os.getenv("DEEP_URL", "https://api.intelligence.io.solutions/api/v1/chat/completions")
DEEP_KEY = os.getenv("DEEP_KEY")
DEEP_MODEL = os.getenv("DEEP_MODEL", "deepseek-ai/DeepSeek-R1-0528")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {DEEP_KEY}",
}

EN_SYSTEM_PROMPT = (
    "You are writing a short, warm birthday message for a Discord community member.\n"
    "- 2–3 sentences, friendly and sincere.\n"
    "- Address them as 'you' (no names, no stats, no tags).\n"
    "- No lists, hashtags, or quotes.\n"
    "- Use exactly one emoji: a single '😊' appended at the very end.\n"
    "- Keep it human, natural, and positive."
)

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]")

def _strip_think(text: str) -> str:
    """Удаляет размышления <think>...</think> и прочий мусор."""
    cleaned = THINK_RE.sub("", text or "").strip()
    cleaned = re.sub(r"🇯🇵.*|🇰🇷.*|🇨🇳.*", "", cleaned)
    return cleaned.strip()

def _normalize(text: str) -> str:
    """Убирает все эмодзи и добавляет одно 😊 в конце."""
    text = EMOJI_RE.sub("", text or "").strip()
    if not text.endswith((".", "!", "?", "。", "！")):
        text += "."
    return text + " 😊"

def generate_birthday_en(profile) -> str:
    """Создаёт короткое поздравление EN (2–3 предложения, одно 😊)."""
    if not DEEP_KEY:
        raise RuntimeError("DEEP_KEY missing")

    # немного контекста о пользователе
    is_new = profile.level < 2
    prompt = (
        f"Write a birthday message for a Discord user who is {'new' if is_new else 'an active regular'} "
        f"in the community. The tone should be warm, sincere, and short (2–3 sentences, max 180 chars)."
    )

    data = {
        "model": DEEP_MODEL,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": EN_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }

    resp = requests.post(DEEP_URL, headers=HEADERS, json=data, timeout=60)
    resp.raise_for_status()
    js = resp.json()
    raw = js["choices"][0]["message"]["content"]
    return _normalize(_strip_think(raw))
