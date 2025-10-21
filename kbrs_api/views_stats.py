# kbrs_api/views_stats.py
from datetime import timedelta
import pytz

from django.db.models import Count, Sum, Min, Max, IntegerField
from django.db.models.functions import Cast
from django.utils import timezone
from datetime import timezone as dt_timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .services.xp import xp_needed

from .models import DiscordProfile
from .models_events import MessageEvent, ReactionEvent, XpTransaction


RANGE_MAP = {
    "day":   timedelta(days=1),
    "week":  timedelta(days=7),
    "month": timedelta(days=30),
    "all":   None,
}


def _range_bounds(range_key: str, tz_name: str | None):
    range_key = (range_key or "all").lower()
    if range_key not in RANGE_MAP:
        range_key = "all"

    if RANGE_MAP[range_key] is None:
        return (None, None)

    try:
        tz = pytz.timezone(tz_name) if tz_name else dt_timezone.utc
    except Exception:
        tz = dt_timezone.utc

    now_local = timezone.now().astimezone(tz)
    start_local = now_local - RANGE_MAP[range_key]
    start_local = start_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = now_local

    start_utc = start_local.astimezone(dt_timezone.utc)
    end_utc = end_local.astimezone(dt_timezone.utc)
    return (start_utc, end_utc)


def _has_field(model, name: str) -> bool:
    return any(getattr(f, "name", None) == name for f in model._meta.get_fields())


class UserStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        GET /stats/user/?discord_id=...&range=day|week|month|all&tz=Europe/Moscow

        Ответ:
        {
          "discord_id": ...,
          "username": "...",
          "range": "week",
          "level": 5, "xp": 42, "xp_needed": 225,

          "messages_total": 123,
          "stickers_sent": 7,
          "attachments_sent": 15,
          "words_total": 2500,
          "chars_total": 14000 | null,
          "channels_used": 8,

          "reactions_given": 40,
          "reactions_received": 55,

          "emoji_in_messages": 12,          # если есть поле emoji_count
          "mentions_made": 5,               # если есть поле mention_cnt
          "links_shared": 3,                 # если есть поле link_count
          "replies_made": 10,                # если есть поле is_reply (bool)

          "top_emoji_given": [{"emoji_key":"😂","count":10}, ...],
          "first_seen": "2025-10-01T12:34:56Z",
          "last_seen": "2025-10-19T12:00:00Z"
        }
        """
        # --- валидируем вход ---
        try:
            discord_id = int(request.query_params.get("discord_id"))
        except (TypeError, ValueError):
            return Response({"detail": "discord_id is required and must be int"},
                            status=status.HTTP_400_BAD_REQUEST)

        range_key = (request.query_params.get("range") or "all").lower()
        tz_name = request.query_params.get("tz")
        start, end = _range_bounds(range_key, tz_name)

        try:
            prof = DiscordProfile.objects.get(discord_id=discord_id)
        except DiscordProfile.DoesNotExist:
            return Response({"detail": "profile not found"}, status=status.HTTP_404_NOT_FOUND)

        # --- базовые кверисеты за период ---
        msg_qs = MessageEvent.objects.filter(author_id=discord_id)
        react_given_qs = ReactionEvent.objects.filter(reactor_id=discord_id)
        react_recv_qs = ReactionEvent.objects.filter(author_id=discord_id)

        if start and end:
            msg_qs = msg_qs.filter(created_at__gte=start, created_at__lte=end)
            react_given_qs = react_given_qs.filter(created_at__gte=start, created_at__lte=end)
            react_recv_qs = react_recv_qs.filter(created_at__gte=start, created_at__lte=end)

        # --- агрегаты по сообщениям (устойчиво к отсутствующим полям) ---
        aggr_kwargs = {
            "messages_total": Count("id"),
            "first_seen": Min("created_at"),
            "last_seen": Max("created_at"),
        }

        # слова/символы
        if _has_field(MessageEvent, "words"):
            aggr_kwargs["words_total"] = Sum("words")
        else:
            aggr_kwargs["words_total"] = Sum("id") * 0  # 0, если поля нет

        if _has_field(MessageEvent, "chars"):
            aggr_kwargs["chars_total"] = Sum("chars")
        # если поля нет — просто не добавляем, вернём None ниже

        # эмодзи в сообщениях (сумма по полю emoji_count)
        if _has_field(MessageEvent, "emoji_count"):
            aggr_kwargs["emoji_in_messages"] = Sum("emoji_count")

        # булевы флаги → считаем как 1/0
        if _has_field(MessageEvent, "has_sticker"):
            aggr_kwargs["stickers_sent"] = Sum(Cast("has_sticker", IntegerField()))
        else:
            aggr_kwargs["stickers_sent"] = Sum("id") * 0

        if _has_field(MessageEvent, "has_attach"):
            aggr_kwargs["attachments_sent"] = Sum(Cast("has_attach", IntegerField()))
        else:
            aggr_kwargs["attachments_sent"] = Sum("id") * 0

        # опциональные метрики, если есть соответствующие поля
        if _has_field(MessageEvent, "mention_cnt"):
            aggr_kwargs["mentions_made"] = Sum("mention_cnt")
        if _has_field(MessageEvent, "link_count"):
            aggr_kwargs["links_shared"] = Sum("link_count")
        if _has_field(MessageEvent, "is_reply"):
            aggr_kwargs["replies_made"] = Sum(Cast("is_reply", IntegerField()))

        msg_aggr = msg_qs.aggregate(**aggr_kwargs)
        channels_used = msg_qs.values("channel_id").distinct().count()

        # --- реакции ---
        given_cnt = react_given_qs.count()
        recv_cnt = react_recv_qs.count()

        top_emoji = (
            react_given_qs.values("emoji_key")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")[:5]
        )
        top_emoji_list = [{"emoji_key": r["emoji_key"], "count": r["cnt"]} for r in top_emoji]

        def _zero(v): return int(v or 0)

        need = int(xp_needed(prof.level))        # сколько нужно на текущем уровне
        curr_xp = int(prof.xp)
        to_next = max(0, need - curr_xp)

        payload = {
            "discord_id": prof.discord_id,
            "username": prof.username,
            "range": range_key,
            "level": prof.level,
            "xp": prof.xp,
            "xp_needed": need,                   # <<< ТЕПЕРЬ НЕ None
            "to_next": to_next,

            "messages_total": _zero(msg_aggr.get("messages_total")),
            "stickers_sent": _zero(msg_aggr.get("stickers_sent")),
            "attachments_sent": _zero(msg_aggr.get("attachments_sent")),
            "words_total": _zero(msg_aggr.get("words_total")),
            "chars_total": _zero(msg_aggr.get("chars_total")) if "chars_total" in msg_aggr else None,
            "channels_used": channels_used,

            "emoji_in_messages": _zero(msg_aggr.get("emoji_in_messages")),
            "mentions_made": _zero(msg_aggr.get("mentions_made")),
            "links_shared": _zero(msg_aggr.get("links_shared")),
            "replies_made": _zero(msg_aggr.get("replies_made")),

            "reactions_given": given_cnt,
            "reactions_received": recv_cnt,

            "top_emoji_given": top_emoji_list,
            "first_seen": msg_aggr.get("first_seen"),
            "last_seen": msg_aggr.get("last_seen"),
        }
        return Response(payload, status=status.HTTP_200_OK)

class ServerHighlightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            guild_id = int(request.query_params.get("guild_id"))
        except (TypeError, ValueError):
            return Response({"detail": "guild_id is required and must be int"}, status=status.HTTP_400_BAD_REQUEST)

        range_key = (request.query_params.get("range") or "day").lower()
        tz_name   = request.query_params.get("tz")
        start, end = _range_bounds(range_key, tz_name)

        msgs = MessageEvent.objects.filter(guild_id=guild_id)
        reacts = ReactionEvent.objects.filter(guild_id=guild_id)
        xps = XpTransaction.objects.filter(guild_id=guild_id)

        if start and end:
            msgs = msgs.filter(created_at__gte=start, created_at__lte=end)
            reacts = reacts.filter(created_at__gte=start, created_at__lte=end)
            xps = xps.filter(created_at__gte=start, created_at__lte=end)

        messages_total = msgs.count()
        active_users = msgs.values("author_id").distinct().count()

        top_senders = list(
            msgs.values("author_id").annotate(count=Count("id")).order_by("-count")[:5]
        )
        top_reactors = list(
            reacts.values("reactor_id").annotate(count=Count("id")).order_by("-count")[:5]
        )
        top_received = list(
            reacts.values("author_id").annotate(count=Count("id")).order_by("-count")[:5]
        )
        top_emoji = list(
            reacts.values("emoji_key").annotate(count=Count("id")).order_by("-count")[:5]
        )
        xp_rows = (
            xps.values("user__discord_id")
            .annotate(amount=Sum("amount"))
            .order_by("-amount")[:5]
        )
        xp_earners = [
            {"discord_id": int(r["user__discord_id"]), "amount": int(r["amount"])}
            for r in xp_rows
        ]
        noisy_ch = msgs.values("channel_id").annotate(c=Count("id")).order_by("-c").first()

        return Response({
            "range": range_key,
            "messages_total": messages_total,
            "active_users": active_users,
            "top_senders": top_senders,       # [{author_id, count}]
            "top_reactors": top_reactors,     # [{reactor_id, count}]
            "top_received": top_received,     # [{author_id, count}]
            "top_emoji": top_emoji,           # [{emoji_key, count}]
            "xp_earners": xp_earners,         # [{user_id, amount}]
            "noisy_channel_id": noisy_ch["channel_id"] if noisy_ch else None
        }, status=status.HTTP_200_OK)