from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_clinic_id
from app.models.appointment import Appointment

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
        filters.append(Appointment.appointment_datetime >= datetime.utcnow())

    result = await db.execute(
        select(Appointment).where(and_(*filters)).order_by(Appointment.appointment_datetime)
    )
    return result.scalars().all()


@router.patch("/{appointment_id}", response_model=AppointmentOut)
async def update_appointment(
    appointment_id: str,
    payload: AppointmentUpdate,
    clinic_id: str = Depends(get_current_clinic_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id, Appointment.clinic_id == clinic_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(appointment, field, value)

    await db.flush()
    return appointment
