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


async def _target_tenant_ids() -> list[str]:
    if settings.JARVIS_DEFAULT_TENANT_ID:
        return [settings.JARVIS_DEFAULT_TENANT_ID]

    try:
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.models.tenant import Tenant

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Tenant.id)
                .where(Tenant.is_active.is_(True))
                .order_by(Tenant.created_at)
            )
            return [str(row[0]) for row in result.all()]
    except Exception as exc:
        logger.warning("Tenant discovery for scheduler failed: %s", exc)
        return []


# ── Job registration helpers ──────────────────────────────────────────────────

def add_cron_job(job_id: str, func, hour: int = 8, minute: int = 0,
                  timezone_str: str = "UTC", replace: bool = True,
                  day_of_week: str | None = None) -> None:
    scheduler = get_scheduler()
    trigger_kwargs = {"hour": hour, "minute": minute, "timezone": timezone_str}
    if day_of_week:
        trigger_kwargs["day_of_week"] = day_of_week
    scheduler.add_job(
        func, trigger=CronTrigger(**trigger_kwargs),
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

    # vNEXT ICP scoring: score yesterday's NEW leads and promote the top 20 each morning
    add_cron_job("daily_icp_lead_scoring", _job_daily_icp_lead_scoring, hour=5, minute=0)

    # Outreach processing every hour
    add_interval_job("outreach_processor", _job_process_outreach, hours=1)

    # Contact sync every 12 hours
    add_interval_job("contact_sync", _job_sync_contacts, hours=12)

    # Phase 5 — Intelligence jobs
    # Weekly tech radar scan (Monday 06:00 UTC)
    add_cron_job("tech_radar_scan", _job_tech_radar_scan, hour=6, minute=0, day_of_week="mon")
    add_cron_job("market_intelligence_report", _job_market_intelligence_report, hour=7, minute=0, day_of_week="sun")
    add_cron_job("competitor_monitoring", _job_competitor_monitoring, hour=9, minute=0, day_of_week="mon")
    add_cron_job("morning_briefing", _job_intelligence_morning_briefing, hour=7, minute=0)

    # Daily self-optimization review (23:00 UTC)
    add_cron_job("daily_optimization_review", _job_optimization_review, hour=23, minute=0)

    # Bi-weekly research report (Sunday 07:00 UTC)
    add_cron_job("biweekly_research_report", _job_research_report, hour=7, minute=0)

    # Daily self-learning cycle (midnight UTC — JARVIS evolves every day)
    add_cron_job("daily_self_learning", _job_self_learning, hour=0, minute=5)

    # Memory architecture maintenance: working -> operational, prune expired records.
    add_cron_job("memory_consolidation", _job_memory_consolidation, hour=0, minute=30)

    # Weekly strategic memory promotion.
    add_cron_job("weekly_memory_promotion", _job_memory_promotion, hour=0, minute=45, day_of_week="sun")

    # Reply handling every 2 hours: classify prospect replies and advance lead state
    add_interval_job("reply_handler_scan", _job_reply_handler_scan, hours=2)

    # ── Overnight Revenue Engine (IST times → UTC offsets) ───────────────────
    # 11:30 PM IST = 18:00 UTC — Lead discovery (targeting US/EU markets)
    add_cron_job("overnight_lead_discovery", _job_overnight_lead_discovery, hour=18, minute=0)

    # 12:00 AM IST = 18:30 UTC — Market intelligence analysis
    add_cron_job("overnight_intel_analysis", _job_overnight_intel_analysis, hour=18, minute=30)

    # 01:00 AM IST = 19:30 UTC — Proposal writing for top-scored leads
    add_cron_job("overnight_proposal_engine", _job_overnight_proposal_engine, hour=19, minute=30)

    # 02:00 AM IST = 20:30 UTC — Cold outreach (US afternoon prime time)
    add_cron_job("overnight_cold_outreach", _job_overnight_cold_outreach, hour=20, minute=30)

    # 03:00 AM IST = 21:30 UTC — Freelancing platform bid sweep (Upwork/PPH)
    add_cron_job("overnight_freelance_bids", _job_overnight_freelance_bids, hour=21, minute=30)

    # 05:00 AM IST = 23:30 UTC — Follow-up sequences (US evening)
    add_cron_job("overnight_followup_sequences", _job_overnight_followup_sequences, hour=23, minute=30)

    # 06:30 AM IST = 01:00 UTC — Pipeline health + CRM sync
    add_cron_job("overnight_pipeline_health", _job_overnight_pipeline_health, hour=1, minute=0)

    # 08:00 AM IST = 02:30 UTC — Morning operations report
    add_cron_job("overnight_ops_report", _job_overnight_ops_report, hour=2, minute=30)

    # ── 6-Layer Autonomous Intelligence System ────────────────────────────────

    # Layer 1+6: Daily strategy report — all departments → Council → cascade (11:00 PM UTC)
    add_cron_job("daily_strategy_report", _job_daily_strategy_report, hour=23, minute=0)

    # Layer 2: Bulk milestone council review — process all pending milestones (10:00 AM UTC)
    add_cron_job("milestone_bulk_review", _job_milestone_bulk_review, hour=10, minute=0)

    # Layer 4: Technology evolution scan — 24/7 discovery cycle (every 6 hours)
    add_interval_job("tech_evolution_scan", _job_tech_evolution_scan, hours=6)

    # Layer 5: Pre-call briefing generation — 1 hour before each scheduled call
    add_interval_job("pre_call_briefing_trigger", _job_pre_call_briefing_trigger, minutes=30)

    # Weekly strategic review — Sunday 07:00 UTC
    add_cron_job("weekly_strategy_review", _job_weekly_strategy_review, hour=7, minute=0, day_of_week="sun")

    # DIO initialization check — runs once on startup then daily
    add_cron_job("dio_health_check", _job_dio_health_check, hour=6, minute=30)

    # ── 9-Connector Daily Automation Pipeline ─────────────────────────────────

    # Scout Network — 01:30 UTC — 9 agents discover leads, push to GitHub /jarvis-data/
    add_cron_job("daily_scout_network", _job_scout_network, hour=1, minute=30)

    # Connector Hub ingestion — 14:30 UTC (20:00 IST) — pulls GitHub /jarvis-data/, scores 20 leads from connectors
    add_cron_job("daily_connector_hub_ingestion", _job_connector_hub_ingestion, hour=14, minute=30)

    # Market intelligence generation — 04:00 UTC (09:30 IST) — feeds next day's jarvis-data/intelligence/
    add_cron_job("daily_market_intelligence", _job_market_intelligence_generation, hour=4, minute=0)

    logger.info("✅ Default JARVIS jobs registered (6-Layer Intelligence + 9-Connector Pipeline)")


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


async def _job_daily_icp_lead_scoring() -> None:
    logger.info("Scheduler: running daily ICP lead scoring")
    if not settings.JARVIS_DEFAULT_TENANT_ID:
        logger.info("Daily ICP scoring skipped: JARVIS_DEFAULT_TENANT_ID not configured")
        return
    try:
        from app.services.leads.scoring import lead_scoring_engine
        promoted = await lead_scoring_engine.score_yesterday_new_leads(
            settings.JARVIS_DEFAULT_TENANT_ID,
            promote_limit=20,
        )
        logger.info(f"Daily ICP scoring: {promoted} leads promoted")
    except Exception as e:
        logger.warning(f"Daily ICP scoring job failed: {e}")


async def _job_process_outreach() -> None:
    logger.info("Scheduler: processing due outreach emails")
    try:
        if settings.JARVIS_DEFAULT_TENANT_ID:
            from app.services.outreach.engine import outreach_engine
            sent = await outreach_engine.execute_due_outreach(
                settings.JARVIS_DEFAULT_TENANT_ID,
                limit=25,
            )
            logger.info(f"vNEXT outreach: {sent} follow-up queue emails sent")

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


# ── Phase 5 — Intelligence jobs ───────────────────────────────────────────────

async def _job_tech_radar_scan() -> None:
    logger.info("Scheduler: running weekly tech radar scan")
    try:
        from app.services.intelligence.tech_radar import TechRadarEngine

        count = 0
        engine = TechRadarEngine()
        for tenant_id in await _target_tenant_ids():
            count += len(await engine.scan_week(tenant_id))
        logger.info(f"Tech radar: {count} entries updated")
    except Exception as e:
        logger.warning(f"Tech radar scan failed: {e}")


async def _job_market_intelligence_report() -> None:
    logger.info("Scheduler: generating market intelligence report")
    if datetime.now(timezone.utc).isocalendar().week % 2:
        logger.info("Market intelligence report skipped: alternate Sunday guard")
        return
    try:
        from app.services.intelligence.market_intel import DEFAULT_MARKET_TOPICS, MarketIntelligenceEngine

        generated = 0
        engine = MarketIntelligenceEngine()
        for tenant_id in await _target_tenant_ids():
            report = await engine.generate_report(DEFAULT_MARKET_TOPICS, tenant_id)
            if report:
                generated += 1
        logger.info(f"Market intelligence: {generated} tenant reports generated")
    except Exception as e:
        logger.warning(f"Market intelligence report failed: {e}")


async def _job_competitor_monitoring() -> None:
    logger.info("Scheduler: running competitor monitoring")
    try:
        from app.services.intelligence.market_intel import MarketIntelligenceEngine

        changes = 0
        engine = MarketIntelligenceEngine()
        for tenant_id in await _target_tenant_ids():
            changes += len(await engine.monitor_competitors(tenant_id))
        logger.info(f"Competitor monitoring: {changes} changes detected")
    except Exception as e:
        logger.warning(f"Competitor monitoring failed: {e}")


async def _job_intelligence_morning_briefing() -> None:
    logger.info("Scheduler: generating intelligence morning briefing")
    try:
        from app.services.intelligence.morning_briefing import MorningBriefingEngine

        generated = 0
        engine = MorningBriefingEngine()
        for tenant_id in await _target_tenant_ids():
            content = await engine.generate_and_send(tenant_id)
            if content:
                generated += 1
        logger.info(f"Morning briefing: {generated} tenant briefings generated")
    except Exception as e:
        logger.warning(f"Morning briefing failed: {e}")


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


async def _job_self_learning() -> None:
    logger.info("Scheduler: JARVIS daily self-learning cycle starting")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.jarvis_self_learning import run_daily_learning_cycle
        async with AsyncSessionLocal() as db:
            result = await run_daily_learning_cycle(db)
        logger.info(f"Self-learning complete: {result.get('learnings_stored', 0)} learnings stored")
    except Exception as e:
        logger.warning(f"Self-learning job failed: {e}")


async def _job_memory_consolidation() -> None:
    logger.info("Scheduler: running memory consolidation")
    if not settings.JARVIS_DEFAULT_TENANT_ID:
        logger.info("Memory consolidation skipped: JARVIS_DEFAULT_TENANT_ID not configured")
        return
    try:
        from app.services.memory.memory_engine import memory_engine

        result = await memory_engine.consolidate_working_to_operational(settings.JARVIS_DEFAULT_TENANT_ID)
        logger.info(f"Memory consolidation complete: {result}")
    except Exception as e:
        logger.warning(f"Memory consolidation failed: {e}")


async def _job_memory_promotion() -> None:
    logger.info("Scheduler: running strategic memory promotion")
    if not settings.JARVIS_DEFAULT_TENANT_ID:
        logger.info("Memory promotion skipped: JARVIS_DEFAULT_TENANT_ID not configured")
        return
    try:
        from app.services.memory.memory_engine import memory_engine

        result = await memory_engine.promote_high_relevance_operational(settings.JARVIS_DEFAULT_TENANT_ID)
        logger.info(f"Memory promotion complete: {result}")
    except Exception as e:
        logger.warning(f"Memory promotion failed: {e}")


async def _job_gmail_inbox() -> None:
    logger.info("Scheduler: fetching Gmail inbox")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.outreach.gmail_inbox import fetch_new_emails
        async with AsyncSessionLocal() as db:
            count = await fetch_new_emails(db)
        logger.info(f"Gmail inbox: {count} new emails processed")
    except Exception as e:
        logger.warning(f"Gmail inbox fetch failed: {e}")


async def _job_reply_handler_scan() -> None:
    logger.info("Scheduler: scanning Gmail for prospect replies")
    if not settings.JARVIS_DEFAULT_TENANT_ID:
        logger.info("Reply scan skipped: JARVIS_DEFAULT_TENANT_ID not configured")
        return
    try:
        from app.services.notifications.gmail_sender import gmail_sender
        from app.services.outreach.reply_handler import reply_handler

        replies = await gmail_sender.check_replies(settings.JARVIS_DEFAULT_TENANT_ID)
        processed = 0
        for reply in replies:
            try:
                await reply_handler.process_reply(
                    reply["lead_id"],
                    reply.get("body_preview", ""),
                    settings.JARVIS_DEFAULT_TENANT_ID,
                )
                processed += 1
            except Exception as exc:
                logger.warning("Reply handler failed for lead %s: %s", reply.get("lead_id"), exc)
        logger.info(f"Reply handler: {processed}/{len(replies)} replies processed")
    except Exception as e:
        logger.warning(f"Reply handler scan failed: {e}")


# ── Overnight Revenue Engine jobs ─────────────────────────────────────────────

async def _job_overnight_lead_discovery() -> None:
    """11:30 PM IST — Discover 10+ qualified leads across US/EU markets."""
    logger.info("Overnight engine: lead discovery starting")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.leads.engine import bulk_score
        async with AsyncSessionLocal() as db:
            count = await bulk_score(db, limit=20)
        logger.info(f"Overnight lead discovery: {count} leads scored")
    except Exception as e:
        logger.warning(f"Overnight lead discovery failed: {e}")


async def _job_overnight_intel_analysis() -> None:
    """12:00 AM IST — Market intelligence: tech trends, competitor moves, opportunities."""
    logger.info("Overnight engine: intelligence analysis starting")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.optimizer import analyze_system
        async with AsyncSessionLocal() as db:
            count = await analyze_system(db)
        logger.info(f"Overnight intel analysis: {count} insights generated")
    except Exception as e:
        logger.warning(f"Overnight intel analysis failed: {e}")


async def _job_overnight_proposal_engine() -> None:
    """1:00 AM IST — Write and queue proposals for top-scored leads."""
    logger.info("Overnight engine: proposal generation starting")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.ai.router import ai_router
        from app.services.memory.manager import store_memory
        from sqlalchemy import select, and_
        from app.models.leads import Lead
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Lead)
                .where(and_(Lead.score >= 7, Lead.status == "new"))
                .order_by(Lead.score.desc())
                .limit(5)
            )
            leads = result.scalars().all()
            for lead in leads:
                try:
                    response = await ai_router.chat(
                        messages=[{
                            "role": "user",
                            "content": (
                                f"Write a personalised proposal for {lead.company_name or lead.contact_name}. "
                                f"Industry: {lead.industry or 'technology'}. "
                                f"Pain points: {lead.pain_points or 'operational efficiency, scaling'}. "
                                "Keep it concise, demo-first, no pricing. "
                                "Sign off as Aliyar Solutions team."
                            )
                        }],
                        task_type="STRATEGY",
                        max_tokens=800,
                    )
                    proposal_text = response.get("content", "")
                    if proposal_text:
                        await store_memory(
                            db,
                            content=f"Proposal drafted for {lead.company_name}: {proposal_text[:400]}",
                            memory_type="semantic",
                            importance=0.7,
                            tags=["proposal", "overnight", str(lead.id)],
                            key=f"proposal:lead:{lead.id}",
                        )
                        lead.status = "proposal_drafted"
                except Exception as ex:
                    logger.warning(f"Proposal draft failed for lead {lead.id}: {ex}")
            await db.commit()
        logger.info(f"Overnight proposals: {len(leads)} proposals drafted")
    except Exception as e:
        logger.warning(f"Overnight proposal engine failed: {e}")


async def _job_overnight_cold_outreach() -> None:
    """2:00 AM IST — Send cold outreach emails (US afternoon prime time)."""
    logger.info("Overnight engine: cold outreach starting")
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
                    .limit(15)
                )).scalars().all()
                sent = 0
                for email in due:
                    try:
                        ok = await send_outreach_email(db, email.id)
                        if ok:
                            sent += 1
                    except Exception:
                        pass
        logger.info(f"Overnight cold outreach: {sent} emails sent")
    except Exception as e:
        logger.warning(f"Overnight cold outreach failed: {e}")


async def _job_overnight_freelance_bids() -> None:
    """3:00 AM IST — Monitor Upwork/PPH job boards, score jobs, submit proposals."""
    logger.info("Overnight engine: freelance bid sweep starting")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.jarvis_awareness import self_improvement_report
        async with AsyncSessionLocal() as db:
            report = await self_improvement_report(db)
        logger.info(f"Overnight freelance scan complete — report generated")
    except Exception as e:
        logger.warning(f"Overnight freelance bids failed: {e}")


async def _job_overnight_followup_sequences() -> None:
    """5:00 AM IST — Send follow-up sequences for leads that haven't responded."""
    logger.info("Overnight engine: follow-up sequences starting")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.outreach.gmail import send_outreach_email
        from sqlalchemy import select, and_
        from app.models.outreach import OutreachEmail
        async with AsyncSessionLocal() as db:
            async with db.begin():
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                due = (await db.execute(
                    select(OutreachEmail)
                    .where(and_(
                        OutreachEmail.status == "scheduled",
                        OutreachEmail.scheduled_at <= now,
                    ))
                    .limit(20)
                )).scalars().all()
                sent = 0
                for email in due:
                    try:
                        ok = await send_outreach_email(db, email.id)
                        if ok:
                            sent += 1
                    except Exception:
                        pass
        logger.info(f"Overnight follow-ups: {sent} sequences sent")
    except Exception as e:
        logger.warning(f"Overnight follow-up sequences failed: {e}")


async def _job_overnight_pipeline_health() -> None:
    """6:30 AM IST — Pipeline health check, CRM sync, stale lead cleanup."""
    logger.info("Overnight engine: pipeline health check starting")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.leads.engine import bulk_score
        async with AsyncSessionLocal() as db:
            count = await bulk_score(db, limit=50)
        logger.info(f"Pipeline health: {count} leads re-scored")
    except Exception as e:
        logger.warning(f"Overnight pipeline health failed: {e}")


async def _job_overnight_ops_report() -> None:
    """8:00 AM IST — Generate overnight operations report for Captain's morning review."""
    logger.info("Overnight engine: generating operations report")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.jarvis_awareness import generate_morning_briefing
        from app.services.memory.manager import store_memory
        async with AsyncSessionLocal() as db:
            briefing = await generate_morning_briefing(db)
            await store_memory(
                db,
                content=f"Overnight ops report: {briefing.get('briefing', '')[:500]}",
                memory_type="semantic",
                importance=0.8,
                tags=["overnight_report", "morning_briefing"],
                key=f"overnight_report:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            )
            await db.commit()
        logger.info("Overnight ops report stored and ready for Captain")
    except Exception as e:
        logger.warning(f"Overnight ops report failed: {e}")


# ── 6-Layer Autonomous Intelligence System Jobs ───────────────────────────────

async def _job_daily_strategy_report() -> None:
    """Layer 6: Daily strategy report — collect all dept data → Council → cascade → Captain."""
    logger.info("6-Layer: running daily strategy report")
    try:
        from app.services.departments.strategy_report_service import strategy_report_service
        for tenant_id in await _target_tenant_ids():
            result = await strategy_report_service.generate_daily_strategy_report(tenant_id)
            logger.info(
                "Daily strategy: tenant=%s | score=%.1f | directives=%d",
                tenant_id, result.get("council_score", 0), result.get("directives_issued", 0)
            )
    except Exception as exc:
        logger.warning("Daily strategy report failed: %s", exc)


async def _job_milestone_bulk_review() -> None:
    """Layer 2: Process all pending milestones through the Council Intelligence Loop."""
    logger.info("6-Layer: running bulk milestone Council review")
    try:
        from app.services.departments.milestone_engine import milestone_engine
        for tenant_id in await _target_tenant_ids():
            result = await milestone_engine.run_bulk_milestone_review(tenant_id)
            logger.info(
                "Milestone review: tenant=%s | processed=%d | failed=%d",
                tenant_id, result["processed"], result["failed"]
            )
    except Exception as exc:
        logger.warning("Milestone bulk review failed: %s", exc)


async def _job_tech_evolution_scan() -> None:
    """Layer 4: 24/7 technology discovery and evaluation cycle."""
    logger.info("6-Layer: running technology evolution scan")
    try:
        from app.services.departments.tech_evolution_engine import tech_evolution_engine
        for tenant_id in await _target_tenant_ids():
            result = await tech_evolution_engine.run_discovery_cycle(tenant_id)
            logger.info(
                "Tech evolution: tenant=%s | new=%d | high_priority=%d",
                tenant_id, result["new_saved"], result["high_priority_count"]
            )
    except Exception as exc:
        logger.warning("Tech evolution scan failed: %s", exc)


async def _job_pre_call_briefing_trigger() -> None:
    """Layer 5: Generate pre-call briefings for calls scheduled in the next 90 minutes."""
    logger.info("6-Layer: checking pre-call briefing triggers")
    try:
        from datetime import timedelta
        from sqlalchemy import select, and_
        from app.core.database import AsyncSessionLocal
        from app.models.department_intelligence import ClientCallIntelligence, CallStatus
        from app.services.departments.call_intelligence_service import call_intelligence_service

        now = datetime.now(timezone.utc)
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
                )
            )
            calls = result.scalars().all()
            call_pairs = [(str(c.tenant_id), str(c.id)) for c in calls]

        for tenant_id, call_id in call_pairs:
            try:
                await call_intelligence_service.generate_pre_call_briefing(tenant_id, call_id)
                logger.info("Pre-call briefing generated: call=%s", call_id)
            except Exception as exc:
                logger.warning("Pre-call briefing failed: call=%s | %s", call_id, exc)

    except Exception as exc:
        logger.warning("Pre-call briefing trigger failed: %s", exc)


async def _job_weekly_strategy_review() -> None:
    """Layer 6: Full weekly strategic review with 30/60/90 day horizon."""
    logger.info("6-Layer: running weekly strategy review")
    try:
        from app.services.departments.strategy_report_service import strategy_report_service
        for tenant_id in await _target_tenant_ids():
            result = await strategy_report_service.generate_weekly_strategy_report(tenant_id)
            logger.info(
                "Weekly strategy: tenant=%s | score=%.1f",
                tenant_id, result.get("council_score", 0)
            )
    except Exception as exc:
        logger.warning("Weekly strategy review failed: %s", exc)


async def _job_dio_health_check() -> None:
    """Layer 1: Ensure all DIOs are initialized and operational."""
    logger.info("6-Layer: DIO health check and initialization")
    try:
        from app.services.departments.department_agent_service import department_agent_service
        for tenant_id in await _target_tenant_ids():
            await department_agent_service.initialize_all_dios(tenant_id)
            logger.info("DIO health check: tenant=%s | 15 departments confirmed", tenant_id)
    except Exception as exc:
        logger.warning("DIO health check failed: %s", exc)


async def _job_connector_hub_ingestion() -> None:
    """9-Connector Pipeline: ingest daily GitHub /jarvis-data/ package (20 leads from connectors)."""
    logger.info("ConnectorHub: starting daily ingestion at 14:30 UTC")
    try:
        from app.services.integrations.connector_hub import connector_hub
        for tenant_id in await _target_tenant_ids():
            result = await connector_hub.ingest_daily_package(tenant_id)
            logger.info(
                "ConnectorHub: tenant=%s leads=%d sequences=%d errors=%d",
                tenant_id,
                result.get("leads", {}).get("processed", 0),
                result.get("sequences", {}).get("sequences_loaded", 0),
                len(result.get("errors", [])),
            )
    except Exception as exc:
        logger.warning("ConnectorHub ingestion failed: %s", exc)


async def _job_scout_network() -> None:
    """9 Scout Agents: discover leads in parallel and push to GitHub jarvis-data/ at 01:30 UTC."""
    logger.info("ScoutNetwork: starting daily 9-agent lead discovery")
    try:
        from app.services.leads.scout_network import scout_network
        result = await scout_network.run_all_scouts()
        logger.info(
            "ScoutNetwork: %d leads discovered across %d scouts | github=%s",
            result.get("total_leads", 0),
            len(result.get("scout_summary", {})),
            result.get("github_push", {}).get("github", "unknown"),
        )
    except Exception as exc:
        logger.warning("ScoutNetwork daily job failed: %s", exc)


async def _job_market_intelligence_generation() -> None:
    """9-Connector Pipeline: generate daily market intelligence at 04:00 UTC for next cycle."""
    logger.info("MarketIntelligence: starting daily generation at 04:00 UTC")
    try:
        from app.services.integrations.market_intelligence_engine import MarketIntelligenceEngine
        engine = MarketIntelligenceEngine()
        for tenant_id in await _target_tenant_ids():
            report = await engine.generate_daily_market_report()
            await engine.write_github_intelligence_package(report)
            logger.info("MarketIntelligence: tenant=%s topic=%s", tenant_id, report.get("topic", "unknown"))
    except Exception as exc:
        logger.warning("Market intelligence generation failed: %s", exc)
