"""E7-3: Department Registry — the 12 Engineering Organization departments.

Mirrors the AI Council's `_MEMBER_CATALOGUE` pattern (council/assembly.py):
departments are a static code catalogue, not a database table. Each department
owns a domain (path globs) and has a builder model tier for drafting work.

Security and Architecture default to Claude-only drafting (builder=None) —
no free-tier draft on security-sensitive or cross-cutting design code, per
docs/architecture/HEADQUARTERS_ENGINEERING_ORG.md section 3.
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Department:
    dept_id: str
    name: str
    owns: str                  # human-readable description of domain
    path_globs: tuple[str, ...]  # ownership boundary — fnmatch patterns, repo-relative
    builder: str | None        # free-tier model for drafting, or None for Claude-only
    default_operation: str     # Authority Matrix operation this department's work maps to


DEPARTMENTS: dict[str, Department] = {
    "platform": Department(
        dept_id="platform",
        name="Platform Engineering",
        owns="Kubernetes/EKS (future), networking, core infra primitives",
        path_globs=("infra/terraform/*", "infra/ssm/*", "infrastructure/docker-compose.yml"),
        builder="nim",
        default_operation="performance.improvement",
    ),
    "cloud": Department(
        dept_id="cloud",
        name="Cloud Engineering",
        owns="AWS resources, Terraform, IAM policy drafting (still ASK_CAPTAIN-gated)",
        path_globs=("infra/terraform/*", "scripts/*aws*", "scripts/*deploy*"),
        builder="gemini",
        default_operation="integration.add_external_credentials",
    ),
    "devops": Department(
        dept_id="devops",
        name="DevOps Engineering",
        owns="GitHub Actions, Docker, CI/CD pipelines",
        path_globs=(".github/workflows/*", "*/Dockerfile", "infrastructure/*"),
        builder="nim",
        default_operation="ci.fix_and_redeploy",
    ),
    "sre": Department(
        dept_id="sre",
        name="Site Reliability Engineering",
        owns="Incidents, monitoring, self-heal runbooks, uptime",
        path_globs=("monitoring/*", "infra/ssm/*heal*", "backend/app/services/kernel/health_aggregator.py"),
        builder="deepseek",
        default_operation="bug.fix",
    ),
    "backend": Department(
        dept_id="backend",
        name="Backend Engineering",
        owns="FastAPI services, business logic, API routes",
        path_globs=("backend/app/services/*", "backend/app/api/*"),
        builder="nim",
        default_operation="endpoint.add",
    ),
    "frontend": Department(
        dept_id="frontend",
        name="Frontend Engineering",
        owns="React components, UI, Zustand stores",
        path_globs=("frontend/src/*",),
        builder="nim",
        default_operation="bug.fix",
    ),
    "ai": Department(
        dept_id="ai",
        name="AI Engineering",
        owns="Fabric routing rules, model registry entries, prompt engineering",
        path_globs=("backend/app/services/fabric/*", "backend/app/services/ai/*"),
        builder="gemini",
        default_operation="model.add",
    ),
    "security": Department(
        dept_id="security",
        name="Security Engineering",
        owns="IAM review, dependency scanning, auth code paths",
        path_globs=("backend/app/services/security/*", "backend/app/core/security*"),
        builder=None,  # Claude-only — no free-tier draft on security-sensitive code
        default_operation="security.patch",
    ),
    "database": Department(
        dept_id="database",
        name="Database Engineering",
        owns="Schema design, indices, query performance",
        path_globs=("backend/alembic/*", "backend/app/models/*"),
        builder="nim",
        default_operation="db.add_column",
    ),
    "documentation": Department(
        dept_id="documentation",
        name="Documentation Team",
        owns="Architecture docs, changelogs, runbooks",
        path_globs=("docs/*", "*.md"),
        builder="nim",
        default_operation="monitoring.configure",
    ),
    "qa": Department(
        dept_id="qa",
        name="QA Automation",
        owns="Test plans, coverage, regression suites",
        path_globs=("backend/tests/*", "frontend/src/*.test.*"),
        builder="nim",
        default_operation="bug.fix",
    ),
    "architecture": Department(
        dept_id="architecture",
        name="Architecture Evolution",
        owns="Cross-department design review, ADRs",
        path_globs=("docs/architecture/*",),
        builder=None,  # Claude-only — cross-cutting design decisions
        default_operation="monitoring.configure",
    ),
}


def get_department(dept_id: str) -> Department | None:
    return DEPARTMENTS.get(dept_id)


def all_departments() -> list[Department]:
    return list(DEPARTMENTS.values())


def find_owning_departments(path: str) -> list[Department]:
    """Return every department whose ownership globs match `path` (repo-relative).

    A path can be owned by more than one department (e.g. a Dockerfile touches
    both DevOps and Platform) — callers decide how to handle multi-ownership.
    """
    matches = []
    for dept in DEPARTMENTS.values():
        for pattern in dept.path_globs:
            if fnmatch.fnmatch(path, pattern):
                matches.append(dept)
                break
    return matches


def is_known_department(dept_id: str) -> bool:
    return dept_id in DEPARTMENTS
