"""
API views for achievements system.

Endpoints:
- GET /achievements/ - List all achievements
- GET /achievements/<id>/ - Get specific achievement
- POST /achievements/user/ - Get user's achievements with progress
- POST /achievements/stats/ - Get user's achievement statistics
- POST /achievements/check/ - Trigger achievement check for user
- GET /achievements/leaderboard/ - Achievement leaderboard
- GET /achievements/categories/ - List all categories
"""

from django.db.models import Count, Q, Sum, F
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Achievement, UserAchievement, AchievementCategory, DiscordProfile
from .serializers_achievements import (
    AchievementSerializer,
    UserAchievementSerializer,
    UserAchievementsRequest,
    LeaderboardRequest,
    CheckAchievementsRequest,
    AchievementStatsSerializer,
    AchievementCategorySerializer,
    UserAchievementSummary,
)
from .tasks.achievements import check_user_achievements


class AchievementListView(APIView):
    """
    GET /api/v1/achievements/

    List all enabled achievements, optionally filtered by category.

    Query params:
        - category: Filter by category key (optional)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        category_key = request.query_params.get('category')

        queryset = Achievement.objects.filter(enabled=True).select_related('category')

        if category_key:
            queryset = queryset.filter(category__key=category_key)

        queryset = queryset.order_by('category__order', 'order', 'condition_value')

        serializer = AchievementSerializer(queryset, many=True)
        return Response({
            'count': len(serializer.data),
            'achievements': serializer.data
        }, status=status.HTTP_200_OK)


class AchievementDetailView(APIView):
    """
    GET /api/v1/achievements/<id>/

    Get detailed information about a specific achievement.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, achievement_id):
        try:
            achievement = Achievement.objects.select_related('category').get(
                id=achievement_id,
                enabled=True
            )
        except Achievement.DoesNotExist:
            return Response(
                {'error': 'Achievement not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AchievementSerializer(achievement)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserAchievementsView(APIView):
    """
    POST /api/v1/achievements/user/

    Get user's achievements with progress.

    Request:
    {
        "discord_id": 123456789,
        "category": "social",  // optional
        "unlocked_only": false  // optional
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserAchievementsRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        discord_id = data['discord_id']
        category = data.get('category')
        unlocked_only = data.get('unlocked_only', False)

        # Check if profile exists
        try:
            profile = DiscordProfile.objects.get(discord_id=discord_id)
        except DiscordProfile.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Build query
        queryset = UserAchievement.objects.filter(
            profile=profile
        ).select_related('achievement', 'achievement__category', 'profile')

        if category:
            queryset = queryset.filter(achievement__category__key=category)

        if unlocked_only:
            queryset = queryset.filter(unlocked=True)

        queryset = queryset.order_by(
            'achievement__category__order',
            'achievement__order',
            'achievement__condition_value'
        )

        # Serialize
        achievement_serializer = UserAchievementSerializer(queryset, many=True)

        # Calculate summary stats
        total_achievements = Achievement.objects.filter(enabled=True).count()
        unlocked_count = queryset.filter(unlocked=True).count()
        completion_percentage = (unlocked_count / total_achievements * 100) if total_achievements > 0 else 0

        total_xp = queryset.filter(unlocked=True).aggregate(
            total=Sum('achievement__xp_reward')
        )['total'] or 0

        return Response({
            'discord_id': discord_id,
            'username': profile.username,
            'total_achievements': total_achievements,
            'unlocked_count': unlocked_count,
            'completion_percentage': round(completion_percentage, 2),
            'total_xp_earned': total_xp,
            'achievements': achievement_serializer.data,
        }, status=status.HTTP_200_OK)


class UserAchievementStatsView(APIView):
    """
    POST /api/v1/achievements/stats/

    Get detailed statistics about user's achievements.

    Request:
    {
        "discord_id": 123456789
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        discord_id = request.data.get('discord_id')
        if not discord_id:
            return Response(
                {'error': 'discord_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            profile = DiscordProfile.objects.get(discord_id=discord_id)
        except DiscordProfile.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get all user achievements
        user_achievements = UserAchievement.objects.filter(
            profile=profile
        ).select_related('achievement', 'achievement__category')

        # Calculate overall stats
        total_achievements = Achievement.objects.filter(enabled=True).count()
        unlocked_achievements = user_achievements.filter(unlocked=True)
        unlocked_count = unlocked_achievements.count()
        completion_percentage = (unlocked_count / total_achievements * 100) if total_achievements > 0 else 0

        # Total XP from achievements
        total_xp = unlocked_achievements.aggregate(
            total=Sum('achievement__xp_reward')
        )['total'] or 0

        # Stats by rarity
        by_rarity = {}
        for rarity_key, rarity_name in Achievement.RARITY_CHOICES:
            total = Achievement.objects.filter(enabled=True, rarity=rarity_key).count()
            unlocked = unlocked_achievements.filter(achievement__rarity=rarity_key).count()
            by_rarity[rarity_key] = {
                'name': rarity_name,
                'total': total,
                'unlocked': unlocked,
                'percentage': round((unlocked / total * 100) if total > 0 else 0, 2)
            }

        # Stats by category
        by_category = {}
        categories = AchievementCategory.objects.all()
        for category in categories:
            total = Achievement.objects.filter(enabled=True, category=category).count()
            unlocked = unlocked_achievements.filter(achievement__category=category).count()
            by_category[category.key] = {
                'name': category.name,
                'total': total,
                'unlocked': unlocked,
                'percentage': round((unlocked / total * 100) if total > 0 else 0, 2)
            }

        # Recent unlocks (last 10)
        recent_unlocks = unlocked_achievements.order_by('-unlocked_at')[:10]
        recent_serializer = UserAchievementSerializer(recent_unlocks, many=True)

        response_data = {
            'total_achievements': total_achievements,
            'unlocked_count': unlocked_count,
            'completion_percentage': round(completion_percentage, 2),
            'total_xp_earned': total_xp,
            'by_rarity': by_rarity,
            'by_category': by_category,
            'recent_unlocks': recent_serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class CheckAchievementsView(APIView):
    """
    POST /api/v1/achievements/check/

    Trigger achievement check for a specific user.

    Request:
    {
        "discord_id": 123456789,
        "trigger_event": "message_sent"  // optional
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckAchievementsRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        discord_id = data['discord_id']
        trigger_event = data.get('trigger_event')

        # Check if profile exists
        try:
            DiscordProfile.objects.get(discord_id=discord_id)
        except DiscordProfile.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Trigger Celery task
        task = check_user_achievements.delay(discord_id, trigger_event)

        return Response({
            'message': 'Achievement check triggered',
            'discord_id': discord_id,
            'task_id': task.id,
        }, status=status.HTTP_202_ACCEPTED)


class AchievementLeaderboardView(APIView):
    """
    GET /api/v1/achievements/leaderboard/

    Get achievement leaderboard (users with most achievements).

    Query params:
        - limit: Number of users to return (default: 10, max: 100)
        - category: Filter by category key (optional)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        limit = min(limit, 100)  # Cap at 100
        category_key = request.query_params.get('category')

        # Build query
        queryset = DiscordProfile.objects.annotate(
            total_unlocked=Count(
                'userachievement',
                filter=Q(userachievement__unlocked=True)
            ),
            total_xp_from_achievements=Sum(
                'userachievement__achievement__xp_reward',
                filter=Q(userachievement__unlocked=True)
            )
        )

        if category_key:
            queryset = queryset.annotate(
                category_unlocked=Count(
                    'userachievement',
                    filter=Q(
                        userachievement__unlocked=True,
                        userachievement__achievement__category__key=category_key
                    )
                )
            ).filter(category_unlocked__gt=0).order_by('-category_unlocked')
        else:
            queryset = queryset.filter(total_unlocked__gt=0).order_by('-total_unlocked')

        queryset = queryset[:limit]

        # Build response
        leaderboard = []
        for rank, profile in enumerate(queryset, start=1):
            leaderboard.append({
                'rank': rank,
                'discord_id': profile.discord_id,
                'username': profile.username,
                'level': profile.level,
                'achievements_unlocked': profile.total_unlocked,
                'xp_from_achievements': profile.total_xp_from_achievements or 0,
            })

        return Response({
            'count': len(leaderboard),
            'category': category_key,
            'leaderboard': leaderboard,
        }, status=status.HTTP_200_OK)


class AchievementCategoriesView(APIView):
    """
    GET /api/v1/achievements/categories/

    List all achievement categories.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = AchievementCategory.objects.all().order_by('order')

        # Annotate with achievement counts
        categories_with_counts = []
        for category in categories:
            achievement_count = Achievement.objects.filter(
                category=category,
                enabled=True
            ).count()

            serializer = AchievementCategorySerializer(category)
            data = serializer.data
            data['achievement_count'] = achievement_count
            categories_with_counts.append(data)

        return Response({
            'count': len(categories_with_counts),
            'categories': categories_with_counts,
        }, status=status.HTTP_200_OK)
