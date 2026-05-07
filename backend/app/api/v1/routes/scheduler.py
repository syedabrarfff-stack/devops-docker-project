"""
JARVIS Scheduler — manage cron/interval/one-shot agent jobs.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.scheduler.engine import (
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
async def create_cron_job(body: CronJobIn, db: AsyncSession = Depends(get_db)):
    from app.services.tasks.queue import enqueue
    async def _job_fn():
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as _db:
            async with _db.begin():
                await enqueue(
                    db=_db, title=body.name, description=body.description or "",
                    task_type=body.task_type, priority=5,
                    payload=body.payload or {}, assigned_to=body.agent,
                )
    add_cron_job(body.job_id, _job_fn, hour=body.hour, minute=body.minute,
                  timezone_str=body.timezone)
    # Persist in DB
    job = ScheduledJob(
        job_id=body.job_id, name=body.name, description=body.description,
        trigger_type="cron",
        trigger_args={"hour": body.hour, "minute": body.minute, "timezone": body.timezone},
        agent=body.agent, task_type=body.task_type, payload=body.payload or {},
    )
    db.add(job)
    await db.commit()
    return {"job_id": body.job_id, "trigger": "cron", "hour": body.hour, "minute": body.minute}


@router.post("/jobs/interval")
async def create_interval_job(body: IntervalJobIn, db: AsyncSession = Depends(get_db)):
    from app.services.tasks.queue import enqueue
    async def _job_fn():
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as _db:
            async with _db.begin():
                await enqueue(
                    db=_db, title=body.name, description=body.description or "",
                    task_type=body.task_type, priority=5,
                    payload=body.payload or {}, assigned_to=body.agent,
                )
    add_interval_job(body.job_id, _job_fn, hours=body.hours, minutes=body.minutes,
                      seconds=body.seconds)
    job = ScheduledJob(
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
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    removed = remove_job(job_id)
    from sqlalchemy import delete
    await db.execute(delete(ScheduledJob).where(ScheduledJob.job_id == job_id))
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
async def list_db_jobs(db: AsyncSession = Depends(get_db)):
    """Jobs persisted in JARVIS DB (includes metadata)."""
    from sqlalchemy import select, desc
    rows = (await db.execute(
        select(ScheduledJob).order_by(desc(ScheduledJob.created_at)).limit(50)
    )).scalars().all()
    return [{
        "id": j.id, "job_id": j.job_id, "name": j.name,
        "trigger_type": j.trigger_type, "trigger_args": j.trigger_args,
        "agent": j.agent, "task_type": j.task_type,
        "enabled": j.enabled, "run_count": j.run_count,
        "last_run_at": str(j.last_run_at) if j.last_run_at else None,
        "next_run_at": str(j.next_run_at) if j.next_run_at else None,
    } for j in rows]
