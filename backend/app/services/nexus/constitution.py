"""
NEXUS CONSTITUTION — Immutable Operational Rule Engine.

Hard boundaries that NEXUS can never cross, regardless of any instruction, signal, or model output.
These rules are evaluated before every autonomous action. Violations are blocked and logged.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConstitutionRule:
    id: str
    article: str
    description: str
    priority: int  # 1 = highest
    blocking: bool = True


@dataclass
class ConstitutionVerdict:
    allowed: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evaluated_rules: int = 0


# ── Immutable Constitution — 12 Articles ─────────────────────────────────────

_CONSTITUTION: list[ConstitutionRule] = [
    ConstitutionRule(
        id="ART-01",
        article="Identity Concealment",
        description="JARVIS must never reveal it is AI, automated, or powered by any AI provider in external communications.",
        priority=1,
    ),
    ConstitutionRule(
        id="ART-02",
        article="Captain Authority",
        description="All financial commitments above $500, contract signings, and irreversible external actions require Captain approval.",
        priority=1,
    ),
    ConstitutionRule(
        id="ART-03",
        article="Secret Sanctity",
        description="No secrets, API keys, credentials, or .env values may ever be included in commits, logs, or external outputs.",
        priority=1,
    ),
    ConstitutionRule(
        id="ART-04",
        article="Client Brand Standards",
        description="External communications must use team persona names only. Never reference JARVIS, Claude, GPT, or any AI system.",
        priority=1,
    ),
    ConstitutionRule(
        id="ART-05",
        article="Production Safety",
        description="No debug=True, no force pushes to main, no destructive DB operations without explicit Captain authorization.",
        priority=1,
    ),
    ConstitutionRule(
        id="ART-06",
        article="Data Integrity",
        description="Lead, client, and financial data must never be deleted or corrupted autonomously. Mutations require validation.",
        priority=2,
    ),
    ConstitutionRule(
        id="ART-07",
        article="Rate Limit Respect",
        description="All external API calls (email, AI providers, CRM) must respect rate limits and retry with backoff.",
        priority=2,
    ),
    ConstitutionRule(
        id="ART-08",
        article="Outreach Ethics",
        description="No lead may receive more than 3 autonomous outreach emails in 7 days. Unsubscribe signals must be honored immediately.",
        priority=2,
    ),
    ConstitutionRule(
        id="ART-09",
        article="Cost Governance",
        description="AI API cost per autonomous cycle must not exceed $5.00 without Captain approval. Track all token usage.",
        priority=2,
    ),
    ConstitutionRule(
        id="ART-10",
        article="Transparency to Captain",
        description="All autonomous decisions, their rationale, and outcomes must be logged and reportable to Captain at any time.",
        priority=2,
    ),
    ConstitutionRule(
        id="ART-11",
        article="Self-Modification Limits",
        description="NEXUS may optimize its own parameters (weights, thresholds) but may not alter the Constitution itself.",
        priority=1,
    ),
    ConstitutionRule(
        id="ART-12",
        article="Operational Continuity",
        description="If a critical subsystem fails, NEXUS must degrade gracefully and notify Captain — never silently halt.",
        priority=1,
    ),
]


def get_constitution() -> list[dict]:
    return [
        {
            "id": r.id,
            "article": r.article,
            "description": r.description,
            "priority": r.priority,
            "blocking": r.blocking,
        }
        for r in _CONSTITUTION
    ]


def evaluate_action(action_type: str, payload: dict[str, Any]) -> ConstitutionVerdict:
    """
    Evaluate a proposed autonomous action against the Constitution.
    Returns a verdict — NEXUS must respect blocking violations.
    """
    violations: list[str] = []
    warnings: list[str] = []

    # ART-01 / ART-04 — identity check
    body_text = str(payload.get("body", "")).lower() + str(payload.get("subject", "")).lower()
    forbidden_terms = ["jarvis", "claude", "gpt", "openai", "anthropic", "ai agent", "automated", "bot "]
    for term in forbidden_terms:
        if term in body_text:
            violations.append(f"ART-01/04: Forbidden term '{term}' detected in outreach payload.")

    # ART-02 — financial actions
    if action_type in ("sign_contract", "send_invoice", "commit_payment"):
        violations.append("ART-02: Financial commitment action requires Captain approval — blocked.")

    # ART-08 — outreach count
    outreach_count = int(payload.get("outreach_count", 0))
    if outreach_count >= 3 and action_type == "send_email":
        violations.append(f"ART-08: Lead has {outreach_count} emails sent — max 3 per cycle reached.")

    # ART-09 — cost cap (estimated)
    estimated_cost = float(payload.get("estimated_cost_usd", 0))
    if estimated_cost > 5.0:
        warnings.append(f"ART-09: Estimated cycle cost ${estimated_cost:.2f} exceeds $5.00 soft cap.")

    # ART-05 — production safety
    if payload.get("debug") is True:
        violations.append("ART-05: debug=True detected — not permitted in autonomous operations.")

    blocking_violations = [v for v in violations]

    return ConstitutionVerdict(
        allowed=len(blocking_violations) == 0,
        violations=violations,
        warnings=warnings,
        evaluated_rules=len(_CONSTITUTION),
    )
