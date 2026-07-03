"""
JARVIS Agent Scheduler — APScheduler with SQLite/PostgreSQL persistence.
Supports cron, interval, and one-shot (date) triggers.
Jobs survive restarts via job store.
"""
import asyncio
import logging
import traceback as _tb
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


# ── Job failure persistence ───────────────────────────────────────────────────

_SYSTEM_TENANT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


async def _record_job_failure(job_name: str, error: str, tb_str: str = "") -> None:
    """Persist a scheduler job failure to DB. Alert Captain after 3 consecutive open failures."""
    import uuid as _uuid
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.scheduling import JobFailure
        from sqlalchemy import select, func

        tenant_id = (
            _uuid.UUID(str(settings.JARVIS_DEFAULT_TENANT_ID))
            if settings.JARVIS_DEFAULT_TENANT_ID
            else _uuid.UUID(_SYSTEM_TENANT_ID)
        )

        async with AsyncSessionLocal() as db:
            async with db.begin():
                db.add(JobFailure(
                    tenant_id=tenant_id,
                    job_name=job_name,
                    status="open",
                    error=error[:2000],
                    traceback=tb_str[:4000] if tb_str else None,
                ))
            open_count = await db.scalar(
                select(func.count()).select_from(JobFailure)
                .where(JobFailure.job_name == job_name)
                .where(JobFailure.status == "open")
            ) or 0

        if open_count >= 3:
            try:
                from app.services.notifications.telegram import notify_telegram
                await notify_telegram(
                    f"⚠️ *Scheduler Failure — {job_name}*\n"
                    f"{open_count} consecutive failures recorded.\n"
                    f"`{error[:200]}`"
                )
            except Exception:
                pass
    except Exception as exc:
        logger.warning("_record_job_failure itself failed for %s: %s", job_name, exc)


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

    # ── AIONX Sovereign Organs — the heartbeat that makes the organs autonomous ──
    try:
        from app.services.aionx.aionx_scheduler import register_aionx_jobs
        register_aionx_jobs(add_cron_job, add_interval_job)
    except Exception as exc:
        logger.warning("AIONX job registration failed: %s", exc)

    # ── Autonomous Self-Healer — runs every 15 minutes ────────────────────────
    add_interval_job("self_healer", _job_self_healer, minutes=15)

    # ── NEXUS Heartbeat — runs every hour ─────────────────────────────────────
    add_interval_job("nexus_heartbeat", _job_nexus_heartbeat, hours=1)

    # ── Semantic Lead Embedding Sweep — nightly at 03:15 ──────────────────────
    add_cron_job("lead_embedding_sweep", _job_embed_leads, hour=3, minute=15)

    # ── Captain Dashboard Briefing — 06:55 every day ──────────────────────────
    add_cron_job("captain_dashboard_briefing", _job_captain_dashboard_briefing, hour=6, minute=55)

    # ── Weekly Performance Briefing — Saturday 19:00 UTC ─────────────────────
    add_cron_job("weekly_performance_briefing", _job_weekly_performance_briefing,
                 day_of_week="sat", hour=19, minute=0)

    # ── Nightly Signal Pipeline Scan — 02:00 UTC ─────────────────────────────
    add_cron_job("nightly_signal_scan", _job_nightly_signal_scan, hour=2, minute=0)

    # ── Routing Optimizer — 1st of each month @ 03:00 UTC (O5-1) ─────────────
    try:
        from app.services.fabric.routing_optimizer import register_routing_optimizer_job
        register_routing_optimizer_job()
    except Exception as _exc:
        logger.warning("routing_optimizer job registration skipped: %s", _exc)

    logger.info("✅ Default JARVIS jobs registered (6-Layer Intelligence + 9-Connector Pipeline + AIONX Organs + Self-Healer + NEXUS Heartbeat + Semantic Embeddings + Daily Briefing + Weekly Performance + Nightly Signal Scan)")


async def _job_morning_briefing() -> None:
    logger.info("Scheduler: running morning briefing")
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            from app.services.notifications.telegram_bot import _handle_briefing
            from app.core.config import settings
            await _handle_briefing(str(settings.TELEGRAM_CHAT_ID or ""), db)
    except Exception as e:
        logger.warning("Morning briefing job failed: %s", e)
        await _record_job_failure("daily_briefing", str(e), _tb.format_exc())


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
        logger.warning("Lead scoring job failed: %s", e)
        await _record_job_failure("lead_scoring_sweep", str(e), _tb.format_exc())


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
        await _record_job_failure("daily_icp_lead_scoring", str(e), _tb.format_exc())


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
                    except Exception as exc:
                        logger.warning("Outreach email %s send failed: %s", email.id, exc)
        logger.info(f"Outreach: {sent}/{len(due)} emails sent")
    except Exception as e:
        logger.warning(f"Outreach job failed: {e}")
        await _record_job_failure("outreach_processor", str(e), _tb.format_exc())


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
        await _record_job_failure("contact_sync", str(e), _tb.format_exc())


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
        await _record_job_failure("tech_radar_scan", str(e), _tb.format_exc())


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
        await _record_job_failure("market_intelligence_report", str(e), _tb.format_exc())


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
        await _record_job_failure("competitor_monitoring", str(e), _tb.format_exc())


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
        await _record_job_failure("intelligence_morning_briefing", str(e), _tb.format_exc())


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
        await _record_job_failure("optimization_review", str(e), _tb.format_exc())


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
        await _record_job_failure("research_report", str(e), _tb.format_exc())


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
        await _record_job_failure("self_learning", str(e), _tb.format_exc())


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
        await _record_job_failure("memory_consolidation", str(e), _tb.format_exc())


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
        await _record_job_failure("memory_promotion", str(e), _tb.format_exc())


async def _job_gmail_inbox() -> None:
    logger.info("Scheduler: executive email inbound sync is disabled until SES inbound is configured")
    return


async def _job_reply_handler_scan() -> None:
    logger.info("Scheduler: reply scanning is disabled until SES inbound processing is configured")
    return


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
        await _record_job_failure("overnight_lead_discovery", str(e), _tb.format_exc())


async def _job_overnight_intel_analysis() -> None:
    """12:00 AM IST — Market intelligence: tech trends, competitor moves, opportunities."""
    logger.info("Overnight engine: intelligence analysis starting")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.optimizer import analyze_system
        async with AsyncSessionLocal() as db:
            async with db.begin():
                count = await analyze_system(db)
        logger.info(f"Overnight intel analysis: {count} insights generated")
    except Exception as e:
        logger.warning(f"Overnight intel analysis failed: {e}")
        await _record_job_failure("overnight_intel_analysis", str(e), _tb.format_exc())


async def _job_overnight_proposal_engine() -> None:
    """1:00 AM IST — Write and queue proposals for top-scored leads."""
    logger.info("Overnight engine: proposal generation starting")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.ai.router import ai_router
        from app.services.memory.manager import store_memory
        from sqlalchemy import select, and_
        from app.models.lead import Lead, LeadStatus
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Lead)
                .where(and_(Lead.score >= 7, Lead.status == LeadStatus.NEW))
                .order_by(Lead.score.desc())
                .limit(5)
            )
            leads = result.scalars().all()
            for lead in leads:
                try:
                    response, _ = await asyncio.wait_for(
                        ai_router.chat(
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
                        ),
                        timeout=60.0,
                    )
                    if response.error:
                        logger.warning("Proposal AI failed for lead %s: %s", lead.id, response.error)
                        continue
                    proposal_text = response.content or ""
                    if proposal_text:
                        await store_memory(
                            db,
                            content=f"Proposal drafted for {lead.company_name}: {proposal_text[:400]}",
                            memory_type="semantic",
                            importance=0.7,
                            tags=["proposal", "overnight", str(lead.id)],
                            key=f"proposal:lead:{lead.id}",
                        )
                        lead.status = LeadStatus.PROPOSAL
                except Exception as ex:
                    logger.warning(f"Proposal draft failed for lead {lead.id}: {ex}")
            await db.commit()
        logger.info(f"Overnight proposals: {len(leads)} proposals drafted")
    except Exception as e:
        logger.warning(f"Overnight proposal engine failed: {e}")
        await _record_job_failure("overnight_proposal_engine", str(e), _tb.format_exc())


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
                    except Exception as exc:
                        logger.warning("Overnight cold outreach email %s failed: %s", email.id, exc)
        logger.info(f"Overnight cold outreach: {sent} emails sent")
    except Exception as e:
        logger.warning(f"Overnight cold outreach failed: {e}")
        await _record_job_failure("overnight_cold_outreach", str(e), _tb.format_exc())


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
        await _record_job_failure("overnight_freelance_bids", str(e), _tb.format_exc())


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
                    except Exception as exc:
                        logger.warning("Overnight follow-up email %s failed: %s", email.id, exc)
        logger.info(f"Overnight follow-ups: {sent} sequences sent")
    except Exception as e:
        logger.warning(f"Overnight follow-up sequences failed: {e}")
        await _record_job_failure("overnight_followup_sequences", str(e), _tb.format_exc())


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
        await _record_job_failure("overnight_pipeline_health", str(e), _tb.format_exc())


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
        await _record_job_failure("overnight_ops_report", str(e), _tb.format_exc())


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
        await _record_job_failure("daily_strategy_report", str(exc), _tb.format_exc())


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
        await _record_job_failure("milestone_bulk_review", str(exc), _tb.format_exc())


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
        await _record_job_failure("tech_evolution_scan", str(exc), _tb.format_exc())


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
                ).limit(50)
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
        await _record_job_failure("pre_call_briefing_trigger", str(exc), _tb.format_exc())


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
        await _record_job_failure("weekly_strategy_review", str(exc), _tb.format_exc())


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
        await _record_job_failure("dio_health_check", str(exc), _tb.format_exc())


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
        await _record_job_failure("connector_hub_ingestion", str(exc), _tb.format_exc())


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
        await _record_job_failure("daily_scout_network", str(exc), _tb.format_exc())


async def _job_market_intelligence_generation() -> None:
    """9-Connector Pipeline: generate daily market intelligence at 04:00 UTC for next cycle."""
    logger.info("MarketIntelligence: starting daily generation at 04:00 UTC")
    try:
        from app.services.integrations.market_intelligence_engine import MarketIntelligenceEngine
        engine = MarketIntelligenceEngine()
        for tenant_id in await _target_tenant_ids():
            _tid = uuid.UUID(str(tenant_id))
            result = await engine.write_github_intelligence_package(
                tenant_id=_tid,
                output_dir="intelligence",
            )
            logger.info("MarketIntelligence: tenant=%s files=%d", tenant_id, len(result.get("files_written", [])))
    except Exception as exc:
        logger.warning("Market intelligence generation failed: %s", exc)
        await _record_job_failure("market_intelligence_generation", str(exc), _tb.format_exc())


async def _job_self_healer() -> None:
    """Autonomous self-healing cycle — runs every 15 minutes."""
    try:
        from app.services.monitoring.self_healer import run_self_healing_cycle
        await run_self_healing_cycle()
    except Exception as exc:
        logger.warning("Self-healer job failed: %s", exc)
        await _record_job_failure("self_healer", str(exc), _tb.format_exc())


async def _job_embed_leads() -> None:
    """Nightly semantic embedding sweep — vectorizes leads without embeddings."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.lead_embeddings import embed_pending_leads
        async with AsyncSessionLocal() as db:
            result = await embed_pending_leads(db, limit=100)
        logger.info("Lead embedding sweep: %s", result)
    except Exception as exc:
        logger.warning("Lead embedding sweep failed: %s", exc)
        await _record_job_failure("embed_leads", str(exc), _tb.format_exc())


async def _job_nexus_heartbeat() -> None:
    """
    NEXUS heartbeat — runs every hour.
    Pulses pipeline state. If action_signal is OUTREACH_READY and no drafts
    are pending, autonomously triggers AUTOPILOT (max 5 leads, min_score 75).
    A Redis lock prevents re-triggering within 4 hours.
    """
    try:
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

        # Autonomous outreach trigger — fire when pipeline is ready and queue is clear
        if action == "OUTREACH_READY" and not pending:
            lock_acquired = False
            try:
                import redis.asyncio as aioredis
                r = aioredis.from_url(settings.REDIS_URL or "redis://localhost:6379")
                lock_acquired = await r.set(
                    "nexus:auto_outreach:lock", "1",
                    nx=True, ex=14400  # 4-hour lock
                )
                await r.aclose()
            except Exception as exc:
                logger.warning("NEXUS: Redis lock unavailable, skipping autonomous outreach: %s", exc)
                lock_acquired = False  # safe default: no rate-limit guard = don't trigger

            if lock_acquired:
                logger.info("NEXUS AUTONOMOUS: OUTREACH_READY — triggering AUTOPILOT (max 5 leads)")
                try:
                    result = await run_autopilot_cycle(max_leads=5, min_score=75.0)
                    logger.info("NEXUS AUTONOMOUS: composed=%s skipped=%s",
                                result.get("composed", 0), result.get("skipped", 0))
                    from app.services.nexus.heartbeat import log_decision
                    await log_decision({
                        "action": "auto_outreach_triggered",
                        "composed": result.get("composed", 0),
                        "source": "nexus_heartbeat",
                    })
                except Exception as exc:
                    logger.warning("NEXUS autonomous outreach failed: %s", exc)

        logger.info("NEXUS heartbeat: signal=%s | drafts=%d | autonomous=%s",
                    action, len(pending), action == "OUTREACH_READY" and not pending)

        # Push pulse to frontend via WebSocket
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

    except Exception as exc:
        logger.warning("NEXUS heartbeat job failed: %s", exc)
        await _record_job_failure("nexus_heartbeat", str(exc), _tb.format_exc())


async def _job_captain_dashboard_briefing() -> None:
    """Captain morning dashboard — 06:55 daily. Sends real pipeline stats via Telegram."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.notifications.telegram_bot import notify_captain_morning_briefing
        async with AsyncSessionLocal() as db:
            await notify_captain_morning_briefing(db)
    except Exception as exc:
        logger.warning("Captain dashboard briefing failed: %s", exc)
        await _record_job_failure("captain_dashboard_briefing", str(exc), _tb.format_exc())


async def _job_weekly_performance_briefing() -> None:
    """Weekly Saturday 19:00 UTC — full 7-day performance summary via Telegram."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.notifications.telegram_bot import notify_weekly_performance_briefing
        async with AsyncSessionLocal() as db:
            await notify_weekly_performance_briefing(db)
    except Exception as exc:
        logger.warning("Weekly performance briefing failed: %s", exc)
        await _record_job_failure("weekly_performance_briefing", str(exc), _tb.format_exc())


async def _job_nightly_signal_scan() -> None:
    """Nightly 02:00 UTC — scan all active pipeline leads and brief Captain on high signals."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.lead import Lead, LeadStatus
        from sqlalchemy import select, and_

        async with AsyncSessionLocal() as db:
            rows = (await db.execute(
                select(Lead)
                .where(
                    and_(
                        Lead.score >= 45,
                        Lead.status.in_([LeadStatus.NEW, LeadStatus.NURTURE, LeadStatus.CONTACTED]),
                    )
                )
                .order_by(Lead.score.desc())
                .limit(30)
            )).scalars().all()

        if not rows:
            logger.info("Nightly signal scan: no leads to scan")
            return

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
            except Exception:
                continue

        logger.info("Nightly signal scan: %d leads scanned, %d high signals", len(rows), len(signals))

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

        # ── Auto-propose for highest-confidence HOT leads ─────────────────────
        # Only fires when: intent_tier=HOT, confidence≥85, outreach_count>0
        # Capped at 2 per nightly run to avoid overwhelming the approval queue
        hot_candidates = [
            s for s in signals
            if s.get("intent_tier") == "HOT"
            and int(s.get("confidence", 0) or 0) >= 85
            and int(s.get("lead_score", 0) or 0) >= 75
        ]
        proposals_queued = 0
        for sig in hot_candidates[:2]:
            if proposals_queued >= 2:
                break
            lead_id_str = sig.get("lead_id")
            if not lead_id_str:
                continue
            try:
                from uuid import UUID
                from app.services.governance.auto_proposal import auto_generate_proposal_for_lead
                lead_score = float(sig.get("lead_score", 75))
                estimated_value = max(3000.0, lead_score * 60)  # score→value heuristic
                result = await auto_generate_proposal_for_lead(
                    lead_id=UUID(lead_id_str),
                    lead_name=sig.get("lead_contact") or "Decision Maker",
                    lead_email=sig.get("lead_email") or "",
                    lead_company=sig.get("lead_company") or "Unknown",
                    estimated_deal_value=estimated_value,
                    lead_context=f"HOT signal — {sig.get('why_now', '')}",
                )
                if result.get("proposal_id"):
                    proposals_queued += 1
                    logger.info(
                        "Auto-proposal queued for HOT lead %s (confidence=%s)",
                        sig.get("lead_company"), sig.get("confidence")
                    )
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

    except Exception as exc:
        logger.warning("Nightly signal scan failed: %s", exc)
        await _record_job_failure("nightly_signal_scan", str(exc), _tb.format_exc())
