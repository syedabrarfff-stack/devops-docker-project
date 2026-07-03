"""K2-6: Kernel Ops Dashboard API — real-time system state, health, tasks, config.

All endpoints require Captain JWT auth. This is the L3 Kernel control plane.

Endpoints:
  GET  /kernel/dashboard     — comprehensive system snapshot (single call for UI)
  GET  /kernel/state         — current StateMachine state
  GET  /kernel/health        — HealthAggregator summary
  GET  /kernel/tasks/depth   — TaskQueue depth by priority
  GET  /kernel/tasks/dead    — dead tasks (max_retries exhausted)
  GET  /kernel/config        — all config entries
  PUT  /kernel/config/{key}  — upsert a config value
  DELETE /kernel/config/{key} — delete a config value
  GET  /kernel/discovery     — ServiceDiscovery snapshot
  GET  /kernel/plugins       — PluginLoader snapshot
  GET  /kernel/failover      — FailoverController status
  GET  /kernel/audit         — recent audit entries (last 50)
  GET  /kernel/sync          — SyncProtocol epoch snapshot
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.auth import get_current_captain
from app.core.database import get_async_db

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/kernel",
    tags=["Kernel Dashboard"],
    dependencies=[Depends(get_current_captain)],
)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ConfigUpsertBody(BaseModel):
    value: Any = Field(..., description="Any JSON-serialisable value")
    updated_by: str = Field(default="captain", max_length=80)


# ── GET /kernel/dashboard ─────────────────────────────────────────────────────

@router.get("/dashboard", summary="Full kernel system snapshot")
async def get_dashboard(db: AsyncSession = Depends(get_async_db)):
    """Return a comprehensive single-call snapshot for the Ops Dashboard UI."""
    from app.services.kernel.state_machine import StateMachine
    from app.services.kernel.health_aggregator import get_health_aggregator
    from app.services.kernel.task_queue import TaskQueue
    from app.services.kernel.config_service import get_config_service
    from app.services.kernel.service_discovery import get_service_discovery
    from app.services.kernel.plugin_loader import get_plugin_loader
    from app.services.kernel.failover_controller import get_failover_controller
    from app.services.kernel.audit_logger import AuditLogger

    results = await asyncio.gather(
        _safe(StateMachine(db).get(), "state"),
        _safe_sync(lambda: get_health_aggregator().get_summary(), "health"),
        _safe(TaskQueue(db).depth(), "task_depth"),
        _safe(get_config_service().get_all(), "config"),
        _safe(get_service_discovery().snapshot(), "discovery"),
        _safe_sync(lambda: get_plugin_loader().snapshot(), "plugins"),
        _safe(get_failover_controller().status(), "failover"),
        _safe(AuditLogger(db).recent(limit=10), "audit"),
        return_exceptions=True,
    )

    keys = ["state", "health", "task_depth", "config", "discovery", "plugins", "failover", "audit"]
    return {k: (v if not isinstance(v, Exception) else {"error": str(v)}) for k, v in zip(keys, results)}


# ── GET /kernel/state ─────────────────────────────────────────────────────────

@router.get("/state", summary="Current system state")
async def get_state(db: AsyncSession = Depends(get_async_db)):
    from app.services.kernel.state_machine import StateMachine
    state = await StateMachine(db).get()
    if state is None:
        return {"stage": "idle", "status": "no_state_record", "version": 0}
    return {
        "id": str(state.id),
        "stage": state.stage,
        "status": state.status,
        "version": state.version,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        "data": state.data,
        "autonomous_action_id": str(state.autonomous_action_id) if state.autonomous_action_id else None,
    }


# ── GET /kernel/health ────────────────────────────────────────────────────────

@router.get("/health", summary="Aggregated engine health summary")
async def get_health():
    from app.services.kernel.health_aggregator import get_health_aggregator
    return get_health_aggregator().get_summary()


# ── GET /kernel/tasks/depth ───────────────────────────────────────────────────

@router.get("/tasks/depth", summary="Task queue depth by priority")
async def get_task_depth(db: AsyncSession = Depends(get_async_db)):
    from app.services.kernel.task_queue import TaskQueue
    return await TaskQueue(db).depth()


@router.get("/tasks/dead", summary="Dead tasks that exhausted retries")
async def get_dead_tasks(db: AsyncSession = Depends(get_async_db)):
    from app.services.kernel.task_queue import TaskQueue
    tasks = await TaskQueue(db).dead_tasks()
    return [
        {
            "id": str(t.id),
            "priority": t.priority,
            "status": t.status,
            "retry_count": t.retry_count,
            "max_retries": t.max_retries,
            "payload": t.payload,
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]


# ── GET /kernel/config ────────────────────────────────────────────────────────

@router.get("/config", summary="All runtime config entries")
async def get_config():
    from app.services.kernel.config_service import get_config_service
    return await get_config_service().get_all()


@router.put("/config/{key}", summary="Upsert a runtime config value")
async def set_config(key: str, body: ConfigUpsertBody):
    if len(key) > 120:
        raise HTTPException(status_code=400, detail="key too long (max 120 chars)")
    from app.services.kernel.config_service import get_config_service
    await get_config_service().set(key, body.value, updated_by=body.updated_by)
    return {"key": key, "value": body.value, "updated_by": body.updated_by, "status": "ok"}


@router.delete("/config/{key}", summary="Delete a runtime config entry")
async def delete_config(key: str):
    from app.services.kernel.config_service import get_config_service
    deleted = await get_config_service().delete(key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    return {"key": key, "status": "deleted"}


# ── GET /kernel/discovery ─────────────────────────────────────────────────────

@router.get("/discovery", summary="Service discovery registry snapshot")
async def get_discovery():
    from app.services.kernel.service_discovery import get_service_discovery
    return await get_service_discovery().snapshot()


# ── GET /kernel/plugins ───────────────────────────────────────────────────────

@router.get("/plugins", summary="Plugin loader registry snapshot")
async def get_plugins():
    from app.services.kernel.plugin_loader import get_plugin_loader
    return get_plugin_loader().snapshot()


# ── GET /kernel/failover ──────────────────────────────────────────────────────

@router.get("/failover", summary="Failover controller status")
async def get_failover():
    from app.services.kernel.failover_controller import get_failover_controller
    return await get_failover_controller().status()


# ── GET /kernel/audit ─────────────────────────────────────────────────────────

@router.get("/audit", summary="Recent audit entries")
async def get_audit(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
):
    from app.services.kernel.audit_logger import AuditLogger
    entries = await AuditLogger(db).recent(limit=limit)
    return [
        {
            "id": str(e.id),
            "action_type": e.action_type,
            "actor": e.actor,
            "outcome": e.outcome,
            "resource_id": str(e.resource_id) if e.resource_id else None,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


# ── GET /kernel/sync ──────────────────────────────────────────────────────────

@router.get("/sync", summary="Sync protocol epoch snapshot")
async def get_sync():
    from app.services.kernel.sync_protocol import get_sync_protocol
    return await get_sync_protocol().snapshot()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _safe(coro, _key: str):
    try:
        return await coro
    except Exception as exc:
        log.warning("dashboard._safe[%s]: %s", _key, exc)
        return {"error": str(exc)}


async def _safe_sync(fn, _key: str):
    try:
        return fn()
    except Exception as exc:
        log.warning("dashboard._safe_sync[%s]: %s", _key, exc)
        return {"error": str(exc)}
