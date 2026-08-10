"""
SMS notifications via Twilio — appointment confirmations and reminders.
"""

import asyncio
import logging

from app.config.settings import get_settings
from app.core.redact import redact_phone
from app.services.twilio_client import get_twilio_client

logger = logging.getLogger(__name__)


def _sms_unavailable(kind: str, to_phone: str) -> bool:
    """Whether SMS is switched off rather than broken.

    Every send below already returns False on failure, so a paused Twilio was
    never going to crash anything -- but it would log an ERROR per attempted
    message for what is a deliberate configuration state. That buries a real
    Twilio outage in expected noise and makes the logs read like the platform
    is failing when it is doing exactly what it was told.

    Checked before the send rather than caught after it so no Twilio API call
    is attempted at all.
    """
    if get_settings().twilio_enabled:
        return False
    logger.info(f"SMS ({kind}) not sent to {redact_phone(to_phone)}: Twilio is paused.")
    return True


def _resolve_from_number(clinic_number: str | None) -> str:
    """The number an SMS should appear to come from.

    Every call site below has access to the clinic's own twilio_phone_number
    (either the number Sarah answers on directly, or the one the clinic's
    existing number forwards to during onboarding). Falling back to the
    platform-wide settings.twilio_phone_number here previously meant EVERY
    clinic's confirmations, reminders, and escalations were sent from the
    same single default number regardless of which number the patient
    actually called -- confusing at best ("who is texting me?"), and
    actively undermining the "keep answering on your own existing number"
    onboarding path this platform is built around, where a mismatched SMS
    sender number is the first thing that looks broken to a real patient.
    """
    settings = get_settings()
    return clinic_number or settings.twilio_phone_number


async def send_appointment_confirmation(
    to_phone: str, clinic_name: str, service: str, when: str, from_number: str | None = None
) -> bool:
    if not to_phone:
        return False
    if _sms_unavailable("confirmation", to_phone):
        return False
    body = (
        f"{clinic_name}: You're confirmed for {service} on {when}. "
        f"Reply or call us if you need to reschedule."
    )
    try:
        client = get_twilio_client()
        await asyncio.to_thread(
            client.messages.create,
            body=body,
            from_=_resolve_from_number(from_number),
            to=to_phone,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS confirmation to {redact_phone(to_phone)}: {e}")
        return False


async def send_appointment_change(
    to_phone: str, clinic_name: str, kind: str, service: str, when: str, from_number: str | None = None
) -> bool:
    """Confirm a reschedule or cancellation by SMS, the same way a booking is
    confirmed — so the caller has it in writing, not just a spoken 'done'."""
    if not to_phone:
        return False
    if _sms_unavailable("change", to_phone):
        return False
    if kind == "rescheduled":
        body = f"{clinic_name}: your {service} has been moved to {when}. See you then."
    elif kind == "cancelled":
        body = f"{clinic_name}: your {service} on {when} has been cancelled. Call us to rebook anytime."
    else:
        return False
    try:
        client = get_twilio_client()
        await asyncio.to_thread(
            client.messages.create,
            body=body,
            from_=_resolve_from_number(from_number),
            to=to_phone,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send {kind} SMS to {redact_phone(to_phone)}: {e}")
        return False


async def send_urgent_escalation(
    to_phone: str,
    clinic_name: str,
    caller_phone: str | None,
    summary: str | None,
    from_number: str | None = None,
) -> bool:
    """Text the on-call number when a caller needed a human and none was available.

    This is the only thing standing between an after-hours caller and being
    forgotten, so it carries the callback number first — the person reading it
    at 11pm needs to act, not scroll.
    """
    if not to_phone:
        return False
    if _sms_unavailable("urgent escalation", to_phone):
        return False
    body = (
        f"{clinic_name} — urgent call needs a callback.\n"
        f"Caller: {caller_phone or 'number withheld'}\n"
        f"{(summary or 'Caller asked to speak with a person.')[:400]}"
    )
    try:
        client = get_twilio_client()
        await asyncio.to_thread(
            client.messages.create,
            body=body,
            from_=_resolve_from_number(from_number),
            to=to_phone,
        )
        logger.info(f"Sent urgent escalation SMS to on-call number for {clinic_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to send urgent escalation SMS to {redact_phone(to_phone)}: {e}")
        return False


async def send_appointment_reminder(
    to_phone: str, clinic_name: str, service: str, when: str, from_number: str | None = None
) -> bool:
    if not to_phone:
        return False
    if _sms_unavailable("reminder", to_phone):
        return False
    body = f"Reminder from {clinic_name}: your {service} appointment is coming up on {when}."
    try:
        client = get_twilio_client()
        await asyncio.to_thread(
            client.messages.create,
            body=body,
            from_=_resolve_from_number(from_number),
            to=to_phone,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS reminder to {redact_phone(to_phone)}: {e}")
        return False
