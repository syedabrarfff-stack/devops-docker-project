"""
Escalation when Sarah decides a human is needed.

Two genuinely different situations, which the old code conflated:

  During opening hours — hand the live call to the front desk. Twilio replaces
  the media stream with a <Dial>, so the caller stays on the line.

  Outside opening hours — there is no one to hand the call to. Promising a
  transfer and then dialling an empty office is worse than not offering one, so
  the caller is told the truth, their details are texted to the on-call number,
  and a genuine emergency is pointed at an emergency room.

The previous implementation said "let me connect you with our office manager,
one moment please" and then hung up, on the emergency path.
"""

import asyncio
import logging
from dataclasses import dataclass
from xml.sax.saxutils import escape as xml_escape
from xml.sax.saxutils import quoteattr

from app.config.settings import get_settings
from app.core.clinic_time import is_open_now
from app.services.twilio_client import get_twilio_client

logger = logging.getLogger(__name__)

# Long enough for a busy front desk to reach the phone, short enough that the
# caller isn't left listening to ringing.
DIAL_TIMEOUT_SECONDS = 20

CONNECTING_MESSAGE = "Let me connect you with our team now. One moment please."

AFTER_HOURS_MESSAGE = (
    "Our office is closed right now, so I can't put you through to anyone at this moment. "
    "I've passed your details to our on-call team and someone will call you back. "
    "If this is a serious emergency — heavy bleeding, swelling that affects your breathing "
    "or swallowing, or a facial injury — please go to your nearest emergency room right away."
)

UNAVAILABLE_MESSAGE = (
    "I'm not able to transfer you at the moment, but I've made a note of this "
    "and our team will follow up with you as soon as possible. "
    "If this is a serious emergency, please go to your nearest emergency room."
)


@dataclass
class TransferPlan:
    """What Sarah should say, and what the system should do about it."""

    spoken_message: str
    dial_number: str | None = None
    escalate_sms_to: str | None = None
    # Persisted to call_logs.transfer_result.
    result: str = "unavailable"

    @property
    def should_dial(self) -> bool:
        return self.dial_number is not None


def plan_transfer(clinic_config: dict | None) -> TransferPlan:
    """Decide between a live handoff and an after-hours escalation.

    Pure and side-effect free so the decision can be tested without Twilio.
    """
    config = clinic_config or {}
    transfer_number = config.get("_transfer_phone_number")
    escalation_number = config.get("_after_hours_escalation_number")
    open_now = is_open_now(config.get("_business_hours"), config.get("_timezone"))

    # Unknown hours with a transfer number configured is treated as open: the
    # clinic gave us a number to ring, and an unanswered ring falls through to
    # their own voicemail — the behaviour they already have today. Refusing to
    # transfer during business hours would be the worse failure.
    if transfer_number and open_now is not False:
        if open_now is None:
            logger.info("Business hours not configured; attempting live transfer")
        return TransferPlan(
            spoken_message=CONNECTING_MESSAGE,
            dial_number=transfer_number,
            result="connected",
        )

    if escalation_number:
        return TransferPlan(
            spoken_message=AFTER_HOURS_MESSAGE,
            escalate_sms_to=escalation_number,
            result="escalated_sms",
        )

    # Nothing configured. Say something true rather than promising a handoff
    # that cannot happen.
    logger.warning("Transfer requested but clinic has no transfer or escalation number configured")
    return TransferPlan(spoken_message=UNAVAILABLE_MESSAGE, result="unavailable")


def build_dial_twiml(dial_number: str, caller_id: str | None) -> str:
    """TwiML that replaces the media stream with a call to the front desk.

    `action` sends the outcome back to /transfer-status, so a call that rings
    out is answered with an apology and an SMS to the on-call number instead of
    silence — and so the real result is recorded rather than assumed.
    """
    settings = get_settings()
    action_url = f"{settings.app_base_url.rstrip('/')}/transfer-status"
    # quoteattr, not escape: escape() leaves quotes untouched, which in an
    # attribute lets a stray " close it early and inject TwiML verbs.
    caller_id_attr = f" callerId={quoteattr(caller_id)}" if caller_id else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Dial timeout="{DIAL_TIMEOUT_SECONDS}"{caller_id_attr} '
        f"action={quoteattr(action_url)} method=\"POST\">"
        f"{xml_escape(dial_number)}"
        "</Dial>"
        "</Response>"
    )


async def redirect_call_to_human(call_sid: str, dial_number: str, caller_id: str | None) -> bool:
    """Hand the in-progress call over to a person. Returns whether Twilio accepted it.

    Updating the live call replaces the <Connect><Stream> TwiML, which also
    tears down our WebSocket — so nothing may be spoken through Sarah after
    this returns.
    """
    twiml = build_dial_twiml(dial_number, caller_id)
    try:
        client = get_twilio_client()
        await asyncio.to_thread(client.calls(call_sid).update, twiml=twiml)
        logger.info(f"[{call_sid}] Transferred live call to {dial_number}")
        return True
    except Exception as e:
        # The caller is still connected to Sarah at this point, so a failure
        # here is recoverable — she keeps talking rather than dropping them.
        logger.error(f"[{call_sid}] Live transfer to {dial_number} failed: {e}")
        return False
