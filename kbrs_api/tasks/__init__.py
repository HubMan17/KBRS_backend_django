# делает модуль видимым и регистрирует таску при автодискавере
from .congratulations import send_birthday_congratulations
from .achievements import (
    check_all_achievements,
    check_user_achievements,
    send_achievement_notifications,
    check_specific_achievement,
    recalculate_achievement_progress,
)

__all__ = [
    "send_birthday_congratulations",
    "check_all_achievements",
    "check_user_achievements",
    "send_achievement_notifications",
    "check_specific_achievement",
    "recalculate_achievement_progress",
]
