"""C4-7: Tests for ConflictResolver (C4-3)."""
from __future__ import annotations

import pytest

from app.services.council.conflict_resolution import (
    SCORE_CONFLICT_THRESHOLD,
    ConflictResolver,
    get_conflict_resolver,
)
from app.services.council.reasoning import MemberResponse


def _make_response(
    member_id: str,
    vote_score: float,
    recommendation: str,
    responded: bool = True,
) -> MemberResponse:
    return MemberResponse(
        member_id=member_id,
        provider="test",
        model_name="test-model",
        specialty="test",
        weight=0.33,
        vote_score=vote_score,
        confidence=70.0,
        recommendation=recommendation,
        reasoning="test reasoning",
        responded=responded,
    )


# ── Empty / no responses ───────────────────────────────────────────────────────

def test_no_responses_returns_safe_default():
    resolver = ConflictResolver()
    report = resolver.resolve([])
    assert not report.has_conflicts
    assert report.conflict_count == 0
    assert report.dominant_recommendation == "CAPTAIN_REVIEW"
    assert report.dominant_share == 0.0
    assert "No members responded" in report.summary


def test_non_responding_members_excluded():
    resolver = ConflictResolver()
    responses = [
        _make_response("a", 80.0, "APPROVE", responded=False),
        _make_response("b", 80.0, "APPROVE", responded=False),
    ]
    report = resolver.resolve(responses)
    assert report.dominant_recommendation == "CAPTAIN_REVIEW"


# ── Consensus ─────────────────────────────────────────────────────────────────

def test_consensus_no_conflicts():
    resolver = ConflictResolver()
    responses = [
        _make_response("a", 80.0, "APPROVE"),
        _make_response("b", 82.0, "APPROVE"),
        _make_response("c", 78.0, "APPROVE"),
    ]
    report = resolver.resolve(responses)
    assert not report.has_conflicts
    assert report.conflict_count == 0
    assert report.dominant_recommendation == "APPROVE"
    assert report.dominant_share == pytest.approx(1.0)
    assert "Consensus" in report.summary


# ── Category conflict ──────────────────────────────────────────────────────────

def test_category_conflict_detected():
    resolver = ConflictResolver()
    responses = [
        _make_response("a", 80.0, "APPROVE"),
        _make_response("b", 30.0, "REJECT"),
    ]
    report = resolver.resolve(responses)
    assert report.has_conflicts
    assert report.conflict_count == 1
    assert "recommendation_divergence" in report.details[0].tags


def test_polar_opposition_tagged():
    resolver = ConflictResolver()
    responses = [
        _make_response("a", 85.0, "APPROVE"),
        _make_response("b", 15.0, "REJECT"),
    ]
    report = resolver.resolve(responses)
    assert "polar_opposition" in report.details[0].tags


# ── Score delta conflict ───────────────────────────────────────────────────────

def test_score_conflict_threshold_is_thirty():
    assert SCORE_CONFLICT_THRESHOLD == 30.0


def test_score_delta_conflict():
    resolver = ConflictResolver()
    responses = [
        _make_response("a", 80.0, "APPROVE"),
        _make_response("b", 49.0, "CAPTAIN_REVIEW"),   # delta=31 > 30 → conflict
    ]
    report = resolver.resolve(responses)
    assert report.has_conflicts
    assert "score_delta" in report.details[0].tags


def test_small_score_delta_no_conflict():
    resolver = ConflictResolver()
    responses = [
        _make_response("a", 80.0, "APPROVE"),
        _make_response("b", 52.0, "CAPTAIN_REVIEW"),   # delta=28 < 30 — no conflict
    ]
    # But different recommendation categories → category_conflict still triggers
    report = resolver.resolve(responses)
    # delta=28, but category differs so has_conflicts = True
    assert report.has_conflicts
    assert "recommendation_divergence" in report.details[0].tags
    assert "score_delta" not in report.details[0].tags


# ── Multi-member analysis ──────────────────────────────────────────────────────

def test_dominant_recommendation():
    resolver = ConflictResolver()
    responses = [
        _make_response("a", 80.0, "APPROVE"),
        _make_response("b", 75.0, "APPROVE"),
        _make_response("c", 30.0, "REJECT"),
    ]
    report = resolver.resolve(responses)
    assert report.dominant_recommendation == "APPROVE"
    assert report.dissenting_count == 1


def test_std_dev_computed():
    resolver = ConflictResolver()
    responses = [
        _make_response("a", 70.0, "APPROVE"),
        _make_response("b", 70.0, "APPROVE"),
        _make_response("c", 70.0, "APPROVE"),
    ]
    report = resolver.resolve(responses)
    assert report.score_std_dev == 0.0


def test_std_dev_non_zero_with_spread():
    resolver = ConflictResolver()
    responses = [
        _make_response("a", 60.0, "APPROVE"),
        _make_response("b", 80.0, "APPROVE"),
    ]
    report = resolver.resolve(responses)
    assert report.score_std_dev > 0.0


# ── Pair-wise counting ─────────────────────────────────────────────────────────

def test_three_way_conflict_counts_pairs():
    resolver = ConflictResolver()
    responses = [
        _make_response("a", 90.0, "APPROVE"),
        _make_response("b", 10.0, "REJECT"),
        _make_response("c", 50.0, "CAPTAIN_REVIEW"),
    ]
    report = resolver.resolve(responses)
    # a-b: polar; a-c: delta=40>30 + category; b-c: delta=40>30 + category
    assert report.conflict_count >= 2


# ── Singleton ─────────────────────────────────────────────────────────────────

def test_singleton_returns_same_instance():
    r1 = get_conflict_resolver()
    r2 = get_conflict_resolver()
    assert r1 is r2
