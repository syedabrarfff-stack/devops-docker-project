"""
JARVIS Agent Scheduler — APScheduler with SQLite/PostgreSQL persistence.
Supports cron, interval, and one-shot (date) triggers.
Jobs survive restarts via job store.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from app.core.config import settings

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


def _get_db_url() -> str:
    url = settings.DATABASE_URL
    # APScheduler uses sync SQLAlchemy — strip async driver prefix
    return url.replace("+asyncpg", "").replace("+aiosqlite", "")


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        try:
            job_store = SQLAlchemyJobStore(url=_get_db_url())
            _scheduler = AsyncIOScheduler(
                jobstores={"default": job_store},
                executors={"default": AsyncIOExecutor()},
                job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
            )
        except Exception as e:
            logger.warning(f"APScheduler DB store unavailable ({e}), using memory store")
            _scheduler = AsyncIOScheduler(
                executors={"default": AsyncIOExecutor()},
                job_defaults={"coalesce": True, "max_instances": 1},
            )
    return _scheduler


async def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("✅ JARVIS Scheduler started")
        await _register_default_jobs()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


# ── Job registration helpers ──────────────────────────────────────────────────

def add_cron_job(job_id: str, func, hour: int = 8, minute: int = 0,
                  timezone_str: str = "UTC", replace: bool = True) -> None:
    scheduler = get_scheduler()
    scheduler.add_job(
        func, trigger=CronTrigger(hour=hour, minute=minute, timezone=timezone_str),
        id=job_id, replace_existing=replace, name=job_id,
    )


def add_interval_job(job_id: str, func, hours: float = 0, minutes: float = 0,
                      seconds: float = 0, replace: bool = True) -> None:
    scheduler = get_scheduler()
    scheduler.add_job(
        func, trigger=IntervalTrigger(hours=hours, minutes=minutes, seconds=seconds),
        id=job_id, replace_existing=replace, name=job_id,
    )


def add_oneshot_job(job_id: str, func, run_at: datetime, replace: bool = True) -> None:
    scheduler = get_scheduler()
    scheduler.add_job(
        func, trigger=DateTrigger(run_date=run_at),
        id=job_id, replace_existing=replace, name=job_id,
    )


def remove_job(job_id: str) -> bool:
    try:
        get_scheduler().remove_job(job_id)
        return True
    except Exception:
        return False


def get_jobs() -> list[dict]:
    scheduler = get_scheduler()
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run.isoformat() if next_run else None,
            "trigger": str(job.trigger),
        })
    return jobs


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


# ── Default JARVIS jobs ───────────────────────────────────────────────────────

async def _register_default_jobs() -> None:
    """Register built-in JARVIS scheduled tasks."""

    # Daily morning briefing via Telegram (8 AM UTC)
    add_cron_job("daily_briefing", _job_morning_briefing, hour=8, minute=0)

    # Lead scoring sweep every 6 hours
    add_interval_job("lead_scoring_sweep", _job_score_leads, hours=6)

    # Outreach processing every hour
    add_interval_job("outreach_processor", _job_process_outreach, hours=1)

    # Contact sync every 12 hours
    add_interval_job("contact_sync", _job_sync_contacts, hours=12)

    # Revenue engine: discover, score, draft, and prepare approval packets.
    # Client-facing sends are never automatic.
    add_cron_job("overnight_revenue_engine", _job_revenue_engine, hour=18, minute=0)

    # Defensive read-only production scan every 30 minutes.
    add_interval_job("defensive_production_scan", _job_defensive_scan, minutes=30)

    # Phase 5 — Intelligence jobs
    # Weekly tech radar scan (Monday 06:00 UTC)
    add_cron_job("weekly_tech_radar_scan", _job_tech_radar_scan, hour=6, minute=0)

    # Daily self-optimization review (23:00 UTC)
    add_cron_job("daily_optimization_review", _job_optimization_review, hour=23, minute=0)

    # Bi-weekly research report (Sunday 07:00 UTC)
    add_cron_job("biweekly_research_report", _job_research_report, hour=7, minute=0)

    logger.info("✅ Default JARVIS jobs registered")


async def _job_morning_briefing() -> None:
    logger.info("Scheduler: running morning briefing")
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            from app.services.notifications.telegram_bot import _handle_briefing
            from app.core.config import settings
            await _handle_briefing(str(settings.TELEGRAM_CHAT_ID or ""), db)
    except Exception as e:
        logger.warning(f"Morning briefing job failed: {e}")


async def _job_score_leads() -> None:
    logger.info("Scheduler: running lead scoring sweep")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.leads.engine import bulk_score
        async with AsyncSessionLocal() as db:
            async with db.begin():
                count = await bulk_score(db, limit=20)
        logger.info(f"Lead scoring: {count} leads processed")
    except Exception as e:
        logger.warning(f"Lead scoring job failed: {e}")


async def _job_process_outreach() -> None:
    logger.info("Scheduler: checking due outreach emails for approval safety")
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models.approval import ApprovalRequest
        from app.models.outreach import OutreachEmail
        from datetime import datetime, timezone
        async with AsyncSessionLocal() as db:
            async with db.begin():
                now = datetime.now(timezone.utc)
                due = (await db.execute(
                    select(OutreachEmail)
                    .where(OutreachEmail.status == "scheduled")
                    .where(OutreachEmail.scheduled_at <= now)
                    .limit(10)
                )).scalars().all()
                for email in due:
                    email.status = "draft"
                if due:
                    db.add(ApprovalRequest(
                        title="Review scheduled outreach before sending",
                        action_type="revenue_outreach_batch",
                        summary=f"{len(due)} scheduled outreach emails are due. JARVIS moved them to drafts for Captain review.",
                        risk_level="medium",
                        benefits="Keeps outreach moving without sending unreviewed client messages.",
                        risks="Emails will not send until Captain approves and executes the batch.",
                        rollback_plan="Reject the approval or delete the draft emails.",
                        payload={"email_ids": [e.id for e in due], "source": "outreach_processor"},
                    ))
        logger.info(f"Outreach: {len(due)} due emails moved to approval drafts")
    except Exception as e:
        logger.warning(f"Outreach job failed: {e}")


async def _job_sync_contacts() -> None:
    logger.info("Scheduler: syncing contacts")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.contacts.sync import sync_from_apollo
        async with AsyncSessionLocal() as db:
            async with db.begin():
                count = await sync_from_apollo(db, limit=50)
        logger.info(f"Contact sync: {count} synced")
    except Exception as e:
        logger.warning(f"Contact sync job failed: {e}")


async def _job_revenue_engine() -> None:
    logger.info("Scheduler: running overnight revenue engine")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.revenue.engine import run_revenue_engine
        async with AsyncSessionLocal() as db:
            async with db.begin():
                result = await run_revenue_engine(db, limit=25)
        logger.info(f"Revenue engine result: {result}")
    except Exception as e:
        logger.warning(f"Revenue engine job failed: {e}")


async def _job_defensive_scan() -> None:
    logger.info("Scheduler: running defensive production scan")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.monitoring.defense import run_defense_scan

        async with AsyncSessionLocal() as db:
            async with db.begin():
                result = await run_defense_scan(db, create_notification=True)
        logger.info(f"Defensive scan threat level: {result.get('threat_level')}")
    except Exception as e:
        logger.warning(f"Defensive scan failed: {e}")


# ── Phase 5 — Intelligence jobs ───────────────────────────────────────────────

async def _job_tech_radar_scan() -> None:
    logger.info("Scheduler: running weekly tech radar scan")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.tech_radar import scan_technologies
        async with AsyncSessionLocal() as db:
            async with db.begin():
                count = await scan_technologies(db)
        logger.info(f"Tech radar: {count} entries updated")
    except Exception as e:
        logger.warning(f"Tech radar scan failed: {e}")


async def _job_optimization_review() -> None:
    logger.info("Scheduler: running daily optimization review")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.optimizer import analyze_system
        async with AsyncSessionLocal() as db:
            async with db.begin():
                count = await analyze_system(db)
        logger.info(f"Optimization review: {count} recommendations generated")
    except Exception as e:
        logger.warning(f"Optimization review failed: {e}")


async def _job_research_report() -> None:
    logger.info("Scheduler: generating bi-weekly research report")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.research import generate_default_reports
        async with AsyncSessionLocal() as db:
            async with db.begin():
                count = await generate_default_reports(db)
        logger.info(f"Research reports: {count} generated")
    except Exception as e:
        logger.warning(f"Research report generation failed: {e}")
