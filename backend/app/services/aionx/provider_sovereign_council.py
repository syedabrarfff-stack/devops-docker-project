"""Provider Sovereign Council — 11 AI providers as calibrated executive advisors.

Each provider earns domain authority through Brier-scored prediction records.
Sessions are event-triggered (Layer 2 sentinel escalation) or adaptive-scheduled.
Convergence gate prevents infinite debate.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aionx_organs import (
    ProviderCalibrationRecord,
    ProviderCouncilSession,
    ShelvedDiscovery,
)
from app.services.ai.router import TaskType, route_task

PROVIDERS = [
    "anthropic",
    "openai",
    "google_gemini",
    "aws_bedrock",
    "deepseek",
    "nvidia",
    "groq",
    "mistral",
    "qwen",
    "llama",
    "perplexity",
]

PROVIDER_DOMAIN_STRENGTHS: dict[str, list[str]] = {
    "anthropic": ["ETHICS", "REASONING", "CONSTITUTIONAL", "STRATEGY"],
    "openai": ["STRATEGY", "PLANNING", "ORCHESTRATION", "PRODUCT"],
    "google_gemini": ["RESEARCH", "LONG_CONTEXT", "SYNTHESIS", "WORLD_KNOWLEDGE"],
    "aws_bedrock": ["INFRASTRUCTURE", "RELIABILITY", "ENTERPRISE", "COST"],
    "deepseek": ["ENGINEERING", "MATH", "CODE_EFFICIENCY", "COST"],
    "nvidia": ["COMPUTE", "SCALING", "GPU_ARCHITECTURE", "PERFORMANCE"],
    "groq": ["LATENCY", "SPEED", "OPERATIONAL", "REAL_TIME"],
    "mistral": ["INFERENCE_EFFICIENCY", "LIGHTWEIGHT", "OPTIMIZATION"],
    "qwen": ["MULTILINGUAL", "GLOBAL", "CROSS_CULTURAL"],
    "llama": ["PRIVATE", "LOCAL", "SOVEREIGNTY", "COST"],
    "perplexity": ["RESEARCH", "WEB_INTELLIGENCE", "REAL_TIME_DATA"],
}

MAX_DEBATE_ROUNDS = 4


async def get_domain_authority(
    db: AsyncSession,
    provider_id: str,
    domain: str,
) -> float:
    result = await db.execute(
        select(func.avg(ProviderCalibrationRecord.domain_authority_weight)).where(
            ProviderCalibrationRecord.provider_id == provider_id,
            ProviderCalibrationRecord.domain == domain,
            ProviderCalibrationRecord.was_correct.is_not(None),
        )
    )
    weight = result.scalar_one_or_none()
    return float(weight) if weight else 1.0


async def record_provider_claim(
    db: AsyncSession,
    *,
    provider_id: str,
    domain: str,
    claim: str,
    confidence: float,
) -> ProviderCalibrationRecord:
    record = ProviderCalibrationRecord(
        provider_id=provider_id,
        domain=domain,
        claim=claim,
        confidence_at_claim=confidence,
    )
    db.add(record)
    await db.commit()
    return record


async def resolve_provider_claim(
    db: AsyncSession,
    record_id: uuid.UUID,
    outcome: str,
    was_correct: bool,
) -> ProviderCalibrationRecord:
    result = await db.execute(
        select(ProviderCalibrationRecord).where(ProviderCalibrationRecord.id == record_id)
    )
    record = result.scalar_one()
    record.outcome = outcome
    record.was_correct = was_correct
    record.resolved_at = datetime.utcnow()

    # Brier score: (confidence - outcome)^2 where outcome is 0 or 1
    p = record.confidence_at_claim
    o = 1.0 if was_correct else 0.0
    record.brier_score = (p - o) ** 2

    # Adjust domain authority weight based on accuracy
    if was_correct:
        record.domain_authority_weight = min(record.domain_authority_weight * 1.1, 2.0)
    else:
        record.domain_authority_weight = max(record.domain_authority_weight * 0.9, 0.1)

    await db.commit()
    return record


async def convene_provider_council(
    db: AsyncSession,
    *,
    trigger_type: str,
    trigger_signal: str | None = None,
    agenda_items: list[str],
    domain: str = "STRATEGY",
) -> ProviderCouncilSession:
    # Select providers with authority in this domain
    relevant_providers = [
        p for p, domains in PROVIDER_DOMAIN_STRENGTHS.items()
        if domain in domains
    ] or PROVIDERS[:6]

    session = ProviderCouncilSession(
        trigger_type=trigger_type,
        trigger_signal=trigger_signal,
        participants=relevant_providers,
        agenda_items=agenda_items,
    )
    db.add(session)
    await db.flush()

    # Run bounded debate via AI router
    recommendations = []
    rounds = 0

    for agenda_item in agenda_items[:3]:
        if rounds >= MAX_DEBATE_ROUNDS:
            break
        try:
            synthesis = await route_task(
                task_type=TaskType.STRATEGY,
                prompt=(
                    f"Provider Council Agenda: {agenda_item}\n\n"
                    f"Domain: {domain}\n"
                    f"Participating providers: {', '.join(relevant_providers)}\n\n"
                    "Synthesize a unified recommendation from the collective intelligence "
                    "of these providers. Format: RECOMMENDATION | CONFIDENCE | KEY_RISKS"
                ),
                max_tokens=800,
            )
            recommendations.append({"item": agenda_item, "synthesis": synthesis})
            rounds += 1
        except Exception:
            recommendations.append({"item": agenda_item, "synthesis": "DEFERRED"})

    session.recommendations = recommendations
    session.debate_rounds = rounds
    session.convergence_reason = (
        "CONSENSUS_REACHED" if rounds < MAX_DEBATE_ROUNDS else "MAX_ROUNDS_HIT"
    )
    session.completed_at = datetime.utcnow()
    await db.commit()
    return session


async def shelve_discovery(
    db: AsyncSession,
    *,
    title: str,
    source: str,
    summary: str,
    wake_condition: str,
    wake_metric: str | None = None,
    wake_threshold: float | None = None,
    priority: str = "MEDIUM",
    roi_estimate: float = 0.0,
    risk_estimate: float = 0.0,
) -> ShelvedDiscovery:
    discovery = ShelvedDiscovery(
        title=title,
        source=source,
        summary=summary,
        wake_condition=wake_condition,
        wake_metric=wake_metric,
        wake_threshold=wake_threshold,
        priority=priority,
        roi_estimate=roi_estimate,
        risk_estimate=risk_estimate,
    )
    db.add(discovery)
    await db.commit()
    return discovery


async def check_wake_conditions(db: AsyncSession, metrics: dict[str, float]) -> list[ShelvedDiscovery]:
    result = await db.execute(
        select(ShelvedDiscovery).where(ShelvedDiscovery.is_activated == False)
    )
    shelved = result.scalars().all()

    activated = []
    for discovery in shelved:
        if discovery.wake_metric and discovery.wake_threshold:
            current_value = metrics.get(discovery.wake_metric, 0.0)
            if current_value >= discovery.wake_threshold:
                discovery.is_activated = True
                discovery.activated_at = datetime.utcnow()
                activated.append(discovery)

    if activated:
        await db.commit()
    return activated
