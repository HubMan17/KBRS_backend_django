"""Add 'First Message' achievement."""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from kbrs_api.models_achievements import Achievement, AchievementCategory

# Get Social category
social = AchievementCategory.objects.get(name='Social')

# Create First Message achievement
achievement, created = Achievement.objects.get_or_create(
    key='first_message',
    defaults={
        'name': 'First Message',
        'description': 'Send your first message',
        'icon': '✍️',
        'condition_type': 'message_count',
        'condition_value': 1,
        'rarity': 'common',
        'xp_reward': 25,
        'category': social,
        'order': 1,
    }
)

if created:
    print(f"Created: {achievement.icon} {achievement.name}")
    print(f"  {achievement.description}")
    print(f"  Reward: {achievement.xp_reward} XP")
    print(f"  Rarity: {achievement.rarity}")
else:
    print(f"Achievement '{achievement.name}' already exists")

print(f"\nTotal achievements: {Achievement.objects.count()}")
