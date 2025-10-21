from __future__ import annotations
from datetime import date, datetime
import re
import pytz
from rest_framework import serializers

DATE_RE_YMD = re.compile(r"^\d{2}-\d{2}-\d{4}$")  # DD-MM-YYYY
DATE_RE_MD  = re.compile(r"^\d{2}-\d{2}$")        # DD-MM

class UpcomingBirthdaysRequest(serializers.Serializer):
    discord_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False
    )
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=5)
    tz = serializers.CharField(required=False, allow_blank=True)

class SetBirthdayRequest(serializers.Serializer):
    discord_id = serializers.IntegerField(min_value=1)
    date = serializers.CharField()  # "DD-MM-YYYY" или "DD-MM"
    tz = serializers.CharField(required=False, allow_blank=True)
    enabled = serializers.BooleanField(required=False, default=True)

    def validate_date(self, s: str) -> date:
        s = s.strip()
        if DATE_RE_YMD.match(s):
            d, m, y = map(int, s.split("-"))
            return date(2000, m, d)  # сохраняем как 2000-MM-DD (год неважен)
        if DATE_RE_MD.match(s):
            d, m = map(int, s.split("-"))
            return date(2000, m, d)
        raise serializers.ValidationError("date must be 'DD-MM' or 'DD-MM-YYYY'")

    def validate_tz(self, s: str):
        s = (s or "").strip()
        if not s:
            return ""
        try:
            pytz.timezone(s)
        except Exception:
            raise serializers.ValidationError("invalid timezone")
        return s
