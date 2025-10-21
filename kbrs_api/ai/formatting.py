def format_multilang_birthday(mention: str, en: str, ja: str, ko: str, zh: str) -> str:
    """Возвращает финальное сообщение с флажками для Discord."""
    return (
        f"🎉 {mention} {en}\n\n"
        f"🇯🇵 **JA:** {ja}\n"
        f"🇰🇷 **KO:** {ko}\n"
        f"🇨🇳 **ZH-CN:** {zh}"
    )
