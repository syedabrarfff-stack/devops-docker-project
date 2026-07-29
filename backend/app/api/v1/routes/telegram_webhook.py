"""
Telegram webhook registration and incoming message handler.
POST /api/v1/telegram/register — sets webhook URL with Telegram
POST /api/v1/telegram/webhook — receives incoming messages from Telegram
"""
import logging
import secrets
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.v1.routes.auth import get_current_captain
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.notifications.telegram_bot import (
    send_message, handle_command, handle_text_message
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/register", dependencies=[Depends(get_current_captain)])
@limiter.limit("5/minute")
async def register_webhook(request: Request, webhook_url: Optional[str] = None):
    """Register JARVIS webhook with Telegram API."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN not configured")

    if not webhook_url:
        webhook_url = f"{settings.APP_BASE_URL}/api/v1/telegram/webhook"

    webhook_payload: dict = {"url": webhook_url}
    if settings.TELEGRAM_WEBHOOK_SECRET:
        webhook_payload["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook",
                json=webhook_payload,
            )
            data = r.json()
        if data.get("ok"):
            logger.info("Telegram webhook registered: %s", webhook_url)
            return {"status": "registered", "url": webhook_url}
        else:
            logger.error("Telegram webhook registration failed: %s", data.get("description"))
            raise HTTPException(status_code=400, detail=data.get("description", "Unknown error"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Telegram webhook registration error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook registration failed")


@router.post("/webhook")
@limiter.limit("60/minute")
async def webhook(request: Request):
    """
    Receive incoming messages from Telegram.
    Validates X-Telegram-Bot-API-Secret-Token header.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=400, detail="Bot not configured")

    if not settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Telegram webhook not configured")
    token_header = request.headers.get("X-Telegram-Bot-API-Secret-Token", "")
    if not secrets.compare_digest(token_header, settings.TELEGRAM_WEBHOOK_SECRET):
        logger.warning("Telegram webhook: invalid or missing secret token")
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Parse update
    update_id = body.get("update_id")
    message = body.get("message")

    if not message:
        logger.debug("Telegram update without message: %s", update_id)
        return {"ok": True}

    chat_id = str(message.get("chat", {}).get("id", ""))
    user_id = str(message.get("from", {}).get("id", ""))
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return {"ok": True}

    logger.info("Telegram message from %s (chat %s): %s", user_id, chat_id, text[:50])

    # Handle commands vs. free text
    if text.startswith("/"):
        cmd = text.split()[0].lstrip("/")
        args = text.split()[1:] if len(text.split()) > 1 else []
        await handle_command(chat_id, cmd, args)
    else:
        await handle_text_message(chat_id, text)

    return {"ok": True}
