from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    REPLIED = "REPLIED"
    DEMO = "DEMO"
    PROPOSAL = "PROPOSAL"
    WON = "WON"
    LOST = "LOST"


class Lead(JarvisBase):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_leads_score_0_100"),
    )

    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status"),
        nullable=False,
        default=LeadStatus.NEW,
        index=True,
    )
    source: Mapped[str | None] = mapped_column(String(100), nullable=True, default="manual")
    pain_points: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enrichment_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    apollo_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    assigned_persona: Mapped[str | None] = mapped_column(String(120), nullable=True)
    outreach_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_contact: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Compatibility fields used by the existing v9 services while vNEXT routes are migrated.
    company: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company_website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    opportunity_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tier: Mapped[str | None] = mapped_column(String(5), nullable=True, default="C")
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    outreach_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_contacted: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


class WorkflowRun(JarvisBase):
    __tablename__ = "workflow_runs"

    workflow_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    workflow_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="running")
    steps_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steps_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
