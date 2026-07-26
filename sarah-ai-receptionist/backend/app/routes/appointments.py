from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_clinic_id, get_current_user
from app.models.appointment import Appointment
from app.services.audit import write_audit_log

router = APIRouter(tags=["appointments"])


class AppointmentOut(BaseModel):
    id: str
    appointment_datetime: datetime
    duration_minutes: int
    service_type: str
    patient_name: str | None
    patient_phone: str | None
    status: str
    source: str

    class Config:
        from_attributes = True


class AppointmentUpdate(BaseModel):
    status: str | None = None
    appointment_datetime: datetime | None = None
    notes: str | None = None


@router.get("", response_model=list[AppointmentOut])
async def list_appointments(
    upcoming_only: bool = Query(default=True),
    clinic_id: str = Depends(get_current_clinic_id),
    db: AsyncSession = Depends(get_db),
):
    filters = [Appointment.clinic_id == clinic_id]
    if upcoming_only:
        filters.append(Appointment.appointment_datetime >= datetime.now(timezone.utc))

    result = await db.execute(
        select(Appointment).where(and_(*filters)).order_by(Appointment.appointment_datetime)
    )
    return result.scalars().all()


@router.patch("/{appointment_id}", response_model=AppointmentOut)
async def update_appointment(
    appointment_id: str,
    payload: AppointmentUpdate,
    request: Request,
    clinic_id: str = Depends(get_current_clinic_id),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id, Appointment.clinic_id == clinic_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    changed_fields = list(payload.model_dump(exclude_unset=True).keys())
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(appointment, field, value)

    await db.flush()

    await write_audit_log(
        db,
        clinic_id=clinic_id,
        actor=current_user.get("email", "unknown"),
        user_id=current_user.get("sub"),
        action="update_appointment",
        resource_type="appointment",
        resource_id=appointment_id,
        ip_address=request.client.host if request.client else None,
        details={"changed_fields": changed_fields},
    )
    return appointment
