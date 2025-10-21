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

# --- regex для вычищения мусора ---
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

def _strip_think(text: str) -> str:
    """Удаляет блоки размышлений <think>...</think> и пробелы вокруг."""
    if not text:
        return ""
    clean = THINK_RE.sub("", text)
    return clean.strip()

def _translate_to(target_lang: str, text: str) -> str:
    """Перевод на один язык, возвращает чистый текст."""
    sys_prompt = (
        f"You are a professional translator. Translate the given English birthday greeting "
        f"into {target_lang} while preserving its tone and meaning.\n"
        f"- Keep exactly one emoji 😊 at the end.\n"
        f"- Return ONLY the translation text — no explanations, no markup, no quotes."
    )

    data = {
        "model": DEEP_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": text},
        ],
    }

    resp = requests.post(DEEP_URL, headers=HEADERS, json=data, timeout=60)
    resp.raise_for_status()
    js = resp.json()
    raw = js["choices"][0]["message"]["content"]
    return _strip_think(raw)

def translate_multi(en_text: str) -> dict:
    """Возвращает переводы EN → JA, KO, ZH-CN (чисто, без размышлений)."""
    if not DEEP_KEY:
        raise RuntimeError("DEEP_KEY missing")

    out = {}
    for lang in ["JA", "KO", "ZH-CN"]:
        try:
            out[lang] = _translate_to(lang, en_text)
        except Exception as e:
            print(f"[translate_multi] error {lang}: {e}")
            if lang == "JA":
                out[lang] = "お誕生日おめでとう！素敵な一日になりますように。😊"
            elif lang == "KO":
                out[lang] = "생일 축하해요! 멋진 하루 되길 바라요. 😊"
            else:
                out[lang] = "生日快乐！祝你度过美好的一天。😊"
    return out
