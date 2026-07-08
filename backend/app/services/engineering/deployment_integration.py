"""E7-8: Deployment Pipeline Integration — wires APPROVED work packages into
the EXISTING pipeline (PR -> CI/CD -> deploy.py). No new deploy mechanism.

Honest scope boundary: this codebase has no existing capability for a backend
service to autonomously write files, commit, and open a GitHub PR — every
Task Book task today gets integrated by a human/Claude session doing that by
hand (see JARVIS_V4_TASKBOOK.md Merge Protocol step 5: "Claude integrates
into the real path, commits"). Building an autonomous git/PR-writing capability
from scratch is a separate, larger undertaking, not something to bolt on here
without its own review. So:

  - For the narrow set of already-safe, already-built deploy ACTIONS (status
    checks, non-mutating verification) this module calls the existing HQ-7
    `run_deploy()` directly — the full pipeline genuinely executes end-to-end.
  - For general code-writing work packages (the common case), this module
    emits the observability event and returns a structured, PR-ready summary
    (title/body/diff) for a human or Claude session to integrate through the
    same git workflow already used for everything else in this repo. It does
    NOT fabricate PR creation that doesn't actually exist.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engineering import EngineeringWorkPackage, WorkPackageStatus
from app.services.kernel.event_bus import get_event_bus

log = logging.getLogger(__name__)

# Work packages with these operations can safely trigger the existing,
# already-Authority-Matrix-gated deploy verification path directly — they are
# read-only status checks, not code mutations.
_SAFE_AUTO_DEPLOY_ACTIONS = {"ci.fix_and_redeploy": "verify-status"}


def build_pr_summary(work_package: EngineeringWorkPackage) -> dict:
    """Format an APPROVED work package as a PR-ready summary for a human/Claude
    session to actually commit and push — matching the existing Merge Protocol."""
    draft = work_package.draft_output or {}
    return {
        "suggested_branch": f"engineering/{work_package.department}/{work_package.id}",
        "suggested_title": f"feat({work_package.department}): {work_package.title}",
        "body": (
            f"## Summary\n{draft.get('summary', '')}\n\n"
            f"## Approach\n{draft.get('approach', '')}\n\n"
            f"## Acceptance criteria\n"
            + "\n".join(f"- {c}" for c in (work_package.acceptance_criteria or []))
            + f"\n\n## Peer review\n{(work_package.review_result or {}).get('unified_reasoning', 'n/a')}\n"
        ),
        "code_snippet": draft.get("code_snippet", ""),
        "department": work_package.department,
        "work_package_id": str(work_package.id),
    }


async def integrate_work_package(db: AsyncSession, work_package: EngineeringWorkPackage) -> dict:
    """Integrate one APPROVED work package. Returns a result dict describing
    what actually happened — never claims a deploy or PR occurred that didn't.
    """
    if work_package.status != WorkPackageStatus.APPROVED:
        raise ValueError(
            f"work package {work_package.id} is {work_package.status}, not APPROVED — cannot integrate"
        )

    bus = get_event_bus()
    await bus.emit(
        "engineering.work_package.approved",
        payload={
            "work_package_id": str(work_package.id),
            "task_graph_id": str(work_package.task_graph_id),
            "department": work_package.department,
            "operation": work_package.operation,
        },
        source_engine="engineering.deployment_integration",
    )

    safe_action = _SAFE_AUTO_DEPLOY_ACTIONS.get(work_package.operation)
    if safe_action:
        from app.services.headquarters.deploy import run_deploy
        deploy_result = await run_deploy(safe_action)
        work_package.deploy_result = deploy_result
        work_package.status = WorkPackageStatus.DEPLOYED if deploy_result.get("ok") else WorkPackageStatus.BLOCKED
        await db.flush()
        log.info(
            "deployment_integration: work package %s auto-deployed via %s (ok=%s)",
            work_package.id, safe_action, deploy_result.get("ok"),
        )
        return {"mode": "auto_deploy", "action": safe_action, "result": deploy_result}

    summary = build_pr_summary(work_package)
    work_package.deploy_result = {"mode": "pending_manual_integration", "pr_summary": summary}
    await db.flush()
    log.info(
        "deployment_integration: work package %s ready for manual/Claude integration (department=%s)",
        work_package.id, work_package.department,
    )
    return {"mode": "pending_manual_integration", "pr_summary": summary}
