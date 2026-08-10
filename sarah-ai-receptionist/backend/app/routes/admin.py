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
    country: str = "SA"  # ISO 3166-1 alpha-2, e.g. SA/AE/US/GB — drives Twilio number search
    timezone: str = "Asia/Riyadh"
    admin_email: str
    admin_password: str
    admin_full_name: str
    auto_buy_twilio_number: bool = True
    area_code: str | None = None
    # A number the clinic already holds in this Twilio account. When set,
    # onboarding wires Sarah's webhook to it instead of buying a new one — this
    # is the "works with your existing number" path (for numbers already in
    # Twilio; porting one in from another carrier is a separate LOA process).
    existing_twilio_number: str | None = None
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
    # Populated when an external side-effect (Twilio purchase, Stripe setup,
    # webhook config) partially failed. The onboarding still succeeded --
    # local rows are durable -- but an operator needs to see and reconcile
    # these instead of them being buried in logs.
    warnings: list[str] = []


async def _create_org_clinic_user(payload: OnboardClinicRequest, db: AsyncSession) -> tuple:
    """Phase 1: create the durable local rows in a single transaction, then
    commit. Everything else is an external side-effect layered on top, so a
    Stripe/Twilio failure never rolls back the org/clinic/user the user just
    paid for creating."""
    org = Organization(name=payload.organization_name, slug=_slugify(payload.organization_name))
    db.add(org)
    await db.flush()

    clinic = Clinic(
        organization_id=org.id,
        name=payload.clinic_name,
        slug=payload.clinic_slug,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        timezone=payload.timezone,
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
    return org, clinic, user


@router.post("/clinics/onboard", response_model=OnboardClinicResponse)
async def onboard_clinic(
    payload: OnboardClinicRequest,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Onboards a clinic in phases, each committed before the next runs.

    Why: the previous flow purchased a Twilio number and created a Stripe
    Customer *inside* the same transaction as the org/clinic/user inserts.
    Any error after those external calls -- a UNIQUE-violation on the slug,
    a downstream exception -- rolled the whole transaction back and left the
    purchased Twilio number and Stripe Customer orphaned with zero local
    record. Real money spent, silently.

    Phased:
      1. Local rows: org/clinic/user, committed.
      2. Twilio: attach an existing number OR purchase one, then wire the
         voice webhook. Failure is a warning, not a rollback -- a clinic
         without a number is fixable, an orphaned number that keeps billing
         is not.
      3. Stripe: real Customer + Subscription against the configured Price.
         Same warning-not-rollback rule.
    """
    warnings: list[str] = []

    # Phase 1: durable local state.
    org, clinic, user = await _create_org_clinic_user(payload, db)
    await db.commit()
    logger.info(f"Onboarding clinic {clinic.id} ({clinic.name}) -- local rows committed")

    # Phase 2: Twilio. Each sub-step is guarded so a partial failure leaves a
    # visible warning, not an orphaned purchase or a number with no webhook.
    twilio_number: str | None = None
    if payload.existing_twilio_number:
        twilio_number = payload.existing_twilio_number.strip()
    elif payload.auto_buy_twilio_number and payload.country.upper() == "SA":
        # Buying a Saudi-local Twilio number outright requires a pre-approved
        # Twilio Regulatory Bundle (business registration + address docs) --
        # without one this call returns no available numbers or fails, and
        # either way onboarding stalls silently at exactly the step a real
        # clinic launch depends on. Production Saudi clinics keep their
        # existing carrier number as the number patients dial and forward it
        # to a Twilio number Sarah already holds (existing_twilio_number,
        # above) -- no purchase or port needed for that number at all, since
        # it's never the one given out to patients. Surface that clearly
        # instead of attempting a purchase likely to fail.
        warnings.append(
            "Skipped auto-buying a Saudi Twilio number: Twilio requires an approved "
            "Regulatory Bundle for SA local numbers, which onboarding cannot obtain "
            "automatically. Use existing_twilio_number instead -- the clinic keeps "
            "answering calls on their own number and forwards them (via their carrier) "
            "to a Twilio number Sarah already holds; no purchase or port is required."
        )
    elif payload.auto_buy_twilio_number:
        try:
            twilio_number = await _buy_twilio_number(payload.area_code, payload.country)
            if not twilio_number:
                warnings.append("No Twilio number was purchased -- none available for the requested criteria.")
        except Exception as e:
            logger.exception(f"Twilio purchase failed for clinic {clinic.id}")
            warnings.append(f"Twilio purchase failed: {e}")

    if twilio_number:
        # Persist the number FIRST, before wiring the webhook: if webhook
        # config fails, the number is still ours and visible in the clinic
        # record for manual fix, rather than "we bought it but forgot where."
        clinic.twilio_phone_number = twilio_number
        await db.commit()
        try:
            await _configure_twilio_webhook(twilio_number)
        except Exception as e:
            logger.exception(f"Twilio webhook configuration failed for {twilio_number}")
            warnings.append(
                f"Twilio number {twilio_number} was assigned but the voice webhook could not be "
                f"configured -- inbound calls will not reach Sarah until this is retried: {e}"
            )

    # Phase 3: Stripe (never raises out).
    billing = await create_stripe_customer_and_subscription(db, clinic, payload.admin_email)
    await db.commit()
    if not billing.stripe_created:
        warnings.append(
            f"Stripe subscription not created ({billing.error or 'unknown'}) -- clinic will not be "
            f"billed until this is reconciled."
        )

    await write_audit_log(
        db,
        clinic_id=clinic.id,
        actor=current_user.get("email", "unknown"),
        user_id=current_user.get("sub"),
        action="onboard_clinic",
        resource_type="clinic",
        resource_id=clinic.id,
        ip_address=request.client.host if request.client else None,
        details={"warnings": warnings},
    )
    await db.commit()

    logger.info(f"Onboarded clinic {clinic.id} with number {twilio_number}; warnings={len(warnings)}")

    return OnboardClinicResponse(
        organization_id=org.id,
        clinic_id=clinic.id,
        user_id=user.id,
        twilio_phone_number=twilio_number,
        warnings=warnings,
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


class PortRequestCreate(BaseModel):
    clinic_id: str
    phone_number: str  # E.164, e.g. +13055551234
    losing_carrier_name: str | None = None
    losing_account_number: str | None = None
    losing_account_pin: str | None = None
    billing_name: str | None = None
    billing_address: str | None = None


class PortRequestOut(BaseModel):
    id: str
    clinic_id: str
    phone_number: str
    status: str
    twilio_port_in_sid: str | None
    status_details: dict
    target_completion_date: datetime | None
    completed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/port-requests", response_model=PortRequestOut)
async def create_port_request(
    payload: PortRequestCreate,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a draft port-in request. Submission to Twilio is a separate
    step so operators can review the collected LOA data first."""
    from app.models.port_request import PortRequest

    clinic = await db.scalar(select(Clinic).where(Clinic.id == payload.clinic_id))
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    port = PortRequest(
        clinic_id=payload.clinic_id,
        phone_number=payload.phone_number.strip(),
        losing_carrier_name=payload.losing_carrier_name,
        losing_account_number=payload.losing_account_number,
        losing_account_pin=payload.losing_account_pin,
        billing_name=payload.billing_name,
        billing_address=payload.billing_address,
        status="draft",
    )
    db.add(port)
    await db.flush()

    await write_audit_log(
        db, clinic_id=payload.clinic_id, actor=current_user.get("email", "unknown"),
        user_id=current_user.get("sub"), action="port_request_create",
        resource_type="port_request", resource_id=port.id,
        ip_address=request.client.host if request.client else None,
    )
    return port


@router.post("/port-requests/{port_id}/submit", response_model=PortRequestOut)
async def submit_port_request(
    port_id: str,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Submit a draft port to Twilio. Idempotent -- re-submitting a
    submitted port just refreshes its status."""
    from app.models.port_request import PortRequest
    from app.services.porting_service import PortingError, submit_port_in

    port = await db.scalar(select(PortRequest).where(PortRequest.id == port_id))
    if not port:
        raise HTTPException(status_code=404, detail="Port request not found")
    try:
        await submit_port_in(db, port)
    except PortingError as e:
        # F3: don't leak raw Twilio API error bodies (may carry account-scoped
        # SIDs / partial numbers) to the HTTP client. Log the reason server-side
        # keyed by request_id so the operator can look it up.
        request_id = getattr(request.state, "request_id", "-")
        logger.warning(f"[req={request_id}] Port submit failed for port_id={port_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Port submission failed. Reference id: {request_id}",
        ) from e

    await write_audit_log(
        db, clinic_id=port.clinic_id, actor=current_user.get("email", "unknown"),
        user_id=current_user.get("sub"), action="port_request_submit",
        resource_type="port_request", resource_id=port.id,
        ip_address=request.client.host if request.client else None,
        details={"twilio_port_in_sid": port.twilio_port_in_sid},
    )
    return port


@router.get("/port-requests", response_model=list[PortRequestOut])
async def list_port_requests(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.port_request import PortRequest

    result = await db.execute(select(PortRequest).order_by(PortRequest.created_at.desc()))
    return result.scalars().all()


@router.post("/port-requests/{port_id}/refresh", response_model=PortRequestOut)
async def refresh_port_request(
    port_id: str,
    request: Request,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Pull latest status from Twilio. In production a nightly Arq job
    should do this automatically; this endpoint is for manual refresh."""
    from app.models.port_request import PortRequest
    from app.services.porting_service import PortingError, refresh_port_status

    port = await db.scalar(select(PortRequest).where(PortRequest.id == port_id))
    if not port:
        raise HTTPException(status_code=404, detail="Port request not found")
    try:
        await refresh_port_status(db, port)
    except PortingError as e:
        request_id = getattr(request.state, "request_id", "-")
        logger.warning(f"[req={request_id}] Port refresh failed for port_id={port_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Port refresh failed. Reference id: {request_id}",
        ) from e
    return port


@router.post("/port-requests/{port_id}/cancel", response_model=PortRequestOut)
async def cancel_port_request(
    port_id: str,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.port_request import PortRequest
    from app.services.porting_service import PortingError, cancel_port_in

    port = await db.scalar(select(PortRequest).where(PortRequest.id == port_id))
    if not port:
        raise HTTPException(status_code=404, detail="Port request not found")
    try:
        await cancel_port_in(db, port)
    except PortingError as e:
        request_id = getattr(request.state, "request_id", "-")
        logger.warning(f"[req={request_id}] Port cancel failed for port_id={port_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Port cancellation failed. Reference id: {request_id}",
        ) from e
    await write_audit_log(
        db, clinic_id=port.clinic_id, actor=current_user.get("email", "unknown"),
        user_id=current_user.get("sub"), action="port_request_cancel",
        resource_type="port_request", resource_id=port.id,
        ip_address=request.client.host if request.client else None,
    )
    return port


@router.get("/analytics")
async def platform_analytics(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # .is_(True), not `== True` (E712) or `not Clinic.is_active` — the latter
    # evaluates Python truthiness of the Column object, not SQL, silently
    # turning the filter into a no-op.
    total_clinics = await db.scalar(select(func.count(Clinic.id)).where(Clinic.is_active.is_(True)))
    total_calls_month = await db.scalar(
        select(func.count(CallLog.id)).where(CallLog.started_at >= month_start)
    )
    total_bookings_month = await db.scalar(
        select(func.count(CallLog.id)).where(
            CallLog.started_at >= month_start, CallLog.appointment_booked.is_(True)
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
