import base64
import httpx
from django.conf import settings

API_BASE = getattr(settings, "DISCORD_API_BASE", "https://discord.com/api").rstrip("/")
TOKEN_URL = f"{API_BASE}/oauth2/token"
USERS_ME_URL = f"{API_BASE}/users/@me"
CHANNEL_MSGS_URL_TMPL = f"{API_BASE}/v10/channels/{{channel_id}}/messages"

def _basic_auth_header(client_id: str, client_secret: str) -> str:
    payload = f"{client_id}:{client_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(payload).decode("ascii")

def exchange_code_for_token(code: str) -> dict:
    """
    Обмен кода на токен на сервере (правильно и безопасно).
    """
    client_id = settings.DISCORD["CLIENT_ID"]
    client_secret = settings.DISCORD["CLIENT_SECRET"]
    if not client_id or not client_secret:
        raise RuntimeError("Discord CLIENT_ID/CLIENT_SECRET not configured")

    headers = {
        "Authorization": _basic_auth_header(client_id, client_secret),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        # redirect_uri НЕ требуется для RPC/Embedded флоу
    }

    with httpx.Client(timeout=15) as client:
        r = client.post(TOKEN_URL, headers=headers, data=data)
        if r.status_code != 200:
            raise httpx.HTTPStatusError(
                f"Token exchange failed: {r.status_code} {r.text}", request=r.request, response=r
            )
        return r.json()

def get_me(access_token: str, token_type: str = "Bearer") -> dict:
    headers = {"Authorization": f"{token_type} {access_token}"}
    with httpx.Client(timeout=15) as client:
        r = client.get(USERS_ME_URL, headers=headers)
        if r.status_code != 200:
            raise httpx.HTTPStatusError(
                f"/users/@me failed: {r.status_code} {r.text}", request=r.request, response=r
            )
        return r.json()

def post_channel_message(channel_id: str, content: str) -> dict:
    """
    Отправка сообщения ботом (пригодится, когда подключим уведомления).
    """
    bot_token = settings.DISCORD.get("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("DISCORD_BOT_TOKEN not configured")

    url = CHANNEL_MSGS_URL_TMPL.format(channel_id=channel_id)
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=15) as client:
        r = client.post(url, headers=headers, json={"content": content})
        if r.status_code not in (200, 201):
            raise httpx.HTTPStatusError(
                f"Send message failed: {r.status_code} {r.text}", request=r.request, response=r
            )
        return r.json()
