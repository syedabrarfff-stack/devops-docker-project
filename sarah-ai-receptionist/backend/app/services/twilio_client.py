"""
Shared Twilio REST client. Previously constructed separately (with identical
try/except boilerplate) in notification_service.py and admin.py — one helper
now, reused everywhere a Twilio API call is needed outside the live call path.
"""

from functools import lru_cache

from twilio.rest import Client

from app.config.settings import get_settings


class TwilioNotConfigured(RuntimeError):
    """Twilio is paused (no subscription) and something asked for the client.

    A named exception rather than letting twilio's own constructor raise:
    callers need to tell "the phone product is deliberately switched off"
    apart from "Twilio is configured but the API call failed", and the two
    demand opposite responses -- the first is expected and should be logged
    calmly, the second is an incident.
    """


@lru_cache
def get_twilio_client() -> Client:
    settings = get_settings()
    if not settings.twilio_enabled:
        raise TwilioNotConfigured(
            "Twilio is not configured (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN unset). "
            "The phone product is paused; set both to re-enable it."
        )
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)
