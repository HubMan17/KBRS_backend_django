import math
from django.db.models import Q
from rest_framework import serializers
from .models import DiscordProfile
from .services.xp import xp_needed

class DiscordProfileSerializer(serializers.ModelSerializer):
    xp_needed   = serializers.SerializerMethodField()
    position    = serializers.SerializerMethodField()
    top_percent = serializers.SerializerMethodField()

    class Meta:
        model = DiscordProfile
        fields = (
            'discord_id','username','level','xp','xp_needed',
            'birthday_date','birthday_tz','birthday_enabled','birthday_last_congrats',
            'position','top_percent',            # ⇦ новые поля
        )

    def get_xp_needed(self, obj):
        return xp_needed(obj.level)

    def get_position(self, obj):
        """
        Место в общем рейтинге при сортировке: level DESC, xp DESC.
        """
        higher = DiscordProfile.objects.filter(
            Q(level__gt=obj.level) |
            Q(level=obj.level, xp__gt=obj.xp)
        ).count()
        pos = higher + 1
        # кэшируем внутри объекта, чтобы не считать второй раз
        setattr(obj, "_position_cache", pos)
        return pos

    def get_top_percent(self, obj):
        total = DiscordProfile.objects.count() or 1
        pos = getattr(obj, "_position_cache", None)
        if pos is None:
            pos = self.get_position(obj)
        return math.ceil(pos / total * 100)

class BirthdayUpdateSerializer(serializers.Serializer):
    discord_id = serializers.IntegerField()
    username   = serializers.CharField(required=False, allow_blank=True)
    birthday_date = serializers.DateField(required=False, allow_null=True)  # null -> очищаем
    birthday_tz   = serializers.CharField(required=False)
    birthday_enabled = serializers.BooleanField(required=False)

class AddXpSerializer(serializers.Serializer):
    discord_id = serializers.IntegerField()
    username   = serializers.CharField(required=False, allow_blank=True)
    amount     = serializers.IntegerField(min_value=1)
    source     = serializers.ChoiceField(choices=['message', 'reaction', 'sticker', 'attachment', 'reply'])
    guild_id   = serializers.IntegerField(required=False, allow_null=True)
