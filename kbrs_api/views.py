from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.db import transaction
from .serializers import DiscordProfileSerializer, AddXpSerializer
from .services.xp import apply_xp, xp_needed
from rest_framework.permissions import IsAuthenticated
from .serializers import BirthdayUpdateSerializer

from .models import DiscordProfile
from .models_events import XpTransaction

class RankView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DiscordProfileSerializer
    lookup_field = 'discord_id'
    queryset = DiscordProfile.objects.all()

class TopView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DiscordProfileSerializer

    def get_queryset(self):
        limit = int(self.request.query_params.get('limit', 10))
        return DiscordProfile.objects.order_by('-level', '-xp')[:max(1, min(limit, 50))]

class AddXpView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        ser = AddXpSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        
        discord_id = data['discord_id']
        username = data.get('username', '')
        amount = data['amount']
        source = data['source']
        guild_id = data.get('guild_id')  # может быть None

        profile, _ = DiscordProfile.objects.select_for_update().get_or_create(
            discord_id=discord_id,
            defaults={'username': username}
        )
        if username and profile.username != username:
            profile.username = username

        result = apply_xp(profile, amount)
        profile.save()

        level = profile.level
        xp    = profile.xp
        need  = xp_needed(profile.level)

        # история XP — вот этого раньше не было
        XpTransaction.objects.create(
            guild_id=guild_id,
            user=profile,
            source=source,
            amount=amount,
        )

        # возвращаем и need, и xp_needed (совместимость с клиентом)
        return Response({
            'discord_id': profile.discord_id,
            'username':   profile.username,
            'level':      level,
            'xp':         xp,
            'need':       need,
            'xp_needed':  need,
            'leveled_up': result.leveled_up,
        }, status=status.HTTP_200_OK)

class SyncMembersView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Body: {"members":[{"discord_id":123,"username":"Name"}, ...]}"""
        members = request.data.get('members', [])
        added = 0
        for m in members:
            did = int(m['discord_id'])
            uname = m.get('username', '')
            obj, created = DiscordProfile.objects.get_or_create(
                discord_id=did,
                defaults={'username': uname}
            )
            if not created and uname and obj.username != uname:
                obj.username = uname
                obj.save(update_fields=['username'])
            added += int(created)
        return Response({'added': added}, status=200)

class BirthdayUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Upsert birthday data for a user.
        Body example:
        {
          "discord_id": 123,
          "username": "John",
          "birthday_date": "2001-10-17",
          "birthday_tz": "Europe/Moscow",
          "birthday_enabled": true
        }
        """
        ser = BirthdayUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        profile, _ = DiscordProfile.objects.select_for_update().get_or_create(
            discord_id=data['discord_id'],
            defaults={'username': data.get('username', '')}
        )

        if 'username' in data and data['username'] is not None:
            profile.username = data['username']
        if 'birthday_date' in data:
            profile.birthday_date = data['birthday_date']  # может быть None -> чистим дату
        if 'birthday_tz' in data and data['birthday_tz']:
            profile.birthday_tz = data['birthday_tz']
        if 'birthday_enabled' in data:
            profile.birthday_enabled = data['birthday_enabled']

        profile.save()
        return Response({"ok": True}, status=status.HTTP_200_OK)