"""AIONX intelligence engine integration smoke tests.

These checks require a configured database and may create real organ records, so
pytest skips them unless RUN_AIONX_INTEGRATION_TESTS=1 is set. The file still
protects normal test collection by importing every engine module.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid

import pytest

from app.core.database import AsyncSessionLocal
from app.models.aionx_organs import DecisionObject, MissionOwnershipRecord
from app.services.aionx.client_trust_index import recovery_protocol
from app.services.aionx.counterfactual_engine import extract_learning, record_actuality, simulate_decision
from app.services.aionx.decision_debt_engine import assess_institutional_debt, compute_decision_debt
from app.services.aionx.executive_accountability_engine import track_maker_accuracy
from app.services.aionx.institutional_wisdom_index import compute_weekly_wisdom
from app.services.aionx.mission_autopsy_engine import analyze_mission_failure

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_AIONX_INTEGRATION_TESTS") != "1",
    reason="AIONX intelligence tests require a configured integration database",
)


def test_intelligence_engine_smoke() -> None:
    asyncio.run(_intelligence_engine_smoke())


async def _intelligence_engine_smoke() -> None:
    async with AsyncSessionLocal() as db:
        maker_id = "AIONX_INTEGRATION_SMOKE"
        decision = DecisionObject(
            trigger_event="AIONX_INTEGRATION_SMOKE",
            problem_statement="Verify intelligence engines execute against live schema",
            tier=2,
            decision_category="TEST",
            executor_role=maker_id,
            confidence_score=0.8,
        )
        db.add(decision)
        await db.flush()

        simulation = await simulate_decision(db, decision.id)
        assert simulation.get("decision_id") == str(decision.id)

        actuality = await record_actuality(
            db,
            decision.id,
            "Positive outcome - target achieved",
            actual_revenue_delta=5000.0,
            actual_timeline_delta_days=-2,
        )
        assert actuality.get("decision_id") == str(decision.id)

        learning = await extract_learning(db)
        assert "decisions_reviewed" in learning

        debt = await compute_decision_debt(
            db,
            decision.id,
            lost_revenue_usd=10000.0,
            remediation_effort_hours=20,
            opportunity_cost_usd=5000.0,
        )
        assert debt.get("decision_id") == str(decision.id)

        institutional_debt = await assess_institutional_debt(db)
        assert "total_institutional_debt_usd" in institutional_debt

        mission_id = uuid.uuid4()
        ownership = MissionOwnershipRecord(
            mission_id=mission_id,
            client_id=uuid.uuid4(),
            mission_status="ACTIVE",
        )
        db.add(ownership)
        await db.flush()

        autopsy = await analyze_mission_failure(
            db,
            mission_id,
            failure_type="SCHEDULE_OVERRUN",
            failure_summary="Smoke mission exceeded expected delivery window",
        )
        assert autopsy.get("mission_id") == str(mission_id)

        accuracy = await track_maker_accuracy(db, maker_id)
        assert accuracy.get("maker_id") == maker_id

        actions = await recovery_protocol(db, ownership.client_id)
        assert isinstance(actions, list)

        wisdom = await compute_weekly_wisdom(db)
        assert 0 <= wisdom.wisdom_score <= 1000

        await db.commit()
        logger.info("AIONX intelligence smoke completed for decision %s", decision.id)


async def run_all_engine_tests() -> dict:
    """Manual script entrypoint used by operational runbooks."""
    try:
        await _intelligence_engine_smoke()
        return {"passed": 1, "total": 1, "results": {"smoke": "passed"}}
    except Exception as exc:
        logger.exception("AIONX intelligence smoke failed")
        return {"passed": 0, "total": 1, "results": {"smoke": {"error": str(exc)}}}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print(asyncio.run(run_all_engine_tests()))
