"""
JARVIS Scheduler — manage cron/interval/one-shot agent jobs.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.services.scheduler.scheduler import (
    SYSTEM_TENANT_ID,
    enqueue_scheduled_task,
    get_jobs, add_cron_job, add_interval_job, add_oneshot_job,
    remove_job, pause_job, resume_job,
)
from app.models.scheduling import ScheduledJob

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


class CronJobIn(BaseModel):
    job_id: str
    name: str
    description: Optional[str] = None
    hour: int = 8
    minute: int = 0
    timezone: str = "UTC"
    agent: str = "jarvis"
    task_type: str = "custom"
    payload: Optional[dict] = None


class IntervalJobIn(BaseModel):
    job_id: str
    name: str
    description: Optional[str] = None
    hours: float = 0
    minutes: float = 0
    seconds: float = 0
    agent: str = "jarvis"
    task_type: str = "custom"
    payload: Optional[dict] = None


class OneshotJobIn(BaseModel):
    job_id: str
    name: str
    run_at: datetime
    agent: str = "jarvis"
    task_type: str = "custom"
    payload: Optional[dict] = None


@router.get("/jobs")
async def list_jobs():
    """List all scheduled jobs from APScheduler."""
    return get_jobs()


@router.post("/jobs/cron")
async def create_cron_job(body: CronJobIn, request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id = _metadata_tenant_id(request)
    add_cron_job(
        body.job_id,
        enqueue_scheduled_task,
        hour=body.hour,
        minute=body.minute,
        timezone_str=body.timezone,
        args=[body.job_id],
        kwargs={"tenant_id": str(tenant_id)},
    )
    # Persist in DB
    job = ScheduledJob(
        tenant_id=tenant_id,
        job_id=body.job_id, name=body.name, description=body.description,
        trigger_type="cron",
        trigger_args={"hour": body.hour, "minute": body.minute, "timezone": body.timezone},
        agent=body.agent, task_type=body.task_type, payload=body.payload or {},
    )
    db.add(job)
    await db.commit()
    return {"job_id": body.job_id, "trigger": "cron", "hour": body.hour, "minute": body.minute}


@router.post("/jobs/interval")
async def create_interval_job(body: IntervalJobIn, request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id = _metadata_tenant_id(request)
    add_interval_job(
        body.job_id,
        enqueue_scheduled_task,
        hours=body.hours,
        minutes=body.minutes,
        seconds=body.seconds,
        args=[body.job_id],
        kwargs={"tenant_id": str(tenant_id)},
    )
    job = ScheduledJob(
        tenant_id=tenant_id,
        job_id=body.job_id, name=body.name, description=body.description,
        trigger_type="interval",
        trigger_args={"hours": body.hours, "minutes": body.minutes, "seconds": body.seconds},
        agent=body.agent, task_type=body.task_type, payload=body.payload or {},
    )
    db.add(job)
    await db.commit()
    return {"job_id": body.job_id, "trigger": "interval",
            "hours": body.hours, "minutes": body.minutes}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    removed = remove_job(job_id)
    from sqlalchemy import delete
    await db.execute(
        delete(ScheduledJob).where(
            ScheduledJob.tenant_id == _metadata_tenant_id(request),
            ScheduledJob.job_id == job_id,
        )
    )
    await db.commit()
    return {"removed": removed, "job_id": job_id}


@router.post("/jobs/{job_id}/pause")
async def pause(job_id: str):
    ok = pause_job(job_id)
    if not ok:
        raise HTTPException(404, "Job not found")
    return {"paused": True, "job_id": job_id}


@router.post("/jobs/{job_id}/resume")
async def resume(job_id: str):
    ok = resume_job(job_id)
    if not ok:
        raise HTTPException(404, "Job not found")
    return {"resumed": True, "job_id": job_id}


@router.get("/jobs/db")
async def list_db_jobs(request: Request, db: AsyncSession = Depends(get_db)):
    """Jobs persisted in JARVIS DB (includes metadata)."""
    from sqlalchemy import select, desc
    rows = (await db.execute(
        select(ScheduledJob)
        .where(ScheduledJob.tenant_id == _metadata_tenant_id(request))
        .order_by(desc(ScheduledJob.created_at))
        .limit(50)
    )).scalars().all()
    return [{
        "id": j.id, "job_id": j.job_id, "name": j.name,
        "trigger_type": j.trigger_type, "trigger_args": j.trigger_args,
        "agent": j.agent, "task_type": j.task_type,
        "enabled": j.enabled, "run_count": j.run_count,
        "last_run_at": str(j.last_run_at) if j.last_run_at else None,
        "next_run_at": str(j.next_run_at) if j.next_run_at else None,
    } for j in rows]


@router.get("/failures")
async def list_job_failures(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import desc, select
    from app.models.scheduling import JobFailure

    query = select(JobFailure).where(JobFailure.tenant_id == _metadata_tenant_id(request))
    if status:
        query = query.where(JobFailure.status == status)
    rows = (
        await db.execute(
            query.order_by(desc(JobFailure.created_at)).limit(max(1, min(limit, 200)))
        )
    ).scalars().all()
    return [
        {
            "id": str(row.id),
            "job_name": row.job_name,
            "status": row.status,
            "error": row.error,
            "retry_count": row.retry_count,
            "last_retry_at": str(row.last_retry_at) if row.last_retry_at else None,
            "next_retry_at": str(row.next_retry_at) if row.next_retry_at else None,
            "created_at": str(row.created_at) if row.created_at else None,
        }
        for row in rows
    ]


def _metadata_tenant_id(request: Request) -> uuid.UUID:
    raw = getattr(request.state, "tenant_id", None) or settings.JARVIS_DEFAULT_TENANT_ID
    if not raw:
        return SYSTEM_TENANT_ID
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))
