from django.urls import path
from .views import RankView, TopView, AddXpView, SyncMembersView, BirthdayUpdateView
from .views_events import MessageEventBulk, ReactionEventBulk, EmojiUsageBulk, XpTransactionBulk
from .views_stats import ServerHighlightsView, UserStatsView
from .views_birthday import UpcomingBirthdaysView, SetBirthdayView
from .views_achievements import (
    AchievementListView,
    AchievementDetailView,
    UserAchievementsView,
    UserAchievementStatsView,
    CheckAchievementsView,
    AchievementLeaderboardView,
    AchievementCategoriesView,
)
from .views_f.discord_views import TokenExchangeView, NotifyAuthorizedView

urlpatterns = [
    path('discord/rank/<int:discord_id>/', RankView.as_view(), name='rank'),
    path('discord/top/', TopView.as_view(), name='top'),
    path('discord/add_xp/', AddXpView.as_view(), name='add_xp'),
    path('discord/sync_members/', SyncMembersView.as_view(), name='sync_members'),
    path('discord/birthday/update/', BirthdayUpdateView.as_view(), name='birthday_update'),
    
    # stats
    path("events/messages/bulk", MessageEventBulk.as_view()),
    path("events/reactions/bulk", ReactionEventBulk.as_view()),
    path("events/emoji_usage/bulk", EmojiUsageBulk.as_view()),
    path("events/xp/bulk", XpTransactionBulk.as_view()),
    
    path("stats/user/", UserStatsView.as_view(), name="stats-user"),
    path("stats/highlights/", ServerHighlightsView.as_view()),
    
    path("birthdays/upcoming/", UpcomingBirthdaysView.as_view()),
    path("birthdays/set/",      SetBirthdayView.as_view()),

    # achievements
    path("achievements/", AchievementListView.as_view(), name="achievement-list"),
    path("achievements/<int:achievement_id>/", AchievementDetailView.as_view(), name="achievement-detail"),
    path("achievements/user/", UserAchievementsView.as_view(), name="user-achievements"),
    path("achievements/stats/", UserAchievementStatsView.as_view(), name="achievement-stats"),
    path("achievements/check/", CheckAchievementsView.as_view(), name="achievement-check"),
    path("achievements/leaderboard/", AchievementLeaderboardView.as_view(), name="achievement-leaderboard"),
    path("achievements/categories/", AchievementCategoriesView.as_view(), name="achievement-categories"),

    path("discord/token", TokenExchangeView.as_view(), name="discord-token"),
    path("discord/notify", NotifyAuthorizedView.as_view(), name="discord-notify"),  # опционально
]
