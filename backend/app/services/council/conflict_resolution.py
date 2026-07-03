"""C4-3: Conflict Resolution Framework.

Detects and analyses disagreements between council members.

A *conflict* exists when:
  - Members produce different recommendation categories (APPROVE vs REJECT),  OR
  - Two members have a vote_score delta ≥ SCORE_CONFLICT_THRESHOLD (30 pts).

A *consensus* exists when all responding members share the same recommendation
category, regardless of minor score variation.

The ConflictReport includes:
  - Whether any conflicts exist.
  - The dominant recommendation (majority category).
  - Per-pair conflict details with reason tags.
  - A structured summary suitable for the confidence-scoring stage.

No LLM calls are made here — conflict detection is pure arithmetic so it
never fails, never blocks, and never costs tokens.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.services.council.reasoning import MemberResponse

log = logging.getLogger(__name__)

# Score delta that triggers a pair-level conflict flag.
SCORE_CONFLICT_THRESHOLD = 30.0


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class ConflictDetail:
    """One pair-wise conflict between two responding members."""
    member_a: str
    member_b: str
    score_a: float
    score_b: float
    score_delta: float
    rec_a: str
    rec_b: str
    category_conflict: bool   # True when recommendations are in different buckets
    score_conflict: bool      # True when delta ≥ SCORE_CONFLICT_THRESHOLD
    tags: list[str] = field(default_factory=list)


@dataclass
class ConflictReport:
    """Aggregated conflict analysis for one council session."""
    has_conflicts: bool
    conflict_count: int
    details: list[ConflictDetail]
    dominant_recommendation: str    # most common recommendation category
    dominant_share: float           # fraction of responses that match dominant (0–1)
    dissenting_count: int           # members NOT in dominant group
    score_std_dev: float            # std-dev of vote_scores (measure of spread)
    summary: str                    # human-readable one-liner for logging/traces


# ── Resolver ──────────────────────────────────────────────────────────────────

class ConflictResolver:
    """Stateless conflict detector and reporter."""

    def resolve(self, responses: list[MemberResponse]) -> ConflictReport:
        """Analyse disagreements across all member responses.

        Args:
            responses: All MemberResponse objects from the reasoning stage
                       (including non-responding members).

        Returns:
            ConflictReport with detailed conflict analysis.
        """
        responded = [r for r in responses if r.responded]

        if not responded:
            return ConflictReport(
                has_conflicts=False,
                conflict_count=0,
                details=[],
                dominant_recommendation="CAPTAIN_REVIEW",
                dominant_share=0.0,
                dissenting_count=0,
                score_std_dev=0.0,
                summary="No members responded — escalating to Captain.",
            )

        # Dominant recommendation.
        rec_counts: dict[str, int] = {}
        for r in responded:
            rec_counts[r.recommendation] = rec_counts.get(r.recommendation, 0) + 1
        dominant_rec = max(rec_counts, key=lambda k: rec_counts[k])
        dominant_share = rec_counts[dominant_rec] / len(responded)
        dissenting = len(responded) - rec_counts[dominant_rec]

        # Score std-dev.
        scores = [r.vote_score for r in responded]
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std_dev = round(variance ** 0.5, 2)

        # Pair-wise conflict detection.
        details: list[ConflictDetail] = []
        for i in range(len(responded)):
            for j in range(i + 1, len(responded)):
                a, b = responded[i], responded[j]
                delta = abs(a.vote_score - b.vote_score)
                cat_conflict = a.recommendation != b.recommendation
                score_conflict = delta >= SCORE_CONFLICT_THRESHOLD
                if cat_conflict or score_conflict:
                    tags: list[str] = []
                    if cat_conflict:
                        tags.append("recommendation_divergence")
                    if score_conflict:
                        tags.append("score_delta")
                    if a.recommendation == "APPROVE" and b.recommendation == "REJECT":
                        tags.append("polar_opposition")
                    details.append(ConflictDetail(
                        member_a=a.member_id,
                        member_b=b.member_id,
                        score_a=a.vote_score,
                        score_b=b.vote_score,
                        score_delta=round(delta, 2),
                        rec_a=a.recommendation,
                        rec_b=b.recommendation,
                        category_conflict=cat_conflict,
                        score_conflict=score_conflict,
                        tags=tags,
                    ))

        has_conflicts = len(details) > 0

        if not has_conflicts:
            summary = (
                f"Consensus: all {len(responded)} member(s) → {dominant_rec}. "
                f"Score spread ±{std_dev}."
            )
        else:
            polar = sum(1 for d in details if "polar_opposition" in d.tags)
            summary = (
                f"{len(details)} conflict(s) detected among {len(responded)} member(s). "
                f"Dominant: {dominant_rec} ({dominant_share:.0%}). "
                f"Score spread ±{std_dev}."
                + (f" {polar} polar opposition(s)." if polar else "")
            )

        log.debug(
            "conflict_resolution: %s conflicts | dominant=%s (%.0f%%) | std=%.1f",
            len(details), dominant_rec, dominant_share * 100, std_dev,
        )

        return ConflictReport(
            has_conflicts=has_conflicts,
            conflict_count=len(details),
            details=details,
            dominant_recommendation=dominant_rec,
            dominant_share=dominant_share,
            dissenting_count=dissenting,
            score_std_dev=std_dev,
            summary=summary,
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_resolver: Optional[ConflictResolver] = None


def get_conflict_resolver() -> ConflictResolver:
    global _resolver
    if _resolver is None:
        _resolver = ConflictResolver()
    return _resolver
