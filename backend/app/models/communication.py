from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy import UUID as SUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class CommunicationChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"


class CommunicationDirection(str, enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class CommunicationEvent(JarvisBase):
    """Unified communication ledger for SES and WhatsApp transport events.

    This is intentionally transport-level only. Psychology, memory, council, and
    proposal logic stay in the existing AIONX organs and are linked here.
    """

    __tablename__ = "communication_events"
    __table_args__ = (
        Index("idx_communication_events_channel_created", "channel", "created_at"),
        Index("idx_communication_events_lead_created", "lead_id", "created_at"),
        Index("idx_communication_events_external", "transport", "external_message_id"),
    )

    channel: Mapped[CommunicationChannel] = mapped_column(
        Enum(CommunicationChannel, name="communication_channel"),
        nullable=False,
        index=True,
    )
    direction: Mapped[CommunicationDirection] = mapped_column(
        Enum(CommunicationDirection, name="communication_direction"),
        nullable=False,
        index=True,
    )
    transport: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    external_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    from_address: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    to_address: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(SUUID(as_uuid=True), nullable=True, index=True)
    contact_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="received", index=True)
    hia_persona: Mapped[str] = mapped_column(String(120), nullable=False, default="Joseph David")
    decision_id: Mapped[uuid.UUID | None] = mapped_column(SUUID(as_uuid=True), nullable=True, index=True)
    twin_interaction_id: Mapped[uuid.UUID | None] = mapped_column(SUUID(as_uuid=True), nullable=True, index=True)
    processing_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class CommunicationChannelStatus(JarvisBase):
    """Current readiness snapshot for a communication provider."""

    __tablename__ = "communication_channel_status"
    __table_args__ = (
        UniqueConstraint("tenant_id", "channel", "provider", name="uq_communication_channel_provider"),
    )

    channel: Mapped[CommunicationChannel] = mapped_column(
        Enum(CommunicationChannel, name="communication_channel"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    identity: Mapped[str | None] = mapped_column(String(300), nullable=True)
    configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown", index=True)
    blocker_code: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    required_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
