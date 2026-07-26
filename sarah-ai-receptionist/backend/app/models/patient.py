from sqlalchemy import String, Boolean, JSON, ForeignKey, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class Patient(Base, UUIDMixin, TimestampMixin):
    """Patient record. PII fields encrypted at rest (handled by DB/KMS layer)."""
    __tablename__ = "patients"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)

    # PII — encrypted at rest via AWS KMS + RDS encryption
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[str] = mapped_column(String(20), nullable=True)

    # Insurance
    insurance_provider: Mapped[str] = mapped_column(String(100), nullable=True)
    insurance_member_id: Mapped[str] = mapped_column(String(100), nullable=True)

    # Notes
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_new_patient: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="patients")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="patient")
    call_logs: Mapped[list["CallLog"]] = relationship("CallLog", back_populates="patient")
