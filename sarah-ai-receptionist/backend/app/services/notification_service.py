"""
SMS notifications via Twilio — appointment confirmations and reminders.
"""

import logging
from twilio.rest import Client
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


def _client() -> Client:
    settings = get_settings()
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


async def send_appointment_confirmation(to_phone: str, clinic_name: str, service: str, when: str) -> bool:
    if not to_phone:
        return False
    settings = get_settings()
    body = (
        f"{clinic_name}: You're confirmed for {service} on {when}. "
        f"Reply or call us if you need to reschedule."
    )
    try:
        _client().messages.create(body=body, from_=settings.twilio_phone_number, to=to_phone)
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS confirmation to {to_phone}: {e}")
        return False


async def send_appointment_reminder(to_phone: str, clinic_name: str, service: str, when: str) -> bool:
    if not to_phone:
        return False
    settings = get_settings()
    body = f"Reminder from {clinic_name}: your {service} appointment is coming up on {when}."
    try:
        _client().messages.create(body=body, from_=settings.twilio_phone_number, to=to_phone)
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS reminder to {to_phone}: {e}")
        return False
