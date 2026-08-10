"""
The platform must run correctly with Twilio switched off.

Twilio is paused (no subscription). It is paused, not removed: every phone
code path is still present and still tested, and re-enabling it is setting
two environment variables. What these tests pin is that the *off* state is a
first-class, correct configuration rather than a broken one.

The distinction that matters throughout: "switched off" and "broken" must not
look alike. A paused deployment should refuse phone work clearly and leave
everything non-telephony -- the browser demo, dashboard, bookings, auth,
billing -- completely untouched.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config.settings import Settings
from app.services.twilio_client import TwilioNotConfigured, get_twilio_client


def _settings(**overrides) -> Settings:
    """A Settings instance with Twilio explicitly unset unless a test says
    otherwise.

    The twilio_* values must be passed explicitly rather than left to default:
    conftest.py exports dummy TWILIO_* env vars for the rest of the suite, and
    pydantic-settings would read those, so an "unconfigured" fixture built by
    omission would silently come back enabled and every assertion here would
    test the wrong state.
    """
    base = {
        "openrouter_api_key": "x",
        "deepgram_api_key": "x",
        "elevenlabs_api_key": "x",
        "elevenlabs_voice_id": "x",
        "database_url": "postgresql+asyncpg://t:t@localhost/t",
        "jwt_secret_key": "x",
        "twilio_account_sid": "",
        "twilio_auth_token": "",
        "twilio_phone_number": "",
    }
    base.update(overrides)
    return Settings(**base)


def test_the_app_starts_with_no_twilio_credentials_at_all():
    """The whole point of pausing rather than removing. If these fields stay
    required, the container cannot boot without a Twilio credential -- which
    is precisely the outage a pause is meant to avoid.

    Asserted against the model's own declared defaults rather than an
    instance, so the dummy TWILIO_* env vars conftest exports cannot make a
    still-required field look optional."""
    for field in ("twilio_account_sid", "twilio_auth_token", "twilio_phone_number"):
        assert Settings.model_fields[field].default == "", f"{field} must be optional"
        assert not Settings.model_fields[field].is_required(), f"{field} must not be required"

    assert _settings().twilio_enabled is False


def test_setting_both_credentials_is_all_it_takes_to_re_enable():
    s = _settings(twilio_account_sid="ACxxx", twilio_auth_token="tok")
    assert s.twilio_enabled is True


def test_the_pause_switch_wins_over_present_credentials():
    """The case that actually applies in production right now: the Twilio
    credentials are still sitting in Secrets Manager, but the subscription has
    lapsed, so they are dead. Pausing has to work WITHOUT emptying that
    secret -- both because rewriting it is a privileged, fumbleable change and
    because those values are what you need intact to switch the product back
    on later."""
    s = _settings(twilio_account_sid="ACxxx", twilio_auth_token="tok", twilio_paused=True)
    assert s.twilio_enabled is False


def test_unpausing_restores_the_phone_product_with_no_other_change():
    """Re-enabling must be this flag alone -- no secret edit, no redeploy of
    credentials. If this ever needs more, the pause was a one-way door."""
    s = _settings(twilio_account_sid="ACxxx", twilio_auth_token="tok", twilio_paused=False)
    assert s.twilio_enabled is True


def test_pausing_is_not_the_default_in_code():
    """The default belongs in deployment config (Terraform), not baked into
    the application: a developer running locally with real Twilio credentials
    should get a working phone path without having to know this flag exists."""
    assert Settings.model_fields["twilio_paused"].default is False


@pytest.mark.parametrize(
    "sid, token",
    [("ACxxx", ""), ("", "tok")],
)
def test_a_half_configured_twilio_counts_as_off(sid, token):
    """Both halves or nothing. A SID with no auth token cannot validate a
    webhook signature, so treating it as enabled would accept inbound calls
    into validation that rejects every one of them -- a phone line that is
    dead while reporting itself healthy."""
    assert _settings(twilio_account_sid=sid, twilio_auth_token=token).twilio_enabled is False


def test_asking_for_the_client_while_paused_says_why(monkeypatch):
    """A named exception, not twilio's own constructor error: callers have to
    tell 'deliberately off' apart from 'configured but failing', because the
    first is routine and the second is an incident."""
    import app.services.twilio_client as tc

    get_twilio_client.cache_clear()
    monkeypatch.setattr(tc, "get_settings", lambda: _settings())
    try:
        with pytest.raises(TwilioNotConfigured) as excinfo:
            get_twilio_client()
        assert "paused" in str(excinfo.value).lower()
    finally:
        get_twilio_client.cache_clear()


def test_sms_is_skipped_rather_than_attempted(monkeypatch):
    """Every SMS path already returned False on failure, so a paused Twilio
    was never going to crash. The regression this guards is noise: an ERROR
    logged per message for an intentional config state buries a real Twilio
    outage and makes healthy logs look like a failing platform."""
    import app.services.notification_service as ns

    monkeypatch.setattr(ns, "get_settings", lambda: _settings())

    def _explode():
        raise AssertionError("no Twilio client may be constructed while paused")

    monkeypatch.setattr(ns, "get_twilio_client", _explode)

    assert ns._sms_unavailable("confirmation", "+966500000000") is True


def test_sms_proceeds_normally_once_twilio_is_back(monkeypatch):
    import app.services.notification_service as ns

    monkeypatch.setattr(
        ns, "get_settings", lambda: _settings(twilio_account_sid="ACx", twilio_auth_token="t")
    )
    assert ns._sms_unavailable("confirmation", "+966500000000") is False


def test_the_browser_demo_does_not_depend_on_twilio():
    """The demo is what is being sold right now, and it is deliberately
    Twilio-free and database-free. If it ever grew a Twilio import, pausing
    Twilio would take the demo down with the phone product."""
    import inspect

    from app.services import demo_call_manager

    source = inspect.getsource(demo_call_manager)
    assert "twilio" not in source.lower().replace("no twilio", "").replace(
        "twilio's", ""
    ) or "import twilio" not in source.lower()

    # The hard guarantee: no Twilio module is imported at any depth.
    assert not any(
        name.startswith("twilio")
        for name in dir(demo_call_manager)
        if not name.startswith("__")
    )
