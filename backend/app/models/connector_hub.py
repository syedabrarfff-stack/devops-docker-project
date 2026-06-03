"""
Connector Hub SQLAlchemy models.
Tracks daily ingestion runs and individual data packages from the GitHub bridge.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String
from sqlalchemy import UUID as SUUID
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

try:
    from sqlalchemy.dialects.postgresql import JSONB as JSONB_TYPE
    _json_type = JSONB_TYPE
except ImportError:
    from sqlalchemy import JSON as _json_type  # type: ignore[assignment]

from app.models.base import JarvisBase


class ConnectorHubIngestion(JarvisBase):
    """
    One record per tenant per day — tracks the full ingestion run
    from /jarvis-data/daily/YYYY-MM-DD/ into JARVIS.
    """
    __tablename__ = "connector_hub_ingestions"

    # Override base created_at/updated_at to avoid having updated_at here
    date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    leads_processed: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    sequences_loaded: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    decks_matched: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    intelligence_reports: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    council_approvals: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    council_revisions: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    outreach_triggered: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    summary: Mapped[dict | None] = mapped_column(_json_type, nullable=True)


class ConnectorHubPackage(JarvisBase):
    """
    Individual data package record — one per file per ingestion run.
    Tracks the raw data received, processing status, and AI Council verdict.
    """
    __tablename__ = "connector_hub_packages"

    package_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    package_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="leads|sequences|decks|invoices|calendar|market_report|intelligence"
    )
    raw_data: Mapped[dict | None] = mapped_column(_json_type, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    council_verdict: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="APPROVE|REVISE|REJECT"
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
