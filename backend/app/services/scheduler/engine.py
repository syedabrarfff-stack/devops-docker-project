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
    logger.info("Scheduler: processing due outreach emails")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.outreach.gmail import send_outreach_email
        from sqlalchemy import select
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
                sent = 0
                for email in due:
                    try:
                        ok = await send_outreach_email(db, email.id)
                        if ok:
                            sent += 1
                    except Exception:
                        pass
        logger.info(f"Outreach: {sent}/{len(due)} emails sent")
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
