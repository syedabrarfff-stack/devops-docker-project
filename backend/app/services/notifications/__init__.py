from app.services.notifications.gmail_sender import GmailSender, gmail_sender
from app.services.notifications.slack import notify_slack
from app.services.notifications.slack import notify_business_event as notify_slack_business_event
from app.services.notifications.telegram import notify_telegram
from app.services.notifications.telegram import notify_business_event as notify_telegram_business_event


async def notify_business_event(event_type: str, title: str, summary: str) -> bool:
    slack_ok = await notify_slack_business_event(event_type, title, summary)
    telegram_ok = await notify_telegram_business_event(event_type, title, summary)
    return slack_ok or telegram_ok


__all__ = [
    "GmailSender",
    "gmail_sender",
    "notify_slack",
    "notify_telegram",
    "notify_business_event",
]
