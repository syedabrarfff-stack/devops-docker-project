"""E7-7: Peer Review Gate — every drafted work package is reviewed before it
can move to deployment. Reuses the Engineering Council (`engineering_review`
category, C4-1..C4-4 + E7-6) rather than a second, parallel review mechanism.

Decision mapping (from CouncilRecommendation.decision, recommendation.py):
  APPROVE        -> work package APPROVED, ready for Deployment Integration (E7-8)
  CAPTAIN_REVIEW -> work package BLOCKED, same surfacing as an authority-tier block
  REJECT         -> work package REJECTED, back to the department for a fresh draft
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engineering import EngineeringWorkPackage, WorkPackageStatus
from app.services.council import get_council_session

log = logging.getLogger(__name__)

_DECISION_TO_STATUS = {
    "APPROVE": WorkPackageStatus.APPROVED,
    "CAPTAIN_REVIEW": WorkPackageStatus.BLOCKED,
    "REJECT": WorkPackageStatus.REJECTED,
}


async def review_work_package(db: AsyncSession, work_package: EngineeringWorkPackage) -> dict:
    """Run peer review on a drafted work package. Returns the recommendation dict.

    Raises ValueError if called on a work package with no draft — reviewing
    nothing is a programming error, not an expected failure mode.
    """
    if not work_package.draft_output:
        raise ValueError(f"work package {work_package.id} has no draft_output to review")

    session = get_council_session()
    outcome = await session.run(
        task_category="engineering_review",
        question=(
            f"Should we approve this {work_package.department} work package for merge?\n\n"
            f"Title: {work_package.title}\n"
            f"Acceptance criteria: {work_package.acceptance_criteria}\n"
            f"Proposed approach: {work_package.draft_output.get('approach', '')}\n"
            f"Self-test notes: {work_package.draft_output.get('_self_test_notes', '')}\n"
            f"Risks flagged by drafter: {work_package.draft_output.get('risks', [])}"
        ),
        context={
            "work_package_id": str(work_package.id),
            "department": work_package.department,
            "draft": work_package.draft_output,
        },
        session=db,
    )

    recommendation = outcome.recommendation.to_dict()
    new_status = _DECISION_TO_STATUS.get(recommendation["decision"], WorkPackageStatus.BLOCKED)

    work_package.review_result = recommendation
    work_package.status = new_status
    await db.flush()

    log.info(
        "peer_review: work package %s -> %s (decision=%s confidence=%.2f)",
        work_package.id, new_status, recommendation["decision"], recommendation["aggregate_confidence"],
    )
    return recommendation
