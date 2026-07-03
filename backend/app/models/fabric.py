"""SQLAlchemy models for the JARVIS v4 AI Fabric (L4).

These are system-level tables — no tenant_id, no JarvisBase.
Created by migration 0039_fabric_tables.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date

from sqlalchemy import (
    UUID, BigInteger, Boolean, Date, DateTime, ForeignKey, Index,
    Integer, Numeric, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class FabricBase(DeclarativeBase):
    """Separate base for fabric tables — no tenant scope."""
    __abstract__ = True


class ModelRegistry(FabricBase):
    """Every AI provider/model with its role, live status, and cost/perf metrics."""
    __tablename__ = "ai_model_registry"

    id: Mapped[uuid.UUID]          = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str]          = mapped_column(Text, nullable=False)
    model_name: Mapped[str]        = mapped_column(Text, nullable=False)
    role: Mapped[str]              = mapped_column(Text, nullable=False)
    status: Mapped[str]            = mapped_column(Text, nullable=False, server_default="active")
    latency_p50: Mapped[float | None]      = mapped_column(Numeric(10, 2), nullable=True)
    latency_p95: Mapped[float | None]      = mapped_column(Numeric(10, 2), nullable=True)
    error_rate: Mapped[float | None]       = mapped_column(Numeric(6, 4), nullable=True, server_default="0.0")
    cost_per_mtok: Mapped[float | None]    = mapped_column(Numeric(10, 6), nullable=True, server_default="0.0")
    availability_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True, server_default="100.0")
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    metrics: Mapped[list[ModelMetrics]] = relationship("ModelMetrics", back_populates="model", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("provider", "model_name", name="uix_model_registry_provider_model"),
        Index("ix_model_registry_role", "role"),
        Index("ix_model_registry_status", "status"),
    )


class ModelMetrics(FabricBase):
    """Daily aggregate metrics per model.  One row per (model_id, execution_date)."""
    __tablename__ = "ai_model_metrics"

    id: Mapped[uuid.UUID]              = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), ForeignKey("ai_model_registry.id", ondelete="CASCADE"), nullable=False)
    execution_date: Mapped[date]       = mapped_column(Date, nullable=False)
    total_calls: Mapped[int]           = mapped_column(Integer, nullable=False, server_default="0")
    successful_calls: Mapped[int]      = mapped_column(Integer, nullable=False, server_default="0")
    failed_calls: Mapped[int]          = mapped_column(Integer, nullable=False, server_default="0")
    avg_latency_ms: Mapped[float | None]   = mapped_column(Numeric(10, 2), nullable=True)
    total_tokens: Mapped[int]          = mapped_column(BigInteger, nullable=False, server_default="0")
    total_cost_usd: Mapped[float]      = mapped_column(Numeric(10, 6), nullable=False, server_default="0.0")
    hallucination_rate: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    quality_score: Mapped[float | None]     = mapped_column(Numeric(4, 3), nullable=True)
    reliability_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    model: Mapped[ModelRegistry] = relationship("ModelRegistry", back_populates="metrics")

    __table_args__ = (
        UniqueConstraint("model_id", "execution_date", name="uix_model_metrics_model_date"),
        Index("ix_model_metrics_date", "execution_date"),
    )


class CouncilAssembly(FabricBase):
    """Records every AI Council session for high-stakes decisions."""
    __tablename__ = "ai_council_assemblies"

    id: Mapped[uuid.UUID]          = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    task_category: Mapped[str]     = mapped_column(Text, nullable=False)
    selected_models: Mapped[list]  = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}")
    task_context: Mapped[dict]     = mapped_column(JSONB, nullable=False, server_default="{}")
    assembled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    final_recommendation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    outcome: Mapped[dict | None]   = mapped_column(JSONB, nullable=True)
    outcome_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    __table_args__ = (
        Index("ix_council_assemblies_decision", "decision_id"),
        Index("ix_council_assemblies_category", "task_category"),
        Index("ix_council_assemblies_assembled", "assembled_at"),
    )
