"""
Admin panel API — Captain's clinic onboarding + platform-wide analytics.
All routes require the platform_admin role.
"""

import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_admin, hash_password
from app.models.organization import Organization
from app.models.clinic import Clinic
from app.models.user import User
from app.models.call_log import CallLog
from app.prompts.dental_receptionist import get_default_clinic_config

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"], dependencies=[Depends(require_admin)])


class OnboardClinicRequest(BaseModel):
    organization_name: str
    clinic_name: str
    clinic_slug: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    timezone: str = "America/New_York"
    admin_email: str
    admin_password: str
    admin_full_name: str
    auto_buy_twilio_number: bool = True
    area_code: str | None = None


class OnboardClinicResponse(BaseModel):
    organization_id: str
    clinic_id: str
    user_id: str
    twilio_phone_number: str | None


@router.post("/clinics/onboard", response_model=OnboardClinicResponse)
async def onboard_clinic(payload: OnboardClinicRequest, db: AsyncSession = Depends(get_db)):
    org = Organization(name=payload.organization_name, slug=_slugify(payload.organization_name))
    db.add(org)
    await db.flush()

    twilio_number = None
    if payload.auto_buy_twilio_number:
        twilio_number = await _buy_twilio_number(payload.area_code)

    clinic = Clinic(
        organization_id=org.id,
        name=payload.clinic_name,
        slug=payload.clinic_slug,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        timezone=payload.timezone,
        twilio_phone_number=twilio_number,
        clinic_config=get_default_clinic_config(),
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


@router.get("/analytics")
async def platform_analytics(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_clinics = await db.scalar(select(func.count(Clinic.id)).where(Clinic.is_active == True))  # noqa: E712
    total_calls_month = await db.scalar(
        select(func.count(CallLog.id)).where(CallLog.started_at >= month_start)
    )
    total_bookings_month = await db.scalar(
        select(func.count(CallLog.id)).where(
            CallLog.started_at >= month_start, CallLog.appointment_booked == True  # noqa: E712
        )
    )

    return {
        "active_clinics": total_clinics or 0,
        "calls_this_month": total_calls_month or 0,
        "bookings_this_month": total_bookings_month or 0,
    }


def _slugify(name: str) -> str:
    return name.lower().strip().replace(" ", "-").replace("&", "and")[:100]


async def _buy_twilio_number(area_code: str | None) -> str | None:
    from twilio.rest import Client
    from app.config.settings import get_settings

    settings = get_settings()
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    try:
        search_params = {"limit": 1}
        if area_code:
            search_params["area_code"] = area_code
        numbers = client.available_phone_numbers("US").local.list(**search_params)
        if not numbers:
            logger.warning("No available Twilio numbers found")
            return None
        purchased = client.incoming_phone_numbers.create(phone_number=numbers[0].phone_number)
        return purchased.phone_number
    except Exception as e:
        logger.error(f"Failed to buy Twilio number: {e}")
        return None


async def _configure_twilio_webhook(phone_number: str):
    from twilio.rest import Client
    from app.config.settings import get_settings

    settings = get_settings()
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    webhook_url = f"{settings.app_base_url}/incoming-call"

    try:
        numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
        if numbers:
            numbers[0].update(voice_url=webhook_url, voice_method="POST")
    except Exception as e:
        logger.error(f"Failed to configure Twilio webhook for {phone_number}: {e}")
