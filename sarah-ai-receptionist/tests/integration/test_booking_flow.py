"""
Integration tests for the booking lifecycle -- these hit a real Postgres via
testcontainers, so they catch the class of bug that unit tests can't:
migrations, foreign keys, unique constraints, tz-aware column semantics.

The paths covered here (book / reschedule / cancel / lookup) were the ones
flagged in the audit as "verified by import + static review, not integration
tests". Now they're really exercised.
"""

import pytest


async def _seed_clinic(db):
    from app.models.clinic import Clinic
    from app.models.organization import Organization

    org = Organization(name="Test Group", slug="test-group")
    db.add(org)
    await db.flush()
    clinic = Clinic(
        organization_id=org.id,
        name="Test Dental",
        slug="test-dental",
        timezone="America/New_York",
    )
    db.add(clinic)
    await db.commit()
    return clinic


@pytest.mark.asyncio
async def test_book_appointment_persists_with_clinic_local_time(db_session):
    """The bug this catches: a naive datetime landing in a TIMESTAMPTZ column
    as UTC. If clinic_time.py's contract ever regresses, this fails against
    real Postgres semantics, not a mock."""
    clinic = await _seed_clinic(db_session)
    from app.services.appointment_service import book_appointment_from_action

    appt = await book_appointment_from_action(
        db_session, clinic.id,
        {"phone": "+15551234567", "name": "Jane Doe", "service": "cleaning",
         "datetime": "tomorrow at 3pm"},
    )
    await db_session.commit()

    assert appt.appointment_datetime.tzinfo is not None, "must be tz-aware"
    assert appt.appointment_datetime.utcoffset().total_seconds() == 0, "must be stored as UTC"

    # Round-trip check: read it back and re-render for the caller. Should
    # come out as 3:00 PM in their clinic's tz.
    from sqlalchemy import select
    from app.models.appointment import Appointment
    from app.core.clinic_time import format_for_caller
    row = await db_session.scalar(select(Appointment).where(Appointment.id == appt.id))
    assert "3:00 PM" in format_for_caller(row.appointment_datetime, "America/New_York")


@pytest.mark.asyncio
async def test_reschedule_finds_and_moves_upcoming_appointment(db_session):
    """Absolute dates (not 'tomorrow at X') so the test never resolves both
    the original and the new time to the same instant when clocks tick."""
    clinic = await _seed_clinic(db_session)
    from app.services.appointment_service import (
        book_appointment_from_action, reschedule_appointment_from_action,
    )

    orig = await book_appointment_from_action(
        db_session, clinic.id,
        {"phone": "+15551110000", "name": "Bob", "service": "checkup",
         "datetime": "December 15 at 10am"},
    )
    await db_session.commit()
    # Capture the value BEFORE reschedule, since `orig` and `updated` refer
    # to the same row and reading `orig.appointment_datetime` after the
    # in-place mutation would just show the new time.
    orig_id = orig.id
    orig_when = orig.appointment_datetime

    updated = await reschedule_appointment_from_action(
        db_session, clinic.id,
        {"phone": "+15551110000", "datetime": "December 20 at 2pm"},
    )
    await db_session.commit()

    assert updated is not None
    assert updated.id == orig_id, "must move the same row, not create a new one"
    assert updated.appointment_datetime != orig_when
    assert updated.reminder_sent is False, "moved appointment resets reminder"


@pytest.mark.asyncio
async def test_reschedule_returns_none_when_no_match(db_session):
    """Never invents a change: a call from an unknown number gets None back,
    not a silently-created appointment. This was the specific invariant flagged
    in the sales-copy audit -- Sarah must not tell a caller their appointment
    moved when nothing actually did."""
    clinic = await _seed_clinic(db_session)
    from app.services.appointment_service import reschedule_appointment_from_action

    result = await reschedule_appointment_from_action(
        db_session, clinic.id,
        {"phone": "+15559999999", "datetime": "tomorrow at 2pm"},
    )
    assert result is None


@pytest.mark.asyncio
async def test_cancel_keeps_row_marks_status(db_session):
    """Cancellation must NOT delete the row -- the freed slot needs to stay
    visible on the dashboard so staff know a spot opened up."""
    clinic = await _seed_clinic(db_session)
    from app.services.appointment_service import (
        book_appointment_from_action, cancel_appointment_from_action,
    )
    from app.models.appointment import Appointment
    from sqlalchemy import select

    appt = await book_appointment_from_action(
        db_session, clinic.id,
        {"phone": "+15552220000", "name": "Cara", "service": "cleaning",
         "datetime": "tomorrow at 4pm"},
    )
    await db_session.commit()

    canceled = await cancel_appointment_from_action(
        db_session, clinic.id, {"phone": "+15552220000"},
    )
    await db_session.commit()

    assert canceled.status == "cancelled"
    still_there = await db_session.scalar(select(Appointment).where(Appointment.id == appt.id))
    assert still_there is not None, "cancelled appointment row must remain"
    assert still_there.status == "cancelled"


@pytest.mark.asyncio
async def test_patient_lookup_recognizes_existing_upcoming_appointment(db_session):
    """The failure this guards: Sarah confabulating recognition of a caller.
    A hit must return a real note including the appointment; a miss must
    explicitly say 'no record'."""
    clinic = await _seed_clinic(db_session)
    from app.services.appointment_service import book_appointment_from_action
    from app.services.patient_lookup import lookup_patient_context

    await book_appointment_from_action(
        db_session, clinic.id,
        {"phone": "+15553330000", "name": "Diana Prince", "service": "cleaning",
         "datetime": "tomorrow at 11am"},
    )
    await db_session.commit()

    hit = await lookup_patient_context(db_session, clinic.id, "+15553330000", "America/New_York")
    assert "Diana" in hit or "existing patient" in hit.lower()
    assert "cleaning" in hit.lower()

    miss = await lookup_patient_context(db_session, clinic.id, "+15559998888", "America/New_York")
    assert "no existing patient" in miss.lower() or "no record" in miss.lower()
    # The critical assertion: nothing about a fake upcoming appointment
    assert "cleaning" not in miss.lower()
