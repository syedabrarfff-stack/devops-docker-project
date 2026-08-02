"""
Regression tests for caller-spoken time handling.

These guard a bug class that silently corrupts every booking: naive datetimes
being stored into timezone-aware columns (read as UTC), and dateutil quietly
discarding relative words like "tomorrow" under fuzzy parsing.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.clinic_time import (  # noqa: E402
    format_for_caller,
    now_in_clinic,
    parse_caller_datetime,
)

NY = "America/New_York"
LA = "America/Los_Angeles"


def _local(dt_utc, tz):
    return dt_utc.astimezone(ZoneInfo(tz))


def test_returns_timezone_aware_utc():
    """A naive result would be stored as UTC and silently shift the appointment."""
    result = parse_caller_datetime("tomorrow at 3pm", NY)
    assert result is not None
    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)


def test_time_is_interpreted_in_clinic_timezone():
    """3pm means 3pm where the clinic is, not 3pm UTC."""
    assert _local(parse_caller_datetime("tomorrow at 3pm", NY), NY).hour == 15
    assert _local(parse_caller_datetime("tomorrow at 3pm", LA), LA).hour == 15


def test_same_words_differ_by_real_offset_across_coasts():
    """An absolute date isolates the offset — "tomorrow" can't, because the two
    coasts are on different calendar days for part of every day, which is
    itself correct behavior."""
    ny = parse_caller_datetime("August 15 at 3pm", NY)
    la = parse_caller_datetime("August 15 at 3pm", LA)
    assert (la - ny) == timedelta(hours=3)


def test_relative_day_resolves_against_each_clinics_own_calendar():
    """Late evening on the west coast is already tomorrow in UTC — anchoring to
    UTC would resolve "tomorrow" to the wrong day."""
    for tz in (NY, LA):
        expected = now_in_clinic(tz).date() + timedelta(days=1)
        assert _local(parse_caller_datetime("tomorrow at 3pm", tz), tz).date() == expected


def test_relative_day_words_are_honored():
    """dateutil drops these under fuzzy=True — callers would arrive a day early."""
    today = now_in_clinic(NY).date()
    assert _local(parse_caller_datetime("today at 4pm", NY), NY).date() == today
    assert _local(parse_caller_datetime("tomorrow at 4pm", NY), NY).date() == today + timedelta(days=1)
    assert _local(
        parse_caller_datetime("day after tomorrow at 4pm", NY), NY
    ).date() == today + timedelta(days=2)


def test_bare_time_does_not_inherit_current_minute():
    """Anchoring on `now` would turn "3pm" into 3:47pm."""
    local = _local(parse_caller_datetime("3pm", NY), NY)
    assert (local.hour, local.minute) == (15, 0)


def test_explicit_minutes_are_kept():
    local = _local(parse_caller_datetime("Tuesday at 2:30pm", NY), NY)
    assert (local.hour, local.minute) == (14, 30)


def test_time_of_day_words_resolve():
    assert _local(parse_caller_datetime("tomorrow morning", NY), NY).hour == 9
    assert _local(parse_caller_datetime("tomorrow afternoon", NY), NY).hour == 14
    assert _local(parse_caller_datetime("tonight", NY), NY).hour == 18


def test_afternoon_and_evening_imply_pm():
    """"afternoon at 2" is 2 PM — booking 2 AM would be an obvious failure."""
    assert _local(parse_caller_datetime("this afternoon at 2", NY), NY).hour == 14
    assert _local(parse_caller_datetime("tomorrow evening at 6", NY), NY).hour == 18
    assert _local(parse_caller_datetime("tonight at 7", NY), NY).hour == 19


def test_explicit_meridiem_beats_pm_inference():
    """A caller who says "am" means am, even after saying "morning"."""
    assert _local(parse_caller_datetime("tomorrow morning at 10am", NY), NY).hour == 10


def test_morning_does_not_shift_to_pm():
    assert _local(parse_caller_datetime("tomorrow morning at 10", NY), NY).hour == 10


def test_past_bare_time_rolls_to_next_day():
    """"3pm" said at 5pm means tomorrow; a past booking vanishes from the
    dashboard's upcoming filter entirely."""
    result = parse_caller_datetime("3pm", NY)
    assert result is not None
    assert result > datetime.now(timezone.utc)


def test_unparseable_input_returns_none_not_a_wrong_time():
    assert parse_caller_datetime("uhh whenever works", NY) is None
    assert parse_caller_datetime("", NY) is None
    assert parse_caller_datetime(None, NY) is None


def test_unknown_timezone_falls_back_instead_of_raising():
    """A bad clinic timezone must never take down a live call."""
    assert parse_caller_datetime("tomorrow at 3pm", "Mars/Olympus_Mons") is not None
    assert parse_caller_datetime("tomorrow at 3pm", None) is not None


def test_format_renders_in_clinic_local_time():
    """Patients must never be told the UTC hour."""
    utc_9pm = datetime(2026, 8, 15, 21, 0, tzinfo=timezone.utc)
    assert "5:00 PM" in format_for_caller(utc_9pm, NY)
    assert "2:00 PM" in format_for_caller(utc_9pm, LA)


def test_format_handles_missing_value():
    assert format_for_caller(None, NY) == "the scheduled time"


def test_round_trip_is_stable():
    """What we store must read back as what the caller asked for."""
    for phrase, expected in [
        ("tomorrow at 3pm", "3:00 PM"),
        ("Tuesday at 2:30pm", "2:30 PM"),
        ("tomorrow morning at 10", "10:00 AM"),
    ]:
        assert expected in format_for_caller(parse_caller_datetime(phrase, NY), NY)
