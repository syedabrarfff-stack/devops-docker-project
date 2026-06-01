from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, JSON, String, Text
from sqlalchemy import UUID as SUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalRequest(JarvisBase):
    __tablename__ = "approval_requests"

    action_type: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(30), nullable=True, default="MEDIUM", index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"),
        nullable=False,
        default=ApprovalStatus.PENDING,
        index=True,
    )
    raised_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Compatibility fields used by the existing approvals UI and authority service.
    estimated_cost: Mapped[str | None] = mapped_column(String(80), nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    risks: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    captain_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(JarvisBase):
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(SUUID(as_uuid=True), nullable=True, index=True)
    action: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(SUUID(as_uuid=True), nullable=True, index=True)
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_addr: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Compatibility fields used by existing services.
    actor: Mapped[str | None] = mapped_column(String(120), nullable=True, default="JARVIS")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(SUUID(as_uuid=True), nullable=True, index=True)
