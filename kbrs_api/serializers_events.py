from rest_framework import serializers

class MessageEventIn(serializers.Serializer):
    guild_id    = serializers.IntegerField()
    channel_id  = serializers.IntegerField()
    message_id  = serializers.IntegerField()
    author_id   = serializers.IntegerField()
    words       = serializers.IntegerField()
    chars       = serializers.IntegerField()
    has_attach  = serializers.BooleanField()
    has_sticker = serializers.BooleanField()
    is_reply    = serializers.BooleanField()
    emoji_count = serializers.IntegerField()
    link_count  = serializers.IntegerField()
    mention_cnt = serializers.IntegerField()
    created_at  = serializers.DateTimeField()

class ReactionEventIn(serializers.Serializer):
    guild_id    = serializers.IntegerField()
    channel_id  = serializers.IntegerField()
    message_id  = serializers.IntegerField()
    reactor_id  = serializers.IntegerField()
    author_id   = serializers.IntegerField(allow_null=True, required=False)
    emoji_key   = serializers.CharField(max_length=128)
    created_at  = serializers.DateTimeField()

class EmojiUsageIn(serializers.Serializer):
    guild_id    = serializers.IntegerField()
    message_id  = serializers.IntegerField()
    sender_id   = serializers.IntegerField()
    key         = serializers.CharField(max_length=128)
    count       = serializers.IntegerField()
    created_at  = serializers.DateTimeField()

class XpTransactionIn(serializers.Serializer):
    guild_id    = serializers.IntegerField()
    user_id     = serializers.IntegerField()
    source      = serializers.CharField(max_length=32)
    amount      = serializers.IntegerField()
    created_at  = serializers.DateTimeField()
    level_before = serializers.IntegerField(required=False, allow_null=True)
    xp_before    = serializers.IntegerField(required=False, allow_null=True)
    level_after  = serializers.IntegerField(required=False, allow_null=True)
    xp_after     = serializers.IntegerField(required=False, allow_null=True)
    leveled_up   = serializers.BooleanField(required=False)

class BulkWrap(serializers.Serializer):
    events = serializers.ListField(child=serializers.DictField(), allow_empty=False)
