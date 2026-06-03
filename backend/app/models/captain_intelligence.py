"""
Captain Intelligence Models — Brain dumps, email analysis, predicted actions, pushbacks.
All tables use UUID PKs and tenant_id for full RLS compatibility.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import JarvisBase


class CaptainBrainDump(JarvisBase):
    """Raw text dumps from Captain parsed into structured intelligence."""

    __tablename__ = "captain_brain_dumps"

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    action_items: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    leads_mentioned: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    decisions_made: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    follow_ups_needed: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    key_insights: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CaptainEmailIntelligence(JarvisBase):
    """Email thread intelligence extracted by JARVIS for Captain review."""

    __tablename__ = "captain_email_intelligence"

    raw_thread: Mapped[str] = mapped_column(Text, nullable=False)
    sender: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    key_asks: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    objections: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    buying_signals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    recommended_next_step: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    urgency_score: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)


class PredictedAction(JarvisBase):
    """AI-predicted high-leverage actions recommended to Captain."""

    __tablename__ = "predicted_actions"

    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    expected_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    effort_level: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    deadline_suggestion: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # PENDING / EXECUTED / DISMISSED


class CaptainPushback(JarvisBase):
    """Log of every decision JARVIS evaluated and its verdict."""

    __tablename__ = "captain_pushbacks"

    decision_text: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)  # APPROVE / CAUTION / PUSHBACK
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0.0)
    risks: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    alternatives: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    final_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    captain_overrode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
