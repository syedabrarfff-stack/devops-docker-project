from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class DoNotContact(JarvisBase):
    __tablename__ = "do_not_contact"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_do_not_contact_tenant_email"),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(120), nullable=False, default="unsubscribe")
    source: Mapped[str] = mapped_column(String(120), nullable=False, default="outreach")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    token: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OutreachPauseState(JarvisBase):
    __tablename__ = "outreach_pause_states"
    __table_args__ = (
        UniqueConstraint("tenant_id", "scope", name="uq_outreach_pause_scope"),
    )

    scope: Mapped[str] = mapped_column(String(80), nullable=False, default="global", index=True)
    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paused_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resumed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ProcessedWebhook(JarvisBase):
    __tablename__ = "processed_webhooks"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source", "event_id", name="uq_processed_webhook_event"),
    )

    source: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
