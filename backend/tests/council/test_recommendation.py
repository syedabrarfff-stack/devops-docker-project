"""C4-7: Tests for RecommendationEngine (C4-4)."""
from __future__ import annotations

import pytest

from app.services.council.conflict_resolution import (
    ConflictDetail,
    ConflictReport,
)
from app.services.council.recommendation import (
    APPROVE_THRESHOLD,
    CONFLICT_PENALTY,
    MAX_CONFLICT_PENALTY,
    MIN_QUORUM,
    REVIEW_THRESHOLD,
    CouncilRecommendation,
    RecommendationEngine,
    get_recommendation_engine,
)
from app.services.council.reasoning import MemberResponse


def _make_response(
    member_id: str,
    vote_score: float,
    recommendation: str = "APPROVE",
    weight: float = 0.33,
    responded: bool = True,
    cost_usd: float = 0.001,
    tokens_used: int = 100,
) -> MemberResponse:
    return MemberResponse(
        member_id=member_id,
        provider="test",
        model_name="test-model",
        specialty="test",
        weight=weight,
        vote_score=vote_score,
        confidence=vote_score,
        recommendation=recommendation,
        reasoning="test reasoning text that is long enough",
        risks=["risk_a"],
        evidence=["evidence_a"],
        responded=responded,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
    )


def _no_conflict_report(dominant_rec: str = "APPROVE") -> ConflictReport:
    return ConflictReport(
        has_conflicts=False,
        conflict_count=0,
        details=[],
        dominant_recommendation=dominant_rec,
        dominant_share=1.0,
        dissenting_count=0,
        score_std_dev=0.0,
        summary="Consensus.",
    )


def _conflict_report(n_conflicts: int) -> ConflictReport:
    return ConflictReport(
        has_conflicts=True,
        conflict_count=n_conflicts,
        details=[],
        dominant_recommendation="APPROVE",
        dominant_share=0.5,
        dissenting_count=1,
        score_std_dev=10.0,
        summary=f"{n_conflicts} conflicts.",
    )


# ── Threshold constants ────────────────────────────────────────────────────────

def test_approve_threshold_is_seventy_five_percent():
    assert APPROVE_THRESHOLD == 0.75


def test_review_threshold_is_fifty_percent():
    assert REVIEW_THRESHOLD == 0.50


def test_conflict_penalty_per_pair():
    assert CONFLICT_PENALTY == 0.04


def test_max_conflict_penalty():
    assert MAX_CONFLICT_PENALTY == 0.25


def test_min_quorum():
    assert MIN_QUORUM == 2


# ── APPROVE decision ──────────────────────────────────────────────────────────

def test_approve_when_high_confidence():
    engine = RecommendationEngine()
    responses = [
        _make_response("a", 80.0, "APPROVE", 0.5),
        _make_response("b", 80.0, "APPROVE", 0.5),
    ]
    rec = engine.synthesise(responses, _no_conflict_report())
    assert rec.decision == "APPROVE"
    assert rec.aggregate_confidence >= APPROVE_THRESHOLD
    assert rec.actionable is True
    assert rec.quorum_met is True


# ── CAPTAIN_REVIEW decision ───────────────────────────────────────────────────

def test_captain_review_when_medium_confidence():
    engine = RecommendationEngine()
    responses = [
        _make_response("a", 60.0, "CAPTAIN_REVIEW", 0.5),
        _make_response("b", 60.0, "CAPTAIN_REVIEW", 0.5),
    ]
    rec = engine.synthesise(responses, _no_conflict_report("CAPTAIN_REVIEW"))
    assert rec.decision == "CAPTAIN_REVIEW"
    assert rec.actionable is False


# ── REJECT decision ───────────────────────────────────────────────────────────

def test_reject_when_low_confidence():
    engine = RecommendationEngine()
    responses = [
        _make_response("a", 30.0, "REJECT", 0.5),
        _make_response("b", 30.0, "REJECT", 0.5),
    ]
    rec = engine.synthesise(responses, _no_conflict_report("REJECT"))
    assert rec.decision == "REJECT"
    assert rec.actionable is False


# ── Quorum gate ───────────────────────────────────────────────────────────────

def test_quorum_not_met_downgrades_to_captain_review():
    engine = RecommendationEngine()
    responses = [
        _make_response("a", 90.0, "APPROVE", responded=True),   # only 1 responder
        _make_response("b", 90.0, "APPROVE", responded=False),
    ]
    rec = engine.synthesise(responses, _no_conflict_report())
    assert rec.decision == "CAPTAIN_REVIEW"
    assert rec.quorum_met is False
    assert rec.aggregate_confidence < REVIEW_THRESHOLD


def test_exactly_two_responders_meets_quorum():
    engine = RecommendationEngine()
    responses = [
        _make_response("a", 80.0, "APPROVE", 0.5),
        _make_response("b", 80.0, "APPROVE", 0.5),
    ]
    rec = engine.synthesise(responses, _no_conflict_report())
    assert rec.quorum_met is True


# ── Conflict penalty ──────────────────────────────────────────────────────────

def test_conflict_penalty_applied():
    engine = RecommendationEngine()
    responses = [
        _make_response("a", 80.0, "APPROVE", 0.5),
        _make_response("b", 80.0, "APPROVE", 0.5),
    ]
    rec_no_conflict = engine.synthesise(responses, _no_conflict_report())
    rec_with_conflict = engine.synthesise(responses, _conflict_report(1))
    expected_penalty = CONFLICT_PENALTY
    diff = rec_no_conflict.aggregate_confidence - rec_with_conflict.aggregate_confidence
    assert abs(diff - expected_penalty) < 1e-4


def test_conflict_penalty_capped_at_max():
    engine = RecommendationEngine()
    responses = [
        _make_response("a", 90.0, "APPROVE", 0.5),
        _make_response("b", 90.0, "APPROVE", 0.5),
    ]
    many_conflicts = _conflict_report(100)
    rec = engine.synthesise(responses, many_conflicts)
    raw = 0.90
    expected_min = raw - MAX_CONFLICT_PENALTY
    assert rec.aggregate_confidence >= expected_min - 1e-6


def test_confidence_never_negative():
    engine = RecommendationEngine()
    responses = [
        _make_response("a", 5.0, "REJECT", 0.5),
        _make_response("b", 5.0, "REJECT", 0.5),
    ]
    rec = engine.synthesise(responses, _conflict_report(100))
    assert rec.aggregate_confidence >= 0.0


# ── Weighted scoring ──────────────────────────────────────────────────────────

def test_weighted_score_favours_high_weight_member():
    engine = RecommendationEngine()
    responses = [
        _make_response("a", 90.0, "APPROVE", weight=0.9),    # high weight
        _make_response("b", 10.0, "REJECT", weight=0.1),
    ]
    rec = engine.synthesise(responses, _conflict_report(1))
    assert rec.weighted_score > 75.0


# ── Evidence and risk aggregation ─────────────────────────────────────────────

def test_evidence_and_risks_aggregated():
    engine = RecommendationEngine()
    r1 = _make_response("a", 80.0)
    r1.evidence = ["e1", "e2"]
    r1.risks = ["r1"]
    r2 = _make_response("b", 80.0)
    r2.evidence = ["e3"]
    r2.risks = ["r2", "r3"]
    rec = engine.synthesise([r1, r2], _no_conflict_report())
    assert "e1" in rec.evidence
    assert "e3" in rec.evidence
    assert "r1" in rec.risks
    assert "r3" in rec.risks


def test_evidence_deduplication():
    engine = RecommendationEngine()
    r1 = _make_response("a", 80.0)
    r1.evidence = ["same_evidence"]
    r2 = _make_response("b", 80.0)
    r2.evidence = ["same_evidence"]
    rec = engine.synthesise([r1, r2], _no_conflict_report())
    assert rec.evidence.count("same_evidence") == 1


# ── Cost and token totals ─────────────────────────────────────────────────────

def test_total_cost_and_tokens_summed():
    engine = RecommendationEngine()
    responses = [
        _make_response("a", 80.0, cost_usd=0.002, tokens_used=200),
        _make_response("b", 80.0, cost_usd=0.003, tokens_used=300),
    ]
    rec = engine.synthesise(responses, _no_conflict_report())
    assert abs(rec.total_cost_usd - 0.005) < 1e-6
    assert rec.total_tokens == 500


# ── member_scores and member_confidences ──────────────────────────────────────

def test_member_scores_dict():
    engine = RecommendationEngine()
    responses = [
        _make_response("strategist", 80.0),
        _make_response("analyst", 60.0),
    ]
    rec = engine.synthesise(responses, _no_conflict_report())
    assert "strategist" in rec.member_scores
    assert rec.member_scores["strategist"] == pytest.approx(80.0)


# ── to_dict ───────────────────────────────────────────────────────────────────

def test_to_dict_keys():
    engine = RecommendationEngine()
    responses = [
        _make_response("a", 80.0, weight=0.5),
        _make_response("b", 80.0, weight=0.5),
    ]
    rec = engine.synthesise(responses, _no_conflict_report())
    d = rec.to_dict()
    assert "decision" in d
    assert "aggregate_confidence" in d
    assert "actionable" in d
    assert "unified_reasoning" in d
    assert "evidence" in d
    assert "risks" in d


# ── Singleton ─────────────────────────────────────────────────────────────────

def test_singleton_returns_same_instance():
    e1 = get_recommendation_engine()
    e2 = get_recommendation_engine()
    assert e1 is e2
