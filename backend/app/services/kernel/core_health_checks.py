"""Core engine health checks registered with the HealthAggregator (K1-7).

These mirror the same subsystems /readyz already probes on demand, but here
they run on the aggregator's continuous 30s loop so the Ops/Kernel dashboard
reflects real, current state instead of the aggregator's empty default.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


async def check_database() -> dict:
    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal

    t0 = time.monotonic()
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "HEALTHY", "latency_ms": int((time.monotonic() - t0) * 1000)}
    except Exception as exc:
        return {"status": "CRITICAL", "error": str(exc)}


async def check_redis() -> dict:
    import redis.asyncio as aioredis
    from app.core.config import settings

    try:
        r = aioredis.from_url(settings.REDIS_URL or "redis://localhost:6379", socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        return {"status": "HEALTHY"}
    except Exception as exc:
        # Redis has an in-memory fallback for caching/rate-limiting — a miss
        # degrades performance, it doesn't take the system down.
        return {"status": "DEGRADED", "error": str(exc)}


async def check_ai_providers() -> dict:
    from app.services.ai.router import ai_router

    try:
        status = ai_router.get_provider_status()
        available = [name for name, p in status.items() if p.get("available")]
        if not status:
            return {"status": "CRITICAL", "error": "no providers registered"}
        if not available:
            return {"status": "CRITICAL", "available": 0, "total": len(status)}
        return {"status": "HEALTHY", "available": len(available), "total": len(status)}
    except Exception as exc:
        return {"status": "UNKNOWN", "error": str(exc)}


async def check_scheduler() -> dict:
    from app.services.scheduler.scheduler import get_scheduler

    try:
        sched = get_scheduler()
        running = sched is not None and sched.running
        return {"status": "HEALTHY" if running else "CRITICAL", "running": running}
    except Exception as exc:
        return {"status": "UNKNOWN", "error": str(exc)}


def register_core_checks(aggregator) -> None:
    aggregator.register("database", check_database)
    aggregator.register("redis", check_redis)
    aggregator.register("ai_providers", check_ai_providers)
    aggregator.register("scheduler", check_scheduler)
