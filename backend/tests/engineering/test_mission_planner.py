"""E7-10: Tests for the Mission Planner (E7-2)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.engineering.mission_planner import (
    _heuristic_decompose,
    _parse_decomposition,
    _resolve_dependencies,
    _validate_packages,
    decompose_objective,
)
from app.models.engineering import TaskGraphStatus, WorkPackageStatus


class TestHeuristicDecompose:
    def test_matches_backend_and_frontend_keywords(self):
        packages = _heuristic_decompose(
            "Build a CRM module with API endpoints and a React dashboard", "feature"
        )
        depts = {p["department"] for p in packages}
        assert "backend" in depts
        assert "frontend" in depts

    def test_adds_qa_package_when_multiple_departments(self):
        packages = _heuristic_decompose("Add API endpoint and React UI for X", "feature")
        qa_packages = [p for p in packages if p["department"] == "qa"]
        assert len(qa_packages) == 1
        # QA depends on every other package's title
        other_titles = {p["title"] for p in packages if p["department"] != "qa"}
        assert set(qa_packages[0]["depends_on_titles"]) == other_titles

    def test_no_keyword_match_defaults_to_backend(self):
        packages = _heuristic_decompose("do the thing", "feature")
        assert any(p["department"] == "backend" for p in packages)

    def test_security_keyword_matches_security_department(self):
        packages = _heuristic_decompose("Fix an auth vulnerability", "security")
        assert any(p["department"] == "security" for p in packages)


class TestParseDecomposition:
    def test_parses_clean_json_array(self):
        raw = '[{"department": "backend", "title": "x"}]'
        assert _parse_decomposition(raw) == [{"department": "backend", "title": "x"}]

    def test_parses_json_with_surrounding_prose(self):
        raw = 'Here is the plan:\n[{"department": "backend", "title": "x"}]\nDone.'
        result = _parse_decomposition(raw)
        assert result == [{"department": "backend", "title": "x"}]

    def test_returns_none_for_unparseable_input(self):
        assert _parse_decomposition("not json at all") is None

    def test_returns_none_for_json_object_not_array(self):
        assert _parse_decomposition('{"not": "a list"}') is None


class TestValidatePackages:
    def test_drops_unknown_departments(self):
        packages = [
            {"department": "backend", "title": "a"},
            {"department": "not_a_real_department", "title": "b"},
        ]
        valid = _validate_packages(packages)
        assert len(valid) == 1
        assert valid[0]["title"] == "a"

    def test_normalises_department_case(self):
        packages = [{"department": "BACKEND", "title": "a"}]
        valid = _validate_packages(packages)
        assert valid[0]["department"] == "backend"


class TestResolveDependencies:
    def test_resolves_simple_chain(self):
        packages = [
            {"title": "A", "depends_on_titles": []},
            {"title": "B", "depends_on_titles": ["A"]},
        ]
        resolved = _resolve_dependencies(packages)
        assert resolved[0]["_depends_on_indices"] == []
        assert resolved[1]["_depends_on_indices"] == [0]

    def test_breaks_cycles_rather_than_failing(self):
        packages = [
            {"title": "A", "depends_on_titles": ["B"]},
            {"title": "B", "depends_on_titles": ["A"]},
        ]
        resolved = _resolve_dependencies(packages)
        # One of the two edges must have been dropped to break the cycle.
        total_edges = len(resolved[0]["_depends_on_indices"]) + len(resolved[1]["_depends_on_indices"])
        assert total_edges == 1

    def test_ignores_unknown_dependency_titles(self):
        packages = [{"title": "A", "depends_on_titles": ["does not exist"]}]
        resolved = _resolve_dependencies(packages)
        assert resolved[0]["_depends_on_indices"] == []


class TestDecomposeObjective:
    @pytest.mark.asyncio
    async def test_falls_back_to_heuristic_when_fabric_errors(self):
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        mock_router = MagicMock()
        mock_response = MagicMock(error="provider unavailable", content="", provider="", model="")
        mock_router.chat = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.engineering.mission_planner.get_fabric_router",
            return_value=mock_router,
        ):
            graph = await decompose_objective(db, "Add rate limiting to the outreach webhook", "infra")

        assert graph.decomposed_by == "heuristic"
        assert graph.status == TaskGraphStatus.IN_PROGRESS
        assert db.add.call_count >= 2  # graph + at least one work package

    @pytest.mark.asyncio
    async def test_uses_fabric_decomposition_when_available(self):
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        mock_router = MagicMock()
        mock_response = MagicMock(
            error=None,
            content='[{"department": "backend", "title": "Add rate limiter", '
                     '"description": "d", "acceptance_criteria": [], "depends_on_titles": []}]',
            provider="anthropic",
            model="claude-sonnet",
        )
        mock_router.chat = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.engineering.mission_planner.get_fabric_router",
            return_value=mock_router,
        ):
            graph = await decompose_objective(db, "Add rate limiting", "infra")

        assert graph.decomposed_by == "anthropic/claude-sonnet"

    @pytest.mark.asyncio
    async def test_invalid_objective_type_defaults_to_feature(self):
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        mock_router = MagicMock()
        mock_router.chat = AsyncMock(side_effect=Exception("boom"))

        with patch(
            "app.services.engineering.mission_planner.get_fabric_router",
            return_value=mock_router,
        ):
            graph = await decompose_objective(db, "do a thing", objective_type="not_a_real_type")

        assert graph.objective_type == "feature"
