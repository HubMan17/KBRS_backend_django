"""
Serializers for Achievement API endpoints.
"""

from rest_framework import serializers
from .models import Achievement, UserAchievement, AchievementCategory


class AchievementCategorySerializer(serializers.ModelSerializer):
    """Serializer for achievement categories."""

    class Meta:
        model = AchievementCategory
        fields = ['id', 'key', 'name', 'description', 'icon', 'order']


class AchievementSerializer(serializers.ModelSerializer):
    """Serializer for achievements."""

    rarity_color = serializers.SerializerMethodField()
    rarity_display = serializers.CharField(source='get_rarity_display', read_only=True)
    condition_type_display = serializers.CharField(source='get_condition_type_display', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Achievement
        fields = [
            'id', 'key', 'name', 'description', 'icon',
            'condition_type', 'condition_type_display',
            'condition_value', 'rarity', 'rarity_display', 'rarity_color',
            'xp_reward', 'category', 'category_name', 'order', 'enabled'
        ]

    def get_rarity_color(self, obj):
        """Get hex color for rarity."""
        return obj.get_rarity_color()


class UserAchievementSerializer(serializers.ModelSerializer):
    """Serializer for user achievements with progress."""

    achievement = AchievementSerializer(read_only=True)
    username = serializers.CharField(source='profile.username', read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UserAchievement
        fields = [
            'id', 'profile', 'username', 'achievement',
            'progress', 'progress_percentage', 'unlocked',
            'unlocked_at', 'notified_at'
        ]

    def get_progress_percentage(self, obj):
        """Calculate progress percentage."""
        if obj.achievement.condition_value == 0:
            return 100 if obj.unlocked else 0
        percentage = min(100, int((obj.progress / obj.achievement.condition_value) * 100))
        return percentage


class UserAchievementsRequest(serializers.Serializer):
    """Request serializer for getting user achievements."""

    discord_id = serializers.IntegerField(min_value=1)
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    unlocked_only = serializers.BooleanField(required=False, default=False)


class LeaderboardRequest(serializers.Serializer):
    """Request serializer for achievement leaderboard."""

    limit = serializers.IntegerField(min_value=1, max_value=100, required=False, default=10)
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CheckAchievementsRequest(serializers.Serializer):
    """Request serializer for triggering achievement check."""

    discord_id = serializers.IntegerField(min_value=1)
    trigger_event = serializers.CharField(required=False, allow_blank=True, max_length=100)


class AchievementStatsSerializer(serializers.Serializer):
    """Serializer for achievement statistics."""

    total_achievements = serializers.IntegerField()
    unlocked_count = serializers.IntegerField()
    completion_percentage = serializers.FloatField()
    total_xp_earned = serializers.IntegerField()
    by_rarity = serializers.DictField()
    by_category = serializers.DictField()
    recent_unlocks = UserAchievementSerializer(many=True)


class UserAchievementSummary(serializers.Serializer):
    """Summary of user's achievements."""

    discord_id = serializers.IntegerField()
    username = serializers.CharField()
    total_achievements = serializers.IntegerField()
    unlocked_count = serializers.IntegerField()
    completion_percentage = serializers.FloatField()
    total_xp_earned = serializers.IntegerField()
    achievements = UserAchievementSerializer(many=True)
