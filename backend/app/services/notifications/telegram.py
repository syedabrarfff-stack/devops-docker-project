import httpx
from app.core.config import settings


async def notify_telegram(message: str) -> bool:
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": settings.TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown",
                },
            )
        return r.status_code == 200
    except Exception:
        return False


async def notify_business_event(event_type: str, title: str, summary: str) -> bool:
    icons = {
        "proposal_accepted": "🎯",
        "meeting_booked": "📅",
        "payment_received": "✅",
        "system_critical_error": "🔴",
    }
    icon = icons.get(event_type, "📢")
    return await notify_telegram(
        f"{icon} *{title}*\n\n"
        f"*Event:* {event_type}\n"
        f"{summary[:800]}"
    )
