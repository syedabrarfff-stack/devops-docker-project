from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy import UUID as SUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class SpeedToLeadEvent(JarvisBase):
    __tablename__ = "speed_to_lead_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_type", "source_id", name="uq_speed_to_lead_source"),
    )

    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        SUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    captain_online: Mapped[bool] = mapped_column(nullable=False, default=False)
    action_taken: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    draft_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    draft_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_send_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class MarketPulseItem(JarvisBase):
    __tablename__ = "market_pulse_items"
    __table_args__ = (
        UniqueConstraint("tenant_id", "content_hash", name="uq_market_pulse_content_hash"),
    )

    source: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    relevance_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class OutreachLearning(JarvisBase):
    __tablename__ = "outreach_learnings"

    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    learning: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    applies_to_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False, default="TeachingEngine")

