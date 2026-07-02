"""
Customer-facing monitoring and cost analytics API.
Exposes real-time system health, operational metrics, and AI cost breakdowns.
"""
from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.tenant_context import get_current_tenant_id
from app.middleware import (
    JARVIS_AI_COST_USD_TOTAL,
    JARVIS_AI_LATENCY_SECONDS,
    JARVIS_CLIENTS_ACTIVE,
    JARVIS_APPROVALS_PENDING,
    JARVIS_DB_CONNECTIONS_ACTIVE,
    JARVIS_REDIS_MEMORY_BYTES,
    JARVIS_MRR_USD,
)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/health")
async def system_health():
    """Get overall system health score (0-100)."""
    try:
        from app.services.aionx.orchestration_cortex import compute_operational_iq
        async with AsyncSessionLocal() as db:
            result = await compute_operational_iq(db)
            return {
                "health_score": result.get("operational_iq", 0),
                "interpretation": result.get("interpretation", ""),
                "components": {
                    "ai_providers": result.get("ai_providers_available", 0),
                    "database": result.get("database_health", "unknown"),
                    "cache": result.get("cache_health", "unknown"),
                    "scheduler": result.get("scheduler_health", "unknown"),
                },
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as exc:
        return {
            "health_score": 0,
            "error": str(exc),
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/metrics/ai-cost/today")
async def ai_cost_today():
    """Get today's AI API costs by provider."""
    try:
        from app.services.ai.cost_tracker import get_daily_cost
        async with AsyncSessionLocal() as db:
            result = await get_daily_cost(db, for_date=date.today())
            return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/metrics/ai-cost/history")
async def ai_cost_history(days: int = Query(7, ge=1, le=90)):
    """Get N-day AI cost history."""
    try:
        from app.services.ai.cost_tracker import get_cost_summary
        async with AsyncSessionLocal() as db:
            result = await get_cost_summary(db, days=days)
            return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/metrics/ai-cost/audit")
async def ai_cost_audit(
    limit: int = Query(100, ge=1, le=500),
    provider: Optional[str] = None,
):
    """Get detailed AI cost audit log."""
    try:
        from app.services.ai.cost_tracker import get_audit_log
        async with AsyncSessionLocal() as db:
            result = await get_audit_log(db, limit=limit, provider=provider)
            return {
                "limit": limit,
                "count": len(result),
                "provider_filter": provider,
                "entries": result,
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/metrics/prometheus")
async def prometheus_metrics_summary():
    """Get summary of current Prometheus metrics."""
    try:
        # Parse prometheus_client metric objects
        ai_cost = {}
        ai_latency = {}

        try:
            for sample in JARVIS_AI_COST_USD_TOTAL.collect()[0].samples:
                labels = sample.labels or {}
                key = f"{labels.get('provider', 'unknown')}/{labels.get('model', 'unknown')}"
                ai_cost[key] = sample.value
        except Exception:
            pass

        try:
            for sample in JARVIS_AI_LATENCY_SECONDS.collect()[0].samples:
                labels = sample.labels or {}
                key = f"{labels.get('provider', 'unknown')}/{labels.get('model', 'unknown')}"
                ai_latency[key] = sample.value
        except Exception:
            pass

        return {
            "ai_cost_usd": ai_cost,
            "ai_latency_seconds": ai_latency,
            "active_clients": float(JARVIS_CLIENTS_ACTIVE._value.get() if hasattr(JARVIS_CLIENTS_ACTIVE, '_value') else 0),
            "db_connections": float(JARVIS_DB_CONNECTIONS_ACTIVE._value.get() if hasattr(JARVIS_DB_CONNECTIONS_ACTIVE, '_value') else 0),
            "redis_memory_bytes": float(JARVIS_REDIS_MEMORY_BYTES._value.get() if hasattr(JARVIS_REDIS_MEMORY_BYTES, '_value') else 0),
            "mrr_usd": float(JARVIS_MRR_USD._value.get() if hasattr(JARVIS_MRR_USD, '_value') else 0),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as exc:
        return {"error": str(exc), "timestamp": datetime.now().isoformat()}


@router.get("/metrics/approvals")
async def pending_approvals():
    """Get pending Captain approvals by risk level."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.approval import ApprovalRequest, ApprovalStatus
        from sqlalchemy import select, func

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ApprovalRequest.risk_level, func.count())
                .where(ApprovalRequest.status == ApprovalStatus.PENDING)
                .group_by(ApprovalRequest.risk_level)
            )
            rows = result.all()
            breakdown = {risk: count for risk, count in rows}
            total = sum(v for v in breakdown.values())
            return {
                "total_pending": total,
                "by_risk_level": breakdown,
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/metrics/jobs")
async def scheduler_jobs_status():
    """Get scheduler job execution status and performance."""
    try:
        from app.services.scheduler.engine import get_jobs
        jobs = get_jobs()

        # Group by status
        running = len([j for j in jobs if j.get("next_run")])
        paused = len([j for j in jobs if not j.get("next_run")])

        return {
            "total_jobs": len(jobs),
            "running": running,
            "paused": paused,
            "jobs": jobs,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as exc:
        return {"error": str(exc), "timestamp": datetime.now().isoformat()}


@router.get("/metrics/ai-providers")
async def ai_providers_status():
    """Get status of configured AI providers."""
    try:
        from app.services.ai.router import ai_router
        providers = ai_router.get_provider_status()
        configured = [k for k, v in providers.items() if v.get("configured")]
        available = ai_router.operational_providers()

        return {
            "total": len(providers),
            "configured": len(configured),
            "available": len(available),
            "active_providers": available,
            "configured_providers": configured,
            "provider_details": providers,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/dashboard/overview")
async def dashboard_overview():
    """Comprehensive dashboard overview for customer-facing monitoring UI."""
    try:
        from app.services.ai.router import ai_router
        from app.services.ai.cost_tracker import get_daily_cost, get_cost_summary

        async with AsyncSessionLocal() as db:
            # Health score
            from app.services.aionx.orchestration_cortex import compute_operational_iq
            health = await compute_operational_iq(db)

            # AI costs
            daily_cost = await get_daily_cost(db)
            weekly_cost = await get_cost_summary(db, days=7)

            # Providers
            providers = ai_router.get_provider_status()
            available = ai_router.operational_providers()

            # Approvals
            from app.models.approval import ApprovalRequest, ApprovalStatus
            from sqlalchemy import select, func
            approval_result = await db.execute(
                select(func.count()).select_from(ApprovalRequest)
                .where(ApprovalRequest.status == ApprovalStatus.PENDING)
            )
            pending_approvals = approval_result.scalar() or 0

            return {
                "health": {
                    "score": health.get("operational_iq", 0),
                    "interpretation": health.get("interpretation", ""),
                },
                "ai_costs": {
                    "today_usd": daily_cost.get("total_cost_usd", 0),
                    "week_usd": weekly_cost.get("total_cost_usd", 0),
                    "daily_average_usd": weekly_cost.get("avg_daily_usd", 0),
                    "surge_alert": daily_cost.get("surge_alert", False),
                },
                "providers": {
                    "available": len(available),
                    "configured": sum(1 for p in providers.values() if p.get("configured")),
                    "total": len(providers),
                    "active": available,
                },
                "operations": {
                    "pending_approvals": pending_approvals,
                },
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/metrics/alert/acknowledge/{alert_id}")
async def acknowledge_alert(alert_id: str):
    """Acknowledge a system alert (mark as read)."""
    try:
        # TODO: Implement alert acknowledgment via database
        return {"status": "acknowledged", "alert_id": alert_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
