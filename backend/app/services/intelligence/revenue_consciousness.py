"""
JARVIS Revenue Consciousness Engine.

Revenue is not a metric. Revenue is the oxygen of Aliyar Solutions.
Every system, every decision, every AI action must be evaluated through
the lens of its revenue impact — now and compounded over time.

This engine governs:
 - Client Lifetime Value (LTV) computation and optimization
 - Pricing intelligence and tier optimization
 - Revenue velocity tracking and early warning
 - Churn prevention signals and intervention protocols
 - Upsell/cross-sell trigger intelligence
 - Pipeline health scoring
 - Revenue leakage detection
 - Retainer vs project mix optimization
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# ─── PRICING ARCHITECTURE ─────────────────────────────────────────────────────

PRICING_TIERS = {
    "STARTER": {
        "monthly_retainer": 2000,
        "project_minimum": 3000,
        "ideal_client": "Early-stage startup, 1-5 employees, single automation need",
        "services": ["Basic workflow automation", "CRM setup", "Email outreach system"],
        "max_clients_concurrent": 8,
        "target_ltv": 12000,
        "churn_risk": "HIGH",
        "upsell_target": "GROWTH",
        "upsell_trigger_month": 2,
    },
    "GROWTH": {
        "monthly_retainer": 4000,
        "project_minimum": 8000,
        "ideal_client": "Growing SMB, 10-50 employees, multi-system integration needs",
        "services": [
            "Full AI automation stack",
            "Cloud infrastructure management",
            "AI lead generation + outreach",
            "Client portal + reporting",
        ],
        "max_clients_concurrent": 5,
        "target_ltv": 36000,
        "churn_risk": "MEDIUM",
        "upsell_target": "ENTERPRISE",
        "upsell_trigger_month": 4,
    },
    "ENTERPRISE": {
        "monthly_retainer": 8000,
        "project_minimum": 20000,
        "ideal_client": "Scaling company, 50+ employees, complex multi-system AI needs",
        "services": [
            "JARVIS white-label deployment",
            "Custom AI agent fleet",
            "Dedicated infrastructure",
            "Strategic advisory",
            "24/7 monitoring + SLA",
        ],
        "max_clients_concurrent": 3,
        "target_ltv": 120000,
        "churn_risk": "LOW",
        "upsell_target": "PARTNER",
        "upsell_trigger_month": 6,
    },
    "PARTNER": {
        "monthly_retainer": 15000,
        "project_minimum": 50000,
        "ideal_client": "Agency / enterprise seeking white-label AI operations platform",
        "services": [
            "White-label JARVIS platform license",
            "Custom AI agent development",
            "Multi-tenant infrastructure",
            "Co-selling partnership",
            "Revenue share on sub-clients",
        ],
        "max_clients_concurrent": 2,
        "target_ltv": 360000,
        "churn_risk": "VERY_LOW",
        "upsell_target": None,
        "upsell_trigger_month": None,
    },
}


# ─── CHURN PREVENTION SIGNALS ─────────────────────────────────────────────────

CHURN_SIGNALS = {
    "RED": {
        "severity": "CRITICAL",
        "signals": [
            "No response to last 3 communications",
            "Invoice payment delayed >15 days",
            "Client mentions budget review",
            "Key sponsor left client company",
            "Competitor name mentioned by client",
            "Scope reduction request",
            "Meeting cancellations x2 in a row",
        ],
        "intervention": "IMMEDIATE_CAPTAIN_ESCALATION",
        "response_time_hours": 2,
    },
    "AMBER": {
        "severity": "HIGH",
        "signals": [
            "Response time increased >48h",
            "Reduced engagement on deliverables",
            "Fewer questions / less curious",
            "No expansion conversations in 60 days",
            "NPS-equivalent signal dropped",
            "Missed milestone without rescheduling",
        ],
        "intervention": "PROACTIVE_VALUE_DEMONSTRATION",
        "response_time_hours": 24,
    },
    "GREEN": {
        "severity": "STABLE",
        "signals": [
            "Regular communication cadence",
            "Timely payments",
            "Expanding scope discussions",
            "Referrals provided",
            "Positive sentiment in messages",
            "Asking about additional services",
        ],
        "intervention": "ACCELERATE_UPSELL",
        "response_time_hours": None,
    },
}


# ─── UPSELL INTELLIGENCE ──────────────────────────────────────────────────────

UPSELL_TRIGGERS = {
    "SERVICE_EXPANSION": [
        "Client mentions a problem outside current scope",
        "Client hires a new department we could automate",
        "Client launches a new product/market",
        "Current service ROI clearly demonstrated (>3x)",
        "Client asks 'can you also do...'",
    ],
    "TIER_UPGRADE": [
        "Client revenue grew significantly since contract start",
        "Client headcount exceeded tier's ideal size",
        "Current tier's max service count reached",
        "Engagement depth high (multiple stakeholders involved)",
        "3+ months of on-time payment and positive signal",
    ],
    "PROJECT_TO_RETAINER": [
        "Project delivered successfully — client sees value",
        "Client has ongoing needs in same domain",
        "Client mentions future projects in pipeline",
        "Project ended but relationship is warm",
    ],
    "REFERRAL_ACTIVATION": [
        "Client expressed satisfaction unprompted",
        "Client mentioned peers with same problems",
        "Client in highly networked industry (finance, real estate, tech)",
        "Client has agency relationships",
    ],
}


# ─── REVENUE VELOCITY BENCHMARKS ─────────────────────────────────────────────

REVENUE_BENCHMARKS = {
    "mrr_milestones": [
        {"milestone": 5000,   "phase": "Proof of concept", "target_clients": 2},
        {"milestone": 10000,  "phase": "Revenue foundation", "target_clients": 4},
        {"milestone": 25000,  "phase": "Growth stage", "target_clients": 6},
        {"milestone": 50000,  "phase": "Scale stage", "target_clients": 8},
        {"milestone": 100000, "phase": "Platform stage", "target_clients": 12},
    ],
    "healthy_metrics": {
        "monthly_growth_rate_pct": 15,
        "churn_rate_pct_max": 5,
        "ltv_to_cac_ratio_min": 4.0,
        "avg_contract_length_months_min": 6,
        "retainer_to_project_ratio": 0.70,
        "gross_margin_pct_min": 65,
        "payback_period_months_max": 3,
    },
}


# ─── REVENUE CONSCIOUSNESS ENGINE ────────────────────────────────────────────

class RevenueConsciousness:
    """
    The revenue-first intelligence layer.

    Every operation must pass through the revenue lens. Every client
    interaction, every service decision, every infrastructure choice
    has a revenue implication. This engine makes that explicit.
    """

    def compute_ltv(self, client_data: dict[str, Any]) -> dict[str, Any]:
        tier = client_data.get("tier", "GROWTH")
        months_active = client_data.get("months_active", 1)
        monthly_value = client_data.get("monthly_value", PRICING_TIERS.get(tier, {}).get("monthly_retainer", 4000))
        churn_risk = client_data.get("churn_risk_score", 0.05)

        expected_months = 1 / churn_risk if churn_risk > 0 else 36
        projected_ltv = monthly_value * min(expected_months, 48)
        actual_ltv_to_date = monthly_value * months_active

        tier_config = PRICING_TIERS.get(tier, {})
        target_ltv = tier_config.get("target_ltv", 36000)
        upsell_target = tier_config.get("upsell_target")
        upsell_trigger_month = tier_config.get("upsell_trigger_month", 4)

        return {
            "client_id": client_data.get("client_id"),
            "tier": tier,
            "monthly_value": monthly_value,
            "months_active": months_active,
            "actual_ltv_to_date": actual_ltv_to_date,
            "projected_ltv": round(projected_ltv, 2),
            "target_ltv": target_ltv,
            "ltv_attainment_pct": round((actual_ltv_to_date / target_ltv * 100), 1),
            "churn_risk_score": churn_risk,
            "expected_months_remaining": round(min(expected_months - months_active, 48), 1),
            "upsell_target_tier": upsell_target,
            "upsell_trigger_month": upsell_trigger_month,
            "should_initiate_upsell": months_active >= upsell_trigger_month,
            "computed_at": datetime.now(UTC).isoformat(),
        }

    def score_churn_risk(self, engagement_signals: dict[str, Any]) -> dict[str, Any]:
        score = 0.0
        triggered_signals = []

        red_signals = CHURN_SIGNALS["RED"]["signals"]
        amber_signals = CHURN_SIGNALS["AMBER"]["signals"]

        for signal in engagement_signals.get("observed_signals", []):
            if signal in red_signals:
                score += 0.25
                triggered_signals.append({"signal": signal, "severity": "RED", "weight": 0.25})
            elif signal in amber_signals:
                score += 0.10
                triggered_signals.append({"signal": signal, "severity": "AMBER", "weight": 0.10})

        score = min(score, 1.0)

        if score >= 0.50:
            risk_level = "RED"
            intervention = CHURN_SIGNALS["RED"]["intervention"]
            response_hours = CHURN_SIGNALS["RED"]["response_time_hours"]
        elif score >= 0.20:
            risk_level = "AMBER"
            intervention = CHURN_SIGNALS["AMBER"]["intervention"]
            response_hours = CHURN_SIGNALS["AMBER"]["response_time_hours"]
        else:
            risk_level = "GREEN"
            intervention = CHURN_SIGNALS["GREEN"]["intervention"]
            response_hours = None

        return {
            "client_id": engagement_signals.get("client_id"),
            "churn_risk_score": round(score, 2),
            "risk_level": risk_level,
            "triggered_signals": triggered_signals,
            "intervention_required": intervention,
            "respond_within_hours": response_hours,
            "assessed_at": datetime.now(UTC).isoformat(),
        }

    def identify_upsell_opportunities(self, client_data: dict[str, Any]) -> dict[str, Any]:
        opportunities = []
        client_signals = client_data.get("signals", [])

        for category, triggers in UPSELL_TRIGGERS.items():
            matched = [t for t in triggers if t in client_signals]
            if matched:
                opportunities.append({
                    "category": category,
                    "matched_triggers": matched,
                    "confidence": min(len(matched) / len(triggers) * 10, 10),
                })

        opportunities.sort(key=lambda x: x["confidence"], reverse=True)

        tier = client_data.get("tier", "GROWTH")
        next_tier = PRICING_TIERS.get(tier, {}).get("upsell_target")
        if next_tier:
            tier_delta = PRICING_TIERS[next_tier]["monthly_retainer"] - PRICING_TIERS[tier]["monthly_retainer"]
        else:
            tier_delta = 0

        return {
            "client_id": client_data.get("client_id"),
            "current_tier": tier,
            "upsell_opportunities": opportunities,
            "top_opportunity": opportunities[0] if opportunities else None,
            "next_tier": next_tier,
            "monthly_revenue_increase_if_upgraded": tier_delta,
            "annual_revenue_increase_if_upgraded": tier_delta * 12,
            "identified_at": datetime.now(UTC).isoformat(),
        }

    def compute_pipeline_health(self, pipeline: dict[str, Any]) -> dict[str, Any]:
        mrr = pipeline.get("mrr", 0)
        hot_leads = pipeline.get("hot_leads", 0)
        proposals_sent = pipeline.get("proposals_sent", 0)
        proposals_won = pipeline.get("proposals_won", 0)
        avg_deal_value = pipeline.get("avg_deal_value", 4000)
        benchmarks = REVENUE_BENCHMARKS["healthy_metrics"]

        win_rate = proposals_won / proposals_sent if proposals_sent > 0 else 0
        projected_new_mrr = hot_leads * win_rate * avg_deal_value * 0.20
        monthly_growth = pipeline.get("monthly_growth_pct", 0)

        health_flags = []
        if monthly_growth < benchmarks["monthly_growth_rate_pct"]:
            health_flags.append(f"Growth rate {monthly_growth}% below target {benchmarks['monthly_growth_rate_pct']}%")
        if pipeline.get("churn_rate_pct", 0) > benchmarks["churn_rate_pct_max"]:
            health_flags.append("Churn rate exceeds 5% threshold")
        if win_rate < 0.20:
            health_flags.append(f"Win rate {win_rate*100:.0f}% below healthy threshold of 20%")

        current_milestone = None
        next_milestone = None
        for m in REVENUE_BENCHMARKS["mrr_milestones"]:
            if mrr >= m["milestone"]:
                current_milestone = m
            elif next_milestone is None:
                next_milestone = m

        return {
            "mrr": mrr,
            "monthly_growth_pct": monthly_growth,
            "win_rate_pct": round(win_rate * 100, 1),
            "projected_new_mrr_this_month": round(projected_new_mrr, 0),
            "health_flags": health_flags,
            "health_status": "HEALTHY" if not health_flags else "NEEDS_ATTENTION" if len(health_flags) == 1 else "CRITICAL",
            "current_milestone": current_milestone,
            "next_milestone": next_milestone,
            "gap_to_next_milestone": (next_milestone["milestone"] - mrr) if next_milestone else 0,
            "assessed_at": datetime.now(UTC).isoformat(),
        }

    def get_pricing_recommendation(self, prospect_data: dict[str, Any]) -> dict[str, Any]:
        company_size = prospect_data.get("company_size", 10)
        monthly_budget = prospect_data.get("budget", 0)
        complexity = prospect_data.get("complexity", "medium")
        urgency = prospect_data.get("urgency", "normal")

        if company_size < 10 or monthly_budget < 3000:
            recommended = "STARTER"
        elif company_size < 50 or monthly_budget < 6000:
            recommended = "GROWTH"
        elif company_size < 200 or monthly_budget < 12000:
            recommended = "ENTERPRISE"
        else:
            recommended = "PARTNER"

        if urgency == "high":
            recommended_min = PRICING_TIERS[recommended]["monthly_retainer"] * 1.20
        else:
            recommended_min = PRICING_TIERS[recommended]["monthly_retainer"]

        tier_config = PRICING_TIERS[recommended]
        return {
            "recommended_tier": recommended,
            "monthly_retainer_floor": recommended_min,
            "project_minimum": tier_config["project_minimum"],
            "target_ltv": tier_config["target_ltv"],
            "upsell_path": tier_config.get("upsell_target"),
            "services_included": tier_config["services"],
            "pricing_rationale": f"Company size {company_size}, budget ${monthly_budget}/mo, {complexity} complexity",
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    def get_revenue_dashboard(self) -> dict[str, Any]:
        return {
            "system": "JARVIS Revenue Consciousness Engine",
            "status": "FULLY_OPERATIONAL",
            "pricing_tiers": list(PRICING_TIERS.keys()),
            "tier_details": PRICING_TIERS,
            "churn_framework": CHURN_SIGNALS,
            "upsell_categories": list(UPSELL_TRIGGERS.keys()),
            "milestones": REVENUE_BENCHMARKS["mrr_milestones"],
            "healthy_metrics": REVENUE_BENCHMARKS["healthy_metrics"],
            "evaluated_at": datetime.now(UTC).isoformat(),
        }


revenue_consciousness = RevenueConsciousness()
