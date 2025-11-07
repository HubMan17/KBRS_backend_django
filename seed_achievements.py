"""
Seed script to create initial achievements.

Run: python seed_achievements.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from kbrs_api.models_achievements import Achievement, AchievementCategory


def create_categories():
    """Create achievement categories."""
    categories = [
        {
            'name': 'Social',
            'description': 'Achievements for social interactions',
            'icon': '👥',
            'order': 1
        },
        {
            'name': 'Activity',
            'description': 'Achievements for server activity',
            'icon': '⚡',
            'order': 2
        },
        {
            'name': 'Progression',
            'description': 'Achievements for leveling up',
            'icon': '📈',
            'order': 3
        },
        {
            'name': 'Milestones',
            'description': 'Special milestone achievements',
            'icon': '🏆',
            'order': 4
        },
    ]

    created_categories = {}
    for cat_data in categories:
        category, created = AchievementCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )
        created_categories[cat_data['name'].lower()] = category
        print(f"{'Created' if created else 'Found'} category: {category.name}")

    return created_categories


def create_achievements(categories):
    """Create initial achievements."""
    achievements = [
        # Social achievements
        {
            'key': 'first_join',
            'name': 'Welcome!',
            'description': 'Join the server',
            'icon': '👋',
            'condition_type': 'join_server',
            'condition_value': 1,
            'rarity': 'common',
            'xp_reward': 50,
            'category': categories['social'],
            'order': 1,
        },
        {
            'key': 'chatty',
            'name': 'Chatty',
            'description': 'Send 100 messages',
            'icon': '💬',
            'condition_type': 'message_count',
            'condition_value': 100,
            'rarity': 'common',
            'xp_reward': 100,
            'category': categories['social'],
            'order': 2,
        },
        {
            'key': 'chatterbox',
            'name': 'Chatterbox',
            'description': 'Send 500 messages',
            'icon': '💬',
            'condition_type': 'message_count',
            'condition_value': 500,
            'rarity': 'uncommon',
            'xp_reward': 250,
            'category': categories['social'],
            'order': 3,
        },
        {
            'key': 'conversation_master',
            'name': 'Conversation Master',
            'description': 'Send 1000 messages',
            'icon': '💬',
            'condition_type': 'message_count',
            'condition_value': 1000,
            'rarity': 'rare',
            'xp_reward': 500,
            'category': categories['social'],
            'order': 4,
        },
        {
            'key': 'reactor',
            'name': 'Reactor',
            'description': 'React to 50 messages',
            'icon': '😊',
            'condition_type': 'reaction_count',
            'condition_value': 50,
            'rarity': 'common',
            'xp_reward': 100,
            'category': categories['social'],
            'order': 5,
        },
        {
            'key': 'reaction_master',
            'name': 'Reaction Master',
            'description': 'React to 200 messages',
            'icon': '😊',
            'condition_type': 'reaction_count',
            'condition_value': 200,
            'rarity': 'uncommon',
            'xp_reward': 250,
            'category': categories['social'],
            'order': 6,
        },
        {
            'key': 'emoji_collector',
            'name': 'Emoji Collector',
            'description': 'Use 20 different emojis',
            'icon': '🎨',
            'condition_type': 'emoji_usage',
            'condition_value': 20,
            'rarity': 'uncommon',
            'xp_reward': 200,
            'category': categories['social'],
            'order': 7,
        },
        {
            'key': 'birthday_person',
            'name': 'Birthday Person',
            'description': 'Set your birthday',
            'icon': '🎂',
            'condition_type': 'birthday_set',
            'condition_value': 1,
            'rarity': 'common',
            'xp_reward': 50,
            'category': categories['social'],
            'order': 8,
        },

        # Activity achievements
        {
            'key': 'active_member',
            'name': 'Active Member',
            'description': 'Be active for 7 different days',
            'icon': '📅',
            'condition_type': 'days_active',
            'condition_value': 7,
            'rarity': 'common',
            'xp_reward': 150,
            'category': categories['activity'],
            'order': 1,
        },
        {
            'key': 'veteran',
            'name': 'Veteran',
            'description': 'Be active for 30 different days',
            'icon': '📅',
            'condition_type': 'days_active',
            'condition_value': 30,
            'rarity': 'uncommon',
            'xp_reward': 300,
            'category': categories['activity'],
            'order': 2,
        },
        {
            'key': 'dedicated',
            'name': 'Dedicated',
            'description': 'Be active for 100 different days',
            'icon': '📅',
            'condition_type': 'days_active',
            'condition_value': 100,
            'rarity': 'rare',
            'xp_reward': 1000,
            'category': categories['activity'],
            'order': 3,
        },
        {
            'key': 'streak_3',
            'name': 'Three Day Streak',
            'description': 'Be active for 3 consecutive days',
            'icon': '🔥',
            'condition_type': 'consecutive_days',
            'condition_value': 3,
            'rarity': 'common',
            'xp_reward': 100,
            'category': categories['activity'],
            'order': 4,
        },
        {
            'key': 'streak_7',
            'name': 'Week Warrior',
            'description': 'Be active for 7 consecutive days',
            'icon': '🔥',
            'condition_type': 'consecutive_days',
            'condition_value': 7,
            'rarity': 'uncommon',
            'xp_reward': 250,
            'category': categories['activity'],
            'order': 5,
        },
        {
            'key': 'streak_30',
            'name': 'Unstoppable',
            'description': 'Be active for 30 consecutive days',
            'icon': '🔥',
            'condition_type': 'consecutive_days',
            'condition_value': 30,
            'rarity': 'epic',
            'xp_reward': 1000,
            'category': categories['activity'],
            'order': 6,
        },

        # Progression achievements
        {
            'key': 'level_5',
            'name': 'Novice',
            'description': 'Reach level 5',
            'icon': '⭐',
            'condition_type': 'level_reached',
            'condition_value': 5,
            'rarity': 'common',
            'xp_reward': 100,
            'category': categories['progression'],
            'order': 1,
        },
        {
            'key': 'level_10',
            'name': 'Apprentice',
            'description': 'Reach level 10',
            'icon': '⭐',
            'condition_type': 'level_reached',
            'condition_value': 10,
            'rarity': 'common',
            'xp_reward': 200,
            'category': categories['progression'],
            'order': 2,
        },
        {
            'key': 'level_25',
            'name': 'Expert',
            'description': 'Reach level 25',
            'icon': '⭐',
            'condition_type': 'level_reached',
            'condition_value': 25,
            'rarity': 'uncommon',
            'xp_reward': 500,
            'category': categories['progression'],
            'order': 3,
        },
        {
            'key': 'level_50',
            'name': 'Master',
            'description': 'Reach level 50',
            'icon': '⭐',
            'condition_type': 'level_reached',
            'condition_value': 50,
            'rarity': 'rare',
            'xp_reward': 1000,
            'category': categories['progression'],
            'order': 4,
        },
        {
            'key': 'level_100',
            'name': 'Legend',
            'description': 'Reach level 100',
            'icon': '⭐',
            'condition_type': 'level_reached',
            'condition_value': 100,
            'rarity': 'epic',
            'xp_reward': 2000,
            'category': categories['progression'],
            'order': 5,
        },

        # Milestone achievements
        {
            'key': 'top_10',
            'name': 'Top 10',
            'description': 'Be in the top 10 of the leaderboard',
            'icon': '🏅',
            'condition_type': 'top_rank',
            'condition_value': 10,
            'rarity': 'rare',
            'xp_reward': 500,
            'category': categories['milestones'],
            'order': 1,
        },
        {
            'key': 'top_5',
            'name': 'Top 5',
            'description': 'Be in the top 5 of the leaderboard',
            'icon': '🏅',
            'condition_type': 'top_rank',
            'condition_value': 5,
            'rarity': 'epic',
            'xp_reward': 1000,
            'category': categories['milestones'],
            'order': 2,
        },
        {
            'key': 'top_1',
            'name': 'Number One',
            'description': 'Be #1 on the leaderboard',
            'icon': '👑',
            'condition_type': 'top_rank',
            'condition_value': 1,
            'rarity': 'legendary',
            'xp_reward': 2500,
            'category': categories['milestones'],
            'order': 3,
        },
    ]

    created_count = 0
    for ach_data in achievements:
        achievement, created = Achievement.objects.get_or_create(
            key=ach_data['key'],
            defaults=ach_data
        )
        if created:
            created_count += 1
            print(f"Created achievement: {achievement.name} ({achievement.rarity})")
        else:
            print(f"Found achievement: {achievement.name}")

    return created_count


def main():
    print("=" * 60)
    print("Creating Achievement Categories and Achievements")
    print("=" * 60)

    # Create categories
    print("\n1. Creating categories...")
    categories = create_categories()

    # Create achievements
    print("\n2. Creating achievements...")
    created_count = create_achievements(categories)

    print("\n" + "=" * 60)
    print(f"Done! Created {created_count} new achievements.")
    print(f"Total achievements in database: {Achievement.objects.count()}")
    print(f"Total categories in database: {AchievementCategory.objects.count()}")
    print("=" * 60)


if __name__ == '__main__':
    main()
