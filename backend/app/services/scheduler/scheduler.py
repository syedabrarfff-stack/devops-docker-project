from __future__ import annotations

import logging
import os
import pickle
import shlex
import traceback as traceback_lib
import uuid
import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse, unquote

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.util import datetime_to_utc_timestamp
from sqlalchemy import Column, Float, inspect, text, func, select
from sqlalchemy import UUID as SUUID
from sqlalchemy.exc import IntegrityError

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_scheduler: AsyncIOScheduler | None = None

DAILY_DISCOVERY_TARGETS = [
    # ── Sales & Revenue Division ──────────────────────────────────────────────
    {"query": "AI lead generation software SaaS", "industry": "SaaS", "country": "UK", "location": "London UK", "limit": 8},
    {"query": "cold email outreach automation agency", "industry": "Agency", "country": "UAE", "location": "Dubai UAE", "limit": 8},
    {"query": "sales automation CRM ecommerce", "industry": "E-commerce", "country": "USA", "location": "New York USA", "limit": 8},
    {"query": "CRM architecture recruitment staffing", "industry": "Recruitment", "country": "Australia", "location": "Sydney Australia", "limit": 8},
    # ── AI Automation Division ────────────────────────────────────────────────
    {"query": "appointment scheduling automation clinic", "industry": "Healthcare", "country": "Canada", "location": "Toronto Canada", "limit": 8},
    {"query": "AI voice receptionist hospitality hotel", "industry": "Hospitality", "country": "Bahrain", "location": "Manama Bahrain", "limit": 8},
    {"query": "workflow automation SaaS operations", "industry": "SaaS", "country": "UK", "location": "Manchester UK", "limit": 8},
    {"query": "executive assistant automation fintech", "industry": "Fintech", "country": "UAE", "location": "Abu Dhabi UAE", "limit": 8},
    # ── Cloud & DevOps Division ───────────────────────────────────────────────
    {"query": "AWS cloud architecture startup scaling", "industry": "Technology", "country": "USA", "location": "Austin TX", "limit": 8},
    {"query": "Docker DevOps containerization startup", "industry": "Technology", "country": "Australia", "location": "Melbourne Australia", "limit": 8},
    {"query": "CI CD pipeline DevOps SaaS", "industry": "SaaS", "country": "Canada", "location": "Vancouver Canada", "limit": 8},
    {"query": "Terraform infrastructure as code cloud", "industry": "Technology", "country": "Bahrain", "location": "Manama Bahrain", "limit": 8},
    {"query": "Kubernetes container orchestration cloud", "industry": "Technology", "country": "UK", "location": "Edinburgh UK", "limit": 8},
    {"query": "cloud monitoring observability SaaS", "industry": "E-commerce", "country": "UAE", "location": "Dubai UAE", "limit": 8},
    # ── Security Division ─────────────────────────────────────────────────────
    {"query": "cybersecurity operations fintech finance", "industry": "Finance", "country": "USA", "location": "San Francisco USA", "limit": 8},
    {"query": "vulnerability assessment healthcare clinic", "industry": "Healthcare", "country": "Australia", "location": "Brisbane Australia", "limit": 8},
    {"query": "compliance hardening legal professional services", "industry": "Legal", "country": "Canada", "location": "Montreal Canada", "limit": 8},
    # ── Content & Media Division ──────────────────────────────────────────────
    {"query": "content automation marketing agency", "industry": "Agency", "country": "Bahrain", "location": "Manama Bahrain", "limit": 8},
    {"query": "YouTube operations media brand agency", "industry": "Media", "country": "UK", "location": "London UK", "limit": 8},
    {"query": "social media AI automation restaurant hospitality", "industry": "Hospitality", "country": "UAE", "location": "Dubai UAE", "limit": 8},
    # ── Digital Products Division ─────────────────────────────────────────────
    {"query": "web application development hotel hospitality", "industry": "Hospitality", "country": "USA", "location": "Miami USA", "limit": 8},
    {"query": "client portal SaaS professional services", "industry": "SaaS", "country": "Australia", "location": "Perth Australia", "limit": 8},
    {"query": "operational dashboard analytics operations", "industry": "Logistics", "country": "Canada", "location": "Calgary Canada", "limit": 8},
    # ── Intelligence Division ─────────────────────────────────────────────────
    {"query": "AI research operations consulting firm", "industry": "Consulting", "country": "Bahrain", "location": "Manama Bahrain", "limit": 8},
    {"query": "business intelligence analytics startup SaaS", "industry": "Technology", "country": "UK", "location": "Birmingham UK", "limit": 8},
]

RESEARCH_TOPICS = [
    "AI automation market",
    "SMB technology adoption",
    "competitor pricing changes",
]

DEPRECATED_JOB_IDS = (
    "daily_briefing",
    "lead_scoring_sweep",
    "daily_icp_lead_scoring",
    "outreach_processor",
    "contact_sync",
    "tech_radar_scan",
    "market_intelligence_report",
    "competitor_monitoring",
    "morning_briefing",
    "biweekly_research_report_old",
    "weekly_tech_radar_scan",
    "daily_self_learning",
    "memory_consolidation",
    "weekly_memory_promotion",
    "reply_handler_scan",
    "overnight_lead_discovery",
    "overnight_intel_analysis",
    "overnight_proposal_engine",
    "overnight_cold_outreach",
    "overnight_freelance_bids",
    "overnight_followup_sequences",
    "overnight_pipeline_health",
    "overnight_ops_report",
)

PRODUCTION_JOB_IDS = (
    "daily_morning_briefing",
    "daily_lead_scoring",
    "daily_lead_discovery",
    "daily_follow_up_check",
    "daily_outreach_safety_review",
    "daily_memory_consolidate",
    "daily_optimization_review",
    "weekly_outreach_stats",
    "weekly_pipeline_health",
    "weekly_tech_radar",
    "weekly_innovation_review",
    "biweekly_research_report",
    "monthly_weight_adjust",
    "daily_db_backup",
    "speed_to_lead_5min",
    "daily_free_lead_discovery",
    "weekly_market_scan",
    "daily_connector_hub_ingestion",
    "daily_market_intelligence",
    "self_healer",
    "daily_opportunity_radar",
    "daily_truth_reality_check",
    "weekly_financial_health",
    "weekly_founder_dependency",
    "weekly_moat_scan",
    "weekly_cashflow_forecast",
    "weekly_learning_optimization",
    "weekly_competitor_monitoring",
    "routing_optimizer_sweep",
    "linkedin_outreach_sweep",
    "voice_analytics_daily",
    "captain_dashboard_briefing",
    "weekly_performance_briefing",
    "daily_self_learning",
    "drift_auditor",
    "daily_strategy_report",
    "weekly_strategy_review",
    "milestone_bulk_review",
    "dio_health_check",
    "tech_evolution_scan",
    "daily_scout_network",
    "lead_embedding_sweep",
    "pre_call_briefing_trigger",
    "nexus_heartbeat",
    "nightly_signal_scan",
    "engineering_org_cycle",
)

AIONX_JOB_IDS = (
    "aionx_sentinel_sweep",
    "aionx_escalation_processor",
    "aionx_operational_iq",
    "aionx_retro_30d",
    "aionx_retro_90d",
    "aionx_twin_predictions",
    "aionx_wisdom_weekly",
    "aionx_decision_retrospective",
    "aionx_counterfactual_sync",
    "aionx_debt_assessment",
    "aionx_trust_erosion_check",
    "aionx_authority_recalibration",
    "aionx_system_state_snapshot",
    "aionx_preventive_monitoring_snapshot",
    "aionx_governed_integrity_cycle",
    "aionx_external_scan_record",
    "aionx_supreme_meta_learning",
    "aionx_founder_mirror_analysis",
    "aionx_parallel_universe_analysis",
    "aionx_service_innovation_scan",
    "aionx_predictive_threat_scan",
    "aionx_agent_capacity_check",
    "aionx_idle_intelligence_cycle",
    "aionx_mission_control_snapshot",
    "aionx_execute_due_outreach",
    "aionx_speed_to_lead_check",
)

JOB_LOCK_TTLS = {
    "speed_to_lead_5min": 240,
    "daily_free_lead_discovery": 1800,
    "weekly_market_scan": 2400,
    "daily_db_backup": 2400,
    "daily_outreach_safety_review": 900,
    "linkedin_outreach_sweep": 3600,
}


class TenantAwareSQLAlchemyJobStore(SQLAlchemyJobStore):
    """APScheduler SQL job store with the tenant_id column required by JARVIS vNEXT."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "tenant_id" not in self.jobs_t.c:
            self.jobs_t.append_column(
                Column("tenant_id", SUUID(as_uuid=True), nullable=False, index=True)
            )

    def start(self, scheduler, alias):
        super().start(scheduler, alias)
        self._ensure_tenant_column()

    def add_job(self, job):
        insert = self.jobs_t.insert().values(
            id=job.id,
            tenant_id=_tenant_id_for_job(job),
            next_run_time=datetime_to_utc_timestamp(job.next_run_time),
            job_state=pickle.dumps(job.__getstate__(), self.pickle_protocol),
        )
        with self.engine.begin() as connection:
            try:
                connection.execute(insert)
            except IntegrityError as exc:
                raise ConflictingIdError(job.id) from exc

    def update_job(self, job):
        update = (
            self.jobs_t.update()
            .values(
                tenant_id=_tenant_id_for_job(job),
                next_run_time=datetime_to_utc_timestamp(job.next_run_time),
                job_state=pickle.dumps(job.__getstate__(), self.pickle_protocol),
            )
            .where(self.jobs_t.c.id == job.id)
        )
        with self.engine.begin() as connection:
            result = connection.execute(update)
            if result.rowcount == 0:
                raise JobLookupError(job.id)

    def _ensure_tenant_column(self) -> None:
        try:
            inspector = inspect(self.engine)
            columns = {column["name"] for column in inspector.get_columns(self.jobs_t.name)}
            if "tenant_id" in columns:
                return
            default_tenant = str(SYSTEM_TENANT_ID)
            column_type = "UUID" if self.engine.dialect.name == "postgresql" else "VARCHAR(36)"
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        f'ALTER TABLE "{self.jobs_t.name}" '
                        f"ADD COLUMN tenant_id {column_type} NOT NULL DEFAULT '{default_tenant}'"
                    )
                )
                connection.execute(text(f'CREATE INDEX IF NOT EXISTS "idx_{self.jobs_t.name}_tenant_id" ON "{self.jobs_t.name}" (tenant_id)'))
        except Exception as exc:
            logger.warning("Could not ensure tenant_id on APScheduler job table: %s", exc)


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        jobstore = TenantAwareSQLAlchemyJobStore(
            url=_sync_database_url(),
            tablename="apscheduler_jobs",
        )
        _scheduler = AsyncIOScheduler(
            jobstores={"default": jobstore},
            executors={"default": AsyncIOExecutor()},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 900,
            },
            timezone="UTC",
        )
    return _scheduler


async def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        aionx_error = register_production_jobs()
        try:
            await _sync_job_metadata()
        except Exception as exc:
            logger.warning("Scheduler metadata sync skipped: %s", exc)
        logger.info("JARVIS production scheduler started")

        if aionx_error:
            # All 26 AIONX organ jobs failed to register — that's the whole
            # intelligence layer silently absent, not something to leave as
            # a log line nobody watches.
            try:
                from app.services.notifications.telegram import notify_telegram
                await notify_telegram(
                    "🚨 *AIONX scheduler registration failed on startup*\n"
                    f"Error: {aionx_error}\n\n"
                    "All 26 AIONX organ jobs are absent from the scheduler — core "
                    "production jobs are running normally, only the AIONX layer is affected."
                )
            except Exception as exc:
                logger.warning("AIONX registration-failure alert failed: %s", exc)


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("JARVIS production scheduler stopped")


def register_production_jobs() -> Optional[str]:
    """Registers all production + AIONX jobs. Returns an error string if AIONX
    registration failed (all 26 organ jobs would be silently absent otherwise),
    or None on success."""
    _remove_deprecated_jobs()
    existing_job_ids = {job.id for job in get_scheduler().get_jobs()}
    specs = _production_job_specs()
    seeded = 0
    aionx_seeded = 0

    for raw_spec in specs:
        spec = dict(raw_spec)
        kind = spec.pop("kind", "cron")
        job_id = spec["job_id"]
        already_persisted = job_id in existing_job_ids
        spec["func"] = run_registered_production_job
        spec["args"] = [job_id]
        if kind == "interval":
            add_interval_job(**spec, replace=True)
        else:
            add_cron_job(**spec, replace=True)
        if not already_persisted:
            seeded += 1

    aionx_error: Optional[str] = None
    try:
        from app.services.aionx.aionx_scheduler import register_aionx_jobs

        register_aionx_jobs(add_cron_job, add_interval_job)
        aionx_seeded = len([job_id for job_id in AIONX_JOB_IDS if job_id not in existing_job_ids])
    except Exception as exc:
        logger.warning("AIONX scheduler heartbeat registration skipped: %s", exc)
        aionx_error = str(exc)

    loaded = len(PRODUCTION_JOB_IDS) - seeded
    logger.info(
        "JARVIS production scheduler ready: %s jobs loaded from persistent store, "
        "%s missing production jobs seeded, %s AIONX heartbeat jobs seeded",
        loaded,
        seeded,
        aionx_seeded,
    )
    return aionx_error


def _production_job_specs() -> list[dict[str, Any]]:
    return [
        {"job_id": "daily_morning_briefing", "func": daily_morning_briefing, "hour": 1, "minute": 30},
        {"job_id": "daily_lead_scoring", "func": daily_lead_scoring, "hour": 20, "minute": 30},
        {"job_id": "daily_lead_discovery", "func": daily_lead_discovery, "hour": 22, "minute": 0},
        {"job_id": "daily_follow_up_check", "func": daily_follow_up_check, "hour": 4, "minute": 30},
        {"job_id": "daily_outreach_safety_review", "func": daily_outreach_safety_review, "hour": 4, "minute": 45},
        {"job_id": "daily_memory_consolidate", "func": daily_memory_consolidate, "hour": 19, "minute": 0},
        {"job_id": "daily_optimization_review", "func": daily_optimization_review, "hour": 17, "minute": 30},
        {"job_id": "weekly_outreach_stats", "func": weekly_outreach_stats, "hour": 2, "minute": 30, "day_of_week": "mon"},
        {"job_id": "weekly_pipeline_health", "func": weekly_pipeline_health, "hour": 14, "minute": 30, "day_of_week": "sun"},
        {"job_id": "weekly_tech_radar", "func": weekly_tech_radar, "hour": 0, "minute": 30, "day_of_week": "mon"},
        {"job_id": "weekly_innovation_review", "func": weekly_innovation_review, "hour": 3, "minute": 30, "day_of_week": "mon"},
        {"job_id": "biweekly_research_report", "func": biweekly_research_report, "hour": 1, "minute": 30, "day_of_week": "sun"},
        {"job_id": "monthly_weight_adjust", "func": monthly_weight_adjust, "hour": 18, "minute": 30, "day": "last"},
        {"job_id": "daily_db_backup", "func": daily_db_backup, "hour": 1, "minute": 0},
        {"job_id": "speed_to_lead_5min", "func": speed_to_lead_5min, "kind": "interval", "minutes": 5},
        {"job_id": "daily_free_lead_discovery", "func": daily_free_lead_discovery, "hour": 3, "minute": 30},
        {"job_id": "weekly_market_scan", "func": weekly_market_scan, "hour": 5, "minute": 0, "day_of_week": "mon"},
        # Connector Hub — 14:30 UTC (20:00 IST) — ingest daily GitHub data package
        {"job_id": "daily_connector_hub_ingestion", "func": daily_connector_hub_ingestion, "hour": 14, "minute": 30},
        # Market Intelligence — 04:00 UTC (09:30 IST) — generate daily market reports
        {"job_id": "daily_market_intelligence", "func": daily_market_intelligence, "hour": 4, "minute": 0},
        # Self-Healer — every 15 minutes — circuit breaker reset, pipeline refill, scheduler resurrection
        {"job_id": "self_healer", "func": _job_self_healer, "kind": "interval", "minutes": 15},
        # Opportunity Radar — 06:00 UTC (11:30 IST) — surface idle hot leads before workday
        {"job_id": "daily_opportunity_radar", "func": daily_opportunity_radar, "hour": 6, "minute": 0},
        # Layer 18 — Truth, Validation & Resilience
        {"job_id": "daily_truth_reality_check", "func": daily_truth_reality_check, "hour": 23, "minute": 30},
        {"job_id": "weekly_financial_health", "func": weekly_financial_health, "hour": 7, "minute": 0, "day_of_week": "mon"},
        {"job_id": "weekly_founder_dependency", "func": weekly_founder_dependency, "hour": 7, "minute": 30, "day_of_week": "mon"},
        {"job_id": "weekly_moat_scan", "func": weekly_moat_scan, "hour": 8, "minute": 0, "day_of_week": "mon"},
        {"job_id": "weekly_cashflow_forecast", "func": weekly_cashflow_forecast, "hour": 8, "minute": 30, "day_of_week": "mon"},
        {"job_id": "weekly_learning_optimization", "func": weekly_learning_optimization, "hour": 9, "minute": 0, "day_of_week": "mon"},
        # ── Migrated from engine.py (Task #23 Phase B) ───────────────────────
        # Competitor Monitoring — Monday 09:00 UTC — restored per Captain's
        # decision that competitor intelligence must never silently disappear.
        {"job_id": "weekly_competitor_monitoring", "func": weekly_competitor_monitoring, "hour": 9, "minute": 0, "day_of_week": "mon"},
        # Routing Optimizer — 1st of each month @ 03:00 UTC — AI provider
        # routing weight learning. Never ran in production (dead engine.py
        # registrar); implementation was production-quality, only the wiring
        # was broken.
        {"job_id": "routing_optimizer_sweep", "func": routing_optimizer_sweep, "hour": 3, "minute": 0, "day": 1},
        # LinkedIn Outreach Sweep — every 2h — enrich HOT leads via Proxycurl
        # and generate first-connection messages. Never ran (dead registrar
        # that referenced a non-existent `scheduler` attribute in engine.py).
        {"job_id": "linkedin_outreach_sweep", "func": linkedin_outreach_sweep_job, "kind": "interval", "hours": 2},
        # Voice Analytics — 04:30 UTC daily — voice interaction metrics.
        # Never ran (same broken-attribute registrar bug as LinkedIn above).
        {"job_id": "voice_analytics_daily", "func": voice_analytics_daily, "hour": 4, "minute": 30},
        # ── Migrated from engine.py (Task #23 Phase C) ───────────────────────
        {"job_id": "captain_dashboard_briefing", "func": captain_dashboard_briefing, "hour": 6, "minute": 55},
        {"job_id": "weekly_performance_briefing", "func": weekly_performance_briefing, "hour": 19, "minute": 0, "day_of_week": "sat"},
        {"job_id": "daily_self_learning", "func": daily_self_learning, "hour": 0, "minute": 5},
        {"job_id": "drift_auditor", "func": drift_auditor, "hour": 5, "minute": 30},
        {"job_id": "daily_strategy_report", "func": daily_strategy_report, "hour": 23, "minute": 0},
        {"job_id": "weekly_strategy_review", "func": weekly_strategy_review, "hour": 7, "minute": 0, "day_of_week": "sun"},
        {"job_id": "milestone_bulk_review", "func": milestone_bulk_review, "hour": 10, "minute": 0},
        {"job_id": "dio_health_check", "func": dio_health_check, "hour": 6, "minute": 30},
        {"job_id": "tech_evolution_scan", "func": tech_evolution_scan, "kind": "interval", "hours": 6},
        {"job_id": "daily_scout_network", "func": daily_scout_network, "hour": 1, "minute": 30},
        {"job_id": "lead_embedding_sweep", "func": lead_embedding_sweep, "hour": 3, "minute": 15},
        {"job_id": "pre_call_briefing_trigger", "func": pre_call_briefing_trigger, "kind": "interval", "minutes": 30},
        {"job_id": "nexus_heartbeat", "func": nexus_heartbeat, "kind": "interval", "hours": 1},
        # nightly_signal_scan is the sole proposal-generation pipeline —
        # overnight_proposal_engine was retired, not migrated (see docstring).
        {"job_id": "nightly_signal_scan", "func": nightly_signal_scan, "hour": 2, "minute": 0},
        # Engineering Organization cycle — every 10 minutes — drains the
        # Phase 7 mission_planner -> dispatcher -> department_agent ->
        # peer_review -> deployment_integration pipeline. Previously this
        # code existed and was tested but nothing in production ever called
        # it past dispatch; a submitted objective sat forever.
        {"job_id": "engineering_org_cycle", "func": engineering_org_cycle, "kind": "interval", "minutes": 10},
    ]


async def _job_self_healer() -> None:
    try:
        from app.services.monitoring.self_healer import run_self_healing_cycle
        report = await run_self_healing_cycle()
        await _report_self_heal_to_headquarters(report)
    except Exception as exc:
        logger.warning("Self-healer job failed: %s", exc)


async def _report_self_heal_to_headquarters(report: dict) -> None:
    """Surface self-heal cycles that actually did something into the same
    Headquarters conversation Captain uses — no separate dashboard, per the
    single-front-door principle. Silent no-op cycles are not logged.
    """
    if not isinstance(report, dict):
        return
    actions = report.get("actions", [])
    alerts = report.get("alerts", [])
    if not actions and not alerts:
        return
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.headquarters.reporter import log_autonomous_operation

        lines = [f"Self-heal cycle ({report.get('duration_ms', 0)}ms):"]
        if actions:
            lines.append(f"{len(actions)} action(s) taken:")
            lines += [f"  - {a}" for a in actions]
        if alerts:
            lines.append(f"{len(alerts)} alert(s) — could not self-recover:")
            lines += [f"  - {a}" for a in alerts]

        async with AsyncSessionLocal() as db:
            await log_autonomous_operation(
                db, source="self_healer", summary="\n".join(lines),
                details=report, had_action=True,
            )
    except Exception as exc:
        logger.warning("Self-healer -> Headquarters reporting failed: %s", exc)


def _remove_deprecated_jobs() -> None:
    scheduler = get_scheduler()
    for job_id in DEPRECATED_JOB_IDS:
        try:
            scheduler.remove_job(job_id)
        except Exception:
            continue


def add_cron_job(
    job_id: str,
    func: Callable,
    hour: int = 8,
    minute: int = 0,
    timezone_str: str = "UTC",
    replace: bool = True,
    day_of_week: str | None = None,
    day: str | int | None = None,
    args: list | None = None,
    kwargs: dict | None = None,
) -> None:
    trigger_kwargs: dict[str, Any] = {"hour": hour, "minute": minute, "timezone": timezone_str}
    if day_of_week:
        trigger_kwargs["day_of_week"] = day_of_week
    if day:
        trigger_kwargs["day"] = day
    get_scheduler().add_job(
        func,
        trigger=CronTrigger(**trigger_kwargs),
        id=job_id,
        name=job_id,
        replace_existing=replace,
        args=args or [],
        kwargs=kwargs or {},
    )


def add_interval_job(
    job_id: str,
    func: Callable,
    hours: float = 0,
    minutes: float = 0,
    seconds: float = 0,
    replace: bool = True,
    args: list | None = None,
    kwargs: dict | None = None,
) -> None:
    get_scheduler().add_job(
        func,
        trigger=IntervalTrigger(hours=hours, minutes=minutes, seconds=seconds),
        id=job_id,
        name=job_id,
        replace_existing=replace,
        args=args or [],
        kwargs=kwargs or {},
    )


def add_oneshot_job(job_id: str, func: Callable, run_at: datetime, replace: bool = True, args: list | None = None, kwargs: dict | None = None) -> None:
    get_scheduler().add_job(
        func,
        trigger=DateTrigger(run_date=run_at),
        id=job_id,
        name=job_id,
        replace_existing=replace,
        args=args or [],
        kwargs=kwargs or {},
    )


def remove_job(job_id: str) -> bool:
    try:
        get_scheduler().remove_job(job_id)
        return True
    except Exception:
        return False


def pause_job(job_id: str) -> bool:
    try:
        get_scheduler().pause_job(job_id)
        return True
    except Exception:
        return False


def resume_job(job_id: str) -> bool:
    try:
        get_scheduler().resume_job(job_id)
        return True
    except Exception:
        return False


def get_jobs() -> list[dict]:
    jobs = []
    for job in get_scheduler().get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
        )
    return jobs


async def run_registered_production_job(job_id: str, retry_count: int = 0) -> None:
    registry = _production_job_registry()
    func = registry.get(job_id)
    if not func:
        await _record_job_result(job_id, "failed", {"error": "production job not registered"})
        return

    token = uuid.uuid4().hex
    lock_acquired = await _acquire_job_lock(job_id, token)
    if not lock_acquired:
        await _record_job_result(job_id, "skipped", {"reason": "already_running"})
        return

    try:
        await func()
    except Exception as exc:
        await _record_job_failure(job_id, exc, retry_count=retry_count)
    finally:
        await _release_job_lock(job_id, token)


async def retry_registered_production_job(job_id: str, retry_count: int) -> None:
    await run_registered_production_job(job_id, retry_count=retry_count)


async def enqueue_scheduled_task(job_id: str, tenant_id: str | None = None) -> None:
    from app.core.database import AsyncSessionLocal, set_tenant_context
    from app.models.scheduling import JobFailure, ScheduledJob
    from app.services.tasks.queue import enqueue

    tenant_uuid = _coerce_tenant_id(tenant_id) if tenant_id else SYSTEM_TENANT_ID
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await _safe_set_tenant_context(db, tenant_uuid)
            job = await db.scalar(
                select(ScheduledJob).where(
                    ScheduledJob.tenant_id == tenant_uuid,
                    ScheduledJob.job_id == job_id,
                )
            )
            if not job:
                return
            await enqueue(
                db=db,
                title=job.name or job.job_id,
                description=job.description or "",
                task_type=job.task_type or "custom",
                priority=5,
                payload=job.payload or {},
                assigned_to=job.agent or "jarvis",
            )
            job.last_run_at = datetime.now(UTC)
            job.last_status = "success"
            job.run_count = int(job.run_count or 0) + 1


async def daily_morning_briefing() -> None:
    from app.services.intelligence.morning_briefing import MorningBriefingEngine

    engine = MorningBriefingEngine()
    generated = 0
    for tenant_id in await _target_tenant_ids():
        if await engine.generate_and_send(tenant_id):
            generated += 1
    await _record_job_result("daily_morning_briefing", "success", {"briefings": generated})


async def daily_lead_scoring() -> None:
    from app.services.leads.scoring import lead_scoring_engine

    promoted = 0
    for tenant_id in await _target_tenant_ids():
        promoted += await lead_scoring_engine.score_yesterday_new_leads(tenant_id, promote_limit=20)
    await _record_job_result("daily_lead_scoring", "success", {"promoted": promoted})


async def daily_lead_discovery() -> None:
    from app.services.leads.discovery import lead_discovery_engine
    from app.core.config import settings

    discovered = 0
    for tenant_id in await _target_tenant_ids():
        discovered += await lead_discovery_engine.run_daily_discovery(tenant_id, DAILY_DISCOVERY_TARGETS)

    result_payload = {"discovered": discovered}
    if not settings.APOLLO_API_KEY and not settings.GOOGLE_MAPS_API_KEY:
        # Without either key this job (and the free-tier fallback) can still create
        # leads, but none carry an email address — outreach silently never fires
        # for them. Surface that loudly instead of leaving it to be discovered later.
        result_payload["warning"] = "no_email_capable_discovery_source_configured"
        try:
            from app.services.notifications.telegram import notify_telegram
            await notify_telegram(
                "⚠️ *Lead Discovery* — APOLLO_API_KEY and GOOGLE_MAPS_API_KEY are both unset.\n"
                f"{discovered} lead(s) discovered today via free sources only — none carry an "
                "email address, so automated outreach cannot fire for them. Add an Apollo API "
                "key to production `.env` to unlock email-capable discovery."
            )
        except Exception as exc:
            logger.warning("Lead discovery config-gap notification failed: %s", exc)

    await _record_job_result("daily_lead_discovery", "success", result_payload)


async def daily_follow_up_check() -> None:
    from app.services.outreach.engine import outreach_engine

    sent = 0
    for tenant_id in await _target_tenant_ids():
        sent += await outreach_engine.execute_due_outreach(tenant_id, limit=48)
    await _record_job_result("daily_follow_up_check", "success", {"sent": sent})


async def daily_outreach_safety_review() -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.notifications import notify_business_event
    from app.services.outreach.compliance import outreach_compliance

    results = []
    for tenant_id in await _target_tenant_ids():
        tenant_uuid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            async with db.begin():
                await _safe_set_tenant_context(db, tenant_uuid)
                result = await outreach_compliance.assess_reply_rate_pause(db, tenant_uuid)
                results.append({"tenant_id": str(tenant_uuid), **result})
                if result.get("paused"):
                    await notify_business_event(
                        "outreach_auto_paused",
                        "Outreach auto-paused",
                        (
                            f"JARVIS paused outreach for tenant {tenant_uuid}: "
                            f"reply rate {result.get('reply_rate')} after {result.get('sent')} sends."
                        ),
                    )
    await _record_job_result("daily_outreach_safety_review", "success", {"tenants": results})


async def speed_to_lead_5min() -> None:
    from app.services.revenue_activation.speed_to_lead import speed_to_lead_engine

    processed = 0
    tenants = []
    for tenant_id in await _target_tenant_ids():
        result = await speed_to_lead_engine.trigger(tenant_id, lookback_minutes=5)
        processed += int(result.get("processed", 0))
        tenants.append(result)
    await _record_job_result(
        "speed_to_lead_5min",
        "success",
        {"processed": processed, "tenants": tenants},
    )


async def daily_free_lead_discovery() -> None:
    from app.services.revenue_activation.free_discovery import free_discovery_engine

    inserted = 0
    enriched = 0
    tenants = []
    for tenant_id in await _target_tenant_ids():
        result = await free_discovery_engine.run(tenant_id, limit=50)
        inserted += int(result.get("inserted", 0))
        enriched += int(result.get("manual_leads_enriched", 0))
        tenants.append(result)
    await _record_job_result(
        "daily_free_lead_discovery",
        "success",
        {"inserted": inserted, "manual_leads_enriched": enriched, "tenants": tenants},
    )


async def weekly_market_scan() -> None:
    from app.services.revenue_activation.market_awareness import market_awareness_engine

    scans = []
    high_relevance = 0
    for tenant_id in await _target_tenant_ids():
        result = await market_awareness_engine.weekly_scan(tenant_id)
        high_relevance += int(result.get("high_relevance_new_items", 0))
        scans.append(result)
    await _record_job_result(
        "weekly_market_scan",
        "success",
        {"high_relevance_new_items": high_relevance, "tenants": scans},
    )


async def daily_memory_consolidate() -> None:
    from app.services.memory.memory_engine import memory_engine

    results = []
    for tenant_id in await _target_tenant_ids():
        consolidated = await memory_engine.consolidate_working_to_operational(tenant_id)
        pruned = await memory_engine.prune_operational(tenant_id)
        promoted = await memory_engine.promote_high_relevance_operational(tenant_id)
        results.append({"tenant_id": tenant_id, "consolidated": consolidated, "pruned": pruned, "promoted": promoted})
    await _record_job_result("daily_memory_consolidate", "success", {"tenants": results})


async def daily_optimization_review() -> None:
    from app.core.database import AsyncSessionLocal, set_tenant_context
    from app.services.intelligence.optimizer import analyze_system

    generated = 0
    for tenant_id in await _target_tenant_ids():
        tenant_uuid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            async with db.begin():
                await _safe_set_tenant_context(db, tenant_uuid)
                generated += await analyze_system(db, tenant_uuid)
    await _record_job_result("daily_optimization_review", "success", {"recommendations": generated})


async def weekly_outreach_stats() -> None:
    from app.services.notifications import notify_business_event
    from app.services.outreach.engine import outreach_engine

    summaries = []
    for tenant_id in await _target_tenant_ids():
        stats = await outreach_engine.stats(tenant_id)
        summaries.append({"tenant_id": tenant_id, **stats})
    await notify_business_event(
        "weekly_outreach_stats",
        "Weekly outreach stats",
        _format_stats_summary(summaries),
    )
    await _record_job_result("weekly_outreach_stats", "success", {"tenants": summaries})


async def weekly_pipeline_health() -> None:
    summary = await _pipeline_health_summary()
    from app.services.notifications import notify_business_event

    await notify_business_event("weekly_pipeline_health", "Weekly pipeline health", summary["text"])
    await _record_job_result("weekly_pipeline_health", "success", summary)


async def weekly_tech_radar() -> None:
    from app.services.intelligence.tech_radar import TechRadarEngine

    entries = 0
    engine = TechRadarEngine()
    for tenant_id in await _target_tenant_ids():
        entries += len(await engine.scan_week(tenant_id))
    await _record_job_result("weekly_tech_radar", "success", {"entries": entries})


async def weekly_innovation_review() -> None:
    from app.services.innovation import innovation_queue_service

    reviewed = 0
    for tenant_id in await _target_tenant_ids():
        result = await innovation_queue_service.weekly_council_review(tenant_id)
        reviewed += int(result.get("reviewed", 0))
    await _record_job_result("weekly_innovation_review", "success", {"reviewed": reviewed})


async def biweekly_research_report() -> None:
    if datetime.now(UTC).isocalendar().week % 2:
        await _record_job_result("biweekly_research_report", "skipped", {"reason": "alternate_week_guard"})
        return

    from app.services.intelligence.market_intel import MarketIntelligenceEngine

    generated = 0
    engine = MarketIntelligenceEngine()
    for tenant_id in await _target_tenant_ids():
        if await engine.generate_report(RESEARCH_TOPICS, tenant_id):
            generated += 1
    await _record_job_result("biweekly_research_report", "success", {"reports": generated})


async def monthly_weight_adjust() -> None:
    from app.services.ai.council import intelligence_council

    adjusted = 0
    for tenant_id in await _target_tenant_ids():
        await intelligence_council.adjust_weights_monthly(tenant_id)
        adjusted += 1
    await _record_job_result("monthly_weight_adjust", "success", {"tenants": adjusted})


async def daily_db_backup() -> None:
    from app.services.notifications import notify_business_event

    parsed = _parse_postgres_url(settings.DATABASE_URL)
    if not parsed:
        await _record_job_result("daily_db_backup", "skipped", {"reason": "unsupported_database_url"})
        return

    backup_dir = Path("/var/backups/jarvis")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    output_path = backup_dir / f"postgres-{stamp}.sql.gz"
    command = (
        f"pg_dump -h {shlex.quote(parsed['host'])} -p {shlex.quote(parsed['port'])} "
        f"-U {shlex.quote(parsed['user'])} -d {shlex.quote(parsed['database'])} "
        f"| gzip -c > {shlex.quote(str(output_path))}"
    )
    env = {**os.environ, "PGPASSWORD": parsed["password"]}
    process = await asyncio.create_subprocess_shell(
        command,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {stderr.decode(errors='replace')[:1000]}")
    size = output_path.stat().st_size if output_path.exists() else 0
    if size <= 0:
        raise RuntimeError("pg_dump produced an empty backup file")

    bucket = settings.S3_BACKUP_BUCKET or settings.AWS_S3_BUCKET
    uploaded = False
    if bucket:
        import boto3

        key = f"postgres/{stamp}.sql.gz"
        boto3.client("s3", region_name=settings.AWS_REGION).upload_file(str(output_path), bucket, key)
        uploaded = True
    else:
        try:
            await notify_business_event(
                "backup_local_only",
                "Database backup stored locally",
                "S3_BACKUP_BUCKET is not configured. Backup saved locally in /var/backups/jarvis/.",
            )
        except Exception as exc:
            logger.warning("Local backup notification skipped: %s", exc)

    _prune_local_backups(backup_dir, keep=30)
    await _record_job_result(
        "daily_db_backup",
        "success",
        {"path": str(output_path), "size_bytes": size, "uploaded_to_s3": uploaded, "bucket": bucket},
    )


async def daily_connector_hub_ingestion() -> None:
    """Pull daily data package from GitHub /jarvis-data/ and ingest into JARVIS pipeline."""
    from app.services.integrations.connector_hub import connector_hub

    results = {}
    for tenant_id in await _target_tenant_ids():
        try:
            result = await connector_hub.ingest_daily_package(tenant_id)
            results[str(tenant_id)] = {
                "leads_processed": result.get("leads", {}).get("processed", 0),
                "sequences_loaded": result.get("sequences", {}).get("sequences_loaded", 0),
                "errors": result.get("errors", []),
            }
        except Exception as exc:
            logger.error("Connector hub ingestion failed for tenant %s: %s", tenant_id, exc)
            results[str(tenant_id)] = {"error": str(exc)}

    await _record_job_result(
        "daily_connector_hub_ingestion",
        "success",
        {"tenants": len(results), "results": results},
    )


async def daily_market_intelligence() -> None:
    """Generate daily market intelligence report and trending opportunity scan."""
    from app.services.integrations.market_intelligence_engine import market_intelligence_engine
    from app.services.integrations.github_bridge import github_bridge
    import os

    reports = 0
    for tenant_id in await _target_tenant_ids():
        try:
            output_dir = os.path.join(github_bridge.REPO_DATA_PATH, "intelligence")
            result = await market_intelligence_engine.write_github_intelligence_package(
                tenant_id=tenant_id,
                output_dir=output_dir,
            )
            reports += len(result.get("files_written", []))
        except Exception as exc:
            logger.error("Market intelligence failed for tenant %s: %s", tenant_id, exc)

    await _record_job_result(
        "daily_market_intelligence",
        "success",
        {"files_generated": reports},
    )


async def weekly_competitor_monitoring() -> None:
    """Weekly competitor intelligence scan (Monday 09:00 UTC) — restored per
    Task #23 Phase B: competitor intelligence is a core strategic capability
    and must always exist as a scheduled job, not silently disappear.
    """
    from app.services.intelligence.market_intel import MarketIntelligenceEngine

    engine = MarketIntelligenceEngine()
    changes = 0
    for tenant_id in await _target_tenant_ids():
        try:
            changes += len(await engine.monitor_competitors(tenant_id))
        except Exception as exc:
            logger.error("Competitor monitoring failed for tenant %s: %s", tenant_id, exc)
    await _record_job_result("weekly_competitor_monitoring", "success", {"changes_detected": changes})


async def routing_optimizer_sweep() -> None:
    """Monthly AI routing weight optimization (1st of month, 03:00 UTC) —
    migrated from the dead engine.py registrar per Task #23 Phase B.
    """
    from app.core.database import AsyncSessionLocal
    from app.services.fabric.routing_optimizer import run_routing_optimizer

    async with AsyncSessionLocal() as db:
        result = await run_routing_optimizer(db)
    await _record_job_result("routing_optimizer_sweep", "success", result)


async def linkedin_outreach_sweep_job() -> None:
    """LinkedIn outreach enrichment + message generation sweep (every 2h) —
    migrated from the dead engine.py registrar per Task #23 Phase B. The
    business logic (Proxycurl enrichment, AI message generation) was already
    production-quality; only the scheduler wiring was broken.
    """
    from app.services.outreach.linkedin_outreach import linkedin_outreach_sweep

    result = await linkedin_outreach_sweep()
    await _record_job_result("linkedin_outreach_sweep", "success", result)


async def voice_analytics_daily() -> None:
    """Daily voice interaction analytics (04:30 UTC) — migrated from the dead
    engine.py registrar per Task #23 Phase B.
    """
    from app.services.voice.analytics import run_voice_analytics_job

    result = await run_voice_analytics_job()
    await _record_job_result("voice_analytics_daily", "success", result)


async def daily_opportunity_radar() -> None:
    """Scan for hot leads that have gone idle and surface them to Captain."""
    from app.services.intelligence.opportunity_radar import run_opportunity_radar

    reports = 0
    for tenant_id in await _target_tenant_ids():
        try:
            report = await run_opportunity_radar(tenant_id)
            found = report.get("summary", {}).get("total_opportunities", 0)
            if found:
                reports += found
        except Exception as exc:
            logger.error("Opportunity radar failed for tenant %s: %s", tenant_id, exc)

    await _record_job_result("daily_opportunity_radar", "success", {"opportunities_found": reports})


async def engineering_org_cycle() -> None:
    """E7-10: drains the Engineering Organization pipeline end to end.

    Phase 7 (mission_planner/dispatcher/department_agent/peer_review/
    deployment_integration) shipped fully tested but nothing in production
    ever called run_one_cycle/review_work_package/integrate_work_package
    outside unit tests — a submitted objective got decomposed and enqueued,
    then sat forever. This job is that missing caller: for every task graph
    still IN_PROGRESS, dispatch ready work packages, drain a bounded number
    of department drafts, peer-review anything freshly drafted, and integrate
    anything peer-review approved (auto-deploying the narrow safe actions,
    otherwise leaving a PR-ready summary for a human/Claude session — see
    deployment_integration.py's own documented scope boundary).
    """
    from app.core.database import AsyncSessionLocal
    from app.models.engineering import (
        EngineeringTaskGraph,
        EngineeringWorkPackage,
        TaskGraphStatus,
        WorkPackageStatus,
    )
    from app.services.engineering import department_agent, deployment_integration, dispatcher, peer_review

    MAX_DRAFT_CYCLES_PER_TICK = 20

    drafted = 0
    reviewed = 0
    integrated = 0
    pending_manual_integration = []
    errors = 0

    async with AsyncSessionLocal() as db:
        async with db.begin():
            graph_ids = (
                await db.execute(
                    select(EngineeringTaskGraph.id).where(
                        EngineeringTaskGraph.status == TaskGraphStatus.IN_PROGRESS
                    )
                )
            ).scalars().all()

            for graph_id in graph_ids:
                await dispatcher.dispatch_ready_packages(db, graph_id)

            for _ in range(MAX_DRAFT_CYCLES_PER_TICK):
                wp = await department_agent.run_one_cycle(db)
                if wp is None:
                    break
                drafted += 1

            in_review = (
                await db.execute(
                    select(EngineeringWorkPackage).where(
                        EngineeringWorkPackage.status == WorkPackageStatus.IN_REVIEW
                    )
                )
            ).scalars().all()
            for wp in in_review:
                try:
                    await peer_review.review_work_package(db, wp)
                    reviewed += 1
                except Exception:
                    logger.exception("engineering_org_cycle: peer review failed for work package %s", wp.id)
                    errors += 1

            approved = (
                await db.execute(
                    select(EngineeringWorkPackage).where(
                        EngineeringWorkPackage.status == WorkPackageStatus.APPROVED,
                        EngineeringWorkPackage.deploy_result.is_(None),
                    )
                )
            ).scalars().all()
            for wp in approved:
                try:
                    result = await deployment_integration.integrate_work_package(db, wp)
                    integrated += 1
                    if result.get("mode") == "pending_manual_integration":
                        pending_manual_integration.append(str(wp.id))
                except Exception:
                    logger.exception("engineering_org_cycle: integration failed for work package %s", wp.id)
                    errors += 1

            for graph_id in graph_ids:
                await dispatcher.refresh_graph_status(db, graph_id)

    if pending_manual_integration:
        try:
            from app.services.notifications import notify_business_event
            await notify_business_event(
                "engineering_work_package_ready",
                "Engineering Organization: work ready for integration",
                f"{len(pending_manual_integration)} approved work package(s) have a PR-ready "
                "summary waiting for a human/Claude session to commit — see "
                "/api/v1/engineering/dashboard.",
            )
        except Exception as exc:
            logger.warning("engineering_org_cycle: ready-for-integration notify failed: %s", exc)

    await _record_job_result(
        "engineering_org_cycle",
        "success",
        {
            "task_graphs_scanned": len(graph_ids),
            "drafted": drafted,
            "reviewed": reviewed,
            "integrated": integrated,
            "pending_manual_integration": pending_manual_integration,
            "errors": errors,
        },
    )


async def _sync_job_metadata() -> None:
    _ensure_model_registry()
    from app.core.database import AsyncSessionLocal
    from app.models.scheduling import JobFailure, ScheduledJob

    async with AsyncSessionLocal() as db:
        async with db.begin():
            await _safe_set_tenant_context(db, SYSTEM_TENANT_ID)
            for job in get_scheduler().get_jobs():
                existing = await db.scalar(
                    select(ScheduledJob).where(
                        ScheduledJob.tenant_id == SYSTEM_TENANT_ID,
                        ScheduledJob.job_id == job.id,
                    )
                )
                payload = _job_metadata(job)
                if existing:
                    existing.name = job.name
                    existing.trigger_type = payload["trigger_type"]
                    existing.trigger_args = payload["trigger_args"]
                    existing.agent = "jarvis"
                    existing.task_type = _task_type_for_job(job.id)
                    existing.payload = {"production_job": True}
                    existing.enabled = True
                    existing.next_run_at = _db_datetime(job.next_run_time)
                else:
                    db.add(
                        ScheduledJob(
                            tenant_id=SYSTEM_TENANT_ID,
                            job_id=job.id,
                            name=job.name,
                            description=f"JARVIS production job: {job.id}",
                            trigger_type=payload["trigger_type"],
                            trigger_args=payload["trigger_args"],
                            agent="jarvis",
                            task_type=_task_type_for_job(job.id),
                            payload={"production_job": True},
                            enabled=True,
                            next_run_at=_db_datetime(job.next_run_time),
                        )
                    )


async def _record_job_result(job_id: str, status: str, payload: dict) -> None:
    _ensure_model_registry()
    from app.core.database import AsyncSessionLocal
    from app.models.approval import AuditLog
    from app.models.scheduling import JobFailure, ScheduledJob

    async with AsyncSessionLocal() as db:
        async with db.begin():
            await _safe_set_tenant_context(db, SYSTEM_TENANT_ID)
            job = await db.scalar(
                select(ScheduledJob).where(
                    ScheduledJob.tenant_id == SYSTEM_TENANT_ID,
                    ScheduledJob.job_id == job_id,
                )
            )
            if job:
                job.last_run_at = _db_datetime(datetime.now(UTC))
                job.last_status = status
                job.run_count = int(job.run_count or 0) + 1
                aps_job = get_scheduler().get_job(job_id)
                job.next_run_at = _db_datetime(aps_job.next_run_time) if aps_job else None
            if status == "success":
                failures = (
                    await db.execute(
                        select(JobFailure).where(
                            JobFailure.tenant_id == SYSTEM_TENANT_ID,
                            JobFailure.job_name == job_id,
                            JobFailure.status.in_(("open", "retry_scheduled", "failed")),
                        ).limit(100)
                    )
                ).scalars().all()
                for failure in failures:
                    failure.status = "resolved"
                    failure.last_retry_at = _db_datetime(datetime.now(UTC))
                    failure.metadata_json = {
                        **(failure.metadata_json or {}),
                        "resolved_by": "successful_job_run",
                        "resolved_at": datetime.now(UTC).isoformat(),
                    }
            db.add(
                AuditLog(
                    tenant_id=SYSTEM_TENANT_ID,
                    action=f"scheduler_{job_id}_{status}",
                    entity_type="scheduled_job",
                    actor="ProductionScheduler",
                    after_json=payload,
                    details=payload,
                )
            )


async def _record_job_failure(job_id: str, exc: Exception, retry_count: int = 0) -> None:
    _ensure_model_registry()
    from app.core.database import AsyncSessionLocal
    from app.models.approval import AuditLog
    from app.models.scheduling import JobFailure
    from app.services.notifications import notify_business_event

    retry_count = int(retry_count or 0)
    delay_minutes = [5, 15, 45][retry_count] if retry_count < 3 else None
    next_retry_at = datetime.now(UTC) + timedelta(minutes=delay_minutes) if delay_minutes else None
    error = str(exc)[:4000]
    trace = traceback_lib.format_exc()

    async with AsyncSessionLocal() as db:
        async with db.begin():
            await _safe_set_tenant_context(db, SYSTEM_TENANT_ID)
            failure = JobFailure(
                tenant_id=SYSTEM_TENANT_ID,
                job_name=job_id,
                status="retry_scheduled" if next_retry_at else "failed",
                error=error,
                traceback=trace,
                retry_count=retry_count,
                next_retry_at=_db_datetime(next_retry_at),
                metadata_json={"managed_scheduler": True},
            )
            db.add(failure)
            db.add(
                AuditLog(
                    tenant_id=SYSTEM_TENANT_ID,
                    action=f"scheduler_{job_id}_failed",
                    entity_type="scheduled_job",
                    actor="ProductionScheduler",
                    after_json={
                        "error": error,
                        "retry_count": retry_count,
                        "next_retry_at": next_retry_at.isoformat() if next_retry_at else None,
                    },
                    details={
                        "error": error,
                        "retry_count": retry_count,
                        "next_retry_at": next_retry_at.isoformat() if next_retry_at else None,
                    },
                )
            )

    if next_retry_at:
        add_oneshot_job(
            f"retry_{job_id}_{retry_count + 1}_{int(datetime.now(UTC).timestamp())}",
            retry_registered_production_job,
            next_retry_at,
            replace=True,
            args=[job_id, retry_count + 1],
        )
    else:
        try:
            await notify_business_event(
                "scheduler_job_failed",
                f"Job failed 3 times: {job_id}",
                f"Job {job_id} failed 3 times. Last error: {error}",
            )
        except Exception as notify_exc:
            logger.warning("Scheduler failure notification skipped: %s", notify_exc)


async def _target_tenant_ids() -> list[str]:
    if settings.JARVIS_DEFAULT_TENANT_ID:
        return [settings.JARVIS_DEFAULT_TENANT_ID]

    from app.core.database import AsyncSessionLocal
    from app.models.tenant import Tenant

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Tenant.id)
            .where(Tenant.is_active.is_(True))
            .order_by(Tenant.created_at)
            .limit(200)
        )
        return [str(row[0]) for row in result.all()]


async def _pipeline_health_summary() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.models.approval import ApprovalRequest, ApprovalStatus
    from app.models.crm import Deal
    from app.models.lead import Lead
    from app.models.outreach import ReplyLog

    rows = []
    async with AsyncSessionLocal() as db:
        for tenant_id in await _target_tenant_ids():
            tenant_uuid = _coerce_tenant_id(tenant_id)
            await _safe_set_tenant_context(db, tenant_uuid)
            leads = await db.scalar(select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_uuid)) or 0
            pipeline = await db.scalar(
                select(func.coalesce(func.sum(Deal.value), 0.0)).where(
                    Deal.tenant_id == tenant_uuid,
                    Deal.stage.notin_(("closed_won", "closed_lost")),
                )
            ) or 0.0
            replies = await db.scalar(
                select(func.count()).select_from(ReplyLog).where(
                    ReplyLog.tenant_id == tenant_uuid,
                    ReplyLog.created_at >= datetime.now(UTC) - timedelta(days=7),
                )
            ) or 0
            approvals = await db.scalar(
                select(func.count()).select_from(ApprovalRequest).where(
                    ApprovalRequest.tenant_id == tenant_uuid,
                    ApprovalRequest.status == ApprovalStatus.PENDING,
                )
            ) or 0
            rows.append({"tenant_id": tenant_id, "leads": int(leads), "pipeline": float(pipeline), "replies": int(replies), "approvals": int(approvals)})

    text = "\n".join(
        f"Tenant {row['tenant_id']}: leads={row['leads']}, pipeline=${row['pipeline']:,.0f}, replies_7d={row['replies']}, pending_approvals={row['approvals']}"
        for row in rows
    ) or "No active tenants found."
    return {"text": text, "tenants": rows}


async def _safe_set_tenant_context(db, tenant_id: uuid.UUID) -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        return
    from app.core.database import set_tenant_context

    await set_tenant_context(db, str(tenant_id))


def _production_job_registry() -> dict[str, Callable]:
    return {spec["job_id"]: spec["func"] for spec in _production_job_specs()}


async def _acquire_job_lock(job_id: str, token: str) -> bool:
    if not settings.REDIS_URL:
        return True
    try:
        import redis.asyncio as aioredis

        ttl = int(JOB_LOCK_TTLS.get(job_id, 900))
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        acquired = await redis.set(f"job_lock:{job_id}", token, ex=ttl, nx=True)
        await redis.aclose()
        return bool(acquired)
    except Exception as exc:
        logger.warning("Scheduler lock degraded for %s: %s", job_id, exc)
        return True


async def _release_job_lock(job_id: str, token: str) -> None:
    if not settings.REDIS_URL:
        return
    try:
        import redis.asyncio as aioredis

        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"job_lock:{job_id}"
        current = await redis.get(key)
        if current == token:
            await redis.delete(key)
        await redis.aclose()
    except Exception as exc:
        logger.warning("Scheduler lock release skipped for %s: %s", job_id, exc)


def _sync_database_url() -> str:
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
    if url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return url


def _parse_postgres_url(url: str) -> dict[str, str] | None:
    if not url.startswith("postgresql"):
        return None
    clean = url.replace("postgresql+asyncpg://", "postgresql://", 1).replace("postgresql+psycopg://", "postgresql://", 1)
    parsed = urlparse(clean)
    if not parsed.hostname or not parsed.username or not parsed.path:
        return None
    return {
        "host": parsed.hostname,
        "port": str(parsed.port or 5432),
        "user": unquote(parsed.username),
        "password": unquote(parsed.password or ""),
        "database": parsed.path.lstrip("/"),
    }


def _prune_local_backups(backup_dir: Path, keep: int = 30) -> None:
    backups = sorted(backup_dir.glob("postgres-*.sql.gz"), key=lambda path: path.stat().st_mtime, reverse=True)
    for old in backups[max(0, keep):]:
        try:
            old.unlink()
        except OSError:
            logger.warning("Could not remove old backup %s", old)


def _ensure_model_registry() -> None:
    from app.models import register_models

    register_models()


def _tenant_id_for_job(job) -> uuid.UUID:
    kwargs = getattr(job, "kwargs", None) or {}
    raw = kwargs.get("tenant_id")
    if raw:
        try:
            return _coerce_tenant_id(raw)
        except (TypeError, ValueError):
            return SYSTEM_TENANT_ID
    return SYSTEM_TENANT_ID


def _coerce_tenant_id(value) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _job_metadata(job) -> dict:
    trigger = str(job.trigger)
    return {
        "trigger_type": "cron" if "cron" in trigger.lower() else "interval" if "interval" in trigger.lower() else "date",
        "trigger_args": {"trigger": trigger},
    }


def _db_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _task_type_for_job(job_id: str) -> str:
    if "free_lead_discovery" in job_id or "lead" in job_id:
        return "lead_ops"
    if "speed_to_lead" in job_id or "outreach" in job_id or "follow_up" in job_id:
        return "outreach"
    if "memory" in job_id:
        return "memory"
    if "briefing" in job_id:
        return "briefing"
    if "connector_hub" in job_id:
        return "connector_hub"
    if "market_intelligence" in job_id:
        return "intelligence"
    if "market_scan" in job_id or "radar" in job_id or "research" in job_id or "optimization" in job_id or "innovation" in job_id or "competitor" in job_id:
        return "intelligence"
    if "weight" in job_id or "routing_optimizer" in job_id:
        return "ai_council"
    if "voice_analytics" in job_id:
        return "voice"
    return "system"


def _format_stats_summary(rows: list[dict]) -> str:
    if not rows:
        return "No active tenants found."
    return "\n".join(
        f"Tenant {row['tenant_id']}: sent={row.get('sent_outreach', 0)}, pending={row.get('pending_followups', 0)}, "
        f"executed={row.get('executed_followups', 0)}, failed={row.get('failed_followups', 0)}"
        for row in rows
    )


# ── Layer 18 — Truth, Validation & Resilience Jobs ───────────────────────────

async def daily_truth_reality_check() -> None:
    """Nightly truth engine sweep: run reality checks across all prediction types."""
    from app.services.intelligence.truth_engine import truth_engine
    checks = ["lead_score", "trust_score", "proposal_acceptance", "revenue_forecast", "client_health"]
    completed = 0
    for tenant_id in await _target_tenant_ids():
        for check_type in checks:
            try:
                await truth_engine.run_reality_check(tenant_id, check_type)
                completed += 1
            except Exception as exc:
                logger.warning("Reality check %s failed for tenant %s: %s", check_type, tenant_id, exc)
    await _record_job_result("daily_truth_reality_check", "success", {"checks_run": completed})


async def weekly_financial_health() -> None:
    """Monday morning: compute financial health snapshot + CFO briefing."""
    from app.services.intelligence.financial_intelligence import financial_intelligence
    computed = 0
    for tenant_id in await _target_tenant_ids():
        try:
            await financial_intelligence.compute_weekly_health(tenant_id)
            computed += 1
        except Exception as exc:
            logger.warning("Weekly financial health failed for tenant %s: %s", tenant_id, exc)
    await _record_job_result("weekly_financial_health", "success", {"tenants": computed})


async def weekly_founder_dependency() -> None:
    """Monday: assess founder dependency score and alert if critical."""
    from app.services.intelligence.founder_dependency import founder_dependency_engine
    assessed = 0
    for tenant_id in await _target_tenant_ids():
        try:
            await founder_dependency_engine.run_weekly_assessment(tenant_id)
            assessed += 1
        except Exception as exc:
            logger.warning("Founder dependency assessment failed for tenant %s: %s", tenant_id, exc)
    await _record_job_result("weekly_founder_dependency", "success", {"tenants": assessed})


async def weekly_moat_scan() -> None:
    """Monday: run competitive moat scan across all dimensions."""
    from app.services.intelligence.moat_engine import moat_engine
    scanned = 0
    for tenant_id in await _target_tenant_ids():
        try:
            await moat_engine.run_weekly_moat_scan(tenant_id)
            scanned += 1
        except Exception as exc:
            logger.warning("Moat scan failed for tenant %s: %s", tenant_id, exc)
    await _record_job_result("weekly_moat_scan", "success", {"tenants": scanned})


async def weekly_cashflow_forecast() -> None:
    """Monday: generate 30/60/90 day cashflow forecasts."""
    from app.services.intelligence.financial_intelligence import financial_intelligence
    forecasted = 0
    for tenant_id in await _target_tenant_ids():
        try:
            await financial_intelligence.generate_cashflow_forecast(tenant_id, horizon_days=90)
            forecasted += 1
        except Exception as exc:
            logger.warning("Cashflow forecast failed for tenant %s: %s", tenant_id, exc)
    await _record_job_result("weekly_cashflow_forecast", "success", {"tenants": forecasted})


async def weekly_learning_optimization() -> None:
    """Monday: generate outreach and proposal optimization recommendations."""
    from app.services.intelligence.learning_engine import learning_engine
    optimized = 0
    for tenant_id in await _target_tenant_ids():
        try:
            await learning_engine.generate_outreach_optimization(tenant_id)
            await learning_engine.generate_proposal_optimization(tenant_id)
            optimized += 1
        except Exception as exc:
            logger.warning("Learning optimization failed for tenant %s: %s", tenant_id, exc)
    await _record_job_result("weekly_learning_optimization", "success", {"tenants": optimized})


# ── Migrated from engine.py (Task #23 Phase C) ───────────────────────────────
# Everything below was ported from the dead engine.py module per the
# migration matrix (docs/architecture/SCHEDULER_MIGRATION_MATRIX.md).

async def captain_dashboard_briefing() -> None:
    """Captain morning dashboard — 06:55 daily. Real pipeline stats via Telegram."""
    from app.core.database import AsyncSessionLocal
    from app.services.notifications.telegram_bot import notify_captain_morning_briefing

    async with AsyncSessionLocal() as db:
        await notify_captain_morning_briefing(db)
    await _record_job_result("captain_dashboard_briefing", "success", {})


async def weekly_performance_briefing() -> None:
    """Weekly Saturday 19:00 UTC — full 7-day performance summary via Telegram."""
    from app.core.database import AsyncSessionLocal
    from app.services.notifications.telegram_bot import notify_weekly_performance_briefing

    async with AsyncSessionLocal() as db:
        await notify_weekly_performance_briefing(db)
    await _record_job_result("weekly_performance_briefing", "success", {})


async def daily_self_learning() -> None:
    """Midnight UTC (00:05) — JARVIS daily self-evolution/learning cycle."""
    from app.core.database import AsyncSessionLocal
    from app.services.intelligence.jarvis_self_learning import run_daily_learning_cycle

    async with AsyncSessionLocal() as db:
        result = await run_daily_learning_cycle(db)
    await _record_job_result("daily_self_learning", "success", result)


async def drift_auditor() -> None:
    """Daily 05:30 UTC — permanent architectural rule: continuously check the
    repo and running infrastructure for duplicate config, stale files, and
    conflicting definitions before they cause an outage.
    """
    from app.services.monitoring.drift_auditor import run_drift_audit

    report = await run_drift_audit()
    await _report_drift_audit_to_headquarters(report)
    await _record_job_result("drift_auditor", "success", report)


async def _report_drift_audit_to_headquarters(report: dict) -> None:
    if not isinstance(report, dict):
        return
    actions = report.get("actions", [])
    alerts = report.get("alerts", [])
    if not actions and not alerts:
        return
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.headquarters.reporter import log_autonomous_operation

        lines = [f"Drift audit ({report.get('duration_ms', 0)}ms):"]
        if actions:
            lines.append(f"{len(actions)} auto-fix(es) applied:")
            lines += [f"  - {a}" for a in actions]
        if alerts:
            lines.append(f"{len(alerts)} issue(s) found — needs a decision, not auto-fixed:")
            lines += [f"  - {a}" for a in alerts]

        async with AsyncSessionLocal() as db:
            await log_autonomous_operation(
                db, source="drift_auditor", summary="\n".join(lines),
                details=report, had_action=True,
            )
    except Exception as exc:
        logger.warning("Drift auditor -> Headquarters reporting failed: %s", exc)

    if alerts:
        # Issues that couldn't be auto-fixed need a decision — surface them as a
        # real incident (Slack + Telegram + WebSocket), not just a Headquarters
        # chat log entry Captain has to go looking for.
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.monitoring.emergency import declare_emergency

            async with AsyncSessionLocal() as db:
                async with db.begin():
                    await declare_emergency(
                        db,
                        title="Drift auditor found issues requiring a decision",
                        severity="medium",
                        category="infrastructure",
                        description="\n".join(f"- {a}" for a in alerts),
                        affected_systems=["drift_auditor"],
                        auto_detected=True,
                    )
        except Exception as exc:
            logger.warning("Drift auditor incident creation failed: %s", exc)


async def daily_strategy_report() -> None:
    """Layer 6: Daily strategy report — collect all dept data → Council → cascade → Captain."""
    from app.services.departments.strategy_report_service import strategy_report_service

    results = []
    for tenant_id in await _target_tenant_ids():
        result = await strategy_report_service.generate_daily_strategy_report(tenant_id)
        results.append({
            "tenant_id": tenant_id,
            "score": result.get("council_score", 0),
            "directives": result.get("directives_issued", 0),
        })
    await _record_job_result("daily_strategy_report", "success", {"tenants": results})


async def weekly_strategy_review() -> None:
    """Layer 6: Full weekly strategic review with 30/60/90 day horizon — Sunday 07:00 UTC."""
    from app.services.departments.strategy_report_service import strategy_report_service

    results = []
    for tenant_id in await _target_tenant_ids():
        result = await strategy_report_service.generate_weekly_strategy_report(tenant_id)
        results.append({"tenant_id": tenant_id, "score": result.get("council_score", 0)})
    await _record_job_result("weekly_strategy_review", "success", {"tenants": results})


async def milestone_bulk_review() -> None:
    """Layer 2: Process all pending milestones through the Council Intelligence Loop — 10:00 UTC."""
    from app.services.departments.milestone_engine import milestone_engine

    results = []
    for tenant_id in await _target_tenant_ids():
        result = await milestone_engine.run_bulk_milestone_review(tenant_id)
        results.append({
            "tenant_id": tenant_id,
            "processed": result.get("processed", 0),
            "failed": result.get("failed", 0),
        })
    await _record_job_result("milestone_bulk_review", "success", {"tenants": results})


async def dio_health_check() -> None:
    """Layer 1: Ensure all Department Intelligence Officers are initialized — 06:30 UTC."""
    from app.services.departments.department_agent_service import department_agent_service

    checked = 0
    for tenant_id in await _target_tenant_ids():
        await department_agent_service.initialize_all_dios(tenant_id)
        checked += 1
    await _record_job_result("dio_health_check", "success", {"tenants_checked": checked})


async def tech_evolution_scan() -> None:
    """Layer 4: 24/7 technology discovery and evaluation cycle — every 6 hours."""
    from app.services.departments.tech_evolution_engine import tech_evolution_engine

    results = []
    for tenant_id in await _target_tenant_ids():
        result = await tech_evolution_engine.run_discovery_cycle(tenant_id)
        results.append({
            "tenant_id": tenant_id,
            "new": result.get("new_saved", 0),
            "high_priority": result.get("high_priority_count", 0),
        })
    await _record_job_result("tech_evolution_scan", "success", {"tenants": results})


async def daily_scout_network() -> None:
    """9 Scout Agents: discover leads in parallel, push to GitHub jarvis-data/ — 01:30 UTC."""
    from app.services.leads.scout_network import scout_network

    result = await scout_network.run_all_scouts()
    await _record_job_result(
        "daily_scout_network",
        "success",
        {
            "total_leads": result.get("total_leads", 0),
            "scouts": len(result.get("scout_summary", {})),
            "github_push": result.get("github_push", {}).get("github", "unknown"),
        },
    )


async def lead_embedding_sweep() -> None:
    """Nightly 03:15 UTC — semantic embedding sweep for leads without embeddings."""
    from app.core.database import AsyncSessionLocal
    from app.services.intelligence.lead_embeddings import embed_pending_leads

    async with AsyncSessionLocal() as db:
        result = await embed_pending_leads(db, limit=100)
    await _record_job_result("lead_embedding_sweep", "success", result)


async def pre_call_briefing_trigger() -> None:
    """Layer 5: Generate pre-call briefings for calls scheduled in the next 90 minutes — every 30 min."""
    from datetime import timedelta
    from sqlalchemy import and_
    from app.core.database import AsyncSessionLocal
    from app.models.department_intelligence import ClientCallIntelligence, CallStatus
    from app.services.departments.call_intelligence_service import call_intelligence_service

    now = datetime.now(UTC)
    window_end = now + timedelta(minutes=90)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ClientCallIntelligence).where(
                and_(
                    ClientCallIntelligence.scheduled_at >= now,
                    ClientCallIntelligence.scheduled_at <= window_end,
                    ClientCallIntelligence.status == CallStatus.SCHEDULED.value,
                    ClientCallIntelligence.briefing_pdf_url.is_(None),
                )
            ).limit(50)
        )
        calls = result.scalars().all()
        call_pairs = [(str(c.tenant_id), str(c.id)) for c in calls]

    generated = 0
    for tenant_id, call_id in call_pairs:
        try:
            await call_intelligence_service.generate_pre_call_briefing(tenant_id, call_id)
            generated += 1
        except Exception as exc:
            logger.warning("Pre-call briefing failed: call=%s | %s", call_id, exc)

    await _record_job_result(
        "pre_call_briefing_trigger",
        "success",
        {"briefings_generated": generated, "calls_found": len(call_pairs)},
    )


async def nexus_heartbeat() -> None:
    """
    NEXUS heartbeat — hourly. Pulses pipeline state. If action_signal is
    OUTREACH_READY and no drafts are pending, autonomously triggers AUTOPILOT
    (max 5 leads, min_score 75).

    Locking note (Task #23): this job's own 4-hour Redis lock is a
    business-logic throttle on the autonomous-outreach *action* — it is
    deliberately separate from run_registered_production_job's
    _acquire_job_lock/_release_job_lock, which only guards against this
    *job* running twice concurrently. Conflating the two would mean a
    concurrency-safety mechanism silently gained business-logic meaning
    (or vice versa) — kept distinct on purpose.
    """
    from app.core.database import AsyncSessionLocal
    from app.services.nexus.heartbeat import run_pulse
    from app.services.autopilot.pipeline import get_pending_drafts, run_autopilot_cycle

    async with AsyncSessionLocal() as db:
        pulse = await run_pulse(db)

    action = pulse.get("action_signal", "MONITOR")
    pending = await get_pending_drafts(None)

    if pending:
        try:
            from app.services.notifications.telegram_bot import notify_autopilot_drafts_pending
            await notify_autopilot_drafts_pending(pending)
        except Exception as exc:
            logger.warning("NEXUS: autopilot draft notification failed: %s", exc)

    autonomous_triggered = False
    if action == "OUTREACH_READY" and not pending:
        lock_acquired = False
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.REDIS_URL or "redis://localhost:6379")
            lock_acquired = await r.set(
                "nexus:auto_outreach:lock", "1",
                nx=True, ex=14400,  # 4-hour business-logic throttle
            )
            await r.aclose()
        except Exception as exc:
            logger.warning("NEXUS: Redis lock unavailable, skipping autonomous outreach: %s", exc)
            lock_acquired = False

        if lock_acquired:
            logger.info("NEXUS AUTONOMOUS: OUTREACH_READY — triggering AUTOPILOT (max 5 leads)")
            try:
                result = await run_autopilot_cycle(max_leads=5, min_score=75.0)
                autonomous_triggered = True
                from app.services.nexus.heartbeat import log_decision
                await log_decision({
                    "action": "auto_outreach_triggered",
                    "composed": result.get("composed", 0),
                    "source": "nexus_heartbeat",
                })
            except Exception as exc:
                logger.warning("NEXUS autonomous outreach failed: %s", exc)

    try:
        from app.api.v1.routes.ws import broadcast
        await broadcast("nexus_pulse", {
            "action_signal": pulse.get("action_signal", "MONITOR"),
            "hot_leads": pulse.get("pipeline", {}).get("hot_leads", 0),
            "pending_drafts": len(pending),
            "ai_available": pulse.get("ai_available", False),
        })
    except Exception as exc:
        logger.warning("NEXUS: WebSocket broadcast failed: %s", exc)

    await _record_job_result(
        "nexus_heartbeat",
        "success",
        {"action_signal": action, "pending_drafts": len(pending), "autonomous_triggered": autonomous_triggered},
    )


async def nightly_signal_scan() -> None:
    """Nightly 02:00 UTC — scan active pipeline leads for buying-intent
    signals, brief Captain on high signals, and auto-queue proposals for the
    highest-confidence HOT leads.

    This is the ONE proposal-generation pipeline (Task #23 architectural
    decision): overnight_proposal_engine was retired rather than migrated
    separately, because this job's auto-proposal path already uses the real
    governance/proposals system (auto_generate_proposal_for_lead, which
    creates an actual Proposal record) with proper confidence gates —
    overnight_proposal_engine only stored a memory blob and flipped lead
    status, a cruder duplicate of the same intent. Do not add a second
    proposal-drafting job; extend this one if requirements change.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.lead import Lead, LeadStatus
    from sqlalchemy import and_

    signals_found = 0
    proposals_queued = 0

    for tenant_id in await _target_tenant_ids():
        tenant_uuid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await _safe_set_tenant_context(db, tenant_uuid)
            rows = (await db.execute(
                select(Lead)
                .where(
                    and_(
                        Lead.tenant_id == tenant_uuid,
                        Lead.score >= 45,
                        Lead.status.in_([LeadStatus.NEW, LeadStatus.NURTURE, LeadStatus.CONTACTED]),
                    )
                )
                .order_by(Lead.score.desc())
                .limit(30)
            )).scalars().all()

        if not rows:
            continue

        from app.services.signal.scanner import scan_lead
        signals = []
        for lead in rows:
            try:
                lead_dict = {
                    "id": str(lead.id),
                    "company_name": lead.company_name or "",
                    "company": lead.company or "",
                    "industry": lead.industry or "",
                    "score": lead.score,
                    "status": lead.status.value if lead.status else "NEW",
                    "pain_points": lead.pain_points or "",
                    "contact_name": lead.contact_name or "",
                    "email": lead.email or "",
                    "country": lead.country or "",
                    "notes": lead.notes or "",
                    "outreach_count": lead.outreach_count or 0,
                }
                result = await scan_lead(lead_dict)
                if result.get("intent_tier") in ("HOT", "WARM"):
                    signals.append(result)
            except Exception as exc:
                logger.warning("Signal scan failed for lead %s: %s", lead.id, exc)

        signals_found += len(signals)

        if signals:
            from app.services.notifications.telegram import notify_telegram
            lines = [f"📡 *Nightly Signal Scan — {len(signals)} high-signal lead(s)*\n"]
            for s in signals[:5]:
                company = s.get("lead_company", "?")
                tier = s.get("intent_tier", "?")
                why_now = (s.get("why_now") or "")[:80]
                lines.append(f"• *{company}* [{tier}] — {why_now}")
            if len(signals) > 5:
                lines.append(f"\n_...and {len(signals) - 5} more. Review in /control-room/signal_")
            await notify_telegram("\n".join(lines))

        hot_candidates = [
            s for s in signals
            if s.get("intent_tier") == "HOT"
            and int(s.get("confidence", 0) or 0) >= 85
            and int(s.get("lead_score", 0) or 0) >= 75
        ]
        for sig in hot_candidates[:2]:
            if proposals_queued >= 2:
                break
            lead_id_str = sig.get("lead_id")
            if not lead_id_str:
                continue
            try:
                from app.services.governance.auto_proposal import auto_generate_proposal_for_lead
                lead_score = float(sig.get("lead_score", 75))
                estimated_value = max(3000.0, lead_score * 60)
                result = await auto_generate_proposal_for_lead(
                    lead_id=uuid.UUID(lead_id_str),
                    lead_name=sig.get("lead_contact") or "Decision Maker",
                    lead_email=sig.get("lead_email") or "",
                    lead_company=sig.get("lead_company") or "Unknown",
                    estimated_deal_value=estimated_value,
                    lead_context=f"HOT signal — {sig.get('why_now', '')}",
                )
                if result.get("proposal_id"):
                    proposals_queued += 1
            except Exception as exc:
                logger.warning("Auto-proposal failed for lead %s: %s", lead_id_str, exc)

    if proposals_queued:
        try:
            from app.services.notifications.telegram import notify_telegram
            await notify_telegram(
                f"📋 *Auto-Proposals Queued*\n"
                f"{proposals_queued} proposal(s) drafted for your highest-confidence HOT leads.\n"
                f"Review at /control-room/proposals"
            )
        except Exception as exc:
            logger.warning("Auto-proposal Telegram notify failed: %s", exc)

    await _record_job_result(
        "nightly_signal_scan",
        "success",
        {"signals_found": signals_found, "proposals_queued": proposals_queued},
    )
