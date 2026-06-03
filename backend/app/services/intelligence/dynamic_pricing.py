"""
JARVIS Dynamic Pricing Engine — calculates context-aware pricing for all 30 service divisions
using company size, urgency, geography, complexity, and loyalty signals.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── Base pricing ──────────────────────────────────────────────────────────────

_BASE_PRICES: dict[str, float] = {
    "STARTER": 2_500.0,
    "GROWTH": 5_500.0,
    "ENTERPRISE": 12_000.0,
}

_TIER_FEATURES: dict[str, dict[str, Any]] = {
    "STARTER": {
        "price_per_month": 2_500,
        "project_range": "3,000 – 8,000",
        "team_members": 1,
        "services": 1,
        "response_time": "48h",
        "reporting": "Monthly summary",
        "revisions": 2,
        "best_for": "Solo founders, early-stage startups, single-service needs",
    },
    "GROWTH": {
        "price_per_month": 5_500,
        "project_range": "8,000 – 18,000",
        "team_members": 3,
        "services": 3,
        "response_time": "24h",
        "reporting": "Bi-weekly dashboard",
        "revisions": 4,
        "best_for": "Growing SMBs, multi-service requirements, scaling operations",
    },
    "ENTERPRISE": {
        "price_per_month": 12_000,
        "project_range": "18,000 – 50,000",
        "team_members": "Dedicated team",
        "services": "Unlimited",
        "response_time": "4h",
        "reporting": "Real-time dashboard + weekly calls",
        "revisions": "Unlimited",
        "best_for": "Large enterprises, complex integrations, white-glove delivery",
    },
}

# ── Geography premium/discount map ───────────────────────────────────────────

_GEO_MULTIPLIERS: dict[str, float] = {
    "usa": 0.15,
    "uk": 0.12,
    "uae": 0.18,
    "bahrain": 0.15,
    "qatar": 0.15,
    "saudi arabia": 0.15,
    "australia": 0.10,
    "canada": 0.08,
    "germany": 0.10,
    "netherlands": 0.08,
    "singapore": 0.12,
    "india": -0.10,
    "pakistan": -0.15,
    "nigeria": -0.12,
    "kenya": -0.12,
}


def _determine_tier(lead_data: dict[str, Any]) -> str:
    """Infer service tier from company signals."""
    company_size = str(lead_data.get("company_size", "") or "").lower()
    industry = str(lead_data.get("industry", "") or "").lower()
    score = float(lead_data.get("score", 0) or 0)
    enrichment = lead_data.get("enrichment_data", {}) or {}
    employees = enrichment.get("employee_count", 0) or 0

    enterprise_signals = ["enterprise", "fortune", "corporation", "inc.", "ltd", "plc"]
    if any(s in company_size for s in enterprise_signals) or employees > 500 or score >= 85:
        return "ENTERPRISE"
    if employees > 50 or score >= 65 or any(
        ind in industry for ind in ["saas", "fintech", "healthcare", "logistics", "ecommerce"]
    ):
        return "GROWTH"
    return "STARTER"


def _apply_adjustments(
    base: float,
    tier: str,
    lead_data: dict[str, Any],
    context: dict[str, Any],
) -> tuple[float, list[dict[str, Any]]]:
    adjustments: list[dict[str, Any]] = []
    price = base

    # Company size premium
    enrichment = lead_data.get("enrichment_data", {}) or {}
    employees = enrichment.get("employee_count", 0) or 0
    if employees > 500:
        adj = base * 0.20
        price += adj
        adjustments.append({"factor": "company_size", "adjustment": round(adj, 2), "reason": "Enterprise-scale company (500+ employees)"})
    elif employees < 10:
        adj = -base * 0.10
        price += adj
        adjustments.append({"factor": "company_size", "adjustment": round(adj, 2), "reason": "Early-stage company (<10 employees)"})

    # Urgency premium
    notes = str(lead_data.get("notes", "") or "").lower()
    pain_text = " ".join(str(p) for p in (lead_data.get("pain_points") or []))
    if any(w in notes + pain_text for w in ["urgent", "asap", "immediately", "this week", "deadline"]):
        adj = base * 0.15
        price += adj
        adjustments.append({"factor": "urgency_premium", "adjustment": round(adj, 2), "reason": "Urgent timeline signals detected"})

    # Competitive threat discount
    if context and context.get("competitive_bid", False):
        adj = -base * 0.10
        price += adj
        adjustments.append({"factor": "competitive_threat", "adjustment": round(adj, 2), "reason": "Competitive bid situation — strategic discount applied"})

    # Geography premium
    country = str(lead_data.get("country", "") or context.get("country", "") or "").lower().strip()
    for geo, multiplier in _GEO_MULTIPLIERS.items():
        if geo in country:
            adj = base * multiplier
            price += adj
            direction = "premium" if multiplier > 0 else "discount"
            adjustments.append({"factor": f"geography_{direction}", "adjustment": round(adj, 2), "reason": f"{country.title()} market rate adjustment"})
            break

    # Complexity premium
    if context and context.get("high_complexity", False):
        adj = base * 0.25
        price += adj
        adjustments.append({"factor": "complexity_premium", "adjustment": round(adj, 2), "reason": "High integration complexity flagged"})

    # Loyalty discount for existing clients
    if context and context.get("existing_client", False):
        adj = -base * 0.10
        price += adj
        adjustments.append({"factor": "loyalty_discount", "adjustment": round(adj, 2), "reason": "Existing client loyalty discount"})

    return max(base * 0.60, price), adjustments  # floor at 60% of base


def _build_rationale(tier: str, final: float, base: float, adjustments: list[dict]) -> str:
    delta = final - base
    direction = "above" if delta >= 0 else "below"
    pct = abs(delta / base * 100) if base > 0 else 0
    adj_summary = ", ".join(a["factor"].replace("_", " ") for a in adjustments) if adjustments else "standard base rate"
    return (
        f"Pricing positioned at the {tier} tier (${base:,.0f}/mo base). "
        f"Final price is {pct:.1f}% {direction} base rate based on: {adj_summary}. "
        f"Recommended as a competitive, value-aligned offer for this prospect profile."
    )


def _confidence(adjustments: list[dict], lead_data: dict) -> float:
    score = float(lead_data.get("score", 0) or 0)
    base_conf = min(0.90, 0.50 + score / 200.0)
    # More data signals = higher confidence
    data_fields = sum(1 for k in ["industry", "country", "notes", "company_name"] if lead_data.get(k))
    return round(min(0.95, base_conf + data_fields * 0.02), 2)


class DynamicPricingEngine:
    """Calculates context-aware pricing with multi-factor adjustments."""

    def calculate_price(
        self,
        service_type: str,
        lead_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        tier = _determine_tier(lead_data)
        base = _BASE_PRICES[tier]
        final, adjustments = _apply_adjustments(base, tier, lead_data, context)
        final = round(final, 2)

        return {
            "service_type": service_type,
            "base_price": base,
            "final_price": final,
            "price_tier": tier,
            "adjustments": adjustments,
            "confidence": _confidence(adjustments, lead_data),
            "rationale": _build_rationale(tier, final, base, adjustments),
            "price_range": {
                "low": round(final * 0.90, 2),
                "high": round(final * 1.10, 2),
            },
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_service_catalog_pricing(self) -> dict[str, Any]:
        """Return the full service tier catalog with features and pricing."""
        return {
            "tiers": _TIER_FEATURES,
            "pricing_notes": [
                "All retainer prices are monthly recurring",
                "Project rates billed 50% upfront, 50% on delivery",
                "Minimum engagement: 3 months for retainers",
                "Custom pricing available for multi-year contracts",
                "Enterprise pricing subject to scope review",
            ],
            "add_ons": {
                "priority_support": 500,
                "dedicated_slack_channel": 0,
                "weekly_strategy_calls": 750,
                "white_label_rights": 2000,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


dynamic_pricing_engine = DynamicPricingEngine()
