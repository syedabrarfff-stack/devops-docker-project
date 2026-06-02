from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class ScheduledJob(JarvisBase):
    __tablename__ = "scheduled_jobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "job_id", name="uq_scheduled_jobs_tenant_job_id"),
    )

    job_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_args: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    agent: Mapped[str] = mapped_column(String(100), nullable=False, default="jarvis")
    task_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    run_count: Mapped[int] = mapped_column(nullable=False, default=0)
