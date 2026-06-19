from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class CivilizationLedger(JarvisBase):
    __tablename__ = "civilization_ledger"
    __table_args__ = (
        UniqueConstraint("tenant_id", "record_hash", name="uq_civilization_ledger_hash"),
        Index("ix_civilization_ledger_tenant_event_type", "tenant_id", "event_type"),
    )

    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(String(120), nullable=False, default="operational")
    milestone: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    actors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    data_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    event_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
