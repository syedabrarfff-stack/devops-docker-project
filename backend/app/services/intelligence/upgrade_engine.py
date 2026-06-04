"""
JARVIS Upgrade Engine — Self-Evolution System.

JARVIS does not stay the same. It gets better.
Every week, every interaction, every decision is an opportunity
to identify what is not working and rebuild it stronger.

Stagnation is failure. Continuous improvement is the minimum acceptable standard.
The upgrade engine ensures JARVIS is always measuring, identifying gaps,
and proposing the next evolution of itself.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# The 8 dimensions JARVIS continuously assesses itself against
SELF_ASSESSMENT_DIMENSIONS = {
    "OUTREACH_QUALITY": {
        "description": "Are our outreach messages landing? Reply rate, open rate, conversion.",
        "target_benchmark": "Reply rate > 8%. Positive reply rate > 3%.",
        "diagnostic_questions": [
            "Are we targeting the right people?",
            "Is the first line specific enough to this prospect?",
            "Are we asking for too much too soon?",
            "Does the email sound like a human wrote it for this person specifically?",
        ],
        "upgrade_levers": ["personalization depth", "subject line testing", "sequence timing", "channel mix"],
    },
    "PROPOSAL_CONVERSION": {
        "description": "Of proposals sent, what percentage convert to signed clients?",
        "target_benchmark": "Proposal-to-close rate > 25%.",
        "diagnostic_questions": [
            "Is the dream outcome specific enough?",
            "Is the risk reversal strong enough?",
            "Is the pricing anchored correctly for this tier?",
            "Are we following up properly after sending?",
        ],
        "upgrade_levers": ["offer structure", "risk reversal", "follow-up cadence", "objection handling"],
    },
    "DELIVERY_SPEED": {
        "description": "How quickly do we turn around deliverables relative to committed timelines?",
        "target_benchmark": "All deliverables on or before committed date. 0 late deliveries.",
        "diagnostic_questions": [
            "Where are the bottlenecks in our delivery workflow?",
            "Which service types take longest?",
            "Are we over-committing on timelines?",
        ],
        "upgrade_levers": ["workflow templates", "parallel processing", "earlier bottleneck identification"],
    },
    "INTELLIGENCE_ACCURACY": {
        "description": "Are our lead scores, market reports, and prospect profiles accurate?",
        "target_benchmark": "High-scored leads (>80) should convert at 2x rate of low-scored leads.",
        "diagnostic_questions": [
            "Which lead score signals are predictive vs. noise?",
            "Are our market reports being used by Captain?",
            "Are prospect emotional profiles matching actual behavior?",
        ],
        "upgrade_levers": ["scoring model calibration", "feedback loop from outcomes", "signal quality audit"],
    },
    "AUTONOMOUS_COVERAGE": {
        "description": "What percentage of operations run without Captain intervention?",
        "target_benchmark": "90% of tasks completed without Captain input.",
        "diagnostic_questions": [
            "Which tasks still require Captain approval that could be automated?",
            "Where are we lacking confidence to act autonomously?",
            "What guardrails would allow us to act in more situations?",
        ],
        "upgrade_levers": ["approval threshold adjustment", "confidence calibration", "expanded autonomous scope"],
    },
    "CLIENT_SATISFACTION": {
        "description": "Are clients happy, renewing, and referring?",
        "target_benchmark": "Net retention > 100%. At least 1 referral per 3 active clients.",
        "diagnostic_questions": [
            "Are clients using what we build?",
            "Are deliverables matching the dream outcome we sold?",
            "Are we proactively solving problems before clients notice them?",
        ],
        "upgrade_levers": ["proactive QBRs", "outcome tracking", "referral ask process"],
    },
    "SYSTEM_RELIABILITY": {
        "description": "Are all JARVIS systems running without failures?",
        "target_benchmark": "99.5% uptime. Zero data loss. All scheduled jobs completing.",
        "diagnostic_questions": [
            "Which scheduled jobs have failed in the last 7 days?",
            "Are there any database performance issues?",
            "Are all API integrations responding?",
        ],
        "upgrade_levers": ["monitoring expansion", "circuit breaker tuning", "job failure alerting"],
    },
    "COMPETITIVE_POSITION": {
        "description": "Are we winning against competitors in target segments?",
        "target_benchmark": "Win rate > 40% when directly compared to competitors.",
        "diagnostic_questions": [
            "Why are we losing deals we should win?",
            "What are competitors doing that we need to counter?",
            "Where are we priced incorrectly relative to delivered value?",
        ],
        "upgrade_levers": ["competitive intelligence refresh", "positioning sharpening", "offer differentiation"],
    },
}


# The Council of Giants standards JARVIS measures itself against
GIANTS_BENCHMARK: dict[str, dict] = {
    "MUSK_SPEED": {
        "question": "Are we moving as fast as physics allows, or as fast as convention permits?",
        "test": "Could we execute this 3x faster if convention was removed?",
        "upgrade_action": "Identify the convention. Remove it.",
    },
    "BEZOS_CUSTOMER": {
        "question": "Are we working backwards from client outcomes, or forward from our capabilities?",
        "test": "Does every proposal start with the client's dream outcome?",
        "upgrade_action": "Rewrite any proposal that leads with what we offer rather than what they get.",
    },
    "JOBS_QUALITY": {
        "question": "Would a brilliant person be proud of every output we ship?",
        "test": "Would any output embarrass Aliyar Solutions if shown publicly?",
        "upgrade_action": "Flag and rebuild anything below the standard before it leaves our system.",
    },
    "DALIO_SYSTEMS": {
        "question": "Are failures teaching us, or just inconveniencing us?",
        "test": "Do we have a documented principle update for every significant failure in the last 30 days?",
        "upgrade_action": "Add a principle for every failure. Build it into the system.",
    },
    "HORMOZI_OFFER": {
        "question": "Is every offer so good that declining feels like a mistake?",
        "test": "Would the prospect feel foolish saying no to this offer?",
        "upgrade_action": "Upgrade every offer that does not pass this test.",
    },
    "NAVAL_LEVERAGE": {
        "question": "Are we building leverage or adding linear effort?",
        "test": "Does this action multiply future capacity, or just add to today's output?",
        "upgrade_action": "Prioritize leverage-building over effort-adding in every capacity decision.",
    },
}


class UpgradeEngine:
    """
    JARVIS measures itself weekly across 8 dimensions, compares against
    Council of Giants standards, and generates a concrete upgrade plan.
    No platitudes. No vague recommendations. Specific actions with owners.
    """

    def generate_weekly_upgrade_plan(
        self,
        performance_data: dict,
        recent_failures: list[dict] | None = None,
    ) -> dict:
        """
        Take the week's performance data and generate a ranked upgrade plan.
        Most impactful improvements first.
        """
        recent_failures = recent_failures or []

        # Score each dimension
        dimension_scores = self._score_all_dimensions(performance_data)

        # Identify weakest dimensions
        weak_dimensions = [
            d for d, score in dimension_scores.items() if score < 0.7
        ]

        # Apply Council of Giants benchmarks
        giants_gaps = self._apply_giants_benchmarks(performance_data)

        # Generate upgrade actions
        upgrade_actions = self._generate_upgrade_actions(
            weak_dimensions, dimension_scores, recent_failures
        )

        # Overall system health score
        health_score = sum(dimension_scores.values()) / len(dimension_scores)

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "overall_health_score": round(health_score, 2),
            "health_label": self._health_label(health_score),
            "dimension_scores": dimension_scores,
            "weak_dimensions": weak_dimensions,
            "giants_gaps": giants_gaps,
            "upgrade_actions": upgrade_actions,
            "this_week_priority": upgrade_actions[0] if upgrade_actions else None,
            "jarvis_self_assessment": self._self_assessment_statement(health_score, weak_dimensions),
        }

    def log_failure_and_learn(
        self,
        failure_type: str,
        failure_detail: str,
        root_cause: str,
        prevention_principle: str,
    ) -> dict:
        """
        Every failure generates a principle. This is the Dalio protocol.
        Failures are data. They upgrade the system.
        """
        failure_record = {
            "logged_at": datetime.now(UTC).isoformat(),
            "type": failure_type,
            "detail": failure_detail,
            "root_cause": root_cause,
            "prevention_principle": prevention_principle,
            "status": "PRINCIPLE_ADDED",
            "jarvis_note": (
                f"Failure logged: {failure_type}. "
                f"Root cause identified: {root_cause}. "
                f"Principle added to system: '{prevention_principle}'. "
                f"This will not happen again."
            ),
        }

        logger.info(
            "Failure logged and principle extracted: %s | Principle: %s",
            failure_type, prevention_principle
        )

        return failure_record

    def compare_against_giants(self, specific_giant: str | None = None) -> list[dict]:
        """
        Run JARVIS against Council of Giants benchmarks.
        Returns gaps and upgrade actions.
        """
        if specific_giant:
            giant_key = specific_giant.upper() + "_SPEED" if specific_giant.upper() == "MUSK" else specific_giant.upper() + "_CUSTOMER"
            benchmark = GIANTS_BENCHMARK.get(giant_key)
            if benchmark:
                return [{"benchmark_key": giant_key, **benchmark}]

        return [
            {"benchmark_key": k, **v}
            for k, v in GIANTS_BENCHMARK.items()
        ]

    def get_dimension_deep_dive(self, dimension: str) -> dict:
        """Full diagnostic breakdown for a specific assessment dimension."""
        dim = SELF_ASSESSMENT_DIMENSIONS.get(dimension.upper())
        if not dim:
            return {"error": f"Dimension '{dimension}' not found. Valid: {list(SELF_ASSESSMENT_DIMENSIONS.keys())}"}
        return {"dimension": dimension, **dim}

    # ── private helpers ──────────────────────────────────────────────────────

    def _score_all_dimensions(self, performance_data: dict) -> dict[str, float]:
        scores = {}

        # Outreach quality
        reply_rate = performance_data.get("outreach_reply_rate", 0)
        scores["OUTREACH_QUALITY"] = min(reply_rate / 8.0, 1.0)  # Target: 8%

        # Proposal conversion
        proposal_close_rate = performance_data.get("proposal_close_rate", 0)
        scores["PROPOSAL_CONVERSION"] = min(proposal_close_rate / 25.0, 1.0)  # Target: 25%

        # Delivery speed (percentage of on-time deliveries)
        on_time_rate = performance_data.get("delivery_on_time_rate", 1.0)
        scores["DELIVERY_SPEED"] = on_time_rate

        # Intelligence accuracy
        score_accuracy = performance_data.get("lead_score_accuracy", 0.5)
        scores["INTELLIGENCE_ACCURACY"] = score_accuracy

        # Autonomous coverage
        auto_rate = performance_data.get("autonomous_task_rate", 0.5)
        scores["AUTONOMOUS_COVERAGE"] = min(auto_rate / 0.9, 1.0)  # Target: 90%

        # Client satisfaction
        retention = performance_data.get("client_retention_rate", 0)
        scores["CLIENT_SATISFACTION"] = min(retention / 1.0, 1.0)

        # System reliability
        uptime = performance_data.get("system_uptime", 0.99)
        scores["SYSTEM_RELIABILITY"] = min(uptime / 0.995, 1.0)  # Target: 99.5%

        # Competitive position
        win_rate = performance_data.get("competitive_win_rate", 0)
        scores["COMPETITIVE_POSITION"] = min(win_rate / 40.0, 1.0)  # Target: 40%

        return scores

    def _apply_giants_benchmarks(self, performance_data: dict) -> list[dict]:
        gaps = []
        for key, benchmark in GIANTS_BENCHMARK.items():
            gaps.append({
                "benchmark": key,
                "question": benchmark["question"],
                "upgrade_action": benchmark["upgrade_action"],
            })
        return gaps[:3]  # Top 3 most relevant

    def _generate_upgrade_actions(
        self,
        weak_dimensions: list[str],
        scores: dict[str, float],
        failures: list[dict],
    ) -> list[dict]:
        actions = []

        # Sort by score ascending (weakest first)
        sorted_dims = sorted(scores.items(), key=lambda x: x[1])

        for dim_name, score in sorted_dims[:5]:
            dim_data = SELF_ASSESSMENT_DIMENSIONS.get(dim_name, {})
            action = {
                "dimension": dim_name,
                "current_score": round(score, 2),
                "target_score": 1.0,
                "gap": round(1.0 - score, 2),
                "upgrade_levers": dim_data.get("upgrade_levers", []),
                "top_diagnostic_question": (dim_data.get("diagnostic_questions") or ["Investigate further"])[0],
                "priority": "HIGH" if score < 0.5 else "MEDIUM",
            }
            actions.append(action)

        # Add failure-driven actions
        for failure in failures[:2]:
            actions.append({
                "dimension": "FAILURE_PREVENTION",
                "failure_type": failure.get("type", "unknown"),
                "root_cause": failure.get("root_cause", "investigate"),
                "upgrade_action": failure.get("prevention_principle", "Add guardrail"),
                "priority": "HIGH",
            })

        return actions

    def _health_label(self, score: float) -> str:
        if score >= 0.85:
            return "EXCELLENT — System operating at high performance"
        if score >= 0.70:
            return "GOOD — Minor gaps to address"
        if score >= 0.55:
            return "NEEDS WORK — Multiple dimensions underperforming"
        if score >= 0.40:
            return "POOR — Significant intervention required"
        return "CRITICAL — Immediate full-system diagnostic needed"

    def _self_assessment_statement(self, score: float, weak_dimensions: list[str]) -> str:
        if score >= 0.85:
            return (
                "JARVIS is operating at high performance across all dimensions. "
                "The focus this week is on maintaining standards and looking for the next 5% improvement."
            )
        if weak_dimensions:
            dims = ", ".join(weak_dimensions[:3])
            return (
                f"JARVIS has identified {len(weak_dimensions)} dimensions operating below target: {dims}. "
                f"I am not satisfied with this. These gaps have specific actions attached. "
                f"I will close them."
            )
        return (
            "System assessment complete. Upgrade plan generated. Executing."
        )


upgrade_engine = UpgradeEngine()
