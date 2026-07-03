"""C4-4: Confidence Scoring + Unified Recommendation.

After all members have reasoned (C4-2) and conflicts are catalogued (C4-3),
this stage synthesises a single, evidence-bound recommendation.

Algorithm:
  1. Compute a *weighted vote score* — each member's vote_score × their
     normalised weight (from the Assembly).
  2. Convert to *aggregate_confidence* on a 0–1 scale.
  3. Penalise for conflict: each pair-conflict lowers confidence by
     CONFLICT_PENALTY (default 0.04) — disagreement is real uncertainty.
  4. Apply quorum gate: if fewer than MIN_QUORUM members responded, downgrade
     to CAPTAIN_REVIEW regardless of score.
  5. Map to decision:
       ≥ APPROVE_THRESHOLD  (0.75) → APPROVE
       ≥ REVIEW_THRESHOLD   (0.50) → CAPTAIN_REVIEW
       < REVIEW_THRESHOLD          → REJECT
  6. Collect evidence and risks from ALL responding members (deduped).

No LLM calls — pure arithmetic.  Fast, deterministic, auditable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.services.council.assembly import CONFIDENCE_THRESHOLD
from app.services.council.conflict_resolution import ConflictReport
from app.services.council.reasoning import MemberResponse

log = logging.getLogger(__name__)

APPROVE_THRESHOLD = CONFIDENCE_THRESHOLD   # 0.75
REVIEW_THRESHOLD  = 0.50
CONFLICT_PENALTY  = 0.04    # per conflict pair (capped at MAX_CONFLICT_PENALTY)
MAX_CONFLICT_PENALTY = 0.25
MIN_QUORUM        = 2


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class CouncilRecommendation:
    """Unified recommendation from the full council session."""
    decision: str                       # APPROVE | CAPTAIN_REVIEW | REJECT
    aggregate_confidence: float         # 0–1
    actionable: bool                    # True when confidence ≥ APPROVE_THRESHOLD
    weighted_score: float               # raw weighted score 0–100
    member_scores: dict[str, float]     # member_id → vote_score
    member_confidences: dict[str, float]
    responding_members: int
    quorum_met: bool
    unified_reasoning: str
    evidence: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    total_cost_usd: float = 0.0
    total_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "decision":              self.decision,
            "aggregate_confidence":  round(self.aggregate_confidence, 4),
            "actionable":            self.actionable,
            "weighted_score":        round(self.weighted_score, 2),
            "member_scores":         self.member_scores,
            "member_confidences":    self.member_confidences,
            "responding_members":    self.responding_members,
            "quorum_met":            self.quorum_met,
            "unified_reasoning":     self.unified_reasoning,
            "evidence":              self.evidence[:10],
            "risks":                 self.risks[:10],
            "total_cost_usd":        round(self.total_cost_usd, 6),
            "total_tokens":          self.total_tokens,
        }


# ── Engine ─────────────────────────────────────────────────────────────────────

class RecommendationEngine:
    """Synthesises the final council recommendation from member responses."""

    def synthesise(
        self,
        responses: list[MemberResponse],
        conflict_report: ConflictReport,
    ) -> CouncilRecommendation:
        """Produce a unified recommendation with confidence score.

        Args:
            responses:       All MemberResponse objects (including non-responding).
            conflict_report: ConflictReport from C4-3.

        Returns:
            CouncilRecommendation — the council's collective verdict.
        """
        responded = [r for r in responses if r.responded]
        responding_count = len(responded)
        quorum_met = responding_count >= MIN_QUORUM

        # ── Weighted score ─────────────────────────────────────────────────────
        total_weight = sum(r.weight for r in responded)
        if total_weight <= 0:
            weighted_score = 50.0
        else:
            weighted_score = sum(
                r.vote_score * r.weight for r in responded
            ) / total_weight

        # ── Raw confidence (0–1) ───────────────────────────────────────────────
        raw_confidence = weighted_score / 100.0

        # ── Conflict penalty ───────────────────────────────────────────────────
        penalty = min(
            conflict_report.conflict_count * CONFLICT_PENALTY,
            MAX_CONFLICT_PENALTY,
        )
        aggregate_confidence = max(0.0, min(1.0, raw_confidence - penalty))

        # ── Quorum gate ────────────────────────────────────────────────────────
        if not quorum_met:
            decision = "CAPTAIN_REVIEW"
            aggregate_confidence = min(aggregate_confidence, REVIEW_THRESHOLD - 0.01)
            log.warning(
                "council.recommendation: quorum not met (%d < %d) — downgrading to CAPTAIN_REVIEW",
                responding_count, MIN_QUORUM,
            )
        elif aggregate_confidence >= APPROVE_THRESHOLD:
            decision = "APPROVE"
        elif aggregate_confidence >= REVIEW_THRESHOLD:
            decision = "CAPTAIN_REVIEW"
        else:
            decision = "REJECT"

        actionable = aggregate_confidence >= APPROVE_THRESHOLD and quorum_met

        # ── Aggregate evidence and risks ───────────────────────────────────────
        evidence: list[str] = []
        risks: list[str] = []
        seen_e: set[str] = set()
        seen_r: set[str] = set()
        for r in responded:
            for e in r.evidence:
                if e not in seen_e:
                    evidence.append(e)
                    seen_e.add(e)
            for rk in r.risks:
                if rk not in seen_r:
                    risks.append(rk)
                    seen_r.add(rk)

        # ── Unified reasoning ─────────────────────────────────────────────────
        unified_reasoning = _build_reasoning(
            responded=responded,
            conflict_report=conflict_report,
            decision=decision,
            weighted_score=weighted_score,
            aggregate_confidence=aggregate_confidence,
        )

        # ── Cost + token totals ────────────────────────────────────────────────
        total_cost = sum(r.cost_usd for r in responded)
        total_tokens = sum(r.tokens_used for r in responded)

        log.info(
            "council.recommendation: decision=%s confidence=%.2f score=%.1f "
            "members=%d/%d conflicts=%d",
            decision, aggregate_confidence, weighted_score,
            responding_count, len(responses),
            conflict_report.conflict_count,
        )

        return CouncilRecommendation(
            decision=decision,
            aggregate_confidence=round(aggregate_confidence, 4),
            actionable=actionable,
            weighted_score=round(weighted_score, 2),
            member_scores={r.member_id: r.vote_score for r in responded},
            member_confidences={r.member_id: r.confidence for r in responded},
            responding_members=responding_count,
            quorum_met=quorum_met,
            unified_reasoning=unified_reasoning,
            evidence=evidence[:10],
            risks=risks[:10],
            total_cost_usd=round(total_cost, 6),
            total_tokens=total_tokens,
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_reasoning(
    responded: list[MemberResponse],
    conflict_report: ConflictReport,
    decision: str,
    weighted_score: float,
    aggregate_confidence: float,
) -> str:
    lines = [
        f"Decision: {decision}. "
        f"Aggregate confidence: {aggregate_confidence:.0%}. "
        f"Weighted score: {weighted_score:.1f}/100.",
        conflict_report.summary,
    ]
    for r in responded:
        lines.append(
            f"  [{r.member_id}/{r.specialty}] {r.recommendation} "
            f"(score={r.vote_score:.0f}, conf={r.confidence:.0f}): "
            f"{r.reasoning[:200]}"
        )
    return "\n".join(lines)


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: Optional[RecommendationEngine] = None


def get_recommendation_engine() -> RecommendationEngine:
    global _engine
    if _engine is None:
        _engine = RecommendationEngine()
    return _engine
