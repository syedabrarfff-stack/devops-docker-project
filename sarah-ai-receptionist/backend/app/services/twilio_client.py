"""
Shared Twilio REST client. Previously constructed separately (with identical
try/except boilerplate) in notification_service.py and admin.py — one helper
now, reused everywhere a Twilio API call is needed outside the live call path.
"""

from functools import lru_cache

from twilio.rest import Client

from app.config.settings import get_settings


@lru_cache
def get_twilio_client() -> Client:
    settings = get_settings()
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)
