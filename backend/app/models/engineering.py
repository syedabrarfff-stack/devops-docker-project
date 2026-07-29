"""SQLAlchemy models for the Headquarters Engineering Organization (Phase 7).

System-level tables — no tenant_id, reuses KernelBase. Created by migration
0042_engineering_org_tables. See docs/architecture/HEADQUARTERS_ENGINEERING_ORG.md.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Text, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.kernel import KernelBase


class EngineeringTaskGraph(KernelBase):
    """One Mission Planner run: an objective decomposed into work packages."""
    __tablename__ = "engineering_task_graphs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    objective_type: Mapped[str] = mapped_column(Text, nullable=False, default="feature")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PLANNING")
    decomposed_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_task_graphs_status_orm", "status"),
        Index("ix_task_graphs_created_orm", "created_at"),
    )


class EngineeringWorkPackage(KernelBase):
    """One department-owned unit of work within a task graph."""
    __tablename__ = "engineering_work_packages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_graph_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engineering_task_graphs.id", ondelete="CASCADE"), nullable=False
    )
    department: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    acceptance_criteria: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    depends_on: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}")
    operation: Mapped[str] = mapped_column(Text, nullable=False, default="bug.fix")
    authority_tier: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")
    kernel_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    draft_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    review_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    deploy_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_work_packages_graph_orm", "task_graph_id"),
        Index("ix_work_packages_department_orm", "department"),
        Index("ix_work_packages_status_orm", "status"),
    )


class WorkPackageStatus:
    PENDING = "PENDING"
    DRAFTING = "DRAFTING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    DEPLOYED = "DEPLOYED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"  # authority tier requires Captain approval


class TaskGraphStatus:
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
