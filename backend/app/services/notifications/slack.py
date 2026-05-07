import httpx
from app.core.config import settings


async def notify_slack(message: str, color: str = "#00d4ff") -> bool:
    if not settings.SLACK_WEBHOOK_URL:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                settings.SLACK_WEBHOOK_URL,
                json={
                    "text": message,
                    "attachments": [{
                        "color": color,
                        "footer": "JARVIS — Aliyar Solutions",
                        "ts": int(__import__('time').time()),
                    }],
                },
            )
        return r.status_code == 200
    except Exception:
        return False
