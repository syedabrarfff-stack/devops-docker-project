from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy import UUID as SUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import JarvisBase


class OutreachChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    LINKEDIN = "LINKEDIN"
    WHATSAPP = "WHATSAPP"


class OutreachStatus(str, enum.Enum):
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    REPLIED = "REPLIED"
    BOUNCED = "BOUNCED"
    SKIPPED = "SKIPPED"


class FollowUpStatus(str, enum.Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class ReplyClassification(str, enum.Enum):
    INTERESTED = "INTERESTED"
    QUESTION = "QUESTION"
    NOT_NOW = "NOT_NOW"
    NO = "NO"
    OUT_OF_OFFICE = "OUT_OF_OFFICE"
    UNKNOWN = "UNKNOWN"


class OutreachLog(JarvisBase):
    __tablename__ = "outreach_log"

    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[OutreachChannel] = mapped_column(
        Enum(OutreachChannel, name="outreach_channel"),
        nullable=False,
        default=OutreachChannel.EMAIL,
    )
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_from_persona: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[OutreachStatus] = mapped_column(
        Enum(OutreachStatus, name="outreach_status"),
        nullable=False,
        default=OutreachStatus.SENT,
        index=True,
    )
    sequence_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    skip_reason: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)


class EmailTracking(JarvisBase):
    __tablename__ = "email_tracking"

    outreach_id: Mapped[uuid.UUID | None] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("outreach_log.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bounce_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReplyLog(JarvisBase):
    __tablename__ = "reply_log"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outreach_id: Mapped[uuid.UUID | None] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("outreach_log.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    from_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[ReplyClassification] = mapped_column(
        Enum(ReplyClassification, name="reply_classification"),
        nullable=False,
        default=ReplyClassification.UNKNOWN,
        index=True,
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    action_taken: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    response_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class FollowUpQueue(JarvisBase):
    __tablename__ = "follow_up_queue"

    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    sequence_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[FollowUpStatus] = mapped_column(
        Enum(FollowUpStatus, name="follow_up_status"),
        nullable=False,
        default=FollowUpStatus.PENDING,
        index=True,
    )


class OutreachSequence(JarvisBase):
    """Compatibility model for existing outreach sequence services."""

    __tablename__ = "outreach_sequences"

    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_company_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    service_offered: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    emails_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    emails_opened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    replies_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meetings_booked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    emails = relationship("OutreachEmail", back_populates="sequence")


class OutreachEmail(JarvisBase):
    """Compatibility model for existing scheduled email execution services."""

    __tablename__ = "outreach_emails"

    sequence_id: Mapped[uuid.UUID | None] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("outreach_sequences.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), nullable=True, index=True)
    to_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled", index=True)
    personalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    sequence = relationship("OutreachSequence", back_populates="emails")
