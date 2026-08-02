from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    # relationship() resolves these by class name via SQLAlchemy's mapper
    # registry, not by this import — real models never load at runtime here,
    # so there's no risk of the circular import these classes have with each
    # other. This only makes the `Mapped["X"]` forward references resolvable
    # for type checkers and linters.
    from app.models.appointment import Appointment
    from app.models.call_log import CallLog
    from app.models.organization import Organization
    from app.models.patient import Patient
    from app.models.provider import Provider
    from app.models.user import User


class Clinic(Base, UUIDMixin, TimestampMixin):
    """Individual clinic location. All data is scoped by clinic_id."""
    __tablename__ = "clinics"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Twilio
    twilio_phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=True)

    # Escalation. During opening hours a [TRANSFER] hands the live call to
    # transfer_phone_number. Outside them there is nobody to hand it to, so the
    # caller's details are texted to after_hours_escalation_number instead —
    # promising a transfer to an empty office is worse than not offering one.
    transfer_phone_number: Mapped[str] = mapped_column(String(20), nullable=True)
    after_hours_escalation_number: Mapped[str] = mapped_column(String(20), nullable=True)

    # {"mon": [["08:00","18:00"]], "sat": [["09:00","14:00"]], "sun": []}
    # Evaluated in this clinic's `timezone`, never the server's.
    business_hours: Mapped[dict] = mapped_column(JSON, default=dict)

    # Location
    address: Mapped[str] = mapped_column(Text, nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=True)
    country: Mapped[str] = mapped_column(String(50), default="US")
    timezone: Mapped[str] = mapped_column(String(50), default="America/New_York")

    # AI Configuration
    clinic_config: Mapped[dict] = mapped_column(JSON, default=dict)
    sarah_name: Mapped[str] = mapped_column(String(50), default="Sarah")
    greeting_audio_s3_key: Mapped[str] = mapped_column(String(500), nullable=True)

    # Subscription
    plan: Mapped[str] = mapped_column(String(50), default="starter")
    stripe_customer_id: Mapped[str] = mapped_column(String(100), nullable=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="clinics")
    providers: Mapped[list["Provider"]] = relationship("Provider", back_populates="clinic")
    patients: Mapped[list["Patient"]] = relationship("Patient", back_populates="clinic")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="clinic")
    call_logs: Mapped[list["CallLog"]] = relationship("CallLog", back_populates="clinic")
    users: Mapped[list["User"]] = relationship("User", back_populates="clinic")
