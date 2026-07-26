"""
Turns a parsed [BOOK: ...] action into a real appointment record,
looks up/creates the patient, and triggers an SMS confirmation.
"""

import logging
from datetime import datetime, timezone

from dateutil import parser as dateparser
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.patient import Patient

logger = logging.getLogger(__name__)


async def book_appointment_from_action(
    db: AsyncSession, clinic_id: str, params: dict, call_log_id: str | None = None
) -> Appointment:
    phone = params.get("phone", "").strip()
    name = params.get("name", "Unknown Caller").strip()
    service = params.get("service", "General checkup").strip()
    raw_datetime = params.get("datetime", "")

    try:
        appt_dt = dateparser.parse(raw_datetime, fuzzy=True) if raw_datetime else None
    except (ValueError, OverflowError):
        appt_dt = None
    if appt_dt is None:
        appt_dt = datetime.now(timezone.utc)

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
