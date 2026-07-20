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

    # Intelligence Engine — Counterfactual sync (daily 01:00 UTC)
    add_cron_job("aionx_counterfactual_sync", _job_counterfactual_sync, hour=1, minute=0)

    # Intelligence Engine — Decision debt assessment (daily 02:00 UTC)
    add_cron_job("aionx_debt_assessment", _job_debt_assessment, hour=2, minute=0)

    # Intelligence Engine — Trust erosion check (daily 03:30 UTC)
    add_cron_job("aionx_trust_erosion_check", _job_trust_erosion_check, hour=3, minute=30)

    # Intelligence Engine — Authority recalibration (weekly Sunday 20:00 UTC)
    add_cron_job("aionx_authority_recalibration", _job_authority_recalibration, hour=20, minute=0, day_of_week="sun")

    # Sovereign Organism — durable state heartbeat (every 5 min)
    add_interval_job("aionx_system_state_snapshot", _job_system_state_snapshot, minutes=5)

    # Preventive Monitoring — record watchtower state (every 15 min)
    add_interval_job("aionx_preventive_monitoring_snapshot", _job_preventive_monitoring_snapshot, minutes=15)

    # Outreach Engine — execute due follow-ups (every 30 min during business hours)
    add_interval_job("aionx_execute_due_outreach", _job_execute_due_outreach, minutes=30)

    # Speed-to-Lead — check for fresh replies requiring immediate response (every 5 min)
    add_interval_job("aionx_speed_to_lead_check", _job_speed_to_lead_check, minutes=5)

    # Governed Autonomy — proposals and integrity checks, no self-execution (hourly)
    add_interval_job("aionx_governed_integrity_cycle", _job_governed_integrity_cycle, hours=1)

    # External Scan Record — governed radar placeholder until authenticated sources are configured (daily)
    add_cron_job("aionx_external_scan_record", _job_external_scan_record, hour=4, minute=15)

    # Supreme Council — weekly meta-learning calibration loop
    add_cron_job("aionx_supreme_meta_learning", _job_supreme_meta_learning, hour=21, minute=0, day_of_week="sun")

    # Frontier Intelligence — advanced governed operating systems
    add_cron_job("aionx_founder_mirror_analysis", _job_founder_mirror_analysis, hour=1, minute=0)
    add_cron_job("aionx_parallel_universe_analysis", _job_parallel_universe_analysis, hour=8, minute=0, day_of_week="mon")
    add_cron_job("aionx_service_innovation_scan", _job_service_innovation_scan, hour=10, minute=0, day_of_week="sun")
    add_interval_job("aionx_predictive_threat_scan", _job_predictive_threat_scan, hours=2)
    add_interval_job("aionx_agent_capacity_check", _job_agent_capacity_check, hours=4)
    add_interval_job("aionx_idle_intelligence_cycle", _job_idle_intelligence_cycle, hours=6)
    add_interval_job("aionx_mission_control_snapshot", _job_mission_control_snapshot, minutes=10)

    logger.info("AIONX Sovereign Organ jobs registered (Adaptive Cadence active)")


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
        from app.services.aionx.operational_persistence import record_event

        async with AsyncSessionLocal() as db:
            async with db.begin():
                iq = await compute_operational_iq(db)
                await record_event(
                    db,
                    event_type="OPERATIONAL_IQ_SNAPSHOT",
                    source="aionx_operational_iq",
                    payload=iq,
                    severity="INFO",
                )
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

        from app.core.config import settings as _settings
        from app.core.database import AsyncSessionLocal
        from app.models.aionx_organs import ClientDigitalTwin
        from app.services.aionx.client_digital_twin import update_predictions
        from app.services.aionx.orchestration_cortex import fire_event

        async with AsyncSessionLocal() as db:
            _q = select(ClientDigitalTwin).limit(500)
            if _settings.JARVIS_DEFAULT_TENANT_ID:
                import uuid as _uuid
                _q = _q.where(ClientDigitalTwin.tenant_id == _uuid.UUID(str(_settings.JARVIS_DEFAULT_TENANT_ID)))
            twins = (await db.execute(_q)).scalars().all()
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


# ─── INTELLIGENCE ENGINES ────────────────────────────────────────────────────

async def _job_counterfactual_sync() -> None:
    logger.info("AIONX: counterfactual sync — simulate mature decisions")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.counterfactual_engine import extract_learning
        from sqlalchemy import select
        from app.models.aionx_organs import DecisionObject
        from datetime import timedelta

        async with AsyncSessionLocal() as db:
            # Simulate decisions older than 30 days
            thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30))
            mature_decisions = (await db.execute(
                select(DecisionObject).where(DecisionObject.created_at <= thirty_days_ago).limit(500)
            )).scalars().all()

            learning = await extract_learning(db)
            logger.info("AIONX Counterfactual: %d decisions reviewed, %.0f%% success",
                       learning["decisions_reviewed"], learning["success_rate"] * 100)
    except Exception as exc:
        logger.warning("AIONX counterfactual sync failed: %s", exc)


async def _job_debt_assessment() -> None:
    logger.info("AIONX: institutional debt assessment")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.decision_debt_engine import assess_institutional_debt

        async with AsyncSessionLocal() as db:
            debt_index = await assess_institutional_debt(db)
            logger.info("AIONX Debt: $%.2f institutional, %d high-debt decisions, penalty %.1f pts",
                       debt_index["total_institutional_debt_usd"],
                       debt_index["high_debt_decision_count"],
                       debt_index["wisdom_index_penalty_points"])
    except Exception as exc:
        logger.warning("AIONX debt assessment failed: %s", exc)


async def _job_trust_erosion_check() -> None:
    logger.info("AIONX: client trust erosion detection")
    try:
        from app.core.config import settings as _settings
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.client_trust_index import escalate_trust_erosion
        from sqlalchemy import select
        from app.models.aionx_organs import ClientDigitalTwin

        from app.services.aionx.operational_persistence import record_event

        async with AsyncSessionLocal() as db:
            _q = select(ClientDigitalTwin).limit(500)
            if _settings.JARVIS_DEFAULT_TENANT_ID:
                import uuid as _uuid
                _q = _q.where(ClientDigitalTwin.tenant_id == _uuid.UUID(str(_settings.JARVIS_DEFAULT_TENANT_ID)))
            twins = (await db.execute(_q)).scalars().all()

            erosions = []
            async with db.begin():
                for twin in twins:
                    result = await escalate_trust_erosion(db, twin.client_id)
                    if result.get("escalated"):
                        erosions.append(result)
                        await record_event(
                            db,
                            event_type="CLIENT_TRUST_EROSION",
                            source="aionx_trust_erosion_check",
                            payload=result,
                            severity="WARNING",
                            captain_approval_required=True,
                        )

            logger.info("AIONX Trust: checked %d clients, %d erosion alerts", len(twins), len(erosions))

            if erosions:
                try:
                    from app.services.notifications.telegram import notify_telegram
                    lines = ["⚠️ *Client Trust Erosion Detected*\n"]
                    for e in erosions:
                        lines.append(
                            f"  • Client `{e['client_id']}`: {e['previous_score']} → "
                            f"{e['current_score']} ({e['score_change_30d']:+.1f} pts / 30d)"
                        )
                    lines.append("\nReview via Client Trust in the dashboard.")
                    await notify_telegram("\n".join(lines))
                except Exception as exc:
                    logger.warning("Trust erosion Telegram alert failed: %s", exc)
    except Exception as exc:
        logger.warning("AIONX trust erosion check failed: %s", exc)


async def _job_authority_recalibration() -> None:
    logger.info("AIONX: decision maker authority recalibration")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.executive_accountability_engine import compute_authority_decay
        from sqlalchemy import select, distinct
        from app.models.aionx_organs import DecisionObject

        async with AsyncSessionLocal() as db:
            # Get all unique decision makers
            makers = (await db.execute(
                select(distinct(DecisionObject.executor_role)).limit(200)
            )).scalars().all()

            decayed = 0
            for maker in makers:
                if maker:
                    result = await compute_authority_decay(db, maker)
                    if result.get("authority_decay", 0) > 0:
                        decayed += 1
                        logger.info("AIONX Accountability: %s authority decay %.1f pts",
                                   maker, result["authority_decay"])

            logger.info("AIONX Accountability: recalibrated %d makers, %d with decay", len(makers), decayed)
    except Exception as exc:
        logger.warning("AIONX authority recalibration failed: %s", exc)


async def _job_system_state_snapshot() -> None:
    logger.info("AIONX: capturing durable System State snapshot")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.operational_persistence import capture_system_state_snapshot

        async with AsyncSessionLocal() as db:
            await capture_system_state_snapshot(db, captured_by="AIONX_STATE_HEARTBEAT")
    except Exception as exc:
        logger.warning("AIONX system state snapshot failed: %s", exc)


async def _job_preventive_monitoring_snapshot() -> None:
    logger.info("AIONX: capturing preventive monitoring snapshot")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.operational_persistence import capture_preventive_monitoring_snapshot

        async with AsyncSessionLocal() as db:
            await capture_preventive_monitoring_snapshot(db)
    except Exception as exc:
        logger.warning("AIONX preventive monitoring snapshot failed: %s", exc)


async def _job_governed_integrity_cycle() -> None:
    logger.info("AIONX: running governed integrity cycle")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.operational_persistence import run_governed_integrity_cycle

        async with AsyncSessionLocal() as db:
            result = await run_governed_integrity_cycle(db)
            logger.info(
                "AIONX governed integrity: health=%s proposal=%s",
                result.get("state_health"),
                result.get("proposal_created"),
            )
    except Exception as exc:
        logger.warning("AIONX governed integrity cycle failed: %s", exc)


async def _job_external_scan_record() -> None:
    logger.info("AIONX: recording governed external radar scan")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.operational_persistence import record_external_scan

        async with AsyncSessionLocal() as db:
            await record_external_scan(
                db,
                {
                    "scan_type": "TECH_RADAR",
                    "source": "AIONX_SENTINEL_SCHEDULED",
                    "summary": "Scheduled governed radar pulse recorded. Attach authenticated sources for live crawling.",
                    "findings": [
                        "No autonomous external action executed.",
                        "Radar pulse is persisted for Captain/Council review.",
                    ],
                    "recommended_actions": [
                        "Configure approved web/API sources for production crawling.",
                        "Route strong findings to Provider Sovereign Council before execution.",
                    ],
                },
            )
    except Exception as exc:
        logger.warning("AIONX external scan record failed: %s", exc)


async def _job_supreme_meta_learning() -> None:
    logger.info("AIONX: running Supreme Council meta-learning cycle")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.supreme_council_layer import run_meta_learning_cycle

        async with AsyncSessionLocal() as db:
            result = await run_meta_learning_cycle(db)
            logger.info("AIONX Supreme Council meta-learning recorded: %s", result.get("status"))
    except Exception as exc:
        logger.warning("AIONX Supreme Council meta-learning failed: %s", exc)


async def _job_founder_mirror_analysis() -> None:
    logger.info("AIONX Frontier: Founder Mirror pattern analysis")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.frontier_intelligence import captain_mirror_profile

        async with AsyncSessionLocal() as db:
            profile = await captain_mirror_profile(db)
            logger.info("AIONX Founder Mirror: %s decisions recorded", profile.get("decisions_recorded"))
    except Exception as exc:
        logger.warning("AIONX Founder Mirror analysis failed: %s", exc)


async def _job_parallel_universe_analysis() -> None:
    logger.info("AIONX Frontier: Parallel Universe experiment analysis")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.frontier_intelligence import list_experiments

        async with AsyncSessionLocal() as db:
            experiments = await list_experiments(db)
            logger.info("AIONX Parallel Universe: %s experiments tracked", len(experiments.get("experiments", [])))
    except Exception as exc:
        logger.warning("AIONX Parallel Universe analysis failed: %s", exc)


async def _job_service_innovation_scan() -> None:
    logger.info("AIONX Frontier: service innovation scan")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.frontier_intelligence import generate_service_concept

        async with AsyncSessionLocal() as db:
            concept = await generate_service_concept(
                db,
                {
                    "signals": [
                        "Scheduled market scan found demand for AI operations pilots.",
                        "Pilot-first packaging reduces commitment fear.",
                    ],
                    "industry": "founder-led operations",
                },
            )
            logger.info("AIONX Service Innovation: concept %s ready for Captain review", concept.get("concept_id"))
    except Exception as exc:
        logger.warning("AIONX service innovation scan failed: %s", exc)


async def _job_predictive_threat_scan() -> None:
    logger.info("AIONX Frontier: predictive threat scan")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.frontier_intelligence import scan_threats

        async with AsyncSessionLocal() as db:
            result = await scan_threats(db, {"signals": {}})
            logger.info("AIONX Threat Scan: %s alerts created", result.get("alerts_created"))
    except Exception as exc:
        logger.warning("AIONX predictive threat scan failed: %s", exc)


async def _job_agent_capacity_check() -> None:
    logger.info("AIONX Frontier: agent capacity check")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.frontier_intelligence import agent_capacity

        async with AsyncSessionLocal() as db:
            result = await agent_capacity(db)
            logger.info("AIONX Agent Scaling: %s proposals", len(result.get("agent_proposals", [])))
    except Exception as exc:
        logger.warning("AIONX agent capacity check failed: %s", exc)


async def _job_idle_intelligence_cycle() -> None:
    logger.info("AIONX Frontier: idle intelligence cycle")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.frontier_intelligence import create_knowledge_artifact

        async with AsyncSessionLocal() as db:
            artifact = await create_knowledge_artifact(
                db,
                {
                    "artifact_type": "idle_intelligence",
                    "content": (
                        "Idle cycle doctrine: when no mission is active, generate leads, "
                        "service concepts, proposal angles, and risk scans for Captain review."
                    ),
                    "tags": ["idle_engine", "dream_layer", "captain_review"],
                    "importance_score": 0.8,
                },
            )
            logger.info("AIONX Idle Intelligence: artifact %s recorded", artifact.get("artifact_id"))
    except Exception as exc:
        logger.warning("AIONX idle intelligence cycle failed: %s", exc)


async def _job_mission_control_snapshot() -> None:
    logger.info("AIONX Omni: capturing Mission Control HUD snapshot")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.aionx.omni_mission_control import seed_omni_registry, system_hud

        async with AsyncSessionLocal() as db:
            await seed_omni_registry(db)
            snapshot = await system_hud(db, persist=True)
            logger.info(
                "AIONX Mission Control: jobs=%s systems=%s",
                snapshot.get("scheduler", {}).get("aionx_jobs"),
                snapshot.get("registry", {}).get("total"),
            )
    except Exception as exc:
        logger.warning("AIONX Mission Control snapshot failed: %s", exc)


# ─── OUTREACH ENGINE — DUE FOLLOW-UP EXECUTION ───────────────────────────────

async def _job_execute_due_outreach() -> None:
    """Execute all follow-ups due now — fires up to daily cap emails per run."""
    from app.core.config import settings

    if settings.OUTREACH_PAUSED:
        return

    tenant_id = None
    if settings.JARVIS_DEFAULT_TENANT_ID:
        try:
            import uuid
            tenant_id = uuid.UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
        except Exception as exc:
            logger.warning("AIONX outreach: invalid JARVIS_DEFAULT_TENANT_ID: %s", exc)

    if not tenant_id:
        logger.debug("AIONX outreach: no default tenant configured — skipping")
        return

    logger.info("AIONX outreach: executing due follow-ups for tenant %s", tenant_id)
    try:
        from app.services.outreach.engine import outreach_engine
        sent = await outreach_engine.execute_due_outreach(
            tenant_id,
            limit=int(settings.OUTREACH_DAILY_SEND_CAP or 48),
            autonomy_stage="outreach_emails",
        )
        if sent:
            logger.info("AIONX outreach: sent %d emails", sent)
    except Exception as exc:
        logger.warning("AIONX outreach execution failed: %s", exc)


# ─── SPEED-TO-LEAD — FRESH REPLY MONITORING ──────────────────────────────────

async def _job_speed_to_lead_check() -> None:
    """Check for speed-to-lead events requiring immediate Captain attention."""
    import uuid as _uuid
    from app.core.config import settings

    tenant_id = None
    if settings.JARVIS_DEFAULT_TENANT_ID:
        try:
            tenant_id = _uuid.UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
        except Exception as exc:
            logger.warning("AIONX speed-to-lead: invalid JARVIS_DEFAULT_TENANT_ID: %s", exc)
    if not tenant_id:
        return

    try:
        from datetime import UTC, datetime, timedelta
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.revenue_activation import SpeedToLeadEvent
        from app.services.notifications import notify_business_event

        cutoff = datetime.now(UTC) - timedelta(minutes=10)
        async with AsyncSessionLocal() as db:
            fresh = (await db.execute(
                select(SpeedToLeadEvent).where(
                    SpeedToLeadEvent.tenant_id == tenant_id,
                    SpeedToLeadEvent.action_taken == "QUEUED",
                    SpeedToLeadEvent.created_at >= cutoff,
                ).limit(5)
            )).scalars().all()

            if fresh:
                logger.info("AIONX speed-to-lead: %d fresh events require Captain attention", len(fresh))
                await notify_business_event(
                    "speed_to_lead_alert",
                    f"Speed-to-Lead: {len(fresh)} prospect(s) need immediate follow-up",
                    f"{len(fresh)} prospect(s) replied and are awaiting response. "
                    f"Open the War Room to review and respond.",
                )
                # Mark as notified
                for event in fresh:
                    event.action_taken = "CAPTAIN_NOTIFIED"
                await db.commit()
    except Exception as exc:
        logger.warning("AIONX speed-to-lead check failed: %s", exc)
