"""
JARVIS Autonomous Self-Healer — detects degradation and recovers without human intervention.

Every 15 minutes JARVIS:
  1. Pings each active AI provider — resets circuit breakers on recovered providers
  2. Checks lead velocity — auto-triggers discovery if pipeline runs dry
  3. Verifies scheduler health — restarts any paused critical jobs
  4. Monitors Redis connectivity — reports if cache layer is degraded
  5. Alerts Captain only when it cannot self-recover

This is the difference between a system that breaks and one that heals itself.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

_CRITICAL_JOBS = [
    "daily_morning_briefing",
    "daily_lead_scoring",
    "daily_lead_discovery",
    "daily_follow_up_check",
    "speed_to_lead_5min",
]


async def run_self_healing_cycle() -> dict:
    """Full self-healing pass. Returns a summary dict for observability."""
    started = datetime.now(UTC)
    report: dict[str, object] = {"started_at": started.isoformat(), "actions": [], "alerts": []}

    await asyncio.gather(
        _heal_ai_providers(report),
        _heal_lead_pipeline(report),
        _heal_scheduler_jobs(report),
        _heal_redis(report),
        return_exceptions=True,
    )

    report["duration_ms"] = int((datetime.now(UTC) - started).total_seconds() * 1000)
    if report["alerts"]:
        await _alert_captain(report)
    logger.info("Self-healer cycle complete: %d actions, %d alerts", len(report["actions"]), len(report["alerts"]))
    return report


async def _heal_ai_providers(report: dict) -> None:
    """Reset circuit breakers for any AI provider that has recovered."""
    try:
        from app.services.ai.router import ai_router
        from app.services.ai.health_monitor import health_monitor
        from app.services.ai.base_provider import Message, TaskType

        recovered = []
        still_open = []

        for name, ph in list(health_monitor._providers.items()):
            if ph.state == "OPEN":
                # Probe with a minimal test — if it passes, force reset
                try:
                    await ai_router.chat(
                        [Message(role="user", content="ping")],
                        task_type=TaskType.FAST,
                        force_provider=name,
                    )
                    health_monitor.reset(name)
                    recovered.append(name)
                    report["actions"].append(f"circuit_breaker_reset:{name}")
                except Exception:
                    still_open.append(name)

        if still_open:
            report["alerts"].append(f"AI providers still unreachable: {', '.join(still_open)}")
        if recovered:
            logger.info("Self-healer: circuit breakers reset for %s", recovered)

    except Exception as exc:
        logger.warning("Self-healer AI probe failed: %s", exc)


async def _heal_lead_pipeline(report: dict) -> None:
    """If no new leads in 36 hours, kick off background discovery automatically."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.core.config import settings
        from app.models.lead import Lead, LeadStatus
        from sqlalchemy import func, select

        async with AsyncSessionLocal() as db:
            cutoff = datetime.now(UTC) - timedelta(hours=36)
            recent_count = await db.scalar(
                select(func.count()).select_from(Lead).where(Lead.created_at >= cutoff)
            )

        if (recent_count or 0) == 0:
            tenant_id = settings.JARVIS_DEFAULT_TENANT_ID
            if tenant_id:
                from app.services.leads.discovery import lead_discovery_engine

                targets = [
                    {"query": "business automation AI workflow", "industry": "SaaS", "limit": 20},
                    {"query": "cloud infrastructure DevOps", "industry": "Technology", "limit": 20},
                ]
                try:
                    inserted = await lead_discovery_engine.run_daily_discovery(tenant_id, targets)
                    report["actions"].append(f"auto_discovery_triggered:inserted={inserted}")
                    logger.info("Self-healer: empty pipeline — auto-discovery triggered, %d leads inserted", inserted)
                except Exception as exc:
                    report["alerts"].append(f"Lead pipeline dry (36h) and auto-discovery failed: {exc}")
        else:
            logger.debug("Self-healer: lead pipeline healthy (%d leads in 36h)", recent_count)

    except Exception as exc:
        logger.warning("Self-healer lead pipeline check failed: %s", exc)


async def _heal_scheduler_jobs(report: dict) -> None:
    """Detect paused or missing critical jobs and resume them."""
    try:
        from app.services.scheduler.scheduler import get_scheduler, get_jobs

        scheduler = get_scheduler()
        if not scheduler.running:
            report["alerts"].append("Scheduler is not running — critical background jobs offline")
            return

        running_ids = {j["id"] for j in get_jobs()}
        missing = [jid for jid in _CRITICAL_JOBS if jid not in running_ids]

        for job_id in missing:
            try:
                scheduler.resume_job(job_id)
                report["actions"].append(f"scheduler_job_resumed:{job_id}")
                logger.info("Self-healer: resumed paused job %s", job_id)
            except Exception:
                report["alerts"].append(f"Critical scheduler job missing and cannot be resumed: {job_id}")

    except Exception as exc:
        logger.warning("Self-healer scheduler check failed: %s", exc)


async def _heal_redis(report: dict) -> None:
    """Verify Redis is reachable; report if cache layer is degraded."""
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings

        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await client.ping()
        await client.aclose()
    except Exception as exc:
        report["alerts"].append(f"Redis unreachable — caching and rate limiting degraded: {exc}")
        logger.warning("Self-healer: Redis ping failed: %s", exc)


async def _alert_captain(report: dict) -> None:
    """Send a consolidated self-healer alert to Captain via Telegram."""
    try:
        from app.services.notifications.telegram import notify_telegram

        lines = ["🔧 *JARVIS Self-Healer Report*\n"]
        if report["actions"]:
            lines.append("*Auto-recovered:*")
            lines.extend(f"  ✅ {a}" for a in report["actions"])
        if report["alerts"]:
            lines.append("\n*Requires attention:*")
            lines.extend(f"  ⚠️ {a}" for a in report["alerts"])
        lines.append(f"\n_Scan completed in {report.get('duration_ms', '?')}ms_")
        await notify_telegram("\n".join(lines))
    except Exception as exc:
        logger.warning("Self-healer captain alert failed: %s", exc)
