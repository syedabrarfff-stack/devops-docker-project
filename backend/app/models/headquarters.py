"""HQ-1: Headquarters Action Request — the record of every Captain request
routed through the Headquarters Orchestrator + Execution Engine.

System-level table (no tenant_id), same scope as the Kernel tables it
partners with: audit_log records every step, this table records the
request as a whole (plan, tier, driver/reviewer models, outcome).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.kernel import KernelBase


class HQActionRequest(KernelBase):
    """One Captain request through Headquarters, from message to verified outcome."""
    __tablename__ = "hq_action_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    request_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification
    kind: Mapped[str] = mapped_column(Text, nullable=False, default="status_query")
    # "status_query" (read-only, answered directly) | "change_request" (goes through plan/execute)
    operation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Authority Matrix operation key inferred for this request, e.g. "bug.fix"
    tier: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AUTO | ASK_CAPTAIN | NEVER

    status: Mapped[str] = mapped_column(Text, nullable=False, default="DRAFTED")
    # DRAFTED | PENDING_APPROVAL | REJECTED | EXECUTING | COMPLETED | FAILED | ROLLED_BACK

    plan: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    driver_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_verdict: Mapped[str | None] = mapped_column(Text, nullable=True)

    result: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_commit: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_hq_action_requests_session", "session_id"),
        Index("ix_hq_action_requests_status", "status"),
        Index("ix_hq_action_requests_created", "created_at"),
    )
