"""
Turns a parsed [BOOK: ...] action into a real appointment record,
looks up/creates the patient, and triggers an SMS confirmation.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clinic_time import now_in_clinic, parse_caller_datetime
from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.provider import Provider

logger = logging.getLogger(__name__)

# Matches Appointment.duration_minutes' column default -- what a booking takes
# when Sarah doesn't capture an explicit length (she never does today).
DEFAULT_DURATION_MINUTES = 60
# How far back to look for appointments that might still be running when the
# new one starts. Comfortably longer than any realistic dental appointment, so
# the overlap scan can't miss a long procedure that began earlier.
_CONFLICT_LOOKBACK_MINUTES = 480


def intervals_overlap(
    start_a: datetime, minutes_a: int | None, start_b: datetime, minutes_b: int | None
) -> bool:
    """Whether two appointments collide, as half-open [start, start+duration)
    intervals -- so a 2:00 appointment ending at 3:00 does NOT conflict with
    one starting at exactly 3:00, which is a normal back-to-back booking."""
    end_a = start_a + timedelta(minutes=minutes_a or DEFAULT_DURATION_MINUTES)
    end_b = start_b + timedelta(minutes=minutes_b or DEFAULT_DURATION_MINUTES)
    return start_a < end_b and start_b < end_a


async def _clinic_capacity(db: AsyncSession, clinic_id: str) -> int:
    """How many appointments a clinic can genuinely run at once.

    There's no explicit chairs/capacity column, so the count of active
    providers is the honest proxy: a practice cannot see more patients
    simultaneously than it has dentists. Floors at 1 so a clinic that hasn't
    entered its providers yet still gets double-booking protection rather
    than none.
    """
    count = await db.scalar(
        select(func.count())
        .select_from(Provider)
        .where(Provider.clinic_id == clinic_id, Provider.is_active.is_(True))
    )
    return max(int(count or 0), 1)


async def _resolve_provider_id(db: AsyncSession, clinic_id: str, provider_name: str | None) -> str | None:
    """Best-effort match of a spoken dentist name ("Dr. Aslam") to a provider
    row. Returns None when nothing matches -- the caller then falls back to
    clinic-wide capacity, which is stricter, so a failed match can never make
    conflict detection more permissive."""
    name = (provider_name or "").strip().lower()
    for prefix in ("dr.", "dr ", "doctor "):
        if name.startswith(prefix):
            name = name[len(prefix) :].strip()
    if not name:
        return None

    result = await db.execute(
        select(Provider).where(Provider.clinic_id == clinic_id, Provider.is_active.is_(True))
    )
    for provider in result.scalars().all():
        if name in provider.name.lower():
            return provider.id
    return None


async def find_booking_conflict(
    db: AsyncSession,
    clinic_id: str,
    start: datetime,
    duration_minutes: int = DEFAULT_DURATION_MINUTES,
    provider_id: str | None = None,
    exclude_appointment_id: str | None = None,
) -> Appointment | None:
    """The existing appointment a proposed booking would collide with, if any.

    Only 'scheduled' appointments count -- cancelled ones free their slot, and
    a needs_review one is already flagged for a human, so it must not cascade
    into blocking every later booking at that time.

    With a known provider, a collision means *that dentist* is busy; two
    different dentists working at the same time is normal, not a conflict.
    Without one (Sarah usually names a dentist but can't resolve an ID), fall
    back to whether the clinic as a whole is at capacity.
    """
    window_start = start - timedelta(minutes=_CONFLICT_LOOKBACK_MINUTES)
    window_end = start + timedelta(minutes=duration_minutes)

    stmt = select(Appointment).where(
        Appointment.clinic_id == clinic_id,
        Appointment.status == "scheduled",
        Appointment.appointment_datetime >= window_start,
        Appointment.appointment_datetime < window_end,
    )
    if exclude_appointment_id:
        stmt = stmt.where(Appointment.id != exclude_appointment_id)

    result = await db.execute(stmt)
    overlapping = [
        appt
        for appt in result.scalars().all()
        if intervals_overlap(start, duration_minutes, appt.appointment_datetime, appt.duration_minutes)
    ]
    if not overlapping:
        return None

    if provider_id:
        return next((a for a in overlapping if a.provider_id == provider_id), None)

    capacity = await _clinic_capacity(db, clinic_id)
    return overlapping[0] if len(overlapping) >= capacity else None


async def book_appointment_from_action(
    db: AsyncSession, clinic_id: str, params: dict, call_log_id: str | None = None
) -> Appointment:
    phone = params.get("phone", "").strip()
    name = params.get("name", "Unknown Caller").strip()
    service = params.get("service", "General checkup").strip()
    raw_datetime = params.get("datetime", "")

    # The caller spoke in the clinic's local time — parsing without it would
    # store the wrong hour (and, near midnight, the wrong day).
    clinic_timezone = await db.scalar(select(Clinic.timezone).where(Clinic.id == clinic_id))

    appt_dt = parse_caller_datetime(raw_datetime, clinic_timezone)
    if appt_dt is None:
        # Falling back to "now" would look like a real appointment starting this
        # second. Park it at the next morning instead — visibly a placeholder
        # the front desk will correct, not a booking that silently looks valid.
        local_next_morning = (now_in_clinic(clinic_timezone) + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        appt_dt = local_next_morning.astimezone(timezone.utc)
        logger.warning(
            f"Unparseable appointment time {raw_datetime!r} for clinic {clinic_id}; "
            f"parked at {appt_dt.isoformat()} for staff review"
        )

    patient = None
    if phone:
        result = await db.execute(
            select(Patient).where(Patient.clinic_id == clinic_id, Patient.phone == phone)
        )
        patient = result.scalar_one_or_none()

    if not patient and phone:
        first, _, last = name.partition(" ")
        patient = Patient(
            clinic_id=clinic_id,
            first_name=first or name,
            last_name=last or "",
            phone=phone,
            is_new_patient=True,
        )
        try:
            # A savepoint, not a full rollback — save_call_transcript already
            # flushed the CallLog row in this same transaction; a bare
            # session.rollback() here would discard that too.
            async with db.begin_nested():
                db.add(patient)
                await db.flush()
        except IntegrityError:
            # A concurrent call for the same number won the race — the unique
            # (clinic_id, phone) constraint caught it. Use their row instead.
            result = await db.execute(
                select(Patient).where(Patient.clinic_id == clinic_id, Patient.phone == phone)
            )
            patient = result.scalar_one_or_none()

    # Sarah tells the caller their time is held, so silently dropping a
    # colliding booking would strand a patient who believes they're booked.
    # Writing it as 'scheduled' anyway would double-book a chair. Flagging it
    # does neither: the request survives, the front desk sees the collision,
    # and a needs_review row is excluded from find_booking_conflict so it
    # can't cascade into blocking every later booking at that time.
    provider_id = await _resolve_provider_id(db, clinic_id, params.get("provider"))
    conflict = await find_booking_conflict(
        db, clinic_id, appt_dt, DEFAULT_DURATION_MINUTES, provider_id=provider_id
    )
    status = "scheduled"
    notes = None
    if conflict is not None:
        status = "needs_review"
        notes = (
            f"Scheduling conflict: overlaps appointment {conflict.id} at "
            f"{conflict.appointment_datetime.isoformat()}. Sarah confirmed this time with the "
            "caller, so contact them to confirm or move it."
        )
        logger.warning(
            f"Booking conflict for clinic {clinic_id} at {appt_dt.isoformat()} "
            f"(overlaps {conflict.id}); flagged needs_review instead of double-booking"
        )

    appointment = Appointment(
        clinic_id=clinic_id,
        patient_id=patient.id if patient else None,
        provider_id=provider_id,
        call_log_id=call_log_id,
        appointment_datetime=appt_dt,
        duration_minutes=DEFAULT_DURATION_MINUTES,
        service_type=service,
        patient_name=name,
        patient_phone=phone,
        status=status,
        notes=notes,
        source="ai_call",
    )
    db.add(appointment)
    await db.flush()

    logger.info(
        f"Booked appointment {appointment.id} for clinic {clinic_id}: {service} @ {appt_dt} "
        f"(status={status})"
    )
    return appointment


async def _match_upcoming_appointment(db: AsyncSession, clinic_id: str, phone: str):
    """The soonest scheduled, still-future appointment for a caller's number.

    Reschedule and cancel both act on 'your appointment' — during the call
    Sarah confirms which one via the lookup, so matching the soonest upcoming
    one is the safe interpretation. Returns None when nothing matches, so the
    caller is never told a change happened that didn't.
    """
    from app.services.patient_lookup import find_upcoming_appointments

    appointments = await find_upcoming_appointments(db, clinic_id, phone)
    return appointments[0] if appointments else None


async def reschedule_appointment_from_action(db: AsyncSession, clinic_id: str, params: dict):
    """Move a caller's upcoming appointment to a new time. Returns the updated
    appointment, or None if no matching one was found."""
    phone = params.get("phone", "").strip()
    appointment = await _match_upcoming_appointment(db, clinic_id, phone)
    if not appointment:
        logger.warning(f"Reschedule requested for clinic {clinic_id} but no upcoming appointment matched")
        return None

    clinic_timezone = await db.scalar(select(Clinic.timezone).where(Clinic.id == clinic_id))
    new_dt = parse_caller_datetime(params.get("datetime", ""), clinic_timezone)
    if new_dt is None:
        logger.warning(f"Reschedule for appointment {appointment.id} had an unparseable new time")
        return None

    # Same protection as booking -- moving onto an occupied slot double-books
    # a chair just as surely as creating a new appointment there does.
    # exclude_appointment_id stops it colliding with its own current row.
    conflict = await find_booking_conflict(
        db,
        clinic_id,
        new_dt,
        appointment.duration_minutes or DEFAULT_DURATION_MINUTES,
        provider_id=appointment.provider_id,
        exclude_appointment_id=appointment.id,
    )
    if conflict is not None:
        appointment.status = "needs_review"
        appointment.notes = (
            f"Scheduling conflict on reschedule: overlaps appointment {conflict.id} at "
            f"{conflict.appointment_datetime.isoformat()}. Sarah confirmed the new time with the "
            "caller, so contact them to confirm or move it."
        )
        logger.warning(
            f"Reschedule conflict for appointment {appointment.id} at {new_dt.isoformat()} "
            f"(overlaps {conflict.id}); flagged needs_review"
        )

    appointment.appointment_datetime = new_dt
    # A moved appointment needs its reminder to fire again for the new time.
    appointment.reminder_sent = False
    await db.flush()
    logger.info(f"Rescheduled appointment {appointment.id} for clinic {clinic_id} to {new_dt}")
    return appointment


async def cancel_appointment_from_action(db: AsyncSession, clinic_id: str, params: dict):
    """Cancel a caller's upcoming appointment. Returns the cancelled appointment,
    or None if none matched. The row is kept (status='cancelled') so the slot
    freeing up is visible on the dashboard rather than silently vanishing."""
    phone = params.get("phone", "").strip()
    appointment = await _match_upcoming_appointment(db, clinic_id, phone)
    if not appointment:
        logger.warning(f"Cancel requested for clinic {clinic_id} but no upcoming appointment matched")
        return None

    appointment.status = "cancelled"
    await db.flush()
    logger.info(f"Cancelled appointment {appointment.id} for clinic {clinic_id}")
    return appointment
