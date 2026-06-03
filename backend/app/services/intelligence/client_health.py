"""
JARVIS Client Health Scorer — scores active clients across engagement, payment,
satisfaction, and growth dimensions to surface churn risk early.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, set_tenant_context

logger = logging.getLogger(__name__)

# ── Tier thresholds ───────────────────────────────────────────────────────────
_TIER_CHAMPION = 85.0
_TIER_HEALTHY = 70.0
_TIER_AT_RISK = 50.0

# ── Default scoring weights (25 pts each, total 100) ─────────────────────────
_W_PAYMENT = 25.0
_W_ENGAGEMENT = 25.0
_W_SATISFACTION = 25.0
_W_GROWTH = 25.0


def _health_tier(score: float) -> str:
    if score >= _TIER_CHAMPION:
        return "CHAMPION"
    if score >= _TIER_HEALTHY:
        return "HEALTHY"
    if score >= _TIER_AT_RISK:
        return "AT_RISK"
    return "CRITICAL"


def _churn_probability(score: float) -> float:
    """Linear inverse mapping: score 100 → 0.02, score 0 → 0.95."""
    return round(max(0.02, min(0.95, 1.0 - (score / 100.0) * 0.95 + 0.02)), 3)


def _next_touch_date(tier: str) -> str:
    today = date.today()
    offsets = {"CHAMPION": 30, "HEALTHY": 14, "AT_RISK": 7, "CRITICAL": 2}
    return (today + timedelta(days=offsets.get(tier, 14))).isoformat()


def _recommended_actions(tier: str, signals: list[str]) -> list[str]:
    base: dict[str, list[str]] = {
        "CHAMPION": [
            "Request a referral or testimonial",
            "Propose service expansion or upsell",
            "Schedule a quarterly business review",
        ],
        "HEALTHY": [
            "Send a value summary report",
            "Schedule a check-in call this month",
            "Introduce additional service capabilities",
        ],
        "AT_RISK": [
            "Schedule urgent health-check call within 48 hours",
            "Identify and resolve any delivery concerns",
            "Offer a complimentary optimisation audit",
            "Assign dedicated senior account manager",
        ],
        "CRITICAL": [
            "Emergency escalation — Captain review required",
            "Contact immediately and identify root cause of dissatisfaction",
            "Prepare retention offer or service credit proposal",
            "Document all outstanding deliverables and fast-track completion",
        ],
    }
    return base.get(tier, [])


class ClientHealthScorer:
    """Scores individual clients and portfolios for health and churn risk."""

    def score_client(self, client_data: dict[str, Any]) -> dict[str, Any]:
        """Score a single client from a dict of client attributes."""
        signals: list[str] = []

        # ── Payment timeliness (25 pts) ────────────────────────────────────────
        days_overdue = client_data.get("invoice_days_overdue", 0)
        if days_overdue == 0:
            payment_score = 25.0
            signals.append("Payments consistently on time")
        elif days_overdue <= 7:
            payment_score = 18.0
            signals.append(f"Invoice {days_overdue}d overdue — minor delay")
        elif days_overdue <= 30:
            payment_score = 10.0
            signals.append(f"Invoice {days_overdue}d overdue — follow up required")
        else:
            payment_score = 0.0
            signals.append(f"Invoice {days_overdue}d overdue — CRITICAL payment risk")

        # ── Engagement level (25 pts) ──────────────────────────────────────────
        last_activity_days = client_data.get("days_since_last_activity", 30)
        messages_this_month = client_data.get("messages_this_month", 0)
        if last_activity_days <= 7 and messages_this_month >= 5:
            engagement_score = 25.0
            signals.append("High engagement — active communication this week")
        elif last_activity_days <= 14:
            engagement_score = 18.0
            signals.append("Moderate engagement — within 2-week contact window")
        elif last_activity_days <= 30:
            engagement_score = 10.0
            signals.append(f"Low engagement — last activity {last_activity_days}d ago")
        else:
            engagement_score = 3.0
            signals.append(f"No engagement in {last_activity_days}d — at risk of ghosting")

        # ── Deliverable satisfaction (25 pts) ──────────────────────────────────
        satisfaction_rating = client_data.get("satisfaction_rating", 7)  # 1-10 scale
        open_complaints = client_data.get("open_complaints", 0)
        if satisfaction_rating >= 9 and open_complaints == 0:
            satisfaction_score = 25.0
            signals.append("High satisfaction rating with zero open complaints")
        elif satisfaction_rating >= 7 and open_complaints == 0:
            satisfaction_score = 18.0
            signals.append("Good satisfaction — no active issues")
        elif open_complaints > 0:
            satisfaction_score = max(0.0, 15.0 - open_complaints * 5.0)
            signals.append(f"{open_complaints} open complaint(s) — requires resolution")
        else:
            satisfaction_score = max(0.0, satisfaction_rating * 1.5)
            signals.append(f"Satisfaction rating {satisfaction_rating}/10 — room for improvement")

        # ── Growth indicators (25 pts) ─────────────────────────────────────────
        expanded_services = client_data.get("services_expanded", 0)
        upsell_potential = client_data.get("upsell_potential", False)
        contract_months = client_data.get("contract_months_remaining", 1)
        growth_score = 0.0
        if expanded_services > 0:
            growth_score += 10.0
            signals.append(f"Has expanded to {expanded_services} additional service(s)")
        if upsell_potential:
            growth_score += 8.0
            signals.append("Upsell opportunity identified")
        if contract_months >= 6:
            growth_score += 7.0
            signals.append(f"{contract_months} months remaining on contract")
        elif contract_months >= 3:
            growth_score += 4.0
        else:
            signals.append("Contract renewal approaching — renewal conversation needed")

        health_score = round(
            payment_score + engagement_score + satisfaction_score + growth_score, 2
        )
        tier = _health_tier(health_score)

        return {
            "health_score": health_score,
            "health_tier": tier,
            "signals": signals,
            "churn_probability": _churn_probability(health_score),
            "recommended_actions": _recommended_actions(tier, signals),
            "next_touch_date": _next_touch_date(tier),
            "breakdown": {
                "payment_timeliness": round(payment_score, 2),
                "engagement_level": round(engagement_score, 2),
                "deliverable_satisfaction": round(satisfaction_score, 2),
                "growth_indicators": round(growth_score, 2),
            },
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

    async def score_all_clients(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """
        Query all WON leads (proxying for active clients) and score each.
        Returns list of health records sorted by health_score ascending (worst first).
        """
        from app.models.lead import Lead, LeadStatus

        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, str(tenant_id))
            result = await session.execute(
                select(Lead).where(
                    Lead.tenant_id == tenant_id,
                    Lead.status == LeadStatus.WON,
                )
            )
            clients = result.scalars().all()

        scored: list[dict[str, Any]] = []
        for client in clients:
            last_contact_days = 0
            if client.last_contact:
                delta = datetime.now(timezone.utc) - client.last_contact.replace(
                    tzinfo=timezone.utc if client.last_contact.tzinfo is None else None
                ) if client.last_contact.tzinfo is None else datetime.now(timezone.utc) - client.last_contact
                last_contact_days = max(0, delta.days)

            client_data = {
                "client_id": str(client.id),
                "company_name": client.company_name or client.company or "Unknown",
                "invoice_days_overdue": 0,
                "days_since_last_activity": last_contact_days,
                "messages_this_month": max(0, 10 - last_contact_days // 3),
                "satisfaction_rating": 8,
                "open_complaints": 0,
                "services_expanded": 0,
                "upsell_potential": client.score >= 80,
                "contract_months_remaining": 6,
            }
            health = self.score_client(client_data)
            health["client_id"] = str(client.id)
            health["company_name"] = client_data["company_name"]
            scored.append(health)

        return sorted(scored, key=lambda x: x["health_score"])


client_health_scorer = ClientHealthScorer()
