from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class AICouncilSession(JarvisBase):
    __tablename__ = "ai_council_sessions"

    question: Mapped[str] = mapped_column(Text, nullable=False)
    council_type: Mapped[str] = mapped_column(String(80), nullable=False, default="standard", index=True)
    context_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    votes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    result: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    consensus_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    winner_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    quorum_met: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    responses_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_estimate_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class AICouncilMemberWeight(JarvisBase):
    __tablename__ = "ai_council_member_weights"
    __table_args__ = (
        UniqueConstraint("tenant_id", "member_id", name="uq_ai_council_weights_tenant_member"),
    )

    member_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    specialty: Mapped[str] = mapped_column(String(120), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    correct_predictions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wrong_predictions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_adjusted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
