"""E7-2: Mission Planner — objective -> task graph decomposition.

Pipeline (see docs/architecture/HEADQUARTERS_ENGINEERING_ORG.md section 2):
  Objective -> Fabric Router (classify + decompose into department-shaped
  work packages) -> dependency resolution -> Authority Matrix pre-check per
  package -> persisted TaskGraph -> handed to the Work Package Dispatcher.

If the Fabric call fails or returns unusable output, falls back to a
deterministic heuristic decomposition (keyword match against department
ownership) rather than hard-failing — degraded but functional, matching the
existing codebase's verify-then-fallback pattern.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engineering import EngineeringTaskGraph, EngineeringWorkPackage, TaskGraphStatus, WorkPackageStatus
from app.services.engineering.department_registry import DEPARTMENTS, is_known_department
from app.services.fabric.router import get_fabric_router
from app.services.kernel.authority_matrix import lookup_tier

log = logging.getLogger(__name__)

_OBJECTIVE_TYPES = {"feature", "infra", "security", "migration", "incident"}

_DECOMPOSITION_PROMPT = """You are the Mission Planner for a software engineering organization.
Decompose the objective below into work packages, one per owning department.

Departments available: {departments}

Objective: {objective}
Objective type: {objective_type}

Respond with ONLY a JSON array, no prose. Each element:
{{"department": "<one of the departments above>", "title": "<short title>",
  "description": "<what this work package does>",
  "acceptance_criteria": ["<testable criterion>", ...],
  "depends_on_titles": ["<title of another work package in this same list, if any>"]}}

Keep it to the departments genuinely needed — do not include a department with nothing to do.
"""


def _department_list_str() -> str:
    return ", ".join(sorted(DEPARTMENTS.keys()))


def _heuristic_decompose(objective: str, objective_type: str) -> list[dict[str, Any]]:
    """Deterministic fallback: keyword-match the objective against each
    department's `owns` description. Always includes documentation + qa
    for anything non-trivial, matching real engineering practice."""
    text = objective.lower()
    packages: list[dict[str, Any]] = []

    keyword_map = {
        "backend": ("api", "endpoint", "service", "fastapi", "backend", "business logic"),
        "frontend": ("ui", "react", "frontend", "component", "dashboard view", "page"),
        "database": ("schema", "migration", "table", "index", "database", "query"),
        "devops": ("ci", "pipeline", "docker", "github action", "deploy"),
        "cloud": ("aws", "terraform", "ec2", "s3", "iam", "cloud"),
        "platform": ("kubernetes", "eks", "networking", "infrastructure"),
        "sre": ("incident", "monitoring", "uptime", "alert", "self-heal"),
        "ai": ("model", "fabric", "routing", "prompt", "llm"),
        "security": ("auth", "security", "vulnerability", "iam", "credential"),
        "architecture": ("architecture", "design review", "adr"),
    }
    matched = set()
    for dept_id, keywords in keyword_map.items():
        if any(kw in text for kw in keywords):
            matched.add(dept_id)

    if not matched:
        # Nothing matched — default to backend as the generic owner.
        matched.add("backend")

    for dept_id in matched:
        dept = DEPARTMENTS[dept_id]
        packages.append({
            "department": dept_id,
            "title": f"{dept.name}: {objective[:60]}",
            "description": f"Heuristic decomposition (Fabric unavailable) — {dept.owns}",
            "acceptance_criteria": ["Implementation reviewed and tests pass"],
            "depends_on_titles": [],
        })

    # Every objective touching >1 department gets a QA package that depends on all others.
    if len(packages) > 1:
        qa_dept = DEPARTMENTS["qa"]
        packages.append({
            "department": "qa",
            "title": f"{qa_dept.name}: verify {objective[:50]}",
            "description": "Cross-department verification of the objective as a whole",
            "acceptance_criteria": ["All dependent work packages pass their own tests"],
            "depends_on_titles": [p["title"] for p in packages],
        })

    return packages


def _parse_decomposition(raw: str) -> list[dict[str, Any]] | None:
    """Extract a JSON array from model output — tolerant of surrounding prose."""
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


def _validate_packages(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop packages with unknown departments; log and skip rather than fail the whole graph."""
    valid = []
    for pkg in packages:
        dept_id = str(pkg.get("department", "")).strip().lower()
        if not is_known_department(dept_id):
            log.warning("mission_planner: dropping work package with unknown department %r", dept_id)
            continue
        pkg["department"] = dept_id
        valid.append(pkg)
    return valid


def _resolve_dependencies(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert depends_on_titles -> depends_on (index-based) and detect cycles.

    Cyclical dependencies are broken by dropping the offending edge (logged),
    never by failing the whole graph — a partial, correct graph beats no graph.
    """
    title_to_index = {pkg["title"]: i for i, pkg in enumerate(packages)}
    for pkg in packages:
        resolved = []
        for dep_title in pkg.get("depends_on_titles", []) or []:
            idx = title_to_index.get(dep_title)
            if idx is not None:
                resolved.append(idx)
        pkg["_depends_on_indices"] = resolved

    # Cycle detection via DFS; drop edges that would close a cycle.
    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(i: int) -> None:
        if i in visited:
            return
        visiting.add(i)
        kept = []
        for dep_idx in packages[i]["_depends_on_indices"]:
            if dep_idx in visiting:
                log.warning(
                    "mission_planner: cycle detected (%r -> %r) — dropping edge",
                    packages[i]["title"], packages[dep_idx]["title"],
                )
                continue
            kept.append(dep_idx)
            visit(dep_idx)
        packages[i]["_depends_on_indices"] = kept
        visiting.discard(i)
        visited.add(i)

    for i in range(len(packages)):
        visit(i)

    return packages


async def decompose_objective(
    db: AsyncSession,
    objective: str,
    objective_type: str = "feature",
    *,
    context: dict[str, Any] | None = None,
) -> EngineeringTaskGraph:
    """Decompose an engineering objective into a persisted TaskGraph of WorkPackages.

    Never raises for expected failure modes (Fabric unavailable, bad model
    output) — falls back to heuristic decomposition so a graph is always
    produced. Only raises on genuine programming errors (bad db session, etc).
    """
    if objective_type not in _OBJECTIVE_TYPES:
        objective_type = "feature"

    decomposed_by = "heuristic"
    packages_raw: list[dict[str, Any]] | None = None

    try:
        router = get_fabric_router()
        response = await router.chat(
            messages=[{
                "role": "user",
                "content": _DECOMPOSITION_PROMPT.format(
                    departments=_department_list_str(),
                    objective=objective,
                    objective_type=objective_type,
                ),
            }],
            task_type="reasoning",
            expected_format="json",
            db_session=db,
        )
        if response.error:
            log.warning("mission_planner: fabric call failed (%s) — using heuristic fallback", response.error)
        else:
            packages_raw = _parse_decomposition(response.content)
            if packages_raw is not None:
                decomposed_by = f"{response.provider}/{response.model}"
    except Exception as exc:
        log.warning("mission_planner: fabric call raised (%s) — using heuristic fallback", exc)

    if not packages_raw:
        packages_raw = _heuristic_decompose(objective, objective_type)
        decomposed_by = "heuristic"

    packages_raw = _validate_packages(packages_raw)
    if not packages_raw:
        # Even validation dropped everything — guarantee at least one package.
        packages_raw = _heuristic_decompose(objective, objective_type)
        packages_raw = _validate_packages(packages_raw)
    packages_raw = _resolve_dependencies(packages_raw)

    graph = EngineeringTaskGraph(
        id=uuid.uuid4(),
        objective=objective,
        objective_type=objective_type,
        status=TaskGraphStatus.PLANNING,
        decomposed_by=decomposed_by,
        context=context or {},
    )
    db.add(graph)
    await db.flush()

    index_to_id: dict[int, uuid.UUID] = {}
    work_packages: list[EngineeringWorkPackage] = []
    for i, pkg in enumerate(packages_raw):
        dept = DEPARTMENTS[pkg["department"]]
        operation = pkg.get("operation") or dept.default_operation
        tier = lookup_tier(operation)
        wp = EngineeringWorkPackage(
            id=uuid.uuid4(),
            task_graph_id=graph.id,
            department=pkg["department"],
            title=pkg["title"],
            description=pkg.get("description", ""),
            acceptance_criteria=pkg.get("acceptance_criteria", []),
            depends_on=[],  # filled in below once all IDs are known
            operation=operation,
            authority_tier=tier.value,
            status=WorkPackageStatus.PENDING,
        )
        index_to_id[i] = wp.id
        work_packages.append(wp)

    for i, pkg in enumerate(packages_raw):
        work_packages[i].depends_on = [index_to_id[d] for d in pkg["_depends_on_indices"]]

    for wp in work_packages:
        db.add(wp)

    graph.status = TaskGraphStatus.IN_PROGRESS
    await db.flush()

    log.info(
        "mission_planner: decomposed objective into %d work packages (decomposed_by=%s)",
        len(work_packages), decomposed_by,
    )
    return graph
