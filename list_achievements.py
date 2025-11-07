"""List all achievements."""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from kbrs_api.models_achievements import Achievement, AchievementCategory

print("=" * 80)
print("CURRENT ACHIEVEMENTS")
print("=" * 80)

categories = AchievementCategory.objects.all().order_by('order')

for category in categories:
    achievements = Achievement.objects.filter(category=category).order_by('order', 'condition_value')

    if achievements.exists():
        print(f"\n{category.icon} {category.name}:")
        print("-" * 60)

        for ach in achievements:
            print(f"  {ach.icon} {ach.name} ({ach.rarity})")
            print(f"     {ach.description}")
            print(f"     Target: {ach.condition_value} | Reward: {ach.xp_reward} XP")

# Show easiest achievements
print("\n" + "=" * 80)
print("EASIEST ACHIEVEMENTS (lowest condition_value):")
print("=" * 80)

easiest = Achievement.objects.all().order_by('condition_value', 'xp_reward')[:5]
for i, ach in enumerate(easiest, 1):
    print(f"{i}. {ach.icon} {ach.name} - {ach.description}")
    print(f"   Type: {ach.get_condition_type_display()} = {ach.condition_value}")
    print(f"   Reward: {ach.xp_reward} XP")
    print()

print("=" * 80)
print(f"Total achievements: {Achievement.objects.count()}")
print("=" * 80)
