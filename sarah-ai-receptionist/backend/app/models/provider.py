from sqlalchemy import String, Boolean, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class Provider(Base, UUIDMixin, TimestampMixin):
    """Dentist or hygienist at a clinic."""
    __tablename__ = "providers"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(100), default="Dr.")
    speciality: Mapped[str] = mapped_column(String(100), nullable=True)
    is_accepting_new_patients: Mapped[bool] = mapped_column(Boolean, default=True)
    availability: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="providers")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="provider")
