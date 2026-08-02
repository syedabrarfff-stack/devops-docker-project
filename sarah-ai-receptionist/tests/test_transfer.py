"""
Tests for escalation when Sarah decides a caller needs a human.

This path handles dental emergencies. The failure it replaces — announcing
"let me connect you" and then hanging up — is the one a prospect is most likely
to hit while testing, and the one a patient can be harmed by.
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.clinic_time import is_open_now  # noqa: E402
from app.services.transfer_service import (  # noqa: E402
    AFTER_HOURS_MESSAGE,
    CONNECTING_MESSAGE,
    UNAVAILABLE_MESSAGE,
    build_dial_twiml,
    plan_transfer,
)

NY = "America/New_York"
OPEN_ALL_WEEK = {d: [["00:00", "23:59"]] for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")}
CLOSED_ALL_WEEK = {d: [] for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")}


# ── business hours ────────────────────────────────────────────────────────────

def test_unconfigured_hours_are_unknown_not_closed():
    """None and False must stay distinguishable: unknown hours still transfer."""
    assert is_open_now(None, NY) is None
    assert is_open_now({}, NY) is None


def test_open_and_closed_days():
    assert is_open_now(OPEN_ALL_WEEK, NY) is True
    assert is_open_now(CLOSED_ALL_WEEK, NY) is False


def test_day_with_no_entry_is_closed():
    """A weekday absent from a configured week means closed, not unknown."""
    with patch("app.core.clinic_time.now_in_clinic") as now:
        import datetime
        from zoneinfo import ZoneInfo
        # A Sunday, against a config that only lists Monday.
        now.return_value = datetime.datetime(2026, 8, 2, 12, 0, tzinfo=ZoneInfo(NY))
        assert is_open_now({"mon": [["09:00", "17:00"]]}, NY) is False


def test_lunch_break_closes_the_clinic():
    """A clinic shut 12:00–13:00 must not transfer a caller at 12:30."""
    with patch("app.core.clinic_time.now_in_clinic") as now:
        import datetime
        from zoneinfo import ZoneInfo
        # A Monday at 12:30.
        now.return_value = datetime.datetime(2026, 8, 3, 12, 30, tzinfo=ZoneInfo(NY))
        hours = {"mon": [["08:00", "12:00"], ["13:00", "18:00"]]}
        assert is_open_now(hours, NY) is False
        now.return_value = datetime.datetime(2026, 8, 3, 11, 30, tzinfo=ZoneInfo(NY))
        assert is_open_now(hours, NY) is True
        now.return_value = datetime.datetime(2026, 8, 3, 14, 0, tzinfo=ZoneInfo(NY))
        assert is_open_now(hours, NY) is True


def test_malformed_intervals_do_not_close_the_clinic():
    """Bad data in one interval must not silently strand every caller."""
    with patch("app.core.clinic_time.now_in_clinic") as now:
        import datetime
        from zoneinfo import ZoneInfo
        now.return_value = datetime.datetime(2026, 8, 3, 10, 0, tzinfo=ZoneInfo(NY))
        hours = {"mon": [["not-a-time"], ["09:00", "17:00"]]}
        assert is_open_now(hours, NY) is True


# ── transfer planning ─────────────────────────────────────────────────────────

def _config(**overrides):
    base = {
        "_timezone": NY,
        "_transfer_phone_number": "+15551110000",
        "_after_hours_escalation_number": "+15552220000",
        "_business_hours": OPEN_ALL_WEEK,
    }
    base.update(overrides)
    return base


def test_in_hours_transfers_the_live_call():
    plan = plan_transfer(_config())
    assert plan.should_dial is True
    assert plan.dial_number == "+15551110000"
    assert plan.result == "connected"
    assert plan.spoken_message == CONNECTING_MESSAGE


def test_after_hours_escalates_instead_of_promising_a_transfer():
    plan = plan_transfer(_config(_business_hours=CLOSED_ALL_WEEK))
    assert plan.should_dial is False
    assert plan.escalate_sms_to == "+15552220000"
    assert plan.result == "escalated_sms"
    assert plan.spoken_message == AFTER_HOURS_MESSAGE


def test_after_hours_message_points_a_real_emergency_at_the_er():
    """The clinic is shut; the only safe advice is not to wait for a callback."""
    plan = plan_transfer(_config(_business_hours=CLOSED_ALL_WEEK))
    assert "emergency room" in plan.spoken_message.lower()


def test_unknown_hours_still_transfer_when_a_number_exists():
    """Refusing to transfer during business hours is the worse failure."""
    plan = plan_transfer(_config(_business_hours=None))
    assert plan.should_dial is True


def test_no_transfer_number_falls_back_to_escalation():
    plan = plan_transfer(_config(_transfer_phone_number=None))
    assert plan.should_dial is False
    assert plan.result == "escalated_sms"


def test_nothing_configured_never_promises_a_handoff():
    """The old bug: saying "connecting you" with nowhere to connect to."""
    plan = plan_transfer(_config(_transfer_phone_number=None, _after_hours_escalation_number=None))
    assert plan.should_dial is False
    assert plan.escalate_sms_to is None
    assert plan.result == "unavailable"
    assert plan.spoken_message == UNAVAILABLE_MESSAGE
    for promise in ("connect", "hold", "put you through", "one moment"):
        assert promise not in plan.spoken_message.lower()


def test_missing_config_does_not_raise_mid_call():
    assert plan_transfer(None).result == "unavailable"
    assert plan_transfer({}).result == "unavailable"


# ── dial TwiML ────────────────────────────────────────────────────────────────

def test_dial_twiml_has_timeout_and_status_callback():
    """Without the action URL, a ring-out gives the caller silence and the log
    would claim the transfer succeeded."""
    twiml = build_dial_twiml("+15551110000", "+15559990000")
    assert "<Dial" in twiml and "+15551110000" in twiml
    assert 'timeout="20"' in twiml
    assert "/transfer-status" in twiml
    assert 'callerId="+15559990000"' in twiml


def test_dial_twiml_omits_caller_id_when_unknown():
    assert "callerId" not in build_dial_twiml("+15551110000", None)


def test_dial_twiml_escapes_injected_element_content():
    twiml = build_dial_twiml('+1555"><Hangup/><Dial>evil', None)
    assert "<Hangup/>" not in twiml


def test_dial_twiml_escapes_quotes_in_the_caller_id_attribute():
    """callerId sits inside an attribute: escape() leaves quotes alone, so a
    stray " would close it early and inject TwiML."""
    twiml = build_dial_twiml("+15551110000", '+1555" foo="bar')
    assert 'foo="bar"' not in twiml


def test_dial_twiml_is_well_formed_xml():
    from xml.etree import ElementTree

    ElementTree.fromstring(build_dial_twiml("+15551110000", '+1555"quote'))
