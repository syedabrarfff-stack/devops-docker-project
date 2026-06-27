"""
JARVIS Scheduler — manage cron/interval/one-shot agent jobs.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field
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
    job_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1_000)
    hour: int = Field(default=8, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    timezone: str = Field(default="UTC", max_length=50)
    agent: str = Field(default="jarvis", max_length=100)
    task_type: str = Field(default="custom", max_length=50)
    payload: Optional[dict] = None


class IntervalJobIn(BaseModel):
    job_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1_000)
    hours: float = Field(default=0, ge=0, le=168)
    minutes: float = Field(default=0, ge=0, le=1440)
    seconds: float = Field(default=0, ge=0, le=86400)
    agent: str = Field(default="jarvis", max_length=100)
    task_type: str = Field(default="custom", max_length=50)
    payload: Optional[dict] = None


class OneshotJobIn(BaseModel):
    job_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    run_at: datetime
    agent: str = Field(default="jarvis", max_length=100)
    task_type: str = Field(default="custom", max_length=50)
    payload: Optional[dict] = None


@router.get("/jobs")
async def list_jobs():
    """List all scheduled jobs from APScheduler."""
    return get_jobs()


@router.post("/jobs/cron")
async def create_cron_job(body: CronJobIn, request: Request, db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_captain)):
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
async def create_interval_job(body: IntervalJobIn, request: Request, db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_captain)):
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
async def delete_job(job_id: str, request: Request, db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_captain)):
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
async def pause(job_id: str, _: dict = Depends(get_current_captain)):
    ok = pause_job(job_id)
    if not ok:
        raise HTTPException(404, "Job not found")
    return {"paused": True, "job_id": job_id}


@router.post("/jobs/{job_id}/resume")
async def resume(job_id: str, _: dict = Depends(get_current_captain)):
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
    else:
        query = query.where(JobFailure.status.in_(("open", "retry_scheduled", "failed")))
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


@router.patch("/failures/{failure_id}/resolve", dependencies=[Depends(get_current_captain)])
async def resolve_job_failure(failure_id: str, db: AsyncSession = Depends(get_db)):
    """Mark an open job failure as resolved."""
    from sqlalchemy import select
    from app.models.scheduling import JobFailure

    try:
        fid = uuid.UUID(failure_id)
    except ValueError:
        raise HTTPException(400, "Invalid failure ID")

    row = (await db.execute(select(JobFailure).where(JobFailure.id == fid))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Failure not found")

    row.status = "resolved"
    await db.commit()
    return {"id": failure_id, "status": "resolved"}


@router.post("/jobs/{job_id}/trigger", dependencies=[Depends(get_current_captain)])
async def trigger_job_now(job_id: str):
    """Trigger a scheduled job to run immediately (within 2 seconds)."""
    from datetime import timezone, timedelta
    from app.services.scheduler.engine import get_scheduler

    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found in scheduler")

    run_at = datetime.now(timezone.utc) + timedelta(seconds=2)
    scheduler.modify_job(job_id, next_run_time=run_at)
    return {"job_id": job_id, "status": "triggered", "runs_at": run_at.isoformat()}


def _metadata_tenant_id(request: Request) -> uuid.UUID:
    raw = getattr(request.state, "tenant_id", None) or settings.JARVIS_DEFAULT_TENANT_ID
    if not raw:
        return SYSTEM_TENANT_ID
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))
