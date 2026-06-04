"""Sentinel Layer — Continuous 24/7 world observation.

Layer 1 of the Sovereign Adaptive Cadence. Low-cost models monitor AI industry,
competitors, clients, infrastructure, markets, threats. Significant signals
escalate to Provider Sovereign Council or Grand Convergence Council.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import SentinelObservation, SentinelThreat

SIGNAL_SOURCES = [
    "arxiv", "hacker_news", "github_trending", "product_hunt",
    "techcrunch", "ycombinator", "openai_blog", "anthropic_blog",
    "google_deepmind", "aws_blog", "nvidia_blog", "huggingface",
    "reddit_ai", "enterprise_ai_reports", "startup_funding",
    "ai_benchmarks", "new_api_announcements",
]

ESCALATION_THRESHOLDS = {
    "STRONG": True,
    "MEDIUM": True,
    "WEAK": False,
}


async def record_observation(
    db: AsyncSession,
    *,
    source: str,
    category: str,
    signal_strength: str,
    title: str,
    summary: str,
    url: str | None = None,
    raw_data: dict[str, Any] | None = None,
) -> SentinelObservation:
    obs = SentinelObservation(
        source=source,
        category=category,
        signal_strength=signal_strength,
        title=title,
        summary=summary,
        url=url,
        raw_data=raw_data or {},
        escalated=ESCALATION_THRESHOLDS.get(signal_strength, False),
    )
    db.add(obs)
    await db.commit()
    return obs


async def get_pending_escalations(db: AsyncSession) -> list[SentinelObservation]:
    result = await db.execute(
        select(SentinelObservation).where(
            SentinelObservation.escalated == True,
            SentinelObservation.council_triggered == False,
        ).order_by(SentinelObservation.observed_at.desc()).limit(20)
    )
    return result.scalars().all()


async def mark_escalated_to_council(
    db: AsyncSession,
    observation_id: uuid.UUID,
    council_session_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(SentinelObservation).where(SentinelObservation.id == observation_id)
    )
    obs = result.scalar_one_or_none()
    if obs:
        obs.council_triggered = True
        obs.council_session_id = council_session_id
        await db.commit()


async def register_threat(
    db: AsyncSession,
    *,
    threat_type: str,
    threat_name: str,
    severity: str,
    description: str,
    recommended_response: str | None = None,
) -> SentinelThreat:
    threat = SentinelThreat(
        threat_type=threat_type,
        threat_name=threat_name,
        severity=severity,
        description=description,
        recommended_response=recommended_response,
    )
    db.add(threat)
    await db.commit()
    return threat


async def get_active_threats(
    db: AsyncSession,
    severity: str | None = None,
) -> list[SentinelThreat]:
    query = select(SentinelThreat).where(SentinelThreat.status == "ACTIVE")
    if severity:
        query = query.where(SentinelThreat.severity == severity)
    result = await db.execute(query.order_by(SentinelThreat.created_at.desc()))
    return result.scalars().all()
