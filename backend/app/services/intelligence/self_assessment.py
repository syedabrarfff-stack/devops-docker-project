"""
JARVIS Self-Assessment Engine — evaluates operational performance across 8 dimensions
and produces a scored grade report with priority improvement actions.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, set_tenant_context

logger = logging.getLogger(__name__)

# ── Grading scale ─────────────────────────────────────────────────────────────

def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 45:
        return "D"
    return "F"


def _overall_letter(scores: list[float]) -> tuple[str, float]:
    avg = sum(scores) / len(scores) if scores else 0.0
    return _grade(avg), round(avg, 2)


# ── Dimension assessors ───────────────────────────────────────────────────────

async def _assess_lead_generation(session: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    from app.models.lead import Lead
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    result = await session.execute(
        select(func.count()).select_from(Lead).where(
            Lead.tenant_id == tenant_id,
            Lead.created_at >= cutoff,
        )
    )
    count = result.scalar() or 0
    score = min(100.0, count * 5.0)  # 20 leads/week = 100
    grade = _grade(score)
    return {
        "dimension": "lead_generation",
        "grade": grade,
        "score": round(score, 2),
        "raw_value": count,
        "target": "20+ leads/week",
        "gap": f"{max(0, 20 - count)} additional leads needed this week" if count < 20 else None,
        "action": (
            "Increase Apollo outreach campaigns and activate LinkedIn scraping" if count < 10
            else "Maintain cadence; explore new lead sources for diversity"
        ),
    }


async def _assess_outreach_effectiveness(session: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    from app.models.outreach import OutreachLog, OutreachStatus
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    try:
        sent_result = await session.execute(
            select(func.count()).select_from(OutreachLog).where(
                OutreachLog.tenant_id == tenant_id,
                OutreachLog.sent_at >= cutoff,
            )
        )
        sent = sent_result.scalar() or 0
        replied_result = await session.execute(
            select(func.count()).select_from(OutreachLog).where(
                OutreachLog.tenant_id == tenant_id,
                OutreachLog.sent_at >= cutoff,
                OutreachLog.status == OutreachStatus.REPLIED,
            )
        )
        replied = replied_result.scalar() or 0
    except Exception:
        sent, replied = 0, 0

    ratio = (replied / sent) if sent > 0 else 0.0
    score = min(100.0, ratio * 500.0)  # 20% reply rate = 100
    return {
        "dimension": "outreach_effectiveness",
        "grade": _grade(score),
        "score": round(score, 2),
        "raw_value": {"sent": sent, "replied": replied, "reply_rate": round(ratio, 3)},
        "target": "15-20% reply rate",
        "gap": f"Reply rate at {ratio:.1%} — target is 15%+" if ratio < 0.15 else None,
        "action": (
            "A/B test subject lines and personalise first-line hooks"
            if ratio < 0.10 else "Optimise follow-up timing and sequence length"
        ),
    }


async def _assess_proposal_quality(session: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    from app.models.lead import Lead, LeadStatus
    proposals = (await session.execute(
        select(func.count()).select_from(Lead).where(
            Lead.tenant_id == tenant_id,
            Lead.status.in_([LeadStatus.PROPOSAL, LeadStatus.WON]),
        )
    )).scalar() or 0
    won = (await session.execute(
        select(func.count()).select_from(Lead).where(
            Lead.tenant_id == tenant_id,
            Lead.status == LeadStatus.WON,
        )
    )).scalar() or 0

    ratio = (won / proposals) if proposals > 0 else 0.0
    score = min(100.0, ratio * 333.0)  # 30% win rate = 100
    return {
        "dimension": "proposal_quality",
        "grade": _grade(score),
        "score": round(score, 2),
        "raw_value": {"proposals": proposals, "won": won, "win_rate": round(ratio, 3)},
        "target": "25-30% proposal win rate",
        "gap": f"Win rate at {ratio:.1%} — target is 25%+" if ratio < 0.25 else None,
        "action": (
            "Improve proposal personalisation and pricing tier clarity"
            if ratio < 0.15 else "Strengthen follow-up sequence post-proposal delivery"
        ),
    }


async def _assess_revenue_momentum(session: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    from app.models.lead import Lead, LeadStatus
    won = (await session.execute(
        select(func.count()).select_from(Lead).where(
            Lead.tenant_id == tenant_id,
            Lead.status == LeadStatus.WON,
        )
    )).scalar() or 0
    proxy_mrr = won * 4_500.0
    # Target: $10,000 MRR = 100 score
    score = min(100.0, (proxy_mrr / 10_000.0) * 100.0)
    return {
        "dimension": "revenue_momentum",
        "grade": _grade(score),
        "score": round(score, 2),
        "raw_value": {"estimated_mrr": proxy_mrr, "won_clients": won},
        "target": "$10,000+ MRR",
        "gap": f"${10000 - proxy_mrr:,.0f} MRR gap to target" if proxy_mrr < 10_000 else None,
        "action": (
            "Convert existing pipeline to retainer contracts immediately"
            if won == 0 else "Upsell current clients to higher service tiers"
        ),
    }


async def _assess_system_health(session: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    """Score based on the real AI request success rate over the last 7 days.

    Uses AICostLedger — the table the live AI call path (router.py's
    _record_ai_metrics -> economics_service.log_ai_call) actually writes to.
    AIRequestLog/cost_tracker.log_request looks parallel but nothing calls it;
    it's permanently empty.
    """
    try:
        from app.models.economics import AICostLedger
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        total = (await session.execute(
            select(func.count()).select_from(AICostLedger).where(
                AICostLedger.tenant_id == tenant_id,
                AICostLedger.created_at >= cutoff,
            )
        )).scalar() or 0
        failed = (await session.execute(
            select(func.count()).select_from(AICostLedger).where(
                AICostLedger.tenant_id == tenant_id,
                AICostLedger.created_at >= cutoff,
                AICostLedger.success.is_(False),
            )
        )).scalar() or 0
        error_rate = (failed / total) if total > 0 else 0.0
        score = max(0.0, 100.0 - error_rate * 100.0 * 5.0)  # 20% error rate = 0
    except Exception:
        total, failed, error_rate = 0, 0, 0.0
        score = 70.0
    return {
        "dimension": "system_health",
        "grade": _grade(score),
        "score": round(score, 2),
        "raw_value": {"requests_7d": total, "failed_7d": failed, "error_rate": round(error_rate, 3)},
        "target": "Zero critical failures, <1% error rate",
        "gap": f"AI error rate at {error_rate:.1%} — target is <1%" if error_rate > 0.01 else None,
        "action": "Review circuit-breaker logs and ensure all AI providers have healthy status",
    }


async def _assess_intelligence_depth(session: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    try:
        from app.models.memory import Memory  # type: ignore[attr-defined]
        count = (await session.execute(
            select(func.count()).select_from(Memory).where(Memory.tenant_id == tenant_id)
        )).scalar() or 0
    except Exception:
        count = 0
    score = min(100.0, count * 2.0)  # 50 memories = 100
    return {
        "dimension": "intelligence_depth",
        "grade": _grade(score),
        "score": round(score, 2),
        "raw_value": {"memory_records": count},
        "target": "50+ memory records",
        "gap": f"{max(0, 50 - count)} additional memory records needed" if count < 50 else None,
        "action": (
            "Run memory synthesis on past interactions to build knowledge base"
            if count < 20 else "Enhance memory categorisation and cross-referencing"
        ),
    }


async def _assess_client_satisfaction(session: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    from app.models.lead import Lead, LeadStatus
    won = (await session.execute(
        select(func.count()).select_from(Lead).where(
            Lead.tenant_id == tenant_id, Lead.status == LeadStatus.WON
        )
    )).scalar() or 0
    lost = (await session.execute(
        select(func.count()).select_from(Lead).where(
            Lead.tenant_id == tenant_id, Lead.status == LeadStatus.LOST
        )
    )).scalar() or 0
    total = won + lost
    retention = (won / total) if total > 0 else 1.0
    score = retention * 100.0
    return {
        "dimension": "client_satisfaction",
        "grade": _grade(score),
        "score": round(score, 2),
        "raw_value": {"retained": won, "churned": lost, "retention_rate": round(retention, 3)},
        "target": "85%+ client retention",
        "gap": f"Retention at {retention:.1%} — target is 85%+" if retention < 0.85 else None,
        "action": (
            "Implement proactive health scoring and quarterly business reviews"
            if retention < 0.85 else "Maintain high-touch delivery and expand client scope"
        ),
    }


async def _assess_autonomous_capability(session: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    try:
        from sqlalchemy import text
        total = (await session.execute(
            text("SELECT COUNT(*) FROM autonomous_governance_log WHERE tenant_id = :tenant_id"),
            {"tenant_id": str(tenant_id)},
        )).scalar() or 0
        autonomous = (await session.execute(
            text("SELECT COUNT(*) FROM autonomous_governance_log WHERE tenant_id = :tenant_id AND tier = 1"),
            {"tenant_id": str(tenant_id)},
        )).scalar() or 0
        ratio = (autonomous / total) if total > 0 else 0.5
    except Exception:
        ratio = 0.5
        total = 0
    score = min(100.0, ratio * 100.0 * 1.2)  # 83%+ autonomous = A
    return {
        "dimension": "autonomous_capability",
        "grade": _grade(score),
        "score": round(score, 2),
        "raw_value": {"autonomous_actions": int(ratio * (total or 1)), "total_actions": total},
        "target": "80%+ Tier-1 autonomous execution",
        "gap": f"Autonomy at {ratio:.1%} — target is 80%+" if ratio < 0.80 else None,
        "action": (
            "Expand Tier-1 action catalog and reduce Captain touchpoints for routine tasks"
            if ratio < 0.60 else "Fine-tune governance boundaries for near-autonomous proposals"
        ),
    }


class JarvisSelfAssessment:
    """Evaluates JARVIS performance across 8 operational dimensions."""

    async def run_assessment(self, tenant_id: UUID) -> dict[str, Any]:
        assessors = [
            _assess_lead_generation,
            _assess_outreach_effectiveness,
            _assess_proposal_quality,
            _assess_revenue_momentum,
            _assess_system_health,
            _assess_intelligence_depth,
            _assess_client_satisfaction,
            _assess_autonomous_capability,
        ]

        dimensions: list[dict[str, Any]] = []
        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, str(tenant_id))
            for assessor in assessors:
                try:
                    result = await assessor(session, tenant_id)
                    dimensions.append(result)
                except Exception as exc:
                    logger.warning("Assessor %s failed: %s", assessor.__name__, exc)
                    dimensions.append({
                        "dimension": assessor.__name__.replace("_assess_", ""),
                        "grade": "C",
                        "score": 60.0,
                        "gap": "Assessment data unavailable",
                        "action": "Ensure required data models are populated",
                    })

        scores = [d["score"] for d in dimensions]
        overall_grade, overall_score = _overall_letter(scores)

        strengths = [d["dimension"] for d in dimensions if d["grade"] in ("A", "B")]
        weaknesses = [d["dimension"] for d in dimensions if d["grade"] in ("D", "F")]
        priority_actions = [
            {"dimension": d["dimension"], "action": d.get("action", ""), "grade": d["grade"]}
            for d in sorted(dimensions, key=lambda x: x["score"])[:3]
        ]

        return {
            "overall_grade": overall_grade,
            "overall_score": overall_score,
            "dimensions": dimensions,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "priority_actions": priority_actions,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
            "tenant_id": str(tenant_id),
        }


jarvis_self_assessment = JarvisSelfAssessment()
