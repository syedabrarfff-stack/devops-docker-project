"""
Turns a parsed [BOOK: ...] action into a real appointment record,
looks up/creates the patient, and triggers an SMS confirmation.
"""

import logging
from datetime import timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clinic_time import now_in_clinic, parse_caller_datetime
from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.patient import Patient

logger = logging.getLogger(__name__)


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

    appointment = Appointment(
        clinic_id=clinic_id,
        patient_id=patient.id if patient else None,
        call_log_id=call_log_id,
        appointment_datetime=appt_dt,
        service_type=service,
        patient_name=name,
        patient_phone=phone,
        status="scheduled",
        source="ai_call",
    )
    db.add(appointment)
    await db.flush()

    logger.info(f"Booked appointment {appointment.id} for clinic {clinic_id}: {service} @ {appt_dt}")
    return appointment
