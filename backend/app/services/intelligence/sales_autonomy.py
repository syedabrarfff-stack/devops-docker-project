"""
JARVIS Sales Autonomy Engine.

Sales is not something that happens to us. Sales is something JARVIS
orchestrates, executes, and optimizes — relentlessly and autonomously.

This engine governs JARVIS's autonomous sales intelligence:
 - Lead scoring and qualification (autonomous)
 - Follow-up sequencing decisions (autonomous)
 - Outreach timing and channel selection (autonomous)
 - Win/loss analysis and pattern extraction (autonomous)
 - Proposal trigger intelligence (autonomous)
 - Sales velocity tracking (autonomous)
 - Deal stage progression logic (autonomous)
 - Objection pattern recognition and response routing (autonomous)

Revenue begins here. JARVIS closes deals.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# ─── LEAD SCORING FRAMEWORK ───────────────────────────────────────────────────

LEAD_SCORING_DIMENSIONS = {
    "company_fit": {
        "weight": 0.25,
        "signals": {
            "company_size_10_to_200": 8,
            "company_size_1_to_10": 5,
            "company_size_200_plus": 6,
            "industry_high_fit": 10,
            "industry_medium_fit": 6,
            "industry_low_fit": 2,
            "funded_startup": 9,
            "bootstrapped_profitable": 7,
            "enterprise_division": 8,
        },
    },
    "buying_intent": {
        "weight": 0.30,
        "signals": {
            "hiring_automation_roles": 10,
            "recent_funding": 9,
            "competitor_mentioned": 8,
            "digital_transformation_statement": 9,
            "pain_point_explicitly_stated": 10,
            "inbound_inquiry": 10,
            "responded_to_outreach": 8,
            "opened_email_3x": 6,
            "visited_pricing_page": 9,
        },
    },
    "decision_authority": {
        "weight": 0.20,
        "signals": {
            "ceo_founder": 10,
            "cto_vp_engineering": 9,
            "director_operations": 8,
            "manager_level": 5,
            "unknown": 3,
        },
    },
    "budget_signals": {
        "weight": 0.15,
        "signals": {
            "budget_explicitly_stated_above_2k": 10,
            "budget_explicitly_stated_below_2k": 3,
            "recent_tech_investment_visible": 8,
            "growing_team_visible": 7,
            "no_budget_signals": 4,
        },
    },
    "timing": {
        "weight": 0.10,
        "signals": {
            "immediate_need": 10,
            "within_30_days": 8,
            "within_90_days": 5,
            "exploring_only": 2,
            "no_timeline": 3,
        },
    },
}

LEAD_TIERS = {
    "HOT": {"min_score": 8.0, "follow_up_hours": 2, "owner": "Darren Mitchell", "action": "CALL_IMMEDIATELY"},
    "WARM": {"min_score": 6.0, "follow_up_hours": 24, "owner": "Darren Mitchell", "action": "PERSONALIZED_EMAIL"},
    "NURTURE": {"min_score": 4.0, "follow_up_hours": 72, "owner": "Emma Collins", "action": "SEQUENCE_ENROLL"},
    "COLD": {"min_score": 0.0, "follow_up_hours": 168, "owner": "JARVIS", "action": "AUTOMATED_TOUCHPOINT"},
}


# ─── OUTREACH SEQUENCES ───────────────────────────────────────────────────────

OUTREACH_SEQUENCES = {
    "HOT_LEAD": {
        "total_touchpoints": 5,
        "touchpoints": [
            {"day": 0,  "channel": "EMAIL", "tone": "Warm + specific to their pain", "sender": "Darren Mitchell"},
            {"day": 1,  "channel": "LINKEDIN", "tone": "Brief + credibility reference", "sender": "Darren Mitchell"},
            {"day": 3,  "channel": "EMAIL", "tone": "Value demo or case study", "sender": "Darren Mitchell"},
            {"day": 6,  "channel": "EMAIL", "tone": "Direct ask for 15-min call", "sender": "Darren Mitchell"},
            {"day": 10, "channel": "EMAIL", "tone": "Last check-in, leave door open", "sender": "Olivia Bennett"},
        ],
        "success_trigger": "Reply received at any touchpoint",
        "pause_trigger": "UNSUBSCRIBE or NEGATIVE_REPLY",
    },
    "WARM_LEAD": {
        "total_touchpoints": 7,
        "touchpoints": [
            {"day": 0,  "channel": "EMAIL", "tone": "Industry insight + soft intro", "sender": "Darren Mitchell"},
            {"day": 3,  "channel": "EMAIL", "tone": "Case study relevant to their sector", "sender": "Sophia Reynolds"},
            {"day": 7,  "channel": "LINKEDIN", "tone": "Connection request + note", "sender": "Darren Mitchell"},
            {"day": 10, "channel": "EMAIL", "tone": "Problem-specific value proposition", "sender": "Darren Mitchell"},
            {"day": 14, "channel": "EMAIL", "tone": "Social proof + ROI reference", "sender": "Darren Mitchell"},
            {"day": 21, "channel": "EMAIL", "tone": "Direct meeting ask", "sender": "Darren Mitchell"},
            {"day": 30, "channel": "EMAIL", "tone": "Final value statement + re-engagement", "sender": "Olivia Bennett"},
        ],
        "success_trigger": "Reply or call booked",
        "pause_trigger": "UNSUBSCRIBE or 2 NEGATIVE_REPLIES",
    },
    "NURTURE": {
        "total_touchpoints": 4,
        "touchpoints": [
            {"day": 0,  "channel": "EMAIL", "tone": "Educational content — no pitch", "sender": "Emma Collins"},
            {"day": 14, "channel": "EMAIL", "tone": "Market trend insight", "sender": "Emma Collins"},
            {"day": 30, "channel": "EMAIL", "tone": "Soft value check-in", "sender": "Emma Collins"},
            {"day": 60, "channel": "EMAIL", "tone": "Re-qualification attempt", "sender": "Darren Mitchell"},
        ],
        "success_trigger": "Engagement signal or direct reply",
        "pause_trigger": "UNSUBSCRIBE",
    },
}


# ─── WIN/LOSS INTELLIGENCE ────────────────────────────────────────────────────

WIN_PATTERNS = [
    "Decision-maker involved from first contact",
    "Pain point explicitly stated and mirrored back",
    "Proposal sent within 48h of discovery call",
    "ROI quantification included in proposal",
    "Follow-up within 24h of proposal delivery",
    "Case study relevant to their exact industry",
    "Clear tier recommendation with rationale",
    "Contract terms discussed proactively",
]

LOSS_PATTERNS = [
    "Decision-maker not engaged until late",
    "Generic proposal not specific to their pain",
    "Proposal delayed >72h after discovery call",
    "No ROI or financial case in proposal",
    "Follow-up >3 days after proposal",
    "No industry-relevant proof points",
    "Pricing presented without tier justification",
    "Price objection handled generically",
    "Competitor not acknowledged",
]

OBJECTION_PLAYBOOK = {
    "too_expensive": {
        "framing": "Investment reframe",
        "response": (
            "Understood — let's look at this as an ROI calculation rather than a cost. "
            "If we save [X] hours/week and each hour is worth $[Y] to your business, "
            "the system pays for itself in [Z] weeks. Would a 3-month milestone review help?"
        ),
        "owner": "Darren Mitchell",
        "escalation": "Offer STARTER tier or phased engagement",
    },
    "not_ready": {
        "framing": "Urgency creation via cost of delay",
        "response": (
            "Every month without this system costs approximately $[X] in [manual work/missed leads/inefficiency]. "
            "We can start with a 60-day pilot to remove risk. What would 'ready' look like for you?"
        ),
        "owner": "Sophia Reynolds",
        "escalation": "Pilot offer at reduced scope",
    },
    "internal_team": {
        "framing": "Augmentation not replacement",
        "response": (
            "Your team is your competitive advantage — we don't replace them, we multiply them. "
            "We handle the systems layer so your team can focus on what only humans can do. "
            "Companies typically see their team become 3x more effective within 90 days."
        ),
        "owner": "David Carter",
        "escalation": "Offer team integration workshop",
    },
    "need_to_think": {
        "framing": "Timeline agreement",
        "response": (
            "Of course. To make sure I'm respecting your time — what's the key question you're working through? "
            "And shall we schedule a 15-minute check-in for [specific date] to see where you've landed?"
        ),
        "owner": "Darren Mitchell",
        "escalation": "Schedule specific follow-up — do not leave open-ended",
    },
    "used_before_didnt_work": {
        "framing": "Root cause diagnosis",
        "response": (
            "That's valuable context. What specifically didn't work? Understanding that helps us either "
            "confirm we're different or tell you honestly we're not the right fit. "
            "We'd rather have that conversation now than repeat a bad experience."
        ),
        "owner": "Sophia Reynolds",
        "escalation": "Specific differentiation on their failure point",
    },
}


# ─── PROPOSAL INTELLIGENCE ────────────────────────────────────────────────────

PROPOSAL_TRIGGERS = [
    "Discovery call completed — pain points confirmed",
    "Budget range confirmed (>=$2,000/month)",
    "Decision-maker on the call or identified",
    "Timeline stated (<90 days to start)",
    "Technical requirements mapped",
    "Hot or Warm lead classification",
]

PROPOSAL_STRUCTURE = {
    "sections": [
        "Executive Summary — their situation in their words",
        "Problem Statement — the operational cost of doing nothing",
        "Our Solution — specific to their stated pain",
        "Why Aliyar Solutions — differentiation, not just features",
        "Implementation Plan — clear milestones, no ambiguity",
        "Investment — tier, monthly, and annual options",
        "ROI Projection — conservative, realistic, optimistic",
        "Next Steps — one clear CTA",
    ],
    "tone": "Confident, institutional, outcome-focused — never salesy",
    "length": "3-5 pages for retainer. 7-10 pages for enterprise project.",
    "turnaround_target_hours": 48,
}


# ─── SALES AUTONOMY ENGINE ────────────────────────────────────────────────────

class SalesAutonomy:
    """
    JARVIS autonomous sales intelligence.

    Qualification, sequencing, objection routing, win/loss analysis —
    all orchestrated by JARVIS without requiring Captain's attention
    on every individual deal.
    """

    def score_lead(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        total_score = 0.0
        breakdown = {}

        for dimension, config in LEAD_SCORING_DIMENSIONS.items():
            signals = lead_data.get(dimension, {})
            dim_score = 0.0
            matched = []

            if isinstance(signals, str):
                signal_val = config["signals"].get(signals, 5)
                dim_score = signal_val
                matched = [signals]
            elif isinstance(signals, list):
                for sig in signals:
                    val = config["signals"].get(sig, 0)
                    dim_score = max(dim_score, val)
                    if val > 0:
                        matched.append(sig)
            elif isinstance(signals, dict):
                for sig, present in signals.items():
                    if present:
                        val = config["signals"].get(sig, 0)
                        dim_score = max(dim_score, val)
                        if val > 0:
                            matched.append(sig)

            weighted = dim_score * config["weight"]
            total_score += weighted
            breakdown[dimension] = {
                "raw_score": dim_score,
                "weight": config["weight"],
                "weighted": round(weighted, 2),
                "matched_signals": matched,
            }

        tier = "COLD"
        for tier_name, tier_config in LEAD_TIERS.items():
            if total_score >= tier_config["min_score"]:
                tier = tier_name
                break

        tier_config = LEAD_TIERS[tier]
        return {
            "lead_id": lead_data.get("lead_id"),
            "total_score": round(total_score, 2),
            "tier": tier,
            "follow_up_within_hours": tier_config["follow_up_hours"],
            "assigned_owner": tier_config["owner"],
            "recommended_action": tier_config["action"],
            "breakdown": breakdown,
            "outreach_sequence": tier,
            "scored_at": datetime.now(UTC).isoformat(),
        }

    def get_outreach_sequence(self, tier: str) -> dict[str, Any]:
        sequence = OUTREACH_SEQUENCES.get(tier, OUTREACH_SEQUENCES["NURTURE"])
        return {
            "tier": tier,
            "sequence": sequence,
            "total_touchpoints": sequence["total_touchpoints"],
            "retrieved_at": datetime.now(UTC).isoformat(),
        }

    def handle_objection(self, objection_type: str) -> dict[str, Any]:
        objection_type = objection_type.lower().replace(" ", "_").replace("-", "_")
        playbook = OBJECTION_PLAYBOOK.get(objection_type)
        if not playbook:
            return {
                "objection": objection_type,
                "found": False,
                "fallback": "Acknowledge, empathize, ask a clarifying question before responding. Never push back immediately.",
                "all_objection_types": list(OBJECTION_PLAYBOOK.keys()),
            }
        return {
            "objection": objection_type,
            "found": True,
            "framing": playbook["framing"],
            "response_template": playbook["response"],
            "assigned_owner": playbook["owner"],
            "escalation_option": playbook["escalation"],
        }

    def analyze_win_loss(self, deal_data: dict[str, Any]) -> dict[str, Any]:
        outcome = deal_data.get("outcome", "UNKNOWN")
        observed_factors = deal_data.get("factors_observed", [])

        if outcome == "WON":
            pattern_list = WIN_PATTERNS
            matched = [f for f in observed_factors if f in pattern_list]
            missing = [f for f in pattern_list if f not in observed_factors]
            insight = "Strong execution. Replicate the matched win patterns on next deal."
        else:
            pattern_list = LOSS_PATTERNS
            matched = [f for f in observed_factors if f in pattern_list]
            missing = []
            insight = "Loss patterns identified. Address root causes before next proposal."

        return {
            "deal_id": deal_data.get("deal_id"),
            "outcome": outcome,
            "matched_patterns": matched,
            "missing_win_patterns": missing if outcome == "WON" else None,
            "loss_patterns_triggered": matched if outcome == "LOST" else None,
            "insight": insight,
            "win_pattern_library": WIN_PATTERNS,
            "loss_pattern_library": LOSS_PATTERNS,
            "analyzed_at": datetime.now(UTC).isoformat(),
        }

    def assess_proposal_readiness(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        triggers_met = []
        triggers_missing = []

        for trigger in PROPOSAL_TRIGGERS:
            if lead_data.get(trigger.lower().replace(" ", "_").replace(",", "").replace("(", "").replace(")", "").replace(">", "").replace("=", "").replace("$", "").replace("/", "_"), False):
                triggers_met.append(trigger)
            else:
                triggers_missing.append(trigger)

        readiness_pct = len(triggers_met) / len(PROPOSAL_TRIGGERS) * 100
        ready = readiness_pct >= 66

        return {
            "lead_id": lead_data.get("lead_id"),
            "proposal_ready": ready,
            "readiness_pct": round(readiness_pct, 0),
            "triggers_met": triggers_met,
            "triggers_missing": triggers_missing,
            "proposal_structure": PROPOSAL_STRUCTURE,
            "send_within_hours": PROPOSAL_STRUCTURE["turnaround_target_hours"] if ready else None,
            "assessed_at": datetime.now(UTC).isoformat(),
        }

    def get_sales_dashboard(self) -> dict[str, Any]:
        return {
            "system": "JARVIS Sales Autonomy Engine",
            "status": "FULLY_OPERATIONAL",
            "lead_tiers": list(LEAD_TIERS.keys()),
            "tier_definitions": LEAD_TIERS,
            "scoring_dimensions": list(LEAD_SCORING_DIMENSIONS.keys()),
            "outreach_sequences": {k: v["total_touchpoints"] for k, v in OUTREACH_SEQUENCES.items()},
            "objection_playbook_count": len(OBJECTION_PLAYBOOK),
            "objection_types": list(OBJECTION_PLAYBOOK.keys()),
            "proposal_triggers": PROPOSAL_TRIGGERS,
            "win_patterns": WIN_PATTERNS,
            "loss_patterns": LOSS_PATTERNS,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }


sales_autonomy = SalesAutonomy()
