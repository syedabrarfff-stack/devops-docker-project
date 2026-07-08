"""E7-10: Tests for the Department Registry (E7-3)."""
from __future__ import annotations

from app.services.engineering.department_registry import (
    DEPARTMENTS,
    all_departments,
    find_owning_departments,
    get_department,
    is_known_department,
)

EXPECTED_DEPARTMENTS = {
    "platform", "cloud", "devops", "sre", "backend", "frontend",
    "ai", "security", "database", "documentation", "qa", "architecture",
}


def test_exactly_twelve_departments():
    assert len(DEPARTMENTS) == 12
    assert set(DEPARTMENTS.keys()) == EXPECTED_DEPARTMENTS


def test_all_departments_returns_same_set():
    assert {d.dept_id for d in all_departments()} == EXPECTED_DEPARTMENTS


def test_get_department_known():
    dept = get_department("backend")
    assert dept is not None
    assert dept.name == "Backend Engineering"


def test_get_department_unknown_returns_none():
    assert get_department("nonexistent") is None


def test_is_known_department():
    assert is_known_department("sre") is True
    assert is_known_department("made_up") is False


def test_security_and_architecture_have_no_free_tier_builder():
    """Security-sensitive and cross-cutting design work never gets a free-tier draft."""
    assert get_department("security").builder is None
    assert get_department("architecture").builder is None


def test_other_departments_have_a_builder():
    for dept_id in EXPECTED_DEPARTMENTS - {"security", "architecture"}:
        assert get_department(dept_id).builder is not None, f"{dept_id} should have a builder tier"


def test_find_owning_departments_single_match():
    matches = find_owning_departments(".github/workflows/deploy.yml")
    assert {d.dept_id for d in matches} == {"devops"}


def test_find_owning_departments_multi_match():
    """A file can be owned by more than one department — e.g. fabric code is
    owned by both backend (general service code) and ai (fabric-specific)."""
    matches = find_owning_departments("backend/app/services/fabric/router.py")
    assert {d.dept_id for d in matches} == {"backend", "ai"}


def test_find_owning_departments_no_match():
    assert find_owning_departments("some/random/unowned/path.txt") == []


def test_every_department_default_operation_is_a_string():
    for dept in all_departments():
        assert isinstance(dept.default_operation, str)
        assert dept.default_operation
