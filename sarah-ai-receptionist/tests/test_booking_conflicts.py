"""
Tests for double-booking protection.

The overlap rule itself is a pure function, so it's tested directly here
without a database. The surrounding query/capacity logic needs real Postgres
and lives in tests/integration/test_booking_flow.py.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.appointment_service import (
    DEFAULT_DURATION_MINUTES,
    intervals_overlap,
)

_BASE = datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc)  # 2:00 PM


def test_identical_times_conflict():
    assert intervals_overlap(_BASE, 60, _BASE, 60) is True


def test_partial_overlap_conflicts():
    # 2:00-3:00 vs 2:30-3:30
    assert intervals_overlap(_BASE, 60, _BASE + timedelta(minutes=30), 60) is True


def test_back_to_back_appointments_do_not_conflict():
    """A 2:00 appointment ending at 3:00 and one starting at exactly 3:00 is
    a normal back-to-back booking, not a collision. Treating half-open
    intervals as closed would block a clinic's entire day."""
    assert intervals_overlap(_BASE, 60, _BASE + timedelta(minutes=60), 60) is False


def test_clearly_separate_times_do_not_conflict():
    assert intervals_overlap(_BASE, 60, _BASE + timedelta(hours=3), 60) is False


def test_overlap_is_symmetric():
    later = _BASE + timedelta(minutes=30)
    assert intervals_overlap(_BASE, 60, later, 60) == intervals_overlap(later, 60, _BASE, 60)


def test_a_long_procedure_started_earlier_still_conflicts():
    """A 2-hour root canal starting at 1:00 is still running at 2:00 -- the
    scan must catch it even though it started before the proposed slot."""
    earlier = _BASE - timedelta(hours=1)
    assert intervals_overlap(_BASE, 60, earlier, 120) is True


def test_missing_duration_falls_back_to_the_default():
    """duration_minutes is nullable in the DB. None must mean the standard
    slot length, not a zero-length appointment that collides with nothing."""
    assert intervals_overlap(_BASE, None, _BASE, None) is True
    assert (
        intervals_overlap(_BASE, None, _BASE + timedelta(minutes=DEFAULT_DURATION_MINUTES), None)
        is False
    )
