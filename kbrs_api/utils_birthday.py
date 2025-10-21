from __future__ import annotations
from datetime import date, timedelta

def normalize_birthday_date(d: date) -> date:
    """Храним любой год (например, 2000) — важны только месяц/день."""
    return date(2000, d.month, d.day)

def next_birthday_after(today: date, bday_md: date) -> date:
    """
    bday_md — дата с фиктивным годом (например 2000-10-22, важны month/day).
    Возвращает ближайшую дату наступления ДР после (или в) today.
    Обрабатывает 29 февраля: если нет 29 февраля — сдвиг на 1 марта.
    """
    try:
        candidate = date(today.year, bday_md.month, bday_md.day)
    except ValueError:
        # 29 февраля в невисокосный год -> 1 марта
        candidate = date(today.year, 3, 1)
    if candidate < today:
        year = today.year + 1
        try:
            candidate = date(year, bday_md.month, bday_md.day)
        except ValueError:
            candidate = date(year, 3, 1)
    return candidate

def days_until(today: date, future: date) -> int:
    return (future - today).days
