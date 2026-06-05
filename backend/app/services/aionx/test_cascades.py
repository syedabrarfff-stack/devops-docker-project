"""AIONX cascade integration tests.

These tests require a real configured database, so pytest skips them unless
RUN_AIONX_INTEGRATION_TESTS=1 is set. They can still be run directly as a script.
"""
from __future__ import annotations

import asyncio
import logging
import os
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.aionx_organs import ClientDigitalTwin, DecisionObject, MissionOwnershipRecord
from app.services.aionx.orchestration_cortex import fire_event

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_AIONX_INTEGRATION_TESTS") != "1",
    reason="AIONX cascade tests require a configured integration database",
)


def test_cascade_client_signed() -> None:
    asyncio.run(_cascade_client_signed())


def test_cascade_mission_failed() -> None:
    asyncio.run(_cascade_mission_failed())


def test_cascade_churn_risk() -> None:
    asyncio.run(_cascade_churn_risk())


def test_cascade_lead_replied() -> None:
    asyncio.run(_cascade_lead_replied())


def test_all_cascades() -> None:
    asyncio.run(_all_cascades())


async def _cascade_client_signed() -> None:
    """STEP 12: CLIENT_SIGNED cascade - verify all 5 steps execute."""
    async with AsyncSessionLocal() as db:
        client_id = uuid4()
        mission_id = uuid4()
        payload = {
            "client_id": str(client_id),
            "mission_id": str(mission_id),
            "event_type": "CLIENT_SIGNED",
            "stage_name": "Deal signed and activated",
            "category": "OPPORTUNITY",
        }

        result = await fire_event(db, "CLIENT_SIGNED", payload)
        step_results = {item["step"]: item["status"] for item in result.get("results", [])}

        assert step_results.get("create_digital_twin") == "ok"
        assert step_results.get("create_decision_object") == "ok"
        assert step_results.get("open_delivery_council") == "ok"
        assert step_results.get("record_ownership") == "ok"
        assert step_results.get("notify_captain") == "ok"

        twin = (await db.execute(
            select(ClientDigitalTwin).where(ClientDigitalTwin.client_id == client_id)
        )).scalars().first()
        assert twin is not None

        decision = (await db.execute(
            select(DecisionObject).where(DecisionObject.client_id == client_id)
        )).scalars().first()
        assert decision is not None

        ownership = (await db.execute(
            select(MissionOwnershipRecord).where(MissionOwnershipRecord.mission_id == mission_id)
        )).scalars().first()
        assert ownership is not None


async def _cascade_mission_failed() -> None:
    """STEP 13: MISSION_FAILED cascade - verify autopsy, councils, decision, notify."""
    async with AsyncSessionLocal() as db:
        mission_id = uuid4()
        payload = {
            "mission_id": str(mission_id),
            "event_type": "MISSION_FAILED",
            "problem": "Delivery exceeded timeline and budget",
            "failure_type": "SCHEDULE_OVERRUN",
        }

        result = await fire_event(db, "MISSION_FAILED", payload)
        step_results = {item["step"]: item["status"] for item in result.get("results", [])}

        assert step_results.get("create_autopsy") == "ok"
        assert step_results.get("open_convergence_council") == "ok"
        assert step_results.get("convene_provider_council") == "ok"
        assert step_results.get("create_decision_object") == "ok"
        assert step_results.get("notify_captain") == "ok"


async def _cascade_churn_risk() -> None:
    """STEP 14: CHURN_RISK_DETECTED cascade - verify twin update, council, decision, notify."""
    async with AsyncSessionLocal() as db:
        client_id = uuid4()
        payload = {
            "client_id": str(client_id),
            "event_type": "CHURN_RISK_DETECTED",
            "problem": "Client engagement dropped 35 percent in 14 days",
            "category": "RISK_MITIGATION",
        }

        result = await fire_event(db, "CHURN_RISK_DETECTED", payload)
        step_results = {item["step"]: item["status"] for item in result.get("results", [])}

        assert step_results.get("update_twin_profile") == "ok"
        assert step_results.get("open_convergence_council") == "ok"
        assert step_results.get("create_decision_object") == "ok"
        assert step_results.get("notify_captain") == "ok"


async def _cascade_lead_replied() -> None:
    """STEP 15: LEAD_REPLIED cascade - verify interaction, decision, speed-to-lead."""
    async with AsyncSessionLocal() as db:
        client_id = uuid4()
        payload = {
            "client_id": str(client_id),
            "event_type": "LEAD_REPLIED",
            "event_id": str(uuid4()),
            "interaction_type": "EMAIL_REPLY",
            "sentiment": "positive",
            "problem": "Lead replied to outreach - qualify and respond fast",
        }

        result = await fire_event(db, "LEAD_REPLIED", payload)
        step_results = {item["step"]: item["status"] for item in result.get("results", [])}

        assert step_results.get("create_decision_object") == "ok"
        assert step_results.get("update_twin_interaction") == "ok"
        assert step_results.get("speed_to_lead_queue") == "ok"


async def _all_cascades() -> None:
    logger.info("STEPS 12-15: CASCADE INTEGRATION TESTS")
    await _cascade_client_signed()
    await _cascade_mission_failed()
    await _cascade_churn_risk()
    await _cascade_lead_replied()
    logger.info("ALL CASCADES OPERATIONAL")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(_all_cascades())
