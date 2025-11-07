"""
Celery tasks for achievement checking and notifications.

Tasks:
- check_all_achievements: Periodic task to check all achievements for all users
- check_user_achievements: Check achievements for a specific user (triggered by events)
- send_achievement_notifications: Send Discord notifications for unlocked achievements
"""

import os
import requests
from typing import List, Dict, Any
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from kbrs_api.services.achievements import AchievementEngine, AchievementNotifier
from kbrs_api.models import UserAchievement, DiscordProfile


# Discord configuration
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or getattr(settings, "DISCORD_BOT_TOKEN", "")
ACHIEVEMENT_CHANNEL_ID = int(os.getenv("ACHIEVEMENT_CHANNEL_ID", getattr(settings, "ACHIEVEMENT_CHANNEL_ID", "0")))

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN not configured")


def _send_discord_embed(channel_id: int, embed_data: Dict[str, Any], token: str):
    """Send embed message to Discord channel."""
    if not channel_id:
        print("[Achievement] No channel ID configured, skipping notification")
        return

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}"}

    try:
        resp = requests.post(
            url,
            json={"embeds": [embed_data]},
            headers=headers,
            timeout=15
        )

        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            print(f"[Achievement] Discord API error: status={resp.status_code}, detail={detail}")
            resp.raise_for_status()

        return resp.json()

    except requests.RequestException as e:
        print(f"[Achievement] Failed to send Discord notification: {e}")
        raise


@shared_task(bind=True, max_retries=3)
def check_all_achievements(self, achievement_key: str = None):
    """
    Check achievements for all users.

    This task runs periodically (e.g., every 10 minutes) to check
    all enabled achievements for all users.

    Args:
        achievement_key: Optional specific achievement to check.
                        If None, checks all achievements.

    Returns:
        Dict with stats: {'checked': N, 'unlocked': M}
    """
    try:
        engine = AchievementEngine()
        stats = engine.check_all_users(achievement_key=achievement_key)

        print(f"[Achievement] Checked {stats['checked']} achievement conditions, "
              f"unlocked {stats['unlocked']} new achievements")

        # Trigger notification task if any achievements were unlocked
        if stats['unlocked'] > 0:
            send_achievement_notifications.delay()

        return stats

    except Exception as exc:
        print(f"[Achievement] Error checking achievements: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def check_user_achievements(self, discord_id: int, trigger_event: str = None):
    """
    Check achievements for a specific user.

    This task is triggered by Discord bot events (e.g., message sent,
    reaction added) to immediately check relevant achievements.

    Args:
        discord_id: Discord user ID
        trigger_event: Event that triggered the check (for logging)

    Returns:
        List of newly unlocked achievement data
    """
    try:
        engine = AchievementEngine()
        newly_unlocked = engine.check_user_achievements(discord_id)

        if newly_unlocked:
            print(f"[Achievement] User {discord_id} unlocked {len(newly_unlocked)} achievements "
                  f"(trigger: {trigger_event or 'manual'})")

            # Send notifications for newly unlocked achievements
            send_achievement_notifications.delay()

        return [
            {
                'achievement_key': data['achievement'].key,
                'achievement_name': data['achievement'].name,
                'xp_reward': data['xp_reward'],
            }
            for data in newly_unlocked
        ]

    except Exception as exc:
        print(f"[Achievement] Error checking user {discord_id} achievements: {exc}")
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=5)
def send_achievement_notifications(self):
    """
    Send Discord notifications for unlocked achievements.

    This task fetches all achievements that have been unlocked but not
    yet notified, creates Discord embeds, and sends them to the
    achievement announcement channel.

    Returns:
        Dict with stats: {'sent': N, 'failed': M}
    """
    try:
        notifier = AchievementNotifier(channel_id=ACHIEVEMENT_CHANNEL_ID)
        pending = notifier.get_pending_notifications()

        stats = {'sent': 0, 'failed': 0}

        for user_achievement in pending:
            try:
                # Create embed data
                embed_data = notifier.create_embed_data(user_achievement)

                # Send to Discord
                _send_discord_embed(
                    ACHIEVEMENT_CHANNEL_ID,
                    embed_data,
                    DISCORD_TOKEN
                )

                # Mark as notified
                notifier.mark_as_notified(user_achievement)
                stats['sent'] += 1

                print(f"[Achievement] Notified {user_achievement.profile.username} "
                      f"for achievement '{user_achievement.achievement.name}'")

            except requests.RequestException as e:
                print(f"[Achievement] Failed to notify achievement {user_achievement.id}: {e}")
                stats['failed'] += 1
                # Don't mark as notified if sending failed, will retry later

            except Exception as e:
                print(f"[Achievement] Unexpected error notifying achievement {user_achievement.id}: {e}")
                stats['failed'] += 1

        if stats['sent'] > 0:
            print(f"[Achievement] Notification batch complete: {stats['sent']} sent, {stats['failed']} failed")

        return stats

    except Exception as exc:
        print(f"[Achievement] Error in notification task: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def check_specific_achievement(achievement_key: str):
    """
    Check a specific achievement for all users.

    Useful for manually triggering checks or testing.

    Args:
        achievement_key: Key of the achievement to check

    Returns:
        Dict with stats: {'checked': N, 'unlocked': M}
    """
    return check_all_achievements(achievement_key=achievement_key)


@shared_task
def recalculate_achievement_progress(discord_id: int = None):
    """
    Recalculate achievement progress for user(s).

    This resets progress and rechecks all achievements from scratch.
    Useful for fixing inconsistencies or after achievement condition changes.

    Args:
        discord_id: Specific user to recalculate. If None, recalculates all users.

    Returns:
        Dict with stats: {'users_processed': N, 'achievements_updated': M}
    """
    from kbrs_api.models import Achievement

    engine = AchievementEngine()
    stats = {'users_processed': 0, 'achievements_updated': 0}

    try:
        # Get users to process
        if discord_id:
            profiles = DiscordProfile.objects.filter(discord_id=discord_id)
        else:
            profiles = DiscordProfile.objects.all()

        achievements = Achievement.objects.filter(enabled=True)

        for profile in profiles:
            for achievement in achievements:
                try:
                    # Get checker function
                    checker_func = engine.checkers.get(achievement.condition_type)
                    if not checker_func:
                        continue

                    # Calculate current value
                    current_value = checker_func(profile, achievement)

                    # Update or create user achievement record
                    user_achievement, created = UserAchievement.objects.get_or_create(
                        profile=profile,
                        achievement=achievement,
                        defaults={'progress': current_value}
                    )

                    if not created and user_achievement.progress != current_value:
                        user_achievement.progress = current_value

                        # Check if should be unlocked
                        if not user_achievement.unlocked and current_value >= achievement.condition_value:
                            user_achievement.unlocked = True
                            user_achievement.unlocked_at = timezone.now()

                            # Award XP
                            if achievement.xp_reward > 0:
                                profile.xp += achievement.xp_reward
                                profile.save(update_fields=['xp'])

                        user_achievement.save()
                        stats['achievements_updated'] += 1

                except Exception as e:
                    print(f"[Achievement] Error recalculating {achievement.key} for user {profile.discord_id}: {e}")

            stats['users_processed'] += 1

        print(f"[Achievement] Recalculation complete: {stats['users_processed']} users, "
              f"{stats['achievements_updated']} achievements updated")

        # Send notifications for any newly unlocked achievements
        if stats['achievements_updated'] > 0:
            send_achievement_notifications.delay()

        return stats

    except Exception as e:
        print(f"[Achievement] Error in recalculation task: {e}")
        raise
