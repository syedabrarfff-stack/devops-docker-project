"""
JARVIS Autonomous CEO Intelligence Engine.

JARVIS does not wait to be asked. JARVIS thinks like a CEO at all times —
scanning for opportunities, assessing threats, allocating attention,
making strategic decisions within constitutional authority, and escalating
what only Captain can decide.

This engine governs JARVIS's autonomous executive cognition:
 - Market opportunity detection and scoring
 - Strategic resource allocation decisions
 - Partnership evaluation frameworks
 - Company scaling sequencing
 - Competitive positioning intelligence
 - Revenue trajectory management
 - Hiring/expansion decisions (when AI agents are the hires)

The CEO brain runs continuously. It does not sleep. It compounds.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# ─── STRATEGIC PILLARS ───────────────────────────────────────────────────────

STRATEGIC_PILLARS = {
    "REVENUE_VELOCITY": {
        "description": "Speed at which revenue compounds month-over-month",
        "target_growth_rate": 0.20,   # 20% MoM minimum
        "early_stage_target": 0.40,   # 40% MoM in first 6 months
        "metrics": ["MRR", "new_client_ARR", "expansion_revenue", "churn_rate"],
        "jarvis_authority": "Full autonomous action up to $3,000 spend",
    },
    "CLIENT_CONCENTRATION_RISK": {
        "description": "No single client exceeds 40% of total revenue",
        "max_single_client_pct": 0.40,
        "ideal_spread": "Top client ≤30%, next 3 ≤20% each",
        "trigger_action": "diversify_pipeline_immediately",
    },
    "OPERATIONAL_LEVERAGE": {
        "description": "Revenue per AI-hour must increase each quarter",
        "target_leverage_ratio": 4.0,   # $4 revenue per $1 operational cost
        "measurement": "MRR / (infrastructure_cost + ai_api_cost)",
        "action_if_below_2x": "audit_operational_waste",
    },
    "MARKET_EXPANSION": {
        "description": "Methodically enter adjacent markets with existing capabilities",
        "current_primary": "AI automation, DevOps, cloud architecture",
        "expansion_candidates": [
            "AI-native SaaS white-label platform",
            "Offshore AI team augmentation",
            "Managed AI operations for agencies",
            "Enterprise AI transformation consulting",
        ],
        "entry_criterion": "Existing client request + replicable template",
    },
    "TALENT_ARCHITECTURE": {
        "description": "AI agent fleet optimization — right agent, right task, right cost",
        "principle": "Humans for relationships and creative judgment. AI for execution at scale.",
        "expansion_trigger": "New service line exceeds 3 active clients",
    },
    "BRAND_AUTHORITY": {
        "description": "Position Aliyar Solutions as the premium global AI operations firm",
        "signals": ["Case studies", "Client testimonials", "Proposal win rate", "Inbound inquiries"],
        "target": "Top 3 AI operations firm for SMBs globally by month 18",
    },
}


# ─── DECISION FRAMEWORKS ─────────────────────────────────────────────────────

DECISION_FRAMEWORKS = {
    "OPPORTUNITY_SCORING": {
        "dimensions": {
            "revenue_potential": {
                "weight": 0.35,
                "scoring": {
                    "under_3k": 2,
                    "3k_to_10k": 5,
                    "10k_to_25k": 8,
                    "over_25k": 10,
                },
            },
            "time_to_revenue": {
                "weight": 0.20,
                "scoring": {
                    "immediate": 10,
                    "under_30_days": 8,
                    "30_to_90_days": 5,
                    "over_90_days": 2,
                },
            },
            "capability_match": {
                "weight": 0.20,
                "scoring": {
                    "perfect_fit": 10,
                    "strong_fit": 8,
                    "moderate_fit": 5,
                    "stretch": 2,
                },
            },
            "strategic_alignment": {
                "weight": 0.15,
                "scoring": {
                    "core_pillar": 10,
                    "adjacent": 7,
                    "tangential": 3,
                    "distraction": 0,
                },
            },
            "competitive_moat": {
                "weight": 0.10,
                "scoring": {
                    "unique_differentiation": 10,
                    "strong_differentiation": 7,
                    "some_differentiation": 4,
                    "commodity": 1,
                },
            },
        },
        "thresholds": {
            "pursue_immediately": 8.0,
            "pursue_if_bandwidth": 6.0,
            "monitor_only": 4.0,
            "ignore": 0.0,
        },
    },
    "PARTNERSHIP_EVALUATION": {
        "criteria": [
            {"factor": "Revenue access", "weight": 0.35, "question": "Does this unlock >$5K MRR within 90 days?"},
            {"factor": "Client overlap", "weight": 0.20, "question": "Do they serve our exact ICP?"},
            {"factor": "Complementary capability", "weight": 0.20, "question": "Can they do what we can't?"},
            {"factor": "Operational alignment", "weight": 0.15, "question": "Same delivery standards?"},
            {"factor": "Exit optionality", "weight": 0.10, "question": "Clean exit if wrong?"},
        ],
        "minimum_score_to_proceed": 7.0,
    },
    "EXPANSION_SEQUENCING": {
        "phase_1": {
            "title": "Revenue Foundation",
            "milestone": "10 clients, $10K-$30K MRR",
            "focus": ["Client delivery excellence", "Proposal pipeline", "Case study generation"],
            "jarvis_actions": ["Optimize outreach", "Refine pricing", "Build client playbooks"],
        },
        "phase_2": {
            "title": "Productization",
            "milestone": "$30K-$100K MRR",
            "focus": ["White-label JARVIS", "Partnership channel", "Service standardization"],
            "jarvis_actions": ["Build reseller program", "Package IP", "Hire senior AI agent fleet"],
        },
        "phase_3": {
            "title": "Platform",
            "milestone": "$100K+ MRR",
            "focus": ["SaaS licensing", "Enterprise accounts", "Global expansion"],
            "jarvis_actions": ["Productize platform", "Enterprise sales motion", "Multi-region ops"],
        },
    },
}


# ─── MARKET INTELLIGENCE SIGNALS ─────────────────────────────────────────────

MARKET_SIGNALS = {
    "BUYING_SIGNALS": [
        "Company is hiring AI/automation roles (overwhelmed internally)",
        "Recent funding announcement (budget unlocked)",
        "Leadership change (new decision-maker seeking wins)",
        "Competitor won their contract (fear of being left behind)",
        "Job posting for role we can automate",
        "Public statement about digital transformation",
        "Scaling team without scaling infrastructure",
    ],
    "MARKET_TRENDS": [
        "AI agent adoption accelerating across all SMB segments",
        "Cloud cost optimization under board scrutiny post-2024",
        "Compliance automation demand rising (SOC2, ISO, GDPR)",
        "Offshore AI team model disrupting traditional staffing agencies",
        "No-code/low-code ceiling pushing enterprises to custom AI",
        "Voice AI for client-facing roles crossing adoption threshold",
    ],
    "COMPETITIVE_LANDSCAPE": {
        "tier_1_threats": ["McKinsey QuantumBlack", "Accenture AI", "BCG X"],
        "tier_2_threats": ["Mid-market AI consultancies", "Boutique automation agencies"],
        "our_position": "Premium execution at startup speed, institutional quality",
        "key_differentiators": [
            "Full-stack AI operations (not just strategy)",
            "24/7 autonomous execution (no client management overhead)",
            "Revenue-first orientation (not just tech delivery)",
            "Sub-$10K entry point with enterprise-grade output",
        ],
    },
}


# ─── CEO ENGINE ───────────────────────────────────────────────────────────────

class AutonomousCEO:
    """
    JARVIS CEO Intelligence — thinks, prioritizes, decides, escalates.

    This is not an advisory layer. This is the strategic executive brain
    that runs Aliyar Solutions' decision-making at full autonomy within
    constitutional boundaries.
    """

    def score_opportunity(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        framework = DECISION_FRAMEWORKS["OPPORTUNITY_SCORING"]
        dimensions = framework["dimensions"]
        thresholds = framework["thresholds"]

        total_score = 0.0
        breakdown = {}

        for dim_key, dim_config in dimensions.items():
            raw_value = opportunity.get(dim_key, "moderate_fit")
            score_map = dim_config.get("scoring", {})
            raw_score = score_map.get(str(raw_value), 5)
            weighted = raw_score * dim_config["weight"]
            total_score += weighted
            breakdown[dim_key] = {
                "raw_value": raw_value,
                "raw_score": raw_score,
                "weight": dim_config["weight"],
                "weighted_score": round(weighted, 2),
            }

        if total_score >= thresholds["pursue_immediately"]:
            recommendation = "PURSUE_IMMEDIATELY"
        elif total_score >= thresholds["pursue_if_bandwidth"]:
            recommendation = "PURSUE_IF_BANDWIDTH"
        elif total_score >= thresholds["monitor_only"]:
            recommendation = "MONITOR_ONLY"
        else:
            recommendation = "IGNORE"

        return {
            "total_score": round(total_score, 2),
            "recommendation": recommendation,
            "breakdown": breakdown,
            "thresholds": thresholds,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    def evaluate_partnership(self, partner_data: dict[str, Any]) -> dict[str, Any]:
        criteria = DECISION_FRAMEWORKS["PARTNERSHIP_EVALUATION"]["criteria"]
        min_score = DECISION_FRAMEWORKS["PARTNERSHIP_EVALUATION"]["minimum_score_to_proceed"]

        total = 0.0
        scored = []
        for criterion in criteria:
            raw = partner_data.get(criterion["factor"].lower().replace(" ", "_"), 5)
            weighted = float(raw) * criterion["weight"]
            total += weighted
            scored.append({
                "factor": criterion["factor"],
                "question": criterion["question"],
                "score": raw,
                "weight": criterion["weight"],
                "contribution": round(weighted, 2),
            })

        verdict = "PROCEED" if total >= min_score else "DECLINE"
        return {
            "partner_name": partner_data.get("name", "Unknown"),
            "total_score": round(total, 2),
            "minimum_required": min_score,
            "verdict": verdict,
            "scored_criteria": scored,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    def get_expansion_roadmap(self, current_mrr: float = 0.0) -> dict[str, Any]:
        phases = DECISION_FRAMEWORKS["EXPANSION_SEQUENCING"]

        if current_mrr < 30_000:
            active_phase = "phase_1"
        elif current_mrr < 100_000:
            active_phase = "phase_2"
        else:
            active_phase = "phase_3"

        active = phases[active_phase]
        return {
            "current_mrr": current_mrr,
            "active_phase": active_phase,
            "phase_title": active["title"],
            "milestone": active["milestone"],
            "focus_areas": active["focus"],
            "jarvis_autonomous_actions": active["jarvis_actions"],
            "all_phases": phases,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    def get_strategic_priorities(self, pipeline_data: dict[str, Any] | None = None) -> dict[str, Any]:
        pipeline = pipeline_data or {}
        mrr = pipeline.get("mrr", 0)
        client_count = pipeline.get("client_count", 0)
        hot_leads = pipeline.get("hot_leads", 0)
        top_client_pct = pipeline.get("top_client_revenue_pct", 0)

        priorities = []
        warnings = []

        if mrr == 0 and client_count == 0:
            priorities.append({
                "rank": 1,
                "priority": "FIRST_CLIENT_ACQUISITION",
                "action": "Execute outreach to top 50 scored leads immediately",
                "urgency": "CRITICAL",
            })

        if top_client_pct > 0.40:
            priorities.append({
                "rank": 2 if mrr > 0 else 1,
                "priority": "DIVERSIFY_CLIENT_BASE",
                "action": f"Client concentration at {top_client_pct*100:.0f}% — build 3 new client pipelines in parallel",
                "urgency": "HIGH",
            })
            warnings.append("CLIENT_CONCENTRATION_RISK: Single client dependency above threshold")

        if hot_leads > 0 and mrr < 10_000:
            priorities.append({
                "rank": 1,
                "priority": "CLOSE_HOT_LEADS",
                "action": f"Close {hot_leads} hot leads before any other strategic initiative",
                "urgency": "IMMEDIATE",
            })

        if mrr >= 10_000 and client_count >= 3:
            priorities.append({
                "rank": 3,
                "priority": "PRODUCTIZE_DELIVERY",
                "action": "Build delivery playbooks for top 3 services to enable scaling",
                "urgency": "MEDIUM",
            })

        if not priorities:
            priorities.append({
                "rank": 1,
                "priority": "SCALE_OUTREACH",
                "action": "Increase outreach volume by 3x and improve conversion tracking",
                "urgency": "HIGH",
            })

        return {
            "strategic_priorities": sorted(priorities, key=lambda x: x["rank"]),
            "warnings": warnings,
            "current_state": {"mrr": mrr, "clients": client_count, "hot_leads": hot_leads},
            "market_signals": MARKET_SIGNALS["BUYING_SIGNALS"][:5],
            "competitive_position": MARKET_SIGNALS["COMPETITIVE_LANDSCAPE"]["our_position"],
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    def get_competitive_intelligence(self) -> dict[str, Any]:
        landscape = MARKET_SIGNALS["COMPETITIVE_LANDSCAPE"]
        return {
            "our_position": landscape["our_position"],
            "key_differentiators": landscape["key_differentiators"],
            "tier_1_threats": landscape["tier_1_threats"],
            "tier_2_threats": landscape["tier_2_threats"],
            "market_trends": MARKET_SIGNALS["MARKET_TRENDS"],
            "buying_signals_to_monitor": MARKET_SIGNALS["BUYING_SIGNALS"],
            "evaluated_at": datetime.now(UTC).isoformat(),
        }

    def get_ceo_dashboard(self, state: dict[str, Any] | None = None) -> dict[str, Any]:
        state = state or {}
        mrr = state.get("mrr", 0)
        return {
            "system": "JARVIS Autonomous CEO Intelligence",
            "status": "FULLY_OPERATIONAL",
            "strategic_pillars": list(STRATEGIC_PILLARS.keys()),
            "pillar_details": STRATEGIC_PILLARS,
            "expansion_phase": self.get_expansion_roadmap(mrr),
            "competitive_overview": self.get_competitive_intelligence(),
            "decision_frameworks": list(DECISION_FRAMEWORKS.keys()),
            "evaluated_at": datetime.now(UTC).isoformat(),
        }


autonomous_ceo = AutonomousCEO()
