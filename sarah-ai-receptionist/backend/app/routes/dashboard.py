from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_clinic_id, get_current_user
from app.models.appointment import Appointment
from app.models.call_log import CallLog
from app.models.clinic import Clinic
from app.services.audit import write_audit_log

router = APIRouter(tags=["dashboard"])


class StatsOut(BaseModel):
    calls_today: int
    calls_this_week: int
    appointments_booked_today: int
    transfers_today: int
    avg_response_ms: float | None


class CallLogOut(BaseModel):
    id: str
    call_sid: str
    caller_phone: str | None
    started_at: datetime
    duration_seconds: float | None
    outcome: str | None
    transferred: bool
    transfer_result: str | None = None
    appointment_booked: bool
    ai_summary: str | None
    exchange_count: int = 0

    class Config:
        from_attributes = True


class CallLogDetailOut(CallLogOut):
    transcript: list
    recording_s3_key: str | None


@router.get("/stats", response_model=StatsOut)
async def get_stats(clinic_id: str = Depends(get_current_clinic_id), db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    calls_today = await db.scalar(
        select(func.count(CallLog.id)).where(CallLog.clinic_id == clinic_id, CallLog.started_at >= today_start)
    )
    calls_this_week = await db.scalar(
        select(func.count(CallLog.id)).where(CallLog.clinic_id == clinic_id, CallLog.started_at >= week_start)
    )
    booked_today = await db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id, Appointment.created_at >= today_start
        )
    )
    transfers_today = await db.scalar(
        select(func.count(CallLog.id)).where(
            CallLog.clinic_id == clinic_id, CallLog.started_at >= today_start, CallLog.transferred == True
        )
    )
    avg_latency = await db.scalar(
        select(func.avg(CallLog.avg_response_ms)).where(
            CallLog.clinic_id == clinic_id, CallLog.started_at >= today_start
        )
    )

    return StatsOut(
        calls_today=calls_today or 0,
        calls_this_week=calls_this_week or 0,
        appointments_booked_today=booked_today or 0,
        transfers_today=transfers_today or 0,
        avg_response_ms=avg_latency,
    )


@router.get("/calls", response_model=list[CallLogOut])
async def list_calls(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    clinic_id: str = Depends(get_current_clinic_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CallLog)
        .where(CallLog.clinic_id == clinic_id)
        .order_by(CallLog.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/calls/{call_log_id}", response_model=CallLogDetailOut)
async def get_call_detail(
    call_log_id: str,
    request: Request,
    clinic_id: str = Depends(get_current_clinic_id),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CallLog).where(CallLog.id == call_log_id, CallLog.clinic_id == clinic_id)
    )
    call_log = result.scalar_one_or_none()
    if not call_log:
        raise HTTPException(status_code=404, detail="Call not found")

    await write_audit_log(
        db,
        clinic_id=clinic_id,
        actor=current_user.get("email", "unknown"),
        user_id=current_user.get("sub"),
        action="view_call_transcript",
        resource_type="call_log",
        resource_id=call_log_id,
        ip_address=request.client.host if request.client else None,
    )
    return call_log


@router.get("/calls/{call_log_id}/recording-url")
async def get_call_recording_url(
    call_log_id: str,
    request: Request,
    clinic_id: str = Depends(get_current_clinic_id),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Short-lived presigned S3 URL for the call's audio — never a public link."""
    import asyncio

    import boto3

    from app.config.settings import get_settings

    settings = get_settings()

    result = await db.execute(
        select(CallLog).where(CallLog.id == call_log_id, CallLog.clinic_id == clinic_id)
    )
    call_log = result.scalar_one_or_none()
    if not call_log:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call_log.recording_s3_key:
        raise HTTPException(status_code=404, detail="No recording available for this call")

    s3 = boto3.client("s3", region_name=settings.aws_region)
    url = await asyncio.to_thread(
        s3.generate_presigned_url,
        "get_object",
        Params={"Bucket": settings.s3_bucket_recordings, "Key": call_log.recording_s3_key},
        ExpiresIn=300,
    )

    await write_audit_log(
        db,
        clinic_id=clinic_id,
        actor=current_user.get("email", "unknown"),
        user_id=current_user.get("sub"),
        action="view_call_recording",
        resource_type="call_log",
        resource_id=call_log_id,
        ip_address=request.client.host if request.client else None,
    )
    return {"url": url, "expires_in": 300}


@router.get("/settings")
async def get_clinic_settings(
    clinic_id: str = Depends(get_current_clinic_id), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return {
        "name": clinic.name,
        "address": clinic.address,
        "city": clinic.city,
        "state": clinic.state,
        "timezone": clinic.timezone,
        "sarah_name": clinic.sarah_name,
        "clinic_config": clinic.clinic_config,
        "twilio_phone_number": clinic.twilio_phone_number,
        "transfer_phone_number": clinic.transfer_phone_number,
        "after_hours_escalation_number": clinic.after_hours_escalation_number,
        "business_hours": clinic.business_hours,
    }


@router.patch("/settings")
async def update_clinic_settings(
    payload: dict,
    request: Request,
    clinic_id: str = Depends(get_current_clinic_id),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    allowed_fields = {
        "name", "address", "city", "state", "timezone", "sarah_name", "clinic_config",
        "transfer_phone_number", "after_hours_escalation_number", "business_hours",
    }
    changed_fields = []
    for field, value in payload.items():
        if field in allowed_fields:
            setattr(clinic, field, value)
            changed_fields.append(field)

    await db.flush()

    await write_audit_log(
        db,
        clinic_id=clinic_id,
        actor=current_user.get("email", "unknown"),
        user_id=current_user.get("sub"),
        action="update_clinic_settings",
        resource_type="clinic",
        resource_id=clinic_id,
        ip_address=request.client.host if request.client else None,
        details={"changed_fields": changed_fields},
    )
    return {"status": "updated"}
