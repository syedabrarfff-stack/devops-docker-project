"""C4-7: Tests for CouncilAssembler (C4-1)."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.services.council.assembly import (
    CONFIDENCE_THRESHOLD,
    Assembly,
    CouncilAssembler,
    CouncilMember,
    _CATEGORY_MEMBERS,
    _MEMBER_CATALOGUE,
    _normalise_weights,
)


# ── Weight normalisation ───────────────────────────────────────────────────────

def test_normalise_weights_sums_to_one():
    members = [
        CouncilMember("a", "p1", "m1", "s1", 0.3),
        CouncilMember("b", "p2", "m2", "s2", 0.2),
        CouncilMember("c", "p3", "m3", "s3", 0.5),
    ]
    _normalise_weights(members)
    assert abs(sum(m.weight for m in members) - 1.0) < 1e-6


def test_normalise_weights_zero_total_distributes_evenly():
    members = [
        CouncilMember("a", "p1", "m1", "s1", 0.0),
        CouncilMember("b", "p2", "m2", "s2", 0.0),
    ]
    _normalise_weights(members)
    assert members[0].weight == pytest.approx(0.5)
    assert members[1].weight == pytest.approx(0.5)


# ── Catalogue coverage ─────────────────────────────────────────────────────────

def test_all_category_members_exist_in_catalogue():
    for cat, mids in _CATEGORY_MEMBERS.items():
        for mid in mids:
            assert mid in _MEMBER_CATALOGUE, f"{mid} used in category {cat!r} but not in catalogue"


def test_confidence_threshold_is_seventy_five_percent():
    assert CONFIDENCE_THRESHOLD == 0.75


# ── CouncilAssembler with mocked registry ─────────────────────────────────────

def _make_assembler_with_mock_registry(registry_returns_none=True):
    """Return a CouncilAssembler whose ModelRegistry always returns None (available)."""
    assembler = CouncilAssembler()
    mock_registry = MagicMock()
    mock_registry.get.return_value = None if registry_returns_none else MagicMock(
        status="available", availability_pct=100.0, id=uuid.uuid4()
    )
    assembler._registry = mock_registry
    return assembler


@pytest.mark.asyncio
async def test_assemble_strategy_selects_three_members():
    assembler = _make_assembler_with_mock_registry()
    assembly = await assembler.assemble(
        task_category="strategy",
        question="Should we pivot?",
        context={},
        session=None,
    )
    assert isinstance(assembly, Assembly)
    assert len(assembly.members) == 3
    assert set(assembly.member_ids) == {"strategist", "analyst", "contrarian"}


@pytest.mark.asyncio
async def test_assemble_code_selects_correct_members():
    assembler = _make_assembler_with_mock_registry()
    assembly = await assembler.assemble(
        task_category="code",
        question="Refactor auth module?",
        context={},
        session=None,
    )
    assert set(assembly.member_ids) == {"engineer", "contrarian", "speedster"}


@pytest.mark.asyncio
async def test_assemble_unknown_category_falls_back_to_general():
    assembler = _make_assembler_with_mock_registry()
    assembly = await assembler.assemble(
        task_category="unknowncategory",
        question="What to do?",
        context={},
        session=None,
    )
    assert set(assembly.member_ids) == {"strategist", "engineer", "analyst"}


@pytest.mark.asyncio
async def test_assemble_weights_sum_to_one():
    assembler = _make_assembler_with_mock_registry()
    assembly = await assembler.assemble(
        task_category="general",
        question="Test?",
        context={},
        session=None,
    )
    total = sum(m.weight for m in assembly.members)
    assert abs(total - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_assemble_skips_unavailable_members():
    assembler = CouncilAssembler()
    mock_registry = MagicMock()

    def registry_get(provider, model):
        if provider == "anthropic":
            return MagicMock(status="unavailable", availability_pct=0.0, id=uuid.uuid4())
        return None

    mock_registry.get.side_effect = registry_get
    assembler._registry = mock_registry

    assembly = await assembler.assemble(
        task_category="strategy",
        question="Skip unavailable?",
        context={},
        session=None,
    )
    member_ids = assembly.member_ids
    assert "strategist" not in member_ids
    assert len(member_ids) >= 1


@pytest.mark.asyncio
async def test_assemble_assembly_id_is_unique():
    assembler = _make_assembler_with_mock_registry()
    a1 = await assembler.assemble("general", "Q1", {}, None)
    a2 = await assembler.assemble("general", "Q2", {}, None)
    assert a1.assembly_id != a2.assembly_id


@pytest.mark.asyncio
async def test_assemble_stores_question_and_context():
    assembler = _make_assembler_with_mock_registry()
    ctx = {"revenue": 50000, "runway_months": 18}
    assembly = await assembler.assemble("strategy", "Pivot or not?", ctx, None)
    assert assembly.question == "Pivot or not?"
    assert assembly.context == ctx
    assert assembly.task_category == "strategy"
