from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class AICostLedger(JarvisBase):
    __tablename__ = "ai_cost_ledger"

    provider: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    department: Mapped[str] = mapped_column(String(120), nullable=False, default="general", index=True)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False, default="general", index=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class InfrastructureCostConfig(JarvisBase):
    __tablename__ = "infrastructure_cost_config"

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    ec2_monthly: Mapped[float] = mapped_column(Float, nullable=False, default=45.0)
    postgres_monthly: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    redis_monthly: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_monthly: Mapped[float] = mapped_column(Float, nullable=False, default=45.0)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
