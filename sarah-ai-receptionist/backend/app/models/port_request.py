"""
Tracking record for a number-portability request.

Porting a phone number from another carrier into Twilio is not a single API
call: it requires a Letter of Authorization (LOA), a copy of the losing
carrier's bill, and 5-10 business days of carrier back-and-forth. This model
holds the state of that process end-to-end so operators can see what stage
each pending clinic port is at without asking Twilio Console every day.

Never holds account passwords or SSNs -- only the identifiers the losing
carrier needs to verify (which are on any bill anyway).
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.clinic import Clinic


class PortRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "port_requests"

    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)

    # The number being ported IN to Twilio. E.164 format.
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Losing carrier information -- what the winning carrier (Twilio) needs to
    # request the transfer. All fields come from the losing carrier's most
    # recent bill, so nothing here is more sensitive than a bill copy.
    losing_carrier_name: Mapped[str] = mapped_column(String(120), nullable=True)
    losing_account_number: Mapped[str] = mapped_column(String(60), nullable=True)
    losing_account_pin: Mapped[str] = mapped_column(String(30), nullable=True)
    billing_name: Mapped[str] = mapped_column(String(200), nullable=True)
    billing_address: Mapped[str] = mapped_column(Text, nullable=True)

    # Twilio's Porting Order id, populated after we submit.
    twilio_port_in_sid: Mapped[str] = mapped_column(String(64), nullable=True, unique=True)

    # Mirrors Twilio's PortIn lifecycle plus our own pre-submission states.
    # draft -> submitted -> pending_documents -> pending_carrier -> completed | failed | canceled
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft", index=True)
    status_details: Mapped[dict] = mapped_column(JSON, default=dict)

    target_completion_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    clinic: Mapped["Clinic"] = relationship("Clinic")
