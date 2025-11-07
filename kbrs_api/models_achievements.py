"""
Achievement system models.

Features:
- Flexible achievement definitions
- Progress tracking
- Multiple condition types
- XP rewards
- Rarity tiers
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Achievement(models.Model):
    """
    Achievement template/definition.

    Examples:
    - First Steps: Join the server
    - Chatterbox: Send 100 messages
    - Reactor: Add 50 reactions
    - Social Butterfly: React to 10 different people
    """

    RARITY_CHOICES = [
        ('common', 'Common'),
        ('uncommon', 'Uncommon'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
        ('mythic', 'Mythic'),
    ]

    CONDITION_TYPE_CHOICES = [
        ('message_count', 'Total Messages Sent'),
        ('reaction_count', 'Total Reactions Given'),
        ('emoji_usage', 'Unique Emojis Used'),
        ('level_reached', 'Level Reached'),
        ('join_server', 'Join Server'),
        ('days_active', 'Days Active on Server'),
        ('voice_minutes', 'Voice Channel Minutes'),
        ('birthday_set', 'Birthday Set'),
        ('help_reactions', 'Help Reactions Given'),
        ('consecutive_days', 'Consecutive Days Active'),
        ('top_rank', 'Reach Top N in Leaderboard'),
    ]

    # Basic info
    key = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique identifier for this achievement (e.g., 'first_message')"
    )
    name = models.CharField(max_length=200, help_text="Display name")
    description = models.TextField(help_text="What the user needs to do")

    # Visual
    icon = models.CharField(
        max_length=50,
        default="🏆",
        help_text="Emoji icon for this achievement"
    )
    rarity = models.CharField(
        max_length=20,
        choices=RARITY_CHOICES,
        default='common'
    )

    # Condition
    condition_type = models.CharField(
        max_length=50,
        choices=CONDITION_TYPE_CHOICES,
        help_text="What metric to check"
    )
    condition_value = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Target value (e.g., 100 for '100 messages')"
    )

    # Rewards
    xp_reward = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="XP awarded when unlocked"
    )

    # Category
    category = models.ForeignKey(
        'AchievementCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='achievements',
        help_text="Achievement category"
    )

    # Metadata
    enabled = models.BooleanField(default=True)
    hidden = models.BooleanField(
        default=False,
        help_text="Hidden achievements (surprises)"
    )
    order = models.IntegerField(default=0, help_text="Display order")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['enabled', 'condition_type']),
            models.Index(fields=['rarity']),
        ]

    def __str__(self):
        return f"{self.icon} {self.name} ({self.key})"

    def get_rarity_color(self):
        """Get color for rarity."""
        colors = {
            'common': 0x95A5A6,    # Gray
            'rare': 0x3498DB,      # Blue
            'epic': 0x9B59B6,      # Purple
            'legendary': 0xF1C40F, # Gold
        }
        return colors.get(self.rarity, 0x95A5A6)


class UserAchievement(models.Model):
    """
    Tracks which achievements a user has unlocked.
    """

    profile = models.ForeignKey(
        'DiscordProfile',
        on_delete=models.CASCADE,
        related_name='achievements'
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='unlocks'
    )

    # Progress tracking
    progress = models.IntegerField(
        default=0,
        help_text="Current progress towards this achievement"
    )
    unlocked = models.BooleanField(default=False, db_index=True)

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    notified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user was notified in Discord"
    )

    class Meta:
        unique_together = ['profile', 'achievement']
        indexes = [
            models.Index(fields=['unlocked', 'notified_at']),
            models.Index(fields=['profile', 'unlocked']),
        ]

    def __str__(self):
        status = "✅" if self.unlocked else f"{self.progress}/{self.achievement.condition_value}"
        return f"{self.profile.username} - {self.achievement.name} ({status})"

    def unlock(self):
        """Mark achievement as unlocked."""
        if not self.unlocked:
            self.unlocked = True
            self.unlocked_at = timezone.now()
            self.progress = self.achievement.condition_value
            self.save()
            return True
        return False

    def update_progress(self, new_value: int, auto_unlock: bool = True):
        """
        Update progress and auto-unlock if threshold reached.

        Returns:
            bool: True if achievement was unlocked, False otherwise
        """
        if self.unlocked:
            return False

        self.progress = new_value

        if auto_unlock and self.progress >= self.achievement.condition_value:
            self.unlock()
            return True

        self.save()
        return False

    def get_progress_percentage(self):
        """Get progress as percentage (0-100)."""
        if self.achievement.condition_value == 0:
            return 100
        return min(100, int((self.progress / self.achievement.condition_value) * 100))


class AchievementCategory(models.Model):
    """
    Optional: Group achievements into categories.

    Examples:
    - Social (messages, reactions)
    - Activity (voice, events)
    - Milestones (levels, ranks)
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="📁")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Achievement Categories"

    def __str__(self):
        return f"{self.icon} {self.name}"
