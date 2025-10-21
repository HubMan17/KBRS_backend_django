import base64
import logging
import os
from django.conf import settings
from dotenv import load_dotenv
import httpx
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.permissions import AllowAny

from kbrs_api.serializers_f.serializers import TokenExchangeIn, TokenExchangeOut, NotifyIn
from kbrs_api.services.discord import exchange_code_for_token, get_me, post_channel_message

load_dotenv()

log = logging.getLogger(__name__)

bot_token = os.getenv("DISCORD_BOT_TOKEN")

API_BASE = getattr(settings, "DISCORD_API_BASE", "https://discord.com/api").rstrip("/")

def _basic_auth_header(cid: str, secret: str) -> str:
    return "Basic " + base64.b64encode(f"{cid}:{secret}".encode("utf-8")).decode("ascii")

@method_decorator(csrf_exempt, name="dispatch")
class TokenExchangeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = (request.data or {}).get("code")
        if not code:
            return Response({"error": "missing_code"}, status=400)

        cid = getattr(settings, "DISCORD_CLIENT_ID", None)
        secret = getattr(settings, "DISCORD_CLIENT_SECRET", None)
        if not cid or not secret:
            return Response({"error": "missing_client_credentials"}, status=500)

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cid,
            "client_secret": secret,   # <— в ТЕЛЕ, не в Authorization
            # НЕ добавляем redirect_uri (ты его не указывал в authorize)
        }

        try:
            with httpx.Client(timeout=10) as client:
                r = client.post(f"{API_BASE}/oauth2/token", headers=headers, data=data)
                r.raise_for_status()
                token = r.json()
        except httpx.HTTPStatusError as e:
            return Response({"error": "token_exchange_failed", "status": e.response.status_code, "detail": e.response.text}, status=400)
        except Exception as e:
            return Response({"error": "token_exchange_failed", "detail": str(e)}, status=400)

        # подтянем профиль для фронта
        try:
            with httpx.Client(timeout=10) as client:
                me = client.get(
                    f"{API_BASE}/users/@me",
                    headers={"Authorization": f"{token.get('token_type', 'Bearer')} {token['access_token']}"},
                )
                me.raise_for_status()
                token["_me"] = me.json()
        except Exception as e:
            token["_me_error"] = str(e)

        return Response(token, status=200)

@method_decorator(csrf_exempt, name="dispatch")
class NotifyAuthorizedView(APIView):
    """
    POST /api/v1/discord/notify
    {
        "channel_id": "1429122099234213939",
        "username": "🇷🇺 ONE 🇰🇷",
        "user_id": "123456789012345678"
    }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        channel_id = data.get("channel_id")
        username = data.get("username")
        user_id = data.get("user_id")

        if not (channel_id and username and user_id):
            return Response(
                {"error": "missing_params"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        if not bot_token:
            return Response(
                {"error": "missing_bot_token"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Формируем сообщение (UTF-8 безопасно)
        content = f"✅ User **{username}** (`{user_id}`) has successfully authorized in the application."

        try:
            r = httpx.post(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers={
                    "Authorization": f"Bot {bot_token}",
                    "Content-Type": "application/json",
                },
                json={"content": content},  # json= гарантирует UTF-8
                timeout=10,
            )
            r.raise_for_status()
            return Response(
                {"ok": True, "discord_response": r.json()},
                status=status.HTTP_200_OK,
            )

        except httpx.HTTPStatusError as e:
            return Response(
                {
                    "error": "discord_http_error",
                    "status": e.response.status_code,
                    "detail": e.response.text,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": "send_failed", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
