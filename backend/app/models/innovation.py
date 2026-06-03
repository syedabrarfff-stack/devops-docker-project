from __future__ import annotations

import enum

from sqlalchemy import Boolean, CheckConstraint, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JarvisBase


class InnovationStatus(str, enum.Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    IMPLEMENTING = "implementing"
    DEPLOYED = "deployed"


class InnovationQueueItem(JarvisBase):
    __tablename__ = "innovation_queue"
    __table_args__ = (
        CheckConstraint("impact_score >= 0 AND impact_score <= 100", name="ck_innovation_impact_0_100"),
        CheckConstraint("feasibility_score >= 0 AND feasibility_score <= 100", name="ck_innovation_feasibility_0_100"),
        CheckConstraint("priority_score >= 0 AND priority_score <= 100", name="ck_innovation_priority_0_100"),
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    feasibility_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    status: Mapped[InnovationStatus] = mapped_column(
        String(30),
        nullable=False,
        default=InnovationStatus.PROPOSED.value,
        index=True,
    )
    proposed_by: Mapped[str] = mapped_column(String(120), nullable=False, default="JARVIS")
    council_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
