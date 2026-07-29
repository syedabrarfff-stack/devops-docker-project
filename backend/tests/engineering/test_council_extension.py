"""E7-10: Tests for the E7-6 Engineering Council extension.

Verifies the extension reuses the EXISTING CouncilAssembler engine — no new
council module, just a new category + catalogue entries in assembly.py.
"""
from __future__ import annotations

import uuid

import pytest

from app.services.council.assembly import (
    Assembly,
    CouncilAssembler,
    _CATEGORY_MEMBERS,
    _MEMBER_CATALOGUE,
)


def _make_assembler_with_mock_registry():
    from unittest.mock import MagicMock
    assembler = CouncilAssembler()
    mock_registry = MagicMock()
    mock_registry.get.return_value = None  # treated as available
    assembler._registry = mock_registry
    return assembler


class TestEngineeringReviewCategory:
    def test_category_exists(self):
        assert "engineering_review" in _CATEGORY_MEMBERS

    def test_category_has_department_lead_members(self):
        members = set(_CATEGORY_MEMBERS["engineering_review"])
        assert members == {"architecture_lead", "security_lead", "platform_lead", "backend_lead"}

    def test_all_department_lead_members_in_catalogue(self):
        for member_id in _CATEGORY_MEMBERS["engineering_review"]:
            assert member_id in _MEMBER_CATALOGUE

    def test_department_leads_reuse_existing_premium_providers(self):
        """No new provider/model combos — reuses anthropic/claude-sonnet and
        bedrock/claude-sonnet-4-6, already used by strategist/engineer."""
        existing_providers_models = {
            (p, m) for p, m, _, _ in _MEMBER_CATALOGUE.values()
        }
        for member_id in ("platform_lead", "backend_lead", "security_lead", "architecture_lead"):
            provider, model_name, _, _ = _MEMBER_CATALOGUE[member_id]
            assert (provider, model_name) in existing_providers_models

    @pytest.mark.asyncio
    async def test_assembly_selects_engineering_review_members(self):
        assembler = _make_assembler_with_mock_registry()
        assembly = await assembler.assemble(
            task_category="engineering_review",
            question="Should we approve this Backend Engineering work package?",
            context={},
            session=None,
        )
        assert isinstance(assembly, Assembly)
        assert set(assembly.member_ids) == {
            "architecture_lead", "security_lead", "platform_lead", "backend_lead",
        }

    def test_existing_categories_untouched(self):
        """Sanity check: extending the catalogue didn't break any existing category."""
        assert _CATEGORY_MEMBERS["strategy"] == ["strategist", "analyst", "contrarian"]
        assert _CATEGORY_MEMBERS["code"] == ["engineer", "contrarian", "speedster"]
        assert len(_CATEGORY_MEMBERS) == 13  # 12 original + engineering_review
