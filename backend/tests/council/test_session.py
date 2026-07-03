"""C4-7: End-to-end CouncilSession tests (5 example decisions)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.council import CouncilOutcome, CouncilSession, get_council_session
from app.services.council.assembly import Assembly, CouncilMember
from app.services.council.conflict_resolution import ConflictReport
from app.services.council.recommendation import CouncilRecommendation
from app.services.council.reasoning import MemberResponse


# ── Factories ──────────────────────────────────────────────────────────────────

def _make_assembly(task_category: str = "strategy") -> Assembly:
    return Assembly(
        assembly_id=uuid.uuid4(),
        task_category=task_category,
        question="Test question",
        context={},
        members=[
            CouncilMember("strategist", "anthropic", "claude-sonnet", "strategy", 0.5),
            CouncilMember("analyst",   "openai",    "gpt-4o",         "analysis", 0.5),
        ],
        assembled_at=datetime.now(tz=timezone.utc),
        db_id=uuid.uuid4(),
    )


def _make_responses(vote_score: float, recommendation: str) -> list[MemberResponse]:
    return [
        MemberResponse(
            member_id="strategist",
            provider="anthropic",
            model_name="claude-sonnet",
            specialty="strategy",
            weight=0.5,
            vote_score=vote_score,
            confidence=vote_score,
            recommendation=recommendation,
            reasoning=f"Score {vote_score} because test",
            risks=["risk_a"],
            evidence=["evidence_a"],
            responded=True,
            tokens_used=200,
            cost_usd=0.002,
        ),
        MemberResponse(
            member_id="analyst",
            provider="openai",
            model_name="gpt-4o",
            specialty="analysis",
            weight=0.5,
            vote_score=vote_score,
            confidence=vote_score,
            recommendation=recommendation,
            reasoning=f"Score {vote_score} because test",
            risks=["risk_b"],
            evidence=["evidence_b"],
            responded=True,
            tokens_used=150,
            cost_usd=0.001,
        ),
    ]


def _make_conflict_report(n_conflicts: int = 0) -> ConflictReport:
    return ConflictReport(
        has_conflicts=n_conflicts > 0,
        conflict_count=n_conflicts,
        details=[],
        dominant_recommendation="APPROVE",
        dominant_share=1.0,
        dissenting_count=0,
        score_std_dev=0.0,
        summary="Consensus." if n_conflicts == 0 else f"{n_conflicts} conflicts.",
    )


def _make_recommendation(decision: str, confidence: float) -> CouncilRecommendation:
    return CouncilRecommendation(
        decision=decision,
        aggregate_confidence=confidence,
        actionable=(decision == "APPROVE" and confidence >= 0.75),
        weighted_score=confidence * 100,
        member_scores={"strategist": confidence * 100, "analyst": confidence * 100},
        member_confidences={"strategist": confidence * 100, "analyst": confidence * 100},
        responding_members=2,
        quorum_met=True,
        unified_reasoning=f"Decision: {decision}. Confidence: {confidence:.0%}.",
        evidence=["evidence_a", "evidence_b"],
        risks=["risk_a"],
        total_cost_usd=0.003,
        total_tokens=350,
    )


def _build_mock_session(decision: str, confidence: float, n_conflicts: int = 0, task_category: str = "strategy"):
    """Build a CouncilSession with all sub-components mocked."""
    session = CouncilSession.__new__(CouncilSession)

    assembly = _make_assembly(task_category)
    responses = _make_responses(confidence * 100, decision)
    conflict_report = _make_conflict_report(n_conflicts)
    recommendation = _make_recommendation(decision, confidence)

    mock_assembler = MagicMock()
    mock_assembler.assemble = AsyncMock(return_value=assembly)

    mock_reasoner = MagicMock()
    mock_reasoner.reason = AsyncMock(return_value=responses)

    mock_resolver = MagicMock()
    mock_resolver.resolve = MagicMock(return_value=conflict_report)

    mock_engine = MagicMock()
    mock_engine.synthesise = MagicMock(return_value=recommendation)

    mock_verifier = MagicMock()
    verify_result = MagicMock()
    verify_result.passed = True
    verify_result.issues = []
    mock_verifier.verify = AsyncMock(return_value=verify_result)

    mock_ctx_sync = MagicMock()
    snap = MagicMock()
    snap.snapshot_id = "test-snap-session"
    mock_ctx_sync.snapshot = AsyncMock(return_value=snap)
    mock_ctx_sync.lock = AsyncMock()
    mock_ctx_sync.merge = AsyncMock(return_value=1)
    mock_ctx_sync.discard = MagicMock()

    session._assembler = mock_assembler
    session._reasoner = mock_reasoner
    session._resolver = mock_resolver
    session._engine = mock_engine
    session._verifier = mock_verifier
    session._ctx_sync = mock_ctx_sync

    return session


# ── Scenario 1: Clear APPROVE decision ────────────────────────────────────────

@pytest.mark.asyncio
async def test_scenario_approve_saas_pivot():
    """High confidence consensus → APPROVE (SaaS pivot decision)."""
    session = _build_mock_session("APPROVE", 0.85)
    outcome = await session.run(
        task_category="strategy",
        question="Should Aliyar pivot to a SaaS model for Q3?",
        context={"revenue": 50000, "clients": 12},
    )
    assert isinstance(outcome, CouncilOutcome)
    assert outcome.recommendation.decision == "APPROVE"
    assert outcome.recommendation.actionable is True
    assert outcome.recommendation.quorum_met is True
    assert outcome.verified is True


# ── Scenario 2: Divided council → CAPTAIN_REVIEW ──────────────────────────────

@pytest.mark.asyncio
async def test_scenario_captain_review_expansion():
    """Conflict-penalised medium confidence → CAPTAIN_REVIEW (market expansion)."""
    session = _build_mock_session("CAPTAIN_REVIEW", 0.60, n_conflicts=2)
    outcome = await session.run(
        task_category="strategy",
        question="Should we open a Singapore office?",
        context={"apac_leads": 30},
    )
    assert outcome.recommendation.decision == "CAPTAIN_REVIEW"
    assert outcome.recommendation.actionable is False
    assert outcome.conflict_report.conflict_count == 2


# ── Scenario 3: Clear REJECT decision ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_scenario_reject_risky_client():
    """Low confidence → REJECT (high-risk client engagement)."""
    session = _build_mock_session("REJECT", 0.30)
    outcome = await session.run(
        task_category="legal",
        question="Should we sign the contract with terms waiving liability?",
        context={"contract_value": 120000},
    )
    assert outcome.recommendation.decision == "REJECT"
    assert outcome.recommendation.actionable is False


# ── Scenario 4: Code architecture decision ────────────────────────────────────

@pytest.mark.asyncio
async def test_scenario_approve_architecture_refactor():
    """Technical council approves a code refactoring."""
    session = _build_mock_session("APPROVE", 0.82, task_category="code")
    outcome = await session.run(
        task_category="code",
        question="Should we refactor the AI router to use dependency injection?",
        context={"tech_debt_score": 7.2, "test_coverage": 0.83},
    )
    assert outcome.recommendation.decision == "APPROVE"
    assert outcome.assembly.task_category == "code"
    assert isinstance(outcome.to_dict(), dict)


# ── Scenario 5: Financial decision ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scenario_captain_review_large_spend():
    """Medium confidence on major spend → requires Captain review."""
    session = _build_mock_session("CAPTAIN_REVIEW", 0.55)
    outcome = await session.run(
        task_category="financial",
        question="Should we purchase $40,000 of cloud infrastructure credits?",
        context={"cash_balance": 85000, "runway_months": 14},
    )
    assert outcome.recommendation.decision == "CAPTAIN_REVIEW"
    assert outcome.completed_at is not None


# ── Session validation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_question_raises_value_error():
    session = _build_mock_session("APPROVE", 0.85)
    with pytest.raises(ValueError, match="question must not be empty"):
        await session.run(task_category="strategy", question="  ")


# ── to_dict coverage ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_outcome_to_dict_has_expected_keys():
    session = _build_mock_session("APPROVE", 0.82)
    outcome = await session.run(
        task_category="strategy",
        question="What strategy should we adopt for Q4?",
        context={},
    )
    d = outcome.to_dict()
    assert "session_id" in d
    assert "recommendation" in d
    assert "conflict_report" in d
    assert "member_responses" in d
    assert "verified" in d
    assert "memory_recorded" in d
    assert "completed_at" in d


# ── Verification failure is non-fatal ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_verifier_failure_does_not_raise():
    session = _build_mock_session("APPROVE", 0.82)

    verify_result = MagicMock()
    verify_result.passed = False
    issue = MagicMock()
    issue.category = "hallucination"
    issue.severity = "WARNING"
    issue.detail = "Unverified figure cited"
    verify_result.issues = [issue]
    session._verifier.verify = AsyncMock(return_value=verify_result)

    outcome = await session.run(
        task_category="strategy",
        question="Can we reach $100K revenue by month 6?",
        context={},
    )
    assert outcome.verified is False
    assert len(outcome.verification_issues) == 1
    assert "hallucination" in outcome.verification_issues[0]


# ── Memory recording failure is non-fatal ─────────────────────────────────────

@pytest.mark.asyncio
async def test_memory_recording_failure_is_non_fatal():
    session = _build_mock_session("APPROVE", 0.82)
    session._ctx_sync.merge = AsyncMock(side_effect=Exception("DB connection lost"))

    outcome = await session.run(
        task_category="strategy",
        question="Should we acquire the startup?",
        context={},
        session=MagicMock(),  # provide a session to trigger memory recording
    )
    # Should still return a valid outcome even if memory write fails
    assert outcome.recommendation.decision == "APPROVE"
    assert outcome.memory_recorded is False


# ── Singleton ─────────────────────────────────────────────────────────────────

def test_singleton_returns_same_instance():
    s1 = get_council_session()
    s2 = get_council_session()
    assert s1 is s2
