"""E7-9: Engineering Organization Dashboard API.

All endpoints require Captain JWT auth, matching every other Headquarters
route. This is a read/trigger surface over the Phase 7 engineering org —
see docs/architecture/HEADQUARTERS_ENGINEERING_ORG.md.

Endpoints:
  GET  /engineering/departments             — the 12-department catalogue
  GET  /engineering/dashboard                — overview: graphs + work package counts
  POST /engineering/objectives               — submit a new objective to the Mission Planner
  GET  /engineering/task-graphs/{id}         — one task graph with all its work packages
  POST /engineering/task-graphs/{id}/dispatch — dispatch ready work packages
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.auth import get_current_captain
from app.core.database import get_db as get_async_db
from app.models.engineering import EngineeringTaskGraph, EngineeringWorkPackage
from app.services.engineering import department_registry, dispatcher, mission_planner

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/engineering",
    tags=["Engineering Organization"],
    dependencies=[Depends(get_current_captain)],
)


class ObjectiveBody(BaseModel):
    objective: str = Field(..., min_length=3, max_length=4000)
    objective_type: str = Field(default="feature", max_length=20)
    context: dict[str, Any] = Field(default_factory=dict)


@router.get("/departments")
async def list_departments() -> dict:
    return {
        "departments": [
            {
                "id": d.dept_id,
                "name": d.name,
                "owns": d.owns,
                "path_globs": list(d.path_globs),
                "builder": d.builder or "claude-only",
                "default_operation": d.default_operation,
            }
            for d in department_registry.all_departments()
        ]
    }


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_async_db)) -> dict:
    graph_count = (await db.execute(select(func.count(EngineeringTaskGraph.id)))).scalar_one()

    status_rows = (
        await db.execute(
            select(EngineeringWorkPackage.status, func.count(EngineeringWorkPackage.id))
            .group_by(EngineeringWorkPackage.status)
        )
    ).all()
    by_status = {status: count for status, count in status_rows}

    dept_rows = (
        await db.execute(
            select(EngineeringWorkPackage.department, func.count(EngineeringWorkPackage.id))
            .group_by(EngineeringWorkPackage.department)
        )
    ).all()
    by_department = {dept: count for dept, count in dept_rows}

    recent = (
        await db.execute(
            select(EngineeringTaskGraph).order_by(EngineeringTaskGraph.created_at.desc()).limit(10)
        )
    ).scalars().all()

    return {
        "total_task_graphs": graph_count,
        "work_packages_by_status": by_status,
        "work_packages_by_department": by_department,
        "recent_task_graphs": [
            {
                "id": str(g.id),
                "objective": g.objective,
                "objective_type": g.objective_type,
                "status": g.status,
                "decomposed_by": g.decomposed_by,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            for g in recent
        ],
    }


@router.post("/objectives")
async def submit_objective(body: ObjectiveBody, db: AsyncSession = Depends(get_async_db)) -> dict:
    graph = await mission_planner.decompose_objective(
        db, body.objective, body.objective_type, context=body.context
    )
    await db.commit()
    return await _task_graph_detail(db, graph.id)


@router.get("/task-graphs/{graph_id}")
async def task_graph_detail(graph_id: uuid.UUID, db: AsyncSession = Depends(get_async_db)) -> dict:
    return await _task_graph_detail(db, graph_id)


async def _task_graph_detail(db: AsyncSession, graph_id: uuid.UUID) -> dict:
    graph = await db.get(EngineeringTaskGraph, graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="task graph not found")

    packages = (
        await db.execute(
            select(EngineeringWorkPackage).where(EngineeringWorkPackage.task_graph_id == graph_id)
        )
    ).scalars().all()

    return {
        "id": str(graph.id),
        "objective": graph.objective,
        "objective_type": graph.objective_type,
        "status": graph.status,
        "decomposed_by": graph.decomposed_by,
        "created_at": graph.created_at.isoformat() if graph.created_at else None,
        "completed_at": graph.completed_at.isoformat() if graph.completed_at else None,
        "work_packages": [
            {
                "id": str(wp.id),
                "department": wp.department,
                "title": wp.title,
                "status": wp.status,
                "authority_tier": wp.authority_tier,
                "depends_on": [str(d) for d in (wp.depends_on or [])],
                "draft_output": wp.draft_output,
                "review_result": wp.review_result,
                "deploy_result": wp.deploy_result,
            }
            for wp in packages
        ],
    }


@router.post("/task-graphs/{graph_id}/dispatch")
async def dispatch_task_graph(graph_id: uuid.UUID, db: AsyncSession = Depends(get_async_db)) -> dict:
    graph = await db.get(EngineeringTaskGraph, graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="task graph not found")
    counts = await dispatcher.dispatch_ready_packages(db, graph_id)
    await dispatcher.refresh_graph_status(db, graph_id)
    await db.commit()
    return {"task_graph_id": str(graph_id), "dispatch_counts": counts}
