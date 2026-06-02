from __future__ import annotations

import logging
import pickle
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

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
    {"query": "SaaS operations automation", "industry": "SaaS", "country": "UK", "location": "London UK", "limit": 4},
    {"query": "ecommerce workflow automation", "industry": "E-commerce", "country": "USA", "location": "Austin TX", "limit": 4},
    {"query": "agency CRM automation", "industry": "Agency", "country": "Australia", "location": "Sydney Australia", "limit": 4},
    {"query": "hotel guest communication automation", "industry": "Hospitality", "country": "UAE", "location": "Dubai UAE", "limit": 4},
    {"query": "logistics dispatch automation", "industry": "Logistics", "country": "Canada", "location": "Toronto Canada", "limit": 4},
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
    "daily_memory_consolidate",
    "daily_optimization_review",
    "weekly_outreach_stats",
    "weekly_pipeline_health",
    "weekly_tech_radar",
    "biweekly_research_report",
    "monthly_weight_adjust",
)


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
                        f"ALTER TABLE {self.jobs_t.name} "
                        f"ADD COLUMN tenant_id {column_type} NOT NULL DEFAULT '{default_tenant}'"
                    )
                )
                connection.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{self.jobs_t.name}_tenant_id ON {self.jobs_t.name} (tenant_id)"))
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
        register_production_jobs()
        try:
            await _sync_job_metadata()
        except Exception as exc:
            logger.warning("Scheduler metadata sync skipped: %s", exc)
        logger.info("JARVIS production scheduler started")


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("JARVIS production scheduler stopped")


def register_production_jobs() -> None:
    _remove_deprecated_jobs()
    existing_job_ids = {job.id for job in get_scheduler().get_jobs()}
    specs = _production_job_specs()
    seeded = 0

    for spec in specs:
        if spec["job_id"] in existing_job_ids:
            continue
        add_cron_job(**spec, replace=False)
        seeded += 1

    loaded = len(PRODUCTION_JOB_IDS) - seeded
    logger.info(
        "JARVIS production scheduler ready: %s jobs loaded from persistent store, %s missing jobs seeded",
        loaded,
        seeded,
    )


def _production_job_specs() -> list[dict[str, Any]]:
    return [
        {"job_id": "daily_morning_briefing", "func": daily_morning_briefing, "hour": 1, "minute": 30},
        {"job_id": "daily_lead_scoring", "func": daily_lead_scoring, "hour": 20, "minute": 30},
        {"job_id": "daily_lead_discovery", "func": daily_lead_discovery, "hour": 22, "minute": 0},
        {"job_id": "daily_follow_up_check", "func": daily_follow_up_check, "hour": 4, "minute": 30},
        {"job_id": "daily_memory_consolidate", "func": daily_memory_consolidate, "hour": 19, "minute": 0},
        {"job_id": "daily_optimization_review", "func": daily_optimization_review, "hour": 17, "minute": 30},
        {"job_id": "weekly_outreach_stats", "func": weekly_outreach_stats, "hour": 2, "minute": 30, "day_of_week": "mon"},
        {"job_id": "weekly_pipeline_health", "func": weekly_pipeline_health, "hour": 14, "minute": 30, "day_of_week": "sun"},
        {"job_id": "weekly_tech_radar", "func": weekly_tech_radar, "hour": 0, "minute": 30, "day_of_week": "mon"},
        {"job_id": "biweekly_research_report", "func": biweekly_research_report, "hour": 1, "minute": 30, "day_of_week": "sun"},
        {"job_id": "monthly_weight_adjust", "func": monthly_weight_adjust, "hour": 18, "minute": 30, "day": "last"},
    ]


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


async def enqueue_scheduled_task(job_id: str, tenant_id: str | None = None) -> None:
    from app.core.database import AsyncSessionLocal, set_tenant_context
    from app.models.scheduling import ScheduledJob
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

    discovered = 0
    for tenant_id in await _target_tenant_ids():
        discovered += await lead_discovery_engine.run_daily_discovery(tenant_id, DAILY_DISCOVERY_TARGETS)
    await _record_job_result("daily_lead_discovery", "success", {"discovered": discovered})


async def daily_follow_up_check() -> None:
    from app.services.outreach.engine import outreach_engine

    sent = 0
    for tenant_id in await _target_tenant_ids():
        sent += await outreach_engine.execute_due_outreach(tenant_id, limit=25)
    await _record_job_result("daily_follow_up_check", "success", {"sent": sent})


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


async def _sync_job_metadata() -> None:
    from app.core.database import AsyncSessionLocal
    from app.models.scheduling import ScheduledJob

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
                    existing.next_run_at = job.next_run_time
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
                            next_run_at=job.next_run_time,
                        )
                    )


async def _record_job_result(job_id: str, status: str, payload: dict) -> None:
    from app.core.database import AsyncSessionLocal
    from app.models.approval import AuditLog
    from app.models.scheduling import ScheduledJob

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
                job.last_run_at = datetime.now(UTC)
                job.last_status = status
                job.run_count = int(job.run_count or 0) + 1
                aps_job = get_scheduler().get_job(job_id)
                job.next_run_at = aps_job.next_run_time if aps_job else None
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


def _sync_database_url() -> str:
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
    if url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return url


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


def _task_type_for_job(job_id: str) -> str:
    if "lead" in job_id:
        return "lead_ops"
    if "outreach" in job_id or "follow_up" in job_id:
        return "outreach"
    if "memory" in job_id:
        return "memory"
    if "briefing" in job_id:
        return "briefing"
    if "radar" in job_id or "research" in job_id or "optimization" in job_id:
        return "intelligence"
    if "weight" in job_id:
        return "ai_council"
    return "system"


def _format_stats_summary(rows: list[dict]) -> str:
    if not rows:
        return "No active tenants found."
    return "\n".join(
        f"Tenant {row['tenant_id']}: sent={row.get('sent_outreach', 0)}, pending={row.get('pending_followups', 0)}, "
        f"executed={row.get('executed_followups', 0)}, failed={row.get('failed_followups', 0)}"
        for row in rows
    )
