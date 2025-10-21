from rest_framework import serializers

class TokenExchangeIn(serializers.Serializer):
    code = serializers.CharField(required=True, trim_whitespace=True)

class TokenExchangeOut(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField()
    refresh_token = serializers.CharField(required=False, allow_blank=True)
    scope = serializers.CharField()

class NotifyIn(serializers.Serializer):
    channel_id = serializers.CharField()
    username = serializers.CharField()
    user_id = serializers.CharField()