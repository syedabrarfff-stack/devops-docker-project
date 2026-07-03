"""C4-7: Tests for ParallelReasoner (C4-2) — FabricRouter mocked."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.council.assembly import Assembly, CouncilMember
from app.services.council.reasoning import (
    MemberResponse,
    ParallelReasoner,
    _as_str_list,
    _clamp,
    _normalise_rec,
    _parse_json_vote,
)
import uuid
from datetime import datetime, timezone


def _make_assembly(members=None) -> Assembly:
    if members is None:
        members = [
            CouncilMember("strategist", "anthropic", "claude-sonnet", "strategy", 0.5),
            CouncilMember("analyst",   "openai",    "gpt-4o",         "analysis", 0.5),
        ]
    return Assembly(
        assembly_id=uuid.uuid4(),
        task_category="strategy",
        question="Should we expand to APAC?",
        context={"revenue": 50000},
        members=members,
        assembled_at=datetime.now(tz=timezone.utc),
    )


def _make_fabric_result(vote_score: int = 80, recommendation: str = "APPROVE") -> MagicMock:
    content = json.dumps({
        "vote_score": vote_score,
        "recommendation": recommendation,
        "confidence": 75,
        "reasoning": "Strong market indicators support expansion.",
        "risks": ["currency_risk"],
        "evidence": ["market_size_data"],
    })
    result = MagicMock()
    result.error = None
    result.content = content
    result.provider = "anthropic"
    result.model = "claude-sonnet"
    result.tokens_used = 150
    result.cost_estimate_usd = 0.002
    return result


# ── Helper functions ───────────────────────────────────────────────────────────

def test_clamp_within_bounds():
    assert _clamp(50) == 50.0
    assert _clamp(-5) == 0.0
    assert _clamp(110) == 100.0


def test_clamp_invalid_value():
    assert _clamp("bad") == 50.0
    assert _clamp(None) == 50.0


def test_normalise_rec_approve():
    assert _normalise_rec("approve") == "APPROVE"
    assert _normalise_rec("APPROVE") == "APPROVE"


def test_normalise_rec_reject():
    assert _normalise_rec("REJECT") == "REJECT"


def test_normalise_rec_defaults_to_captain_review():
    assert _normalise_rec("UNKNOWN") == "CAPTAIN_REVIEW"
    assert _normalise_rec(None) == "CAPTAIN_REVIEW"
    assert _normalise_rec("") == "CAPTAIN_REVIEW"


def test_parse_json_vote_valid():
    content = '{"vote_score": 80, "recommendation": "APPROVE", "confidence": 75, "reasoning": "good"}'
    parsed = _parse_json_vote(content)
    assert parsed["vote_score"] == 80
    assert parsed["recommendation"] == "APPROVE"


def test_parse_json_vote_embedded_json():
    content = 'some text {"vote_score": 70, "recommendation": "CAPTAIN_REVIEW", "confidence": 60, "reasoning": "ok"} trailing'
    parsed = _parse_json_vote(content)
    assert parsed["vote_score"] == 70


def test_parse_json_vote_fallback_approve_keyword():
    parsed = _parse_json_vote("I would approve this action")
    assert parsed["vote_score"] == 80


def test_parse_json_vote_fallback_reject_keyword():
    parsed = _parse_json_vote("We should reject this proposal")
    assert parsed["vote_score"] == 40


def test_as_str_list_with_list():
    result = _as_str_list(["a", "b", "c"])
    assert result == ["a", "b", "c"]


def test_as_str_list_with_string():
    result = _as_str_list("single item")
    assert result == ["single item"]


def test_as_str_list_empty():
    assert _as_str_list(None) == []
    assert _as_str_list([]) == []


# ── ParallelReasoner ──────────────────────────────────────────────────────────

def _make_reasoner_with_mock_fabric(fabric_result):
    """Return a ParallelReasoner with FabricRouter mocked."""
    reasoner = ParallelReasoner()
    mock_fabric = MagicMock()
    mock_fabric.chat = AsyncMock(return_value=fabric_result)
    reasoner._fabric = mock_fabric

    mock_ctx_sync = MagicMock()
    snap = MagicMock()
    snap.snapshot_id = "test-snap-id"
    snap.entries = {}
    mock_ctx_sync.snapshot = AsyncMock(return_value=snap)
    mock_ctx_sync.discard = MagicMock()
    reasoner._ctx_sync = mock_ctx_sync

    return reasoner


@pytest.mark.asyncio
async def test_reason_returns_one_response_per_member():
    fabric_result = _make_fabric_result(80, "APPROVE")
    reasoner = _make_reasoner_with_mock_fabric(fabric_result)
    assembly = _make_assembly()

    responses = await reasoner.reason(assembly)
    assert len(responses) == 2
    for r in responses:
        assert isinstance(r, MemberResponse)


@pytest.mark.asyncio
async def test_reason_marks_responded_true_on_success():
    fabric_result = _make_fabric_result(80, "APPROVE")
    reasoner = _make_reasoner_with_mock_fabric(fabric_result)
    assembly = _make_assembly()

    responses = await reasoner.reason(assembly)
    assert all(r.responded for r in responses)


@pytest.mark.asyncio
async def test_reason_populates_vote_score_and_recommendation():
    fabric_result = _make_fabric_result(85, "APPROVE")
    reasoner = _make_reasoner_with_mock_fabric(fabric_result)
    assembly = _make_assembly()

    responses = await reasoner.reason(assembly)
    for r in responses:
        assert r.vote_score == 85.0
        assert r.recommendation == "APPROVE"


@pytest.mark.asyncio
async def test_reason_on_fabric_error_returns_not_responded():
    mock_result = MagicMock()
    mock_result.error = "provider_unavailable"
    mock_result.content = ""

    reasoner = _make_reasoner_with_mock_fabric(mock_result)
    assembly = _make_assembly()

    responses = await reasoner.reason(assembly)
    assert all(not r.responded for r in responses)
    assert all(r.error == "provider_unavailable" for r in responses)


@pytest.mark.asyncio
async def test_reason_on_timeout_returns_not_responded():
    reasoner = ParallelReasoner()

    async def slow_chat(**kwargs):
        await asyncio.sleep(60)  # will be cancelled

    mock_fabric = MagicMock()
    mock_fabric.chat = slow_chat
    reasoner._fabric = mock_fabric

    mock_ctx_sync = MagicMock()
    snap = MagicMock()
    snap.snapshot_id = "test-snap-timeout"
    snap.entries = {}
    mock_ctx_sync.snapshot = AsyncMock(return_value=snap)
    mock_ctx_sync.discard = MagicMock()
    reasoner._ctx_sync = mock_ctx_sync

    assembly = _make_assembly(members=[
        CouncilMember("strategist", "anthropic", "claude-sonnet", "strategy", 1.0),
    ])

    # Patch the timeout constant to speed up the test
    with patch("app.services.council.reasoning._MEMBER_TIMEOUT", 0.05):
        responses = await reasoner.reason(assembly)

    assert len(responses) == 1
    assert not responses[0].responded
    assert responses[0].error == "timeout"


@pytest.mark.asyncio
async def test_reason_uses_force_provider_and_model():
    fabric_result = _make_fabric_result(80, "APPROVE")
    reasoner = _make_reasoner_with_mock_fabric(fabric_result)
    assembly = _make_assembly(members=[
        CouncilMember("strategist", "anthropic", "claude-opus", "strategy", 1.0),
    ])

    await reasoner.reason(assembly)

    # Verify force_provider/force_model were passed
    call_kwargs = reasoner._fabric.chat.call_args.kwargs
    assert call_kwargs.get("force_provider") == "anthropic"
    assert call_kwargs.get("force_model") == "claude-opus"


@pytest.mark.asyncio
async def test_reason_without_session_skips_snapshot():
    fabric_result = _make_fabric_result(80, "APPROVE")
    reasoner = _make_reasoner_with_mock_fabric(fabric_result)
    assembly = _make_assembly()

    # Pass session=None — snapshot should NOT be called
    reasoner._ctx_sync.snapshot.reset_mock()
    responses = await reasoner.reason(assembly, session=None)

    reasoner._ctx_sync.snapshot.assert_not_called()
    assert len(responses) == 2
