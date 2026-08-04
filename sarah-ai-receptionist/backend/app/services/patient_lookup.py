"""
Mid-call patient + appointment lookup.

Sarah's prompt has always offered a [LOOKUP_PATIENT] tag, but nothing handled
it — she would emit it and get no answer back, then either stall or invent one
("yes, I see you in our system") to a real patient about their own record. This
turns the tag into a real database read whose result is fed back into the
conversation, and is the same lookup reschedule/cancel rely on to find the
appointment a caller is talking about.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clinic_time import format_for_caller
from app.models.appointment import Appointment
from app.models.patient import Patient

logger = logging.getLogger(__name__)


async def find_upcoming_appointments(
    db: AsyncSession, clinic_id: str, phone: str
) -> list[Appointment]:
    """Scheduled, still-future appointments for a phone number, soonest first.

    Matched on the appointment's own patient_phone rather than the patient row,
    so a booking made before a patient record existed is still found.
    """
    from datetime import datetime, timezone

    if not phone or not phone.strip():
        return []
    result = await db.execute(
        select(Appointment)
        .where(
            Appointment.clinic_id == clinic_id,
            Appointment.patient_phone == phone.strip(),
            Appointment.status == "scheduled",
            Appointment.appointment_datetime >= datetime.now(timezone.utc),
        )
        .order_by(Appointment.appointment_datetime)
    )
    return list(result.scalars().all())


async def lookup_patient_context(
    db: AsyncSession, clinic_id: str, phone: str, timezone_name: str | None
) -> str:
    """A plain-language note about who's calling, for injection into the model.

    Deliberately returns prose, not structured data: it becomes a system note
    Sarah paraphrases, so it reads like something a colleague told her rather
    than a database dump. Never invents a match — 'no record' is a valid,
    important answer that stops her from pretending to recognise a stranger.
    """
    if not phone or not phone.strip():
        return "No phone number was captured for this caller, so their records can't be looked up."

    phone = phone.strip()
    patient = await db.scalar(
        select(Patient).where(Patient.clinic_id == clinic_id, Patient.phone == phone)
    )
    appointments = await find_upcoming_appointments(db, clinic_id, phone)

    parts: list[str] = []
    if patient:
        name = f"{patient.first_name} {patient.last_name}".strip()
        parts.append(f"This caller matches an existing patient: {name or 'name on file not set'}.")
        if patient.insurance_provider:
            parts.append(f"Insurance on file: {patient.insurance_provider}.")
    else:
        parts.append("No existing patient record matches this caller's number — treat as new.")

    if appointments:
        listed = "; ".join(
            f"{a.service_type} on {format_for_caller(a.appointment_datetime, timezone_name)}"
            for a in appointments[:5]
        )
        parts.append(f"Upcoming appointment(s): {listed}.")
    else:
        parts.append("No upcoming appointments are on file for this number.")

    logger.info(
        f"Patient lookup for clinic {clinic_id}: matched={bool(patient)}, "
        f"upcoming={len(appointments)}"
    )
    return " ".join(parts)
