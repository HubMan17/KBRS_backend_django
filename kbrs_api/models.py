from django.db import models

from .models_events import (
    MessageEvent, ReactionEvent, EmojiUsage, XpTransaction
)
from .models_achievements import (
    Achievement, UserAchievement, AchievementCategory
)

class DiscordProfile(models.Model):
    discord_id = models.BigIntegerField(unique=True, db_index=True)
    username   = models.CharField(max_length=255, blank=True, default="")
    level      = models.IntegerField(default=0)
    xp         = models.IntegerField(default=0)

    # anti-flood (optional)
    last_msg_xp_at   = models.DateTimeField(null=True, blank=True)
    last_react_xp_at = models.DateTimeField(null=True, blank=True)

    # 🎂 birthdays
    birthday_date            = models.DateField(null=True, blank=True)      # if None -> don't congratulate
    birthday_tz              = models.CharField(max_length=64, default="UTC")
    birthday_enabled         = models.BooleanField(default=True)            # toggle per user
    birthday_last_congrats   = models.DateField(null=True, blank=True)      # to avoid duplicates per day

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username or self.discord_id} (lvl {self.level})"
    
    class Meta:
        indexes = [
            models.Index(fields=["-level", "-xp"]),
        ]
