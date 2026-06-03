from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, JSON, String, Text, UniqueConstraint
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


class JobFailure(JarvisBase):
    __tablename__ = "job_failures"

    job_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open", index=True)
    error: Mapped[str] = mapped_column(Text, nullable=False)
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    last_retry_at: Mapped[datetime | None] = mapped_column(nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
