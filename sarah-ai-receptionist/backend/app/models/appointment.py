from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class Appointment(Base, UUIDMixin, TimestampMixin):
    """Appointment booking record."""
    __tablename__ = "appointments"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), nullable=True, index=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), nullable=True)
    call_log_id: Mapped[str] = mapped_column(ForeignKey("call_logs.id"), nullable=True)

    # Scheduling
    appointment_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    service_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Patient info (for new patients before record created)
    patient_name: Mapped[str] = mapped_column(String(255), nullable=True)
    patient_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    patient_email: Mapped[str] = mapped_column(String(255), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="ai_call")

    # Confirmation
    confirmation_sms_sent: Mapped[bool] = mapped_column(default=False)
    reminder_sent: Mapped[bool] = mapped_column(default=False)

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="appointments")
    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    provider: Mapped["Provider"] = relationship("Provider", back_populates="appointments")
