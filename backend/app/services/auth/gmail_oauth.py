"""
Gmail OAuth2 integration.
- /auth/gmail/initiate  → redirect URL
- /auth/gmail/callback  → exchange code, store tokens
- send_via_gmail_api()  → send using Gmail REST API (falls back to SMTP)
"""
import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
]
GOOGLE_AUTH_URL   = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL  = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL    = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _is_oauth_configured() -> bool:
    return bool(settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET)


def get_oauth_url(state: str = "jarvis", redirect_uri: Optional[str] = None) -> str:
    """Generate the OAuth2 consent URL."""
    redirect_uri = redirect_uri or f"{settings.APP_BASE_URL}/api/v1/auth/gmail/callback"
    params = {
        "client_id":     settings.GMAIL_CLIENT_ID or "",
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         " ".join(GMAIL_SCOPES),
        "access_type":   "offline",
        "prompt":        "consent",
        "state":         state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_code(code: str, redirect_uri: str, db) -> dict:
    """Exchange auth code for tokens and persist them."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "redirect_uri":  redirect_uri,
            "grant_type":    "authorization_code",
        })
        r.raise_for_status()
        data = r.json()

    expiry = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
    from app.services.storage.secure import store_oauth_token
    await store_oauth_token(
        db, provider="gmail", account="primary",
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expiry=expiry, scopes=data.get("scope"),
    )
    logger.info("Gmail OAuth tokens stored successfully")
    return data


async def _refresh_access_token(refresh_token: str) -> tuple[str, datetime]:
    """Refresh an expired access token."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(GOOGLE_TOKEN_URL, data={
            "refresh_token": refresh_token,
            "client_id":     settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "grant_type":    "refresh_token",
        })
        r.raise_for_status()
        data = r.json()

    expiry = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
    return data["access_token"], expiry


async def _get_valid_token(db) -> Optional[str]:
    """Return a valid access token, refreshing if necessary."""
    from app.services.storage.secure import get_oauth_token, store_oauth_token
    token_data = await get_oauth_token(db, "gmail", "primary")
    if not token_data:
        return None

    expiry = token_data.get("expiry")
    needs_refresh = (not expiry) or (expiry < datetime.now(timezone.utc) + timedelta(minutes=5))

    if needs_refresh and token_data.get("refresh_token"):
        try:
            new_token, new_expiry = await _refresh_access_token(token_data["refresh_token"])
            await store_oauth_token(
                db, "gmail", "primary",
                access_token=new_token,
                expiry=new_expiry,
            )
            return new_token
        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")
            return None

    return token_data.get("access_token")


async def send_via_gmail_api(db, to: str, subject: str, body: str,
                              to_name: str = "") -> tuple[bool, str]:
    """Send email via Gmail API (OAuth). Returns (success, error)."""
    token = await _get_valid_token(db)
    if not token:
        return False, "No valid Gmail OAuth token — use /api/v1/auth/gmail/initiate to connect"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.GMAIL_ADDRESS or "me"
    msg["To"]      = f"{to_name} <{to}>" if to_name else to

    body_html = body.replace("\n", "<br>")
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(f"<html><body>{body_html}</body></html>", "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                GMAIL_SEND_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"raw": raw},
            )
            r.raise_for_status()
        return True, ""
    except Exception as e:
        logger.error(f"Gmail API send failed: {e}")
        return False, str(e)


async def get_gmail_profile(db) -> Optional[dict]:
    """Fetch the authenticated Gmail profile."""
    token = await _get_valid_token(db)
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                headers={"Authorization": f"Bearer {token}"},
            )
            return r.json()
    except Exception:
        return None


def is_oauth_connected(token_data: Optional[dict]) -> bool:
    return bool(token_data and token_data.get("access_token"))
