# kbrs_api/admin.py
from datetime import timedelta
from django.contrib import admin
from django.utils.timezone import now
from django.db.models import Q

from .models import DiscordProfile
from .models_events import MessageEvent, ReactionEvent, EmojiUsage, XpTransaction


# -------------------- DiscordProfile --------------------

@admin.register(DiscordProfile)
class DiscordProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "username",
        "discord_id",
        "level",
        "xp",
        "messages_30d",
        "reactions_by_30d",
        "emojis_30d",
        "last_msg_xp_at",
        "birthday_date",
        "birthday_enabled",
        "birthday_tz",
        "created_at",
    )
    list_display_links = ("username", "discord_id")
    search_fields = ("username", "discord_id")
    list_filter = ("birthday_enabled", "birthday_tz", "created_at", "updated_at")
    date_hierarchy = "created_at"
    ordering = ("-level", "-xp", "-id")
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 50

    actions = ("enable_bday", "disable_bday")

    @admin.action(description="Включить поздравления с ДР")
    def enable_bday(self, request, qs):
        n = qs.update(birthday_enabled=True)
        self.message_user(request, f"Обновлено профилей: {n}")

    @admin.action(description="Отключить поздравления с ДР")
    def disable_bday(self, request, qs):
        n = qs.update(birthday_enabled=False)
        self.message_user(request, f"Обновлено профилей: {n}")

    # Метрики за 30 дней. Поля в событиях:
    # MessageEvent.author_id, ReactionEvent.reactor_id, EmojiUsage.sender_id, created_at везде есть.
    def _since(self):
        return now() - timedelta(days=30)

    def messages_30d(self, obj):
        return MessageEvent.objects.filter(
            author_id=obj.discord_id,
            created_at__gte=self._since()
        ).count()
    messages_30d.short_description = "Сообщений (30д)"

    def reactions_by_30d(self, obj):
        return ReactionEvent.objects.filter(
            reactor_id=obj.discord_id,
            created_at__gte=self._since()
        ).count()
    reactions_by_30d.short_description = "Реакций поставлено (30д)"

    def emojis_30d(self, obj):
        return EmojiUsage.objects.filter(
            sender_id=obj.discord_id,
            created_at__gte=self._since()
        ).count()
    emojis_30d.short_description = "Эмодзи/стикеров (30д)"


# -------------------- XpTransaction --------------------

@admin.register(XpTransaction)
class XpTransactionAdmin(admin.ModelAdmin):
    # Модель имеет поля: user(FK->DiscordProfile, nullable), guild_id, source, amount, created_at
    list_display = ("id", "user", "guild_id", "amount", "source", "created_at")
    list_filter  = ("source", "created_at", "user")
    search_fields = (
        "guild_id",
        "user__username",
        "user__discord_id",
        "source",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")
    autocomplete_fields = ("user",)


# -------------------- Справочные модели (для просмотра) --------------------

@admin.register(MessageEvent)
class MessageEventAdmin(admin.ModelAdmin):
    list_display = (
        "id", "guild_id", "channel_id", "author_id",
        "words", "chars", "has_attach", "has_sticker",
        "emoji_count", "link_count", "mention_cnt",
        "created_at",
    )
    search_fields = ("guild_id", "channel_id", "author_id", "message_id")
    list_filter = ("has_attach", "has_sticker", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")
    list_per_page = 50


@admin.register(ReactionEvent)
class ReactionEventAdmin(admin.ModelAdmin):
    list_display = (
        "id", "guild_id", "channel_id", "message_id",
        "reactor_id", "author_id", "emoji_key", "created_at",
    )
    search_fields = ("guild_id", "channel_id", "message_id", "reactor_id", "author_id", "emoji_key")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")
    list_per_page = 50


@admin.register(EmojiUsage)
class EmojiUsageAdmin(admin.ModelAdmin):
    list_display = ("id", "guild_id", "message_id", "sender_id", "key", "count", "created_at")
    search_fields = ("guild_id", "message_id", "sender_id", "key")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")
    list_per_page = 50
