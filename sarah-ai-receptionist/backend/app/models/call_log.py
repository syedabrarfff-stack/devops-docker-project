from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    # See app/models/clinic.py — string-only, resolved by SQLAlchemy's mapper
    # registry, never imported at runtime.
    from app.models.clinic import Clinic
    from app.models.patient import Patient


class CallLog(Base, UUIDMixin, TimestampMixin):
    """Complete record of every call handled by Sarah."""
    __tablename__ = "call_logs"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), nullable=True, index=True)

    # Twilio identifiers
    call_sid: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    stream_sid: Mapped[str] = mapped_column(String(100), nullable=True)

    # Call metadata
    caller_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=True)
    exchange_count: Mapped[int] = mapped_column(Integer, default=0)

    # Outcome
    outcome: Mapped[str] = mapped_column(String(50), nullable=True)
    transferred: Mapped[bool] = mapped_column(Boolean, default=False)
    # What actually happened when a transfer was attempted: "connected",
    # "no_answer", "escalated_sms", or "unavailable". `transferred` alone can't
    # distinguish a handoff that worked from one that rang out.
    transfer_result: Mapped[str] = mapped_column(String(30), nullable=True)
    appointment_booked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Recording consent — set once the mandatory disclosure has played (see
    # call_handler.CONSENT_DISCLOSURE). Required before recording in
    # two-party-consent states.
    consent_disclosed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Transcript (encrypted at rest via RDS encryption)
    transcript: Mapped[list] = mapped_column(JSON, default=list)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=True)

    # S3 Recording
    recording_s3_key: Mapped[str] = mapped_column(String(500), nullable=True)
    recording_duration_seconds: Mapped[float] = mapped_column(Float, nullable=True)

    # Latency tracking
    avg_response_ms: Mapped[float] = mapped_column(Float, nullable=True)
    first_token_ms: Mapped[float] = mapped_column(Float, nullable=True)

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="call_logs")
    patient: Mapped["Patient"] = relationship("Patient", back_populates="call_logs")
