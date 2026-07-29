"""SQLAlchemy models for the JARVIS v4 Runtime Kernel (L3).

These are system-level tables — no tenant_id, no JarvisBase.
They are created by migration 0038_kernel_tables.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date

from sqlalchemy import (
    UUID, BigInteger, Boolean, CheckConstraint, Date, DateTime, Index,
    Integer, Numeric, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class KernelBase(DeclarativeBase):
    """Separate base for kernel tables — no tenant scope."""
    __abstract__ = True


class SystemState(KernelBase):
    """Single source of truth for JARVIS system state. Versioned for OCC."""
    __tablename__ = "system_state"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stage: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    autonomous_action_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index("ix_system_state_stage", "stage"),
        Index("ix_system_state_status", "status"),
    )


class KernelEvent(KernelBase):
    """Event Bus persistence. Append-only — never updated."""
    __tablename__ = "kernel_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_engine: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_kernel_events_type", "event_type"),
        Index("ix_kernel_events_source", "source_engine"),
        Index("ix_kernel_events_created", "created_at"),
    )


class KernelTaskQueue(KernelBase):
    """Priority task queue. priority: 1=CRITICAL, 2=HIGH, 3=NORMAL, 4=LOW."""
    __tablename__ = "kernel_task_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_kernel_task_queue_priority_status", "priority", "status"),
        Index("ix_kernel_task_queue_status", "status"),
    )


class AuditLog(KernelBase):
    """Immutable audit record for every autonomous action. Never updated."""
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_log_actor", "actor"),
        Index("ix_audit_log_action_type", "action_type"),
        Index("ix_audit_log_created", "created_at"),
    )


class HealthSnapshot(KernelBase):
    """30-second poll result from the Health Aggregator per engine."""
    __tablename__ = "health_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_health_snapshots_engine", "engine_name", "created_at"),
    )


class KernelConfig(KernelBase):
    """Feature flags and dynamic thresholds. Hot-reload without redeploy."""
    __tablename__ = "kernel_config"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by: Mapped[str] = mapped_column(Text, nullable=False, default="system")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DecisionRecord(KernelBase):
    """Decision record required before every autonomous action."""
    __tablename__ = "decision_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    business_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    rollback_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reported_to_captain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_decision_records_created", "created_at"),
        Index("ix_decision_records_captain", "reported_to_captain"),
    )


class MemoryEntry(KernelBase):
    """5-layer Executive Memory entry. (layer, key) is unique."""
    __tablename__ = "memory_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    layer: Mapped[str] = mapped_column(Text, nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    retention_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner: Mapped[str] = mapped_column(Text, nullable=False, default="jarvis")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "layer IN ('strategic','operational','technical','customer','financial')",
            name="ck_memory_entries_layer"
        ),
        UniqueConstraint("layer", "key", name="uix_memory_entries_layer_key"),
        Index("ix_memory_entries_layer", "layer"),
    )
