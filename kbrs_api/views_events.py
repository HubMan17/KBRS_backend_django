from django.utils.dateparse import parse_datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models_events import MessageEvent, ReactionEvent, EmojiUsage, XpTransaction
from .serializers_events import (
    BulkWrap, MessageEventIn, ReactionEventIn, EmojiUsageIn, XpTransactionIn
)

def _parse_bulk(serializer_cls, items):
    ser = serializer_cls(data=items, many=True)
    ser.is_valid(raise_exception=True)
    return ser.validated_data

def _dt(s):
    # DRF уже сконвертил в datetime, но если хочешь защиту:
    if hasattr(s, "isoformat"):
        return s
    return parse_datetime(s)

class MessageEventBulk(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        wrap = BulkWrap(data=request.data); wrap.is_valid(raise_exception=True)
        items = _parse_bulk(MessageEventIn, wrap.validated_data["events"])
        objs = [
            MessageEvent(
                guild_id=i["guild_id"], channel_id=i["channel_id"], message_id=i["message_id"],
                author_id=i["author_id"], words=i["words"], chars=i["chars"],
                has_attach=i["has_attach"], has_sticker=i["has_sticker"], is_reply=i["is_reply"],
                emoji_count=i["emoji_count"], link_count=i["link_count"], mention_cnt=i["mention_cnt"],
                created_at=_dt(i["created_at"])
            )
            for i in items
        ]
        MessageEvent.objects.bulk_create(objs, ignore_conflicts=True, batch_size=500)
        return Response({"saved": len(objs)}, status=status.HTTP_201_CREATED)

class ReactionEventBulk(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        wrap = BulkWrap(data=request.data); wrap.is_valid(raise_exception=True)
        items = _parse_bulk(ReactionEventIn, wrap.validated_data["events"])
        objs = [
            ReactionEvent(
                guild_id=i["guild_id"], channel_id=i["channel_id"], message_id=i["message_id"],
                reactor_id=i["reactor_id"], author_id=i.get("author_id"),
                emoji_key=i["emoji_key"], created_at=_dt(i["created_at"])
            )
            for i in items
        ]
        ReactionEvent.objects.bulk_create(objs, ignore_conflicts=True, batch_size=500)
        return Response({"saved": len(objs)}, status=status.HTTP_201_CREATED)

class EmojiUsageBulk(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        wrap = BulkWrap(data=request.data); wrap.is_valid(raise_exception=True)
        items = _parse_bulk(EmojiUsageIn, wrap.validated_data["events"])
        objs = [
            EmojiUsage(
                guild_id=i["guild_id"], message_id=i["message_id"], sender_id=i["sender_id"],
                key=i["key"], count=i["count"], created_at=_dt(i["created_at"])
            )
            for i in items
        ]
        EmojiUsage.objects.bulk_create(objs, ignore_conflicts=True, batch_size=500)
        return Response({"saved": len(objs)}, status=status.HTTP_201_CREATED)

class XpTransactionBulk(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        wrap = BulkWrap(data=request.data); wrap.is_valid(raise_exception=True)
        items = _parse_bulk(XpTransactionIn, wrap.validated_data["events"])
        objs = [
            XpTransaction(
                guild_id=i["guild_id"], user_id=i["user_id"], source=i["source"], amount=i["amount"],
                created_at=_dt(i["created_at"]),
                level_before=i.get("level_before"), xp_before=i.get("xp_before"),
                level_after=i.get("level_after"), xp_after=i.get("xp_after"),
                leveled_up=i.get("leveled_up", False),
            )
            for i in items
        ]
        XpTransaction.objects.bulk_create(objs, ignore_conflicts=False, batch_size=500)
        return Response({"saved": len(objs)}, status=status.HTTP_201_CREATED)
