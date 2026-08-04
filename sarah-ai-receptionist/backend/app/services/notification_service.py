"""
SMS notifications via Twilio — appointment confirmations and reminders.
"""

import asyncio
import logging

from app.config.settings import get_settings
from app.services.twilio_client import get_twilio_client

logger = logging.getLogger(__name__)


async def send_appointment_confirmation(to_phone: str, clinic_name: str, service: str, when: str) -> bool:
    if not to_phone:
        return False
    settings = get_settings()
    body = (
        f"{clinic_name}: You're confirmed for {service} on {when}. "
        f"Reply or call us if you need to reschedule."
    )
    try:
        client = get_twilio_client()
        await asyncio.to_thread(
            client.messages.create, body=body, from_=settings.twilio_phone_number, to=to_phone
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS confirmation to {to_phone}: {e}")
        return False


async def send_appointment_change(
    to_phone: str, clinic_name: str, kind: str, service: str, when: str
) -> bool:
    """Confirm a reschedule or cancellation by SMS, the same way a booking is
    confirmed — so the caller has it in writing, not just a spoken 'done'."""
    if not to_phone:
        return False
    settings = get_settings()
    if kind == "rescheduled":
        body = f"{clinic_name}: your {service} has been moved to {when}. See you then."
    elif kind == "cancelled":
        body = f"{clinic_name}: your {service} on {when} has been cancelled. Call us to rebook anytime."
    else:
        return False
    try:
        client = get_twilio_client()
        await asyncio.to_thread(
            client.messages.create, body=body, from_=settings.twilio_phone_number, to=to_phone
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send {kind} SMS to {to_phone}: {e}")
        return False


async def send_urgent_escalation(
    to_phone: str, clinic_name: str, caller_phone: str | None, summary: str | None
) -> bool:
    """Text the on-call number when a caller needed a human and none was available.

    This is the only thing standing between an after-hours caller and being
    forgotten, so it carries the callback number first — the person reading it
    at 11pm needs to act, not scroll.
    """
    if not to_phone:
        return False
    settings = get_settings()
    body = (
        f"{clinic_name} — urgent call needs a callback.\n"
        f"Caller: {caller_phone or 'number withheld'}\n"
        f"{(summary or 'Caller asked to speak with a person.')[:400]}"
    )
    try:
        client = get_twilio_client()
        await asyncio.to_thread(
            client.messages.create, body=body, from_=settings.twilio_phone_number, to=to_phone
        )
        logger.info(f"Sent urgent escalation SMS to on-call number for {clinic_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to send urgent escalation SMS to {to_phone}: {e}")
        return False


async def send_appointment_reminder(to_phone: str, clinic_name: str, service: str, when: str) -> bool:
    if not to_phone:
        return False
    settings = get_settings()
    body = f"Reminder from {clinic_name}: your {service} appointment is coming up on {when}."
    try:
        client = get_twilio_client()
        await asyncio.to_thread(
            client.messages.create, body=body, from_=settings.twilio_phone_number, to=to_phone
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS reminder to {to_phone}: {e}")
        return False
