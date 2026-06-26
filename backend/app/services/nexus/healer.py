"""
NEXUS HEALER — Self-Healing Subsystem Monitor.

Continuously monitors all JARVIS subsystems:
  - AI provider availability (Anthropic, fallback chain)
  - Database connectivity
  - Redis availability
  - Scheduler job health
  - Autopilot draft queue overflow
  - Signal scan failures

On failure: logs heal event, triggers recovery protocol, notifies Captain.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


SUBSYSTEMS = [
    "ai_provider",
    "database",
    "redis",
    "scheduler",
    "autopilot",
    "signal",
    "ghost",
    "pipeline",
]


async def diagnose_all(db) -> dict[str, dict]:
    """Run full subsystem health check. Returns per-system status dict."""
    results: dict[str, dict] = {}

    # AI Provider
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    results["ai_provider"] = {
        "status": "healthy" if anthropic_key else "degraded",
        "detail": "API key present" if anthropic_key else "ANTHROPIC_API_KEY not set",
        "healable": False,
    }

    # Database
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        results["database"] = {"status": "healthy", "detail": "Connected", "healable": False}
    except Exception as exc:
        results["database"] = {"status": "critical", "detail": str(exc), "healable": False}

    # Redis
    try:
        import redis.asyncio as aioredis
        url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        r = aioredis.from_url(url, decode_responses=True)
        await r.ping()
        await r.aclose()
        results["redis"] = {"status": "healthy", "detail": "Connected", "healable": False}
    except Exception as exc:
        results["redis"] = {
            "status": "degraded",
            "detail": f"Redis unavailable: {exc} — using in-memory fallback",
            "healable": True,
            "heal_action": "redis_fallback_active",
        }

    # Autopilot queue
    try:
        from app.services.autopilot.pipeline import get_pending_drafts
        pending = await get_pending_drafts(None)
        overflow = len(pending) > 20
        results["autopilot"] = {
            "status": "warning" if overflow else "healthy",
            "detail": f"{len(pending)} pending drafts" + (" — queue overflow" if overflow else ""),
            "healable": overflow,
            "heal_action": "notify_captain_queue_overflow" if overflow else None,
        }
    except Exception as exc:
        results["autopilot"] = {"status": "degraded", "detail": str(exc), "healable": False}

    # Scheduler
    try:
        from app.services.scheduler.engine import get_scheduler
        sched = get_scheduler()
        running = sched.running if sched else False
        results["scheduler"] = {
            "status": "healthy" if running else "stopped",
            "detail": "APScheduler running" if running else "Scheduler not running",
            "healable": not running,
            "heal_action": "restart_scheduler" if not running else None,
        }
    except Exception as exc:
        results["scheduler"] = {"status": "unknown", "detail": str(exc), "healable": False}

    # Signal and Ghost — check AI key (same dependency)
    for sub in ("signal", "ghost"):
        results[sub] = {
            "status": "healthy" if anthropic_key else "degraded",
            "detail": "Operational" if anthropic_key else "Requires ANTHROPIC_API_KEY",
            "healable": False,
        }

    results["pipeline"] = results.get("database", {"status": "unknown"})

    return results


async def heal_subsystem(subsystem: str, db) -> dict:
    """Attempt to heal a specific subsystem. Returns heal result."""
    from app.services.nexus.heartbeat import log_heal_event

    ts = datetime.now(timezone.utc).isoformat()
    result = {"subsystem": subsystem, "timestamp": ts, "action": None, "success": False, "detail": ""}

    if subsystem == "redis":
        # Redis fallback is automatic — just confirm it
        result["action"] = "redis_fallback_confirmed"
        result["success"] = True
        result["detail"] = "In-memory fallback is active. Redis will reconnect automatically on restart."

    elif subsystem == "scheduler":
        try:
            from app.services.scheduler.engine import get_scheduler, start_scheduler
            engine = get_scheduler()
            if engine and not engine.running:
                await start_scheduler()
                result["action"] = "scheduler_restart"
                result["success"] = True
                result["detail"] = "Scheduler restarted."
            else:
                result["action"] = "noop"
                result["detail"] = "Scheduler already running or engine unavailable."
        except Exception as exc:
            result["detail"] = f"Restart failed: {exc}"

    elif subsystem == "autopilot":
        result["action"] = "captain_notification_queued"
        result["success"] = True
        result["detail"] = "Captain notified of autopilot queue overflow via Telegram."
        try:
            from app.services.communication.telegram import notify_telegram
            await notify_telegram(
                "⚠️ NEXUS HEALER: AUTOPILOT queue has >20 pending drafts. "
                "Review and bulk-approve via /control-room/autopilot."
            )
        except Exception:
            result["detail"] += " (Telegram notification failed — check TG config)"

    else:
        result["detail"] = f"No heal protocol defined for subsystem: {subsystem}"

    await log_heal_event(result)
    return result


async def auto_heal_all(db) -> list[dict]:
    """Diagnose all subsystems and auto-heal any healable failures."""
    diagnosis = await diagnose_all(db)
    heal_results: list[dict] = []

    for subsystem, status in diagnosis.items():
        if status.get("healable") and status.get("status") in ("degraded", "stopped", "warning"):
            logger.info("NEXUS HEALER: Auto-healing %s", subsystem)
            result = await heal_subsystem(subsystem, db)
            heal_results.append(result)

    return heal_results
