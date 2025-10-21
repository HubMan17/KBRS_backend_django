from django.db import models


class XpTransaction(models.Model):
    guild_id   = models.BigIntegerField(null=True, blank=True, db_index=True)
    user       = models.ForeignKey(
        'kbrs_api.DiscordProfile',
        on_delete=models.CASCADE,
        related_name='xp_tx',
        null=True,       # ← вот это добавь
        blank=True       # ← и это
    )
    source     = models.CharField(max_length=32)
    amount     = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class MessageEvent(models.Model):
    guild_id    = models.BigIntegerField(db_index=True)
    channel_id  = models.BigIntegerField(db_index=True)
    message_id  = models.BigIntegerField(unique=True)
    author_id   = models.BigIntegerField(db_index=True)

    words       = models.IntegerField(default=0)
    chars       = models.IntegerField(default=0)
    has_attach  = models.BooleanField(default=False)
    has_sticker = models.BooleanField(default=False)
    is_reply    = models.BooleanField(default=False)
    emoji_count = models.IntegerField(default=0)
    link_count  = models.IntegerField(default=0)
    mention_cnt = models.IntegerField(default=0)

    created_at  = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["guild_id", "author_id", "-created_at"]),
            models.Index(fields=["guild_id", "channel_id", "-created_at"]),
        ]


class ReactionEvent(models.Model):
    guild_id    = models.BigIntegerField(db_index=True)
    channel_id  = models.BigIntegerField(db_index=True)
    message_id  = models.BigIntegerField(db_index=True)
    reactor_id  = models.BigIntegerField(db_index=True)
    author_id   = models.BigIntegerField(null=True, blank=True, db_index=True)  # автор сообщения, если знаем
    emoji_key   = models.CharField(max_length=128, db_index=True)  # 😀 или name:id / a:name:id
    created_at  = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["guild_id", "reactor_id", "-created_at"]),
            models.Index(fields=["guild_id", "emoji_key", "-created_at"]),
        ]


class EmojiUsage(models.Model):
    """
    Единичная запись об использовании эмодзи/стикера В СООБЩЕНИИ.
    Для эмодзи: key = unicode-символ (😀) или '<:name:id>' / '<a:name:id>'.
    Для стикера: key = 'sticker:<sticker_id>'.
    """
    guild_id    = models.BigIntegerField(db_index=True)
    message_id  = models.BigIntegerField(db_index=True)
    sender_id   = models.BigIntegerField(db_index=True)
    key         = models.CharField(max_length=128, db_index=True)
    count       = models.IntegerField(default=1)
    created_at  = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["guild_id", "sender_id", "key", "-created_at"]),
        ]