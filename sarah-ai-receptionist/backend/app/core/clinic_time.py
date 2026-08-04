"""
Clinic-local time handling.

Callers speak in their clinic's local time ("Tuesday at 3pm"), but every
timestamp column is timezone-aware and stored as UTC. dateutil returns *naive*
datetimes for phrases like that, and a naive datetime handed to asyncpg for a
`TIMESTAMPTZ` column is silently read as UTC — so "3pm" at a New York clinic
would land in the database as 11:00 AM local, and 7:00 AM for California.

Everything that converts between what a caller said and what we store goes
through this module.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil import parser as dateparser

logger = logging.getLogger(__name__)

# A caller who says a bare time ("3pm") when it is already past that time
# almost always means tomorrow. Only roll forward inside this window — a parse
# landing further in the past is a bad parse, not an implied next-day booking.
_ROLL_FORWARD_WINDOW = timedelta(hours=24)

# Used when the caller names a date but no time ("Tuesday"). Opening-hours
# morning is a plausible, reviewable slot; midnight would look like a glitch.
_UNSPECIFIED_HOUR = 9

# dateutil has no notion of relative day words — with fuzzy=True it silently
# discards them and resolves to the anchor date, so "tomorrow at 3pm" would
# book *today* and the patient would arrive a day early. Callers say these
# constantly, so they're resolved to a day offset before parsing.
#
# Ordered longest-first so "day after tomorrow" wins over the "tomorrow"
# inside it. Day words only — phrases that also carry a time ("tonight",
# "this afternoon") belong to _TIME_OF_DAY and must not be consumed here, or
# the time sense is stripped and the booking lands in the morning.
_RELATIVE_DAYS: tuple[tuple[str, int], ...] = (
    ("day after tomorrow", 2),
    ("tomorrow", 1),
    ("later today", 0),
    ("today", 0),
)

# "tomorrow morning" / "Tuesday afternoon" carry a real time-of-day that
# dateutil also ignores. Each maps to the hour used when the caller names no
# clock time, plus whether a bare hour should be read as PM — "afternoon at 2"
# means 2 PM, and booking 2 AM instead would be an obvious failure.
_TIME_OF_DAY: tuple[tuple[str, int, bool], ...] = (
    ("morning", 9, False),
    ("afternoon", 14, True),
    ("evening", 17, True),
    ("tonight", 18, True),
    ("night", 18, True),
    ("noon", 12, False),
)

# An explicit am/pm from the caller always wins over the inferred hint.
_EXPLICIT_MERIDIEM = re.compile(r"\b(a\.?m\.?|p\.?m\.?)\b", re.IGNORECASE)

# "at 2" is an hour, but dateutil reads a bare number as a day-of-month.
# Rewriting it to "2:00" forces the time reading.
_BARE_HOUR = re.compile(r"\bat\s+(\d{1,2})\b(?!\s*[:.\d])", re.IGNORECASE)


def get_zone(timezone_name: str | None) -> ZoneInfo:
    """Resolve a clinic's IANA timezone, falling back to UTC rather than raising.

    A bad or missing timezone string must never take down a live call — the
    booking still needs to be written somewhere sane and reviewable.
    """
    if not timezone_name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning(f"Unknown clinic timezone {timezone_name!r}; falling back to UTC")
        return ZoneInfo("UTC")


def now_in_clinic(timezone_name: str | None) -> datetime:
    """Current time as the clinic experiences it — the anchor for 'today'/'tomorrow'."""
    return datetime.now(get_zone(timezone_name))


def parse_caller_datetime(raw: str | None, timezone_name: str | None) -> datetime | None:
    """Interpret a caller's spoken date/time in clinic-local time, return UTC.

    Relative phrases are resolved against the clinic's local clock, not the
    server's — at 9 PM Eastern the server is already on tomorrow's UTC date, so
    anchoring to UTC would resolve "today" to the wrong calendar day.

    Returns None when the phrase can't be understood, so the caller can decide
    what to do rather than getting a silently wrong timestamp.
    """
    if not raw or not raw.strip():
        return None

    zone = get_zone(timezone_name)
    local_now = datetime.now(zone)

    said_meridiem = bool(_EXPLICIT_MERIDIEM.search(raw))

    # day_offset / default_hour are None when the caller used no such word.
    text, day_offset = _resolve_relative_day(raw)
    text, default_hour, assume_pm = _resolve_time_of_day(text)

    # `default` supplies whatever the caller left unsaid. It must carry the
    # target clinic-local *date* but not the current wall-clock time, or "3pm"
    # would inherit the current minute and book 3:53. Anything the caller does
    # state overrides these.
    default = (local_now + timedelta(days=day_offset or 0)).replace(
        hour=default_hour if default_hour is not None else _UNSPECIFIED_HOUR,
        minute=0,
        second=0,
        microsecond=0,
    )

    # "tomorrow" or "tomorrow morning" leave nothing for dateutil once the
    # words are stripped, but the day and hour are already resolved — the
    # default *is* the answer.
    if not text.strip():
        if day_offset is None and default_hour is None:
            return None
        return default.astimezone(timezone.utc)

    try:
        parsed = dateparser.parse(_BARE_HOUR.sub(r"at \1:00", text), fuzzy=True, default=default)
    except (ValueError, OverflowError, TypeError) as e:
        logger.warning(f"Could not parse caller datetime {raw!r}: {e}")
        return None

    if parsed is None:
        return None

    # "afternoon at 2" -> 2 PM. Never override a caller who said "am"/"pm".
    if assume_pm and not said_meridiem and parsed.hour < 12:
        parsed = parsed + timedelta(hours=12)

    # dateutil returns naive datetimes for most spoken phrasings. A naive value
    # here means "clinic-local", never UTC.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=zone)

    # "3pm" said at 5pm means tomorrow at 3pm.
    if parsed < local_now and (local_now - parsed) < _ROLL_FORWARD_WINDOW:
        parsed = parsed + timedelta(days=1)

    return parsed.astimezone(timezone.utc)


_WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def is_open_now(business_hours: dict | None, timezone_name: str | None) -> bool | None:
    """Whether the clinic is open right now, in its own local time.

    `business_hours` maps weekday keys to a list of [open, close] "HH:MM"
    intervals, so a clinic that closes for lunch can say so:

        {"mon": [["08:00", "12:00"], ["13:00", "18:00"]], "sun": []}

    Returns None when hours aren't configured — the caller must decide what to
    do with "unknown", which is not the same as "closed".
    """
    if not business_hours or not isinstance(business_hours, dict):
        return None

    local = now_in_clinic(timezone_name)
    intervals = business_hours.get(_WEEKDAY_KEYS[local.weekday()])
    if not intervals:
        # An explicit empty list means closed that day; a missing key in an
        # otherwise-configured week means the same thing.
        return False

    minutes_now = local.hour * 60 + local.minute
    for interval in intervals:
        parsed = _parse_interval(interval)
        if parsed is None:
            continue
        start, end = parsed
        if start <= end:
            if start <= minutes_now < end:
                return True
        # An interval that wraps midnight ("22:00"–"02:00") is open on both
        # sides of the boundary.
        elif minutes_now >= start or minutes_now < end:
            return True
    return False


def _parse_interval(interval) -> tuple[int, int] | None:
    """Convert ["08:00", "18:00"] to minutes-since-midnight, or None if malformed.

    Bad data in one interval must not make a clinic look permanently closed, so
    unparseable entries are skipped rather than raised.
    """
    if not isinstance(interval, (list, tuple)) or len(interval) != 2:
        logger.warning(f"Malformed business-hours interval: {interval!r}")
        return None
    try:
        start_h, start_m = (int(p) for p in str(interval[0]).split(":", 1))
        end_h, end_m = (int(p) for p in str(interval[1]).split(":", 1))
    except (ValueError, TypeError):
        logger.warning(f"Unparseable business-hours interval: {interval!r}")
        return None
    return start_h * 60 + start_m, end_h * 60 + end_m


def _resolve_relative_day(raw: str) -> tuple[str, int | None]:
    """Strip a relative day word out of the phrase and return its day offset.

    Returns the remaining text plus the offset, or (raw, None) when the caller
    used no relative word — the two cases differ, because a phrase that is
    *only* a relative word ("tomorrow") is still a valid answer once resolved.
    """
    lowered = raw.lower()
    for phrase, offset in _RELATIVE_DAYS:
        match = re.search(rf"\b{re.escape(phrase)}\b", lowered)
        if match:
            # Cut from the original so any casing elsewhere survives for dateutil.
            remaining = raw[: match.start()] + " " + raw[match.end() :]
            return remaining, offset
    return raw, None


def _resolve_time_of_day(raw: str) -> tuple[str, int | None, bool]:
    """Strip a time-of-day word and return its default hour and PM hint.

    Returns (remaining_text, hour, assume_pm); hour is None when the caller
    used no such word.
    """
    lowered = raw.lower()
    for phrase, hour, assume_pm in _TIME_OF_DAY:
        match = re.search(rf"\b{re.escape(phrase)}\b", lowered)
        if match:
            remaining = raw[: match.start()] + " " + raw[match.end() :]
            return remaining, hour, assume_pm
    return raw, None, False


def format_for_caller(dt: datetime | None, timezone_name: str | None) -> str:
    """Render a stored UTC timestamp the way the patient expects to read it.

    Used for SMS confirmations and reminders — a patient in Los Angeles must
    never be told their appointment is at the UTC hour.
    """
    if dt is None:
        return "the scheduled time"

    # Rows written before timezone-aware storage, or hand-inserted ones, can be
    # naive; they were always meant as UTC.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    local = dt.astimezone(get_zone(timezone_name))
    # %-I strips the leading zero ("3:00 PM", not "03:00 PM") — GNU/BSD only,
    # which covers Linux containers and macOS dev machines.
    try:
        return local.strftime("%A, %B %-d at %-I:%M %p")
    except ValueError:
        return local.strftime("%A, %B %d at %I:%M %p")
