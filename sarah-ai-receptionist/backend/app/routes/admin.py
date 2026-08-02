"""
Admin panel API — Captain's clinic onboarding + platform-wide analytics.
All routes require the platform_admin role.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, require_admin
from app.models.call_log import CallLog
from app.models.clinic import Clinic
from app.models.organization import Organization
from app.models.user import User
from app.prompts.dental_receptionist import get_default_clinic_config
from app.services.audit import write_audit_log
from app.services.billing_service import create_stripe_customer_and_subscription

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"], dependencies=[Depends(require_admin)])


class OnboardClinicRequest(BaseModel):
    organization_name: str
    clinic_name: str
    clinic_slug: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str = "US"  # ISO 3166-1 alpha-2, e.g. US/GB/CA/AU/AE — drives Twilio number search
    timezone: str = "America/New_York"
    admin_email: str
    admin_password: str
    admin_full_name: str
    auto_buy_twilio_number: bool = True
    area_code: str | None = None
    # Where an in-hours [TRANSFER] is dialled, and who gets texted outside
    # hours. Without these Sarah declines to promise a handoff at all.
    transfer_phone_number: str | None = None
    after_hours_escalation_number: str | None = None
    # {"mon": [["08:00","18:00"]], "sun": []} — evaluated in `timezone`.
    business_hours: dict | None = None


class OnboardClinicResponse(BaseModel):
    organization_id: str
    clinic_id: str
    user_id: str
    twilio_phone_number: str | None


@router.post("/clinics/onboard", response_model=OnboardClinicResponse)
async def onboard_clinic(
    payload: OnboardClinicRequest,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    org = Organization(name=payload.organization_name, slug=_slugify(payload.organization_name))
    db.add(org)
    await db.flush()

    twilio_number = None
    if payload.auto_buy_twilio_number:
        twilio_number = await _buy_twilio_number(payload.area_code, payload.country)

    clinic = Clinic(
        organization_id=org.id,
        name=payload.clinic_name,
        slug=payload.clinic_slug,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        timezone=payload.timezone,
        twilio_phone_number=twilio_number,
        clinic_config=get_default_clinic_config(),
        transfer_phone_number=payload.transfer_phone_number,
        after_hours_escalation_number=payload.after_hours_escalation_number,
        business_hours=payload.business_hours or {},
    )
    db.add(clinic)
    await db.flush()

    user = User(
        organization_id=org.id,
        clinic_id=clinic.id,
        email=payload.admin_email,
        hashed_password=hash_password(payload.admin_password),
        full_name=payload.admin_full_name,
        role="clinic_manager",
    )
    db.add(user)
    await db.flush()

    if twilio_number:
        await _configure_twilio_webhook(twilio_number)

    await create_stripe_customer_and_subscription(db, clinic, payload.admin_email)

    await write_audit_log(
        db,
        clinic_id=clinic.id,
        actor=current_user.get("email", "unknown"),
        user_id=current_user.get("sub"),
        action="onboard_clinic",
        resource_type="clinic",
        resource_id=clinic.id,
        ip_address=request.client.host if request.client else None,
    )

    logger.info(f"Onboarded clinic {clinic.id} ({clinic.name}) with number {twilio_number}")

    return OnboardClinicResponse(
        organization_id=org.id,
        clinic_id=clinic.id,
        user_id=user.id,
        twilio_phone_number=twilio_number,
    )


@router.get("/clinics")
async def list_all_clinics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Clinic).order_by(Clinic.created_at.desc()))
    clinics = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "twilio_phone_number": c.twilio_phone_number,
            "plan": c.plan,
            "is_active": c.is_active,
            "created_at": c.created_at,
        }
        for c in clinics
    ]


@router.delete("/clinics/{clinic_id}/patients/{patient_id}")
async def erase_patient(
    clinic_id: str,
    patient_id: str,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """GDPR/right-to-erasure: removes a patient's PII record, redacts the
    identifying fields left on their appointments, and scrubs their name/phone
    out of any linked call transcripts. This is a best-effort text scrub (exact
    name/phone matches) — it won't catch every way a caller's identity might
    appear in free-form transcript text, but it's real redaction, not a no-op."""
    from app.models.appointment import Appointment
    from app.models.call_log import CallLog
    from app.models.patient import Patient

    result = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.clinic_id == clinic_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    identifiers = [
        v for v in (patient.phone, patient.first_name, patient.last_name, patient.email) if v
    ]

    appt_result = await db.execute(
        select(Appointment).where(Appointment.patient_id == patient_id, Appointment.clinic_id == clinic_id)
    )
    for appt in appt_result.scalars().all():
        appt.patient_name = "[erased]"
        appt.patient_phone = None
        appt.patient_email = None

    call_result = await db.execute(
        select(CallLog).where(CallLog.patient_id == patient_id, CallLog.clinic_id == clinic_id)
    )
    for call_log in call_result.scalars().all():
        redacted_transcript = []
        for turn in call_log.transcript or []:
            content = turn.get("content", "")
            for identifier in identifiers:
                content = content.replace(identifier, "[redacted]")
            redacted_transcript.append({**turn, "content": content})
        call_log.transcript = redacted_transcript
        if call_log.ai_summary:
            for identifier in identifiers:
                call_log.ai_summary = call_log.ai_summary.replace(identifier, "[redacted]")
        call_log.patient_id = None

    await db.delete(patient)
    await db.flush()

    await write_audit_log(
        db,
        clinic_id=clinic_id,
        actor=current_user.get("email", "unknown"),
        user_id=current_user.get("sub"),
        action="erase_patient",
        resource_type="patient",
        resource_id=patient_id,
        ip_address=request.client.host if request.client else None,
    )
    return {"status": "erased"}


@router.get("/analytics")
async def platform_analytics(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_clinics = await db.scalar(select(func.count(Clinic.id)).where(Clinic.is_active == True))
    total_calls_month = await db.scalar(
        select(func.count(CallLog.id)).where(CallLog.started_at >= month_start)
    )
    total_bookings_month = await db.scalar(
        select(func.count(CallLog.id)).where(
            CallLog.started_at >= month_start, CallLog.appointment_booked == True
        )
    )

    return {
        "active_clinics": total_clinics or 0,
        "calls_this_month": total_calls_month or 0,
        "bookings_this_month": total_bookings_month or 0,
    }


def _slugify(name: str) -> str:
    return name.lower().strip().replace(" ", "-").replace("&", "and")[:100]


async def _buy_twilio_number(area_code: str | None, country: str = "US") -> str | None:
    import asyncio

    from app.services.twilio_client import get_twilio_client

    client = get_twilio_client()

    try:
        search_params = {"limit": 1}
        # area codes are a US/CA-only concept; other countries search by country code alone
        if area_code and country.upper() in ("US", "CA"):
            search_params["area_code"] = area_code
        numbers = await asyncio.to_thread(
            lambda: client.available_phone_numbers(country.upper()).local.list(**search_params)
        )
        if not numbers:
            logger.warning(f"No available Twilio numbers found for country={country}")
            return None
        purchased = await asyncio.to_thread(
            client.incoming_phone_numbers.create, phone_number=numbers[0].phone_number
        )
        return purchased.phone_number
    except Exception as e:
        logger.error(f"Failed to buy Twilio number for country={country}: {e}")
        return None


async def _configure_twilio_webhook(phone_number: str):
    import asyncio

    from app.config.settings import get_settings
    from app.services.twilio_client import get_twilio_client

    settings = get_settings()
    client = get_twilio_client()
    webhook_url = f"{settings.app_base_url}/incoming-call"

    try:
        numbers = await asyncio.to_thread(client.incoming_phone_numbers.list, phone_number=phone_number)
        if numbers:
            await asyncio.to_thread(numbers[0].update, voice_url=webhook_url, voice_method="POST")
    except Exception as e:
        logger.error(f"Failed to configure Twilio webhook for {phone_number}: {e}")
