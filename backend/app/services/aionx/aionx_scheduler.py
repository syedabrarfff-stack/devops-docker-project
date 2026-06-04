"""AIONX Scheduler Jobs — the heartbeat that makes sovereign organs autonomous.

Implements the Sovereign Adaptive Cadence:
  Layer 1 — Continuous Sentinel sweep (every 2h)
  Layer 2 — Event-driven escalation processing (every 30m)
  Layer 5 — Hourly evolution loop, daily proposals, weekly recalibration

Register via register_aionx_jobs() called from the scheduler engine.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def register_aionx_jobs(add_cron_job, add_interval_job) -> None:
    """Wire the AIONX organs into the live scheduler."""

    # Layer 1 — Sentinel continuous world sweep (every 2 hours)
    add_interval_job("aionx_sentinel_sweep", _job_sentinel_sweep, hours=2)

    # Layer 2 — Process pending sentinel escalations into councils (every 30 min)
    add_interval_job("aionx_escalation_processor", _job_process_escalations, minutes=30)

    # Hourly evolution loop — Operational IQ recompute (every hour)
    add_interval_job("aionx_operational_iq", _job_operational_iq, hours=1)

    # Decision Memory — 30-day retrospective sync (daily 22:00 UTC)
    add_cron_job("aionx_retro_30d", _job_retrospective_30d, hour=22, minute=0)

    # Decision Memory — 90-day retrospective sync (daily 22:15 UTC)
    add_cron_job("aionx_retro_90d", _job_retrospective_90d, hour=22, minute=15)

    # Client Digital Twins — refresh churn/upsell predictions (daily 03:00 UTC)
    add_cron_job("aionx_twin_predictions", _job_refresh_twin_predictions, hour=3, minute=0)

    # Institutional Wisdom Index — weekly compute (Sunday 19:00 UTC)
    add_cron_job("aionx_wisdom_weekly", _job_weekly_wisdom, hour=19, minute=0, day_of_week="sun")

    # Decision Memory — weekly retrospective report (Sunday 19:30 UTC)
    add_cron_job("aionx_decision_retrospective", _job_weekly_decision_retro, hour=19, minute=30, day_of_week="sun")

    logger.info("✅ AIONX Sovereign Organ jobs registered (Adaptive Cadence active)")


# ─── LAYER 1 — SENTINEL SWEEP ────────────────────────────────────────────────

async def _job_sentinel_sweep() -> None:
    logger.info("AIONX Sentinel: world observation sweep")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.sentinel_layer import record_observation
        from app.services.ai.router import route_task

        async with AsyncSessionLocal() as db:
            # Use a fast model to scan for any notable AI/market signal worth escalating
            scan = await route_task(
                task_type="fast",
                prompt=(
                    "You are the AIONX Sentinel. In one line, report the single most "
                    "significant AI-industry or B2B-market signal in the last 24h that "
                    "could affect an AI operations company. Format: TITLE | STRENGTH(WEAK/MEDIUM/STRONG) | WHY"
                ),
                max_tokens=200,
            )
            if scan and scan not in ("ROUTE_TASK_UNAVAILABLE", "NO_RESPONSE"):
                parts = [p.strip() for p in scan.split("|")]
                title = parts[0] if parts else scan[:80]
                strength = parts[1].upper() if len(parts) > 1 else "WEAK"
                strength = strength if strength in ("WEAK", "MEDIUM", "STRONG") else "WEAK"
                summary = parts[2] if len(parts) > 2 else scan
                await record_observation(
                    db,
                    source="sentinel_ai_scan",
                    category="TECHNOLOGY",
                    signal_strength=strength,
                    title=title[:200],
                    summary=summary[:1000],
                )
                logger.info("AIONX Sentinel: recorded %s signal", strength)
    except Exception as exc:
        logger.warning("AIONX Sentinel sweep failed: %s", exc)


# ─── LAYER 2 — ESCALATION PROCESSOR ──────────────────────────────────────────

async def _job_process_escalations() -> None:
    logger.info("AIONX: processing sentinel escalations")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.orchestration_cortex import fire_event
        from app.services.aionx.sentinel_layer import (
            get_pending_escalations,
            mark_escalated_to_council,
        )

        async with AsyncSessionLocal() as db:
            escalations = await get_pending_escalations(db)
            for obs in escalations[:5]:
                result = await fire_event(
                    db,
                    "SENTINEL_STRONG_SIGNAL",
                    {
                        "event_type": f"SENTINEL:{obs.title}",
                        "summary": obs.summary,
                        "category": obs.category,
                        "problem": f"Sentinel detected: {obs.title}",
                    },
                )
                session_id = None
                for step in result.get("results", []):
                    if step.get("result", {}).get("provider_session_id"):
                        from uuid import UUID
                        session_id = UUID(step["result"]["provider_session_id"])
                        break
                if session_id:
                    await mark_escalated_to_council(db, obs.id, session_id)
            logger.info("AIONX: processed %d escalations", len(escalations[:5]))
    except Exception as exc:
        logger.warning("AIONX escalation processor failed: %s", exc)


# ─── HOURLY — OPERATIONAL IQ ─────────────────────────────────────────────────

async def _job_operational_iq() -> None:
    logger.info("AIONX: computing Operational IQ")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.orchestration_cortex import compute_operational_iq

        async with AsyncSessionLocal() as db:
            iq = await compute_operational_iq(db)
            logger.info("AIONX Operational IQ: %s — %s", iq["operational_iq"], iq["interpretation"])
    except Exception as exc:
        logger.warning("AIONX Operational IQ failed: %s", exc)


# ─── DECISION MEMORY — RETROSPECTIVES ────────────────────────────────────────

async def _job_retrospective_30d() -> None:
    logger.info("AIONX: 30-day decision retrospective sync")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.decision_memory_engine import retrospective_sync

        async with AsyncSessionLocal() as db:
            due = await retrospective_sync(db, days=30)
            logger.info("AIONX: %d decisions due 30-day review", len(due))
    except Exception as exc:
        logger.warning("AIONX 30d retrospective failed: %s", exc)


async def _job_retrospective_90d() -> None:
    logger.info("AIONX: 90-day decision retrospective sync")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.decision_memory_engine import retrospective_sync

        async with AsyncSessionLocal() as db:
            due = await retrospective_sync(db, days=90)
            logger.info("AIONX: %d decisions due 90-day review", len(due))
    except Exception as exc:
        logger.warning("AIONX 90d retrospective failed: %s", exc)


# ─── CLIENT DIGITAL TWINS — PREDICTION REFRESH ───────────────────────────────

async def _job_refresh_twin_predictions() -> None:
    logger.info("AIONX: refreshing Digital Twin predictions")
    try:
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.models.aionx_organs import ClientDigitalTwin
        from app.services.aionx.client_digital_twin import update_predictions
        from app.services.aionx.orchestration_cortex import fire_event

        async with AsyncSessionLocal() as db:
            twins = (await db.execute(select(ClientDigitalTwin))).scalars().all()
            churn_alerts = 0
            for twin in twins:
                preds = await update_predictions(db, twin.client_id)
                for p in preds:
                    if p.model_type == "CHURN_RISK" and p.prediction_value > 0.7:
                        churn_alerts += 1
                        await fire_event(
                            db, "CHURN_RISK_DETECTED",
                            {
                                "client_id": str(twin.client_id),
                                "event_type": "CHURN_RISK",
                                "problem": f"Churn risk {p.prediction_value:.0%} for client",
                                "category": "RISK_MITIGATION",
                            },
                        )
            logger.info("AIONX: refreshed %d twins, %d churn alerts", len(twins), churn_alerts)
    except Exception as exc:
        logger.warning("AIONX twin prediction refresh failed: %s", exc)


# ─── WEEKLY — WISDOM INDEX ───────────────────────────────────────────────────

async def _job_weekly_wisdom() -> None:
    logger.info("AIONX: computing weekly Institutional Wisdom Index")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.institutional_wisdom_index import compute_weekly_wisdom

        async with AsyncSessionLocal() as db:
            snapshot = await compute_weekly_wisdom(db)
            logger.info("AIONX Wisdom Index: %s", snapshot.narrative)
    except Exception as exc:
        logger.warning("AIONX weekly wisdom failed: %s", exc)


async def _job_weekly_decision_retro() -> None:
    logger.info("AIONX: generating weekly decision retrospective")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.decision_memory_engine import generate_weekly_retrospective

        async with AsyncSessionLocal() as db:
            retro = await generate_weekly_retrospective(db)
            logger.info(
                "AIONX Decision Retro: %d decisions, %d correct, %d incorrect",
                retro.total_decisions, retro.correct_count, retro.incorrect_count,
            )
    except Exception as exc:
        logger.warning("AIONX weekly decision retro failed: %s", exc)
