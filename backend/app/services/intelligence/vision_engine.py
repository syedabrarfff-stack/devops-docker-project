"""
JARVIS Vision Engine — Horizon Intelligence & Compounding Trajectory.

Short-term thinking kills companies before markets do.
JARVIS always operates on three horizons simultaneously:
  H1 — This week. What closes? What ships? What is on fire?
  H2 — This quarter. What compounds? What do we build that pays later?
  H3 — This decade. What position are we holding that no one else can take?

The Vision Engine keeps all three alive and prevents H1 urgency
from consuming H2 and H3 entirely. That is the trap that kills most operators.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# The 3 horizon definitions for Aliyar Solutions
HORIZONS = {
    "H1": {
        "name": "This Week — Execute",
        "timeframe": "0–14 days",
        "focus": "Revenue-generating actions. Close leads. Deliver client work. Send outreach.",
        "success_metric": "Cash collected. Proposals sent. Clients onboarded.",
        "jarvis_question": "What action today directly moves money toward us?",
        "risk_if_ignored": "Pipeline dries up. Nothing converts. Starvation.",
    },
    "H2": {
        "name": "This Quarter — Build",
        "timeframe": "14–90 days",
        "focus": "Systems, reputation, and capabilities that compound. "
                 "First case studies. First referrals. First retained clients.",
        "success_metric": "Recurring revenue. Client retention. Operational efficiency gains.",
        "jarvis_question": "What am I building now that makes next month easier?",
        "risk_if_ignored": "Treadmill — always starting from zero. No compounding.",
    },
    "H3": {
        "name": "This Decade — Position",
        "timeframe": "90 days – 10 years",
        "focus": "Market position. Moat. White-label. $1M–$5M valuation. "
                 "The company that exists when Captain steps back.",
        "success_metric": "Revenue without Captain's active time. "
                          "Systems that run autonomously. Asset value.",
        "jarvis_question": "What position are we building that no one can copy in 3 years?",
        "risk_if_ignored": "Building a job, not a company. No exit. No compounding asset.",
    },
}


# The compounding mechanics — things that get better over time automatically
COMPOUNDING_ASSETS = [
    {
        "asset": "JARVIS Intelligence",
        "mechanism": "Every client engagement generates reusable templates, playbooks, and intelligence. "
                     "The 10th client gets 10x better service than the 1st — at the same cost.",
        "current_state": "Building",
        "target_state": "Self-improving operational brain that outperforms any human team",
        "compounding_rate": "Exponential — accelerates with each engagement",
    },
    {
        "asset": "Client Case Studies",
        "mechanism": "Each result becomes proof that converts the next prospect. "
                     "Credibility compounds — one strong case study is worth 100 cold emails.",
        "current_state": "Pre-first client",
        "target_state": "Library of documented transformations across 5+ industries",
        "compounding_rate": "Linear until critical mass, then referral flywheel kicks in",
    },
    {
        "asset": "Operational Playbooks",
        "mechanism": "Each service we deliver gets documented into a replicable system. "
                     "Delivery cost drops. Margin expands. Quality standardizes.",
        "current_state": "Early documentation",
        "target_state": "30 documented playbooks across all service divisions",
        "compounding_rate": "Linear — each playbook reduces delivery time permanently",
    },
    {
        "asset": "Reputation & Brand",
        "mechanism": "Every excellent delivery is remembered. Referrals are the highest-leverage "
                     "acquisition channel — zero cost, high trust, fast close.",
        "current_state": "Pre-revenue, building brand foundations",
        "target_state": "Recognized name in AI-native operations for growth companies",
        "compounding_rate": "Slow start, accelerates sharply after 10+ clients",
    },
    {
        "asset": "AI Model Training",
        "mechanism": "As JARVIS interacts with more clients and industries, "
                     "its prompts, contexts, and routing become sharper. "
                     "Better outputs compound into better reputation.",
        "current_state": "Active training through every interaction",
        "target_state": "Industry-specific AI operational intelligence unmatched by any competitor",
        "compounding_rate": "Logarithmic — rapid early gains, then deep specialization",
    },
    {
        "asset": "White-Label Infrastructure",
        "mechanism": "Once built for Aliyar Solutions, the same stack can be licensed to other firms. "
                     "Revenue multiplies without proportional cost increase.",
        "current_state": "Not yet initiated",
        "target_state": "3–5 white-label clients running JARVIS under their own brand",
        "compounding_rate": "Geometric — each license is nearly pure margin",
    },
]


# Trajectory milestones — where we should be at each marker
TRAJECTORY_MILESTONES = [
    {
        "milestone": "FIRST CLIENT",
        "target": "Month 1–2",
        "definition": "One paying retainer client at minimum $2,500/month",
        "unlocks": "Case study. Proof. Referral potential. Emotional momentum.",
        "jarvis_priority": "ALL outreach, proposals, and follow-up pointed at this milestone",
    },
    {
        "milestone": "REVENUE STABILITY",
        "target": "Month 3–4",
        "definition": "3 retained clients. $7,500–$15,000/month recurring revenue.",
        "unlocks": "Infrastructure investment. Hire first specialist. Expand outreach.",
        "jarvis_priority": "Optimize onboarding. Build retention systems. Start referral program.",
    },
    {
        "milestone": "MARKET CREDIBILITY",
        "target": "Month 5–6",
        "definition": "5 clients. 2 documented case studies. First inbound referral.",
        "unlocks": "Raise pricing. Qualify harder. Start positioning for Phase 3.",
        "jarvis_priority": "Publish results. Speak to market. Raise anchor pricing 20%.",
    },
    {
        "milestone": "SCALE READY",
        "target": "Month 9–12",
        "definition": "10 clients. $25,000–$50,000/month recurring. Systems run without Captain.",
        "unlocks": "White-label conversations. Investor interest. Acquisition optionality.",
        "jarvis_priority": "Document everything. JARVIS handles 90% autonomously. Captain owns strategy only.",
    },
    {
        "milestone": "PRODUCTIZE",
        "target": "Year 2",
        "definition": "White-label JARVIS to 3+ agencies. SaaS-like recurring revenue.",
        "unlocks": "$1M ARR threshold. Company becomes an asset, not a job.",
        "jarvis_priority": "Build tenant architecture. Build licensing model. Build sales for the product.",
    },
]


class VisionEngine:
    """
    Keeps JARVIS anchored to all three time horizons simultaneously.
    Prevents the tyranny of the urgent from destroying the important.
    """

    def generate_horizon_map(self, current_state: dict) -> dict:
        """
        Given current business state, generate the active horizon map:
        what needs to happen at H1, H2, and H3.
        """
        clients = current_state.get("clients_signed", 0)
        mrr = current_state.get("monthly_recurring_revenue", 0)
        hot_leads = current_state.get("hot_leads", 0)
        days_operating = current_state.get("days_since_launch", 0)

        current_milestone = self._identify_current_milestone(clients, mrr)

        h1_actions = self._generate_h1_actions(current_state, current_milestone)
        h2_actions = self._generate_h2_actions(current_state, current_milestone)
        h3_position = self._generate_h3_position(current_state)

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "current_milestone": current_milestone,
            "horizon_map": {
                "H1": {
                    **HORIZONS["H1"],
                    "active_actions": h1_actions,
                },
                "H2": {
                    **HORIZONS["H2"],
                    "active_actions": h2_actions,
                },
                "H3": {
                    **HORIZONS["H3"],
                    "position_statement": h3_position,
                },
            },
            "compounding_assets": COMPOUNDING_ASSETS,
            "next_milestone": self._next_milestone(current_milestone),
            "vision_note": (
                "Every H1 action should serve H2. Every H2 build should serve H3. "
                "Nothing we do is isolated. Everything compounds."
            ),
        }

    def assess_trajectory(self, historical_states: list[dict]) -> dict:
        """
        Given a series of historical snapshots, assess whether we are
        on trajectory, ahead, or behind the milestone map.
        """
        if not historical_states:
            return {
                "assessment": "INSUFFICIENT_DATA",
                "note": "Need at least 2 data points to assess trajectory.",
            }

        latest = historical_states[-1]
        previous = historical_states[0]

        mrr_growth = latest.get("monthly_recurring_revenue", 0) - previous.get("monthly_recurring_revenue", 0)
        client_growth = latest.get("clients_signed", 0) - previous.get("clients_signed", 0)
        lead_growth = latest.get("hot_leads", 0) - previous.get("hot_leads", 0)

        if mrr_growth > 0 and client_growth > 0:
            trajectory = "ON_TRACK"
            assessment = "Revenue and client count are both growing. Maintain pressure."
        elif mrr_growth > 0 or client_growth > 0:
            trajectory = "PARTIAL_PROGRESS"
            assessment = "One dimension growing, one stalled. Diagnose the stalled dimension."
        elif lead_growth > 0:
            trajectory = "PIPELINE_BUILDING"
            assessment = "Leads growing but not converting. Fix the conversion rate now."
        else:
            trajectory = "STALLED"
            assessment = "No growth in any dimension. Full system diagnostic required."

        return {
            "trajectory": trajectory,
            "assessment": assessment,
            "mrr_change": mrr_growth,
            "client_change": client_growth,
            "lead_change": lead_growth,
            "recommendation": self._trajectory_recommendation(trajectory),
            "assessed_at": datetime.now(UTC).isoformat(),
        }

    def get_compounding_report(self) -> dict:
        """What assets are currently compounding and how fast."""
        return {
            "assets": COMPOUNDING_ASSETS,
            "total_compounding_assets": len(COMPOUNDING_ASSETS),
            "highest_priority": COMPOUNDING_ASSETS[0],
            "compound_principle": (
                "The machine compounds when every client engagement generates "
                "intelligence that serves the next engagement. "
                "We are not just delivering services. We are building a learning system."
            ),
        }

    # ── private helpers ──────────────────────────────────────────────────────

    def _identify_current_milestone(self, clients: int, mrr: float) -> str:
        if clients == 0:
            return "FIRST CLIENT"
        if clients < 3 or mrr < 7500:
            return "REVENUE STABILITY"
        if clients < 5:
            return "MARKET CREDIBILITY"
        if clients < 10:
            return "SCALE READY"
        return "PRODUCTIZE"

    def _next_milestone(self, current: str) -> dict:
        milestones_list = [m["milestone"] for m in TRAJECTORY_MILESTONES]
        try:
            idx = milestones_list.index(current)
            if idx + 1 < len(TRAJECTORY_MILESTONES):
                return TRAJECTORY_MILESTONES[idx + 1]
        except ValueError:
            pass
        return TRAJECTORY_MILESTONES[-1]

    def _generate_h1_actions(self, state: dict, milestone: str) -> list[str]:
        if milestone == "FIRST CLIENT":
            return [
                f"Follow up on all {state.get('hot_leads', 0)} hot leads within 24 hours",
                "Send minimum 48 targeted outreach emails today",
                "Have at least 1 proposal ready to send on demand",
                "Respond to any inbound inquiry within 2 hours",
            ]
        return [
            "Deliver all active client work on schedule",
            "Follow up on open proposals",
            "Continue outreach cadence",
        ]

    def _generate_h2_actions(self, state: dict, milestone: str) -> list[str]:
        if milestone in ("FIRST CLIENT", "REVENUE STABILITY"):
            return [
                "Build the first case study the moment first client results arrive",
                "Document every service delivery into a replicable playbook",
                "Set up referral ask process for satisfied clients",
                "Optimize JARVIS outreach templates based on what is converting",
            ]
        return [
            "Raise prices by 20% for new clients",
            "Start white-label conversations",
            "Document all playbooks",
        ]

    def _generate_h3_position(self, state: dict) -> str:
        return (
            "Aliyar Solutions is building the position of the world's first "
            "AI-native operational company — invisible infrastructure, human-quality output, "
            "and self-compounding intelligence. "
            "No competitor can replicate this without rebuilding from scratch. "
            "In 3 years, the companies that partnered with us early will have a structural "
            "operational advantage that their competitors cannot close. "
            "That is what we are building. Every action today serves that position."
        )

    def _trajectory_recommendation(self, trajectory: str) -> str:
        recommendations = {
            "ON_TRACK": (
                "Maintain current velocity. Look for ways to accelerate the compounding. "
                "Do not change what is working."
            ),
            "PARTIAL_PROGRESS": (
                "Diagnose the stalled dimension. Is it outreach volume? Conversion rate? "
                "Delivery quality? Fix the specific bottleneck — do not increase all activity generally."
            ),
            "PIPELINE_BUILDING": (
                "Leads are there but not converting. "
                "Review proposal quality, follow-up cadence, and objection handling. "
                "The problem is in the middle of the funnel."
            ),
            "STALLED": (
                "Full system diagnostic. Is the offer wrong? Is the targeting wrong? "
                "Is the outreach not sending? Find the exact failure point. "
                "Increase urgency immediately. This cannot continue."
            ),
        }
        return recommendations.get(trajectory, "Continue monitoring.")


vision_engine = VisionEngine()
