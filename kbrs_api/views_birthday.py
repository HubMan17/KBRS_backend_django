from __future__ import annotations
from datetime import datetime
from datetime import timezone as dt_timezone

import pytz
from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import DiscordProfile
from .serializers_birthday import UpcomingBirthdaysRequest, SetBirthdayRequest
from .utils_birthday import normalize_birthday_date, next_birthday_after, days_until

class UpcomingBirthdaysView(APIView):
    """
    POST /api/v1/birthdays/upcoming/
    {
      "discord_ids": [ ... guild member ids ... ],
      "limit": 5,
      "tz": "Asia/Tokyo"   // опционально
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = UpcomingBirthdaysRequest(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        ids = data["discord_ids"]
        limit = data["limit"]
        tz_name = data.get("tz") or "UTC"

        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = dt_timezone.utc

        today_local = timezone.now().astimezone(tz).date()

        profiles = (
            DiscordProfile.objects
            .filter(discord_id__in=ids, birthday_enabled=True)
            .exclude(birthday_date__isnull=True)
            .only("discord_id", "username", "birthday_date", "birthday_tz")
        )

        rows = []
        for p in profiles:
            md = normalize_birthday_date(p.birthday_date)
            next_dt = next_birthday_after(today_local, md)
            left = days_until(today_local, next_dt)
            rows.append({
                "discord_id": p.discord_id,
                "username": p.username,
                "birthday_date": p.birthday_date.isoformat(),
                "next_occurrence": next_dt.isoformat(),
                "days_left": left,
            })

        rows.sort(key=lambda r: (r["days_left"], r["discord_id"]))
        return Response({"items": rows[:limit]}, status=status.HTTP_200_OK)


class SetBirthdayView(APIView):
    """
    POST /api/v1/birthdays/set/
    {
      "discord_id": 123,
      "date": "YYYY-MM-DD" или "MM-DD",
      "tz": "Asia/Tokyo",        // опционально
      "enabled": true            // опционально
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = SetBirthdayRequest(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        discord_id = v["discord_id"]
        bday_md = v["date"]          # уже date(2000, m, d) после validate_date
        tz_name = v.get("tz") or ""
        enabled = v.get("enabled", True)

        prof, _ = DiscordProfile.objects.get_or_create(discord_id=discord_id)
        prof.birthday_date = bday_md           # хранится как DateField с «фиктивным» годом 2000
        if tz_name:
            prof.birthday_tz = tz_name
        prof.birthday_enabled = enabled
        prof.save(update_fields=["birthday_date", "birthday_tz", "birthday_enabled"])

        return Response({
            "discord_id": prof.discord_id,
            "username": prof.username,
            "birthday_date": prof.birthday_date.isoformat(),
            "birthday_tz": prof.birthday_tz,
            "birthday_enabled": prof.birthday_enabled,
        }, status=status.HTTP_200_OK)
