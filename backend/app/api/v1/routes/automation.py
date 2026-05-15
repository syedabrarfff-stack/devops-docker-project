from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.lead import WorkflowRun
from app.services.operations.capabilities import n8n_status
from app.services.storage.secure import get_credential


router = APIRouter(prefix="/automation", tags=["Automation"])


WORKFLOWS = {
    "local_market_discovery": {
        "name": "Local Market Hunter",
        "description": "Find local businesses with Google Places, analyze pain, create CRM leads, and prepare outreach.",
        "risk": "low",
        "approval_rule": "Safe discovery auto-runs; external outreach requires approval.",
    },
    "sales_war_room": {
        "name": "Sales War Room",
        "description": "Summarize pipeline, top opportunities, drafts, blockers, and next approvals.",
        "risk": "low",
        "approval_rule": "Reporting auto-runs.",
    },
    "approved_outreach_send": {
        "name": "Approved Outreach Send",
        "description": "Send a Captain-approved Gmail outreach message and record the result.",
        "risk": "medium",
        "approval_rule": "Always requires an approved approval_request payload.",
    },
}


class WorkflowRunRequest(BaseModel):
    input: dict = Field(default_factory=dict)


@router.get("/n8n/status")
async def get_n8n_status(db: AsyncSession = Depends(get_db)):
    return await n8n_status(db)


@router.get("/workflows")
async def list_workflows():
    return {"workflows": [{"key": key, **value} for key, value in WORKFLOWS.items()]}


@router.post("/workflows/{workflow_key}/run")
async def run_workflow(workflow_key: str, req: WorkflowRunRequest, db: AsyncSession = Depends(get_db)):
    if workflow_key not in WORKFLOWS:
        raise HTTPException(404, "Workflow not registered in Jarvis")

    workflow = WORKFLOWS[workflow_key]
    run = WorkflowRun(
        workflow_id=workflow_key,
        workflow_name=workflow["name"],
        status="running",
        steps_total=1,
        steps_done=0,
        metadata_={"input": req.input, "approval_rule": workflow["approval_rule"]},
    )
    db.add(run)
    await db.flush()

    webhook_base = await get_credential(db, "N8N_WEBHOOK_BASE_URL")
    n8n_api_key = await get_credential(db, "N8N_API_KEY")

    if webhook_base:
        url = f"{webhook_base.rstrip('/')}/{workflow_key}"
        try:
            headers = {"X-Jarvis-Run-Id": str(run.id)}
            if n8n_api_key:
                headers["X-N8N-API-KEY"] = n8n_api_key
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json={"run_id": run.id, "workflow_key": workflow_key, **req.input}, headers=headers)
            run.status = "completed" if response.status_code < 400 else "blocked"
            run.steps_done = 1 if response.status_code < 400 else 0
            run.result = response.text[:4000]
            if response.status_code >= 400:
                run.error = f"n8n webhook returned HTTP {response.status_code}"
        except Exception as exc:
            run.status = "blocked"
            run.error = str(exc)
    else:
        run.status = "blocked"
        run.error = "N8N_WEBHOOK_BASE_URL missing. Add it in Access Vault to let Jarvis trigger n8n."

    run.completed_at = datetime.now(timezone.utc) if run.status in ("completed", "blocked") else None
    await db.commit()
    await db.refresh(run)
    return _serialize_run(run)


@router.get("/runs")
async def list_runs(limit: int = 25, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkflowRun).order_by(desc(WorkflowRun.started_at)).limit(limit))
    return {"runs": [_serialize_run(run) for run in result.scalars().all()]}


@router.post("/callback/n8n")
async def n8n_callback(payload: dict, db: AsyncSession = Depends(get_db)):
    run_id = payload.get("run_id")
    if not run_id:
        raise HTTPException(400, "run_id is required")
    result = await db.execute(select(WorkflowRun).where(WorkflowRun.id == int(run_id)))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Workflow run not found")

    run.status = payload.get("status", "completed")
    run.steps_done = payload.get("steps_done", run.steps_total)
    run.result = payload.get("result")
    run.error = payload.get("error")
    run.metadata_ = {**(run.metadata_ or {}), "callback": payload}
    run.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "run": _serialize_run(run)}


def _serialize_run(run: WorkflowRun) -> dict:
    return {
        "id": run.id,
        "workflow_id": run.workflow_id,
        "workflow_name": run.workflow_name,
        "status": run.status,
        "steps_total": run.steps_total,
        "steps_done": run.steps_done,
        "result": run.result,
        "error": run.error,
        "metadata": run.metadata_ or {},
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
