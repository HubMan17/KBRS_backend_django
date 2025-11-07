"""
Achievement checking engine.

Checks conditions and unlocks achievements for users.
"""

from typing import List, Dict, Any
from django.db.models import Count, Q, F
from django.utils import timezone
from datetime import timedelta

from kbrs_api.models import (
    DiscordProfile,
    Achievement,
    UserAchievement,
    MessageEvent,
    ReactionEvent,
    EmojiUsage,
)


class AchievementEngine:
    """
    Core engine for checking and unlocking achievements.

    Usage:
        engine = AchievementEngine()
        unlocked = engine.check_user_achievements(user_id)
    """

    def __init__(self):
        self.checkers = {
            'message_count': self._check_message_count,
            'reaction_count': self._check_reaction_count,
            'emoji_usage': self._check_emoji_usage,
            'level_reached': self._check_level_reached,
            'join_server': self._check_join_server,
            'days_active': self._check_days_active,
            'birthday_set': self._check_birthday_set,
            'consecutive_days': self._check_consecutive_days,
            'top_rank': self._check_top_rank,
        }

    def check_user_achievements(self, discord_id: int) -> List[Dict[str, Any]]:
        """
        Check all achievements for a specific user.

        Returns:
            List of newly unlocked achievements with their data
        """
        try:
            profile = DiscordProfile.objects.get(discord_id=discord_id)
        except DiscordProfile.DoesNotExist:
            return []

        # Get all enabled achievements
        achievements = Achievement.objects.filter(enabled=True)

        newly_unlocked = []

        for achievement in achievements:
            unlocked_data = self._check_single_achievement(profile, achievement)
            if unlocked_data:
                newly_unlocked.append(unlocked_data)

        return newly_unlocked

    def check_all_users(self, achievement_key: str = None) -> Dict[str, int]:
        """
        Check achievements for all users.

        Args:
            achievement_key: If provided, check only this achievement

        Returns:
            Dict with stats: {'checked': N, 'unlocked': M}
        """
        stats = {'checked': 0, 'unlocked': 0}

        # Get achievements to check
        if achievement_key:
            achievements = Achievement.objects.filter(key=achievement_key, enabled=True)
        else:
            achievements = Achievement.objects.filter(enabled=True)

        # Get all users
        profiles = DiscordProfile.objects.all()

        for profile in profiles:
            for achievement in achievements:
                stats['checked'] += 1
                unlocked_data = self._check_single_achievement(profile, achievement)
                if unlocked_data:
                    stats['unlocked'] += 1

        return stats

    def _check_single_achievement(
        self,
        profile: DiscordProfile,
        achievement: Achievement
    ) -> Dict[str, Any] | None:
        """
        Check if user meets achievement condition.

        Returns:
            Achievement data if newly unlocked, None otherwise
        """
        # Get or create user achievement record
        user_achievement, created = UserAchievement.objects.get_or_create(
            profile=profile,
            achievement=achievement,
            defaults={'progress': 0}
        )

        # Already unlocked
        if user_achievement.unlocked:
            return None

        # Get checker function
        checker_func = self.checkers.get(achievement.condition_type)
        if not checker_func:
            print(f"[AchievementEngine] Unknown condition type: {achievement.condition_type}")
            return None

        # Check condition
        current_value = checker_func(profile, achievement)

        # Update progress
        was_unlocked = user_achievement.update_progress(current_value, auto_unlock=True)

        if was_unlocked:
            # Award XP
            if achievement.xp_reward > 0:
                profile.xp += achievement.xp_reward
                profile.save(update_fields=['xp'])

            return {
                'achievement': achievement,
                'profile': profile,
                'xp_reward': achievement.xp_reward,
                'unlocked_at': user_achievement.unlocked_at,
            }

        return None

    # ========================================================================
    # Condition Checkers
    # ========================================================================

    def _check_message_count(self, profile: DiscordProfile, achievement: Achievement) -> int:
        """Check total messages sent."""
        count = MessageEvent.objects.filter(author_id=profile.discord_id).count()
        return count

    def _check_reaction_count(self, profile: DiscordProfile, achievement: Achievement) -> int:
        """Check total reactions given."""
        count = ReactionEvent.objects.filter(reactor_id=profile.discord_id).count()
        return count

    def _check_emoji_usage(self, profile: DiscordProfile, achievement: Achievement) -> int:
        """Check unique emojis used."""
        count = EmojiUsage.objects.filter(
            sender_id=profile.discord_id
        ).values('key').distinct().count()
        return count

    def _check_level_reached(self, profile: DiscordProfile, achievement: Achievement) -> int:
        """Check current level."""
        return profile.level

    def _check_join_server(self, profile: DiscordProfile, achievement: Achievement) -> int:
        """Check if user joined server (always 1 if profile exists)."""
        return 1

    def _check_days_active(self, profile: DiscordProfile, achievement: Achievement) -> int:
        """Check days active on server (based on message activity)."""
        dates = MessageEvent.objects.filter(
            author_id=profile.discord_id
        ).dates('created_at', 'day')
        return dates.count()

    def _check_birthday_set(self, profile: DiscordProfile, achievement: Achievement) -> int:
        """Check if birthday is set."""
        return 1 if profile.birthday_date else 0

    def _check_consecutive_days(self, profile: DiscordProfile, achievement: Achievement) -> int:
        """Check consecutive days active."""
        # Get all activity dates
        dates = list(MessageEvent.objects.filter(
            author_id=profile.discord_id
        ).dates('created_at', 'day'))

        if not dates:
            return 0

        # Calculate longest streak
        max_streak = 1
        current_streak = 1

        for i in range(1, len(dates)):
            prev_date = dates[i - 1]
            curr_date = dates[i]
            diff = (curr_date - prev_date).days

            if diff == 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1

        return max_streak

    def _check_top_rank(self, profile: DiscordProfile, achievement: Achievement) -> int:
        """Check if user is in top N of leaderboard."""
        # Get user's rank
        rank = DiscordProfile.objects.filter(
            Q(level__gt=profile.level) | Q(level=profile.level, xp__gt=profile.xp)
        ).count() + 1

        # Achievement value is target rank (e.g., 10 for "Top 10")
        target_rank = achievement.condition_value
        return 1 if rank <= target_rank else 0


class AchievementNotifier:
    """
    Handles notifications for unlocked achievements.

    Integrates with Discord bot to send messages.
    """

    def __init__(self, discord_channel_id: int = None):
        self.channel_id = discord_channel_id

    def get_pending_notifications(self) -> List[UserAchievement]:
        """Get achievements that haven't been notified yet."""
        return UserAchievement.objects.filter(
            unlocked=True,
            notified_at__isnull=True
        ).select_related('profile', 'achievement')

    def mark_as_notified(self, user_achievement: UserAchievement):
        """Mark achievement as notified."""
        user_achievement.notified_at = timezone.now()
        user_achievement.save(update_fields=['notified_at'])

    def create_embed_data(self, user_achievement: UserAchievement) -> Dict[str, Any]:
        """
        Create Discord embed data for achievement notification.

        Returns:
            Dict compatible with Discord API embed format
        """
        achievement = user_achievement.achievement
        profile = user_achievement.profile

        return {
            'title': f'{achievement.icon} Achievement Unlocked!',
            'description': f'**{achievement.name}**\n{achievement.description}',
            'color': achievement.get_rarity_color(),
            'fields': [
                {
                    'name': 'Rarity',
                    'value': achievement.rarity.capitalize(),
                    'inline': True
                },
                {
                    'name': 'XP Reward',
                    'value': f'+{achievement.xp_reward} XP',
                    'inline': True
                },
            ],
            'footer': {
                'text': f'Unlocked by {profile.username}'
            },
            'timestamp': user_achievement.unlocked_at.isoformat() if user_achievement.unlocked_at else None
        }
