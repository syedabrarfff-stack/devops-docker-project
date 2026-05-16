from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.lead import WorkflowRun
from app.services.operations.capabilities import n8n_status
from app.services.storage.secure import get_credential


router = APIRouter(prefix="/automation", tags=["Automation"])


WORKFLOWS = {
    "revenue_engine": {
        "name": "Revenue Engine",
        "description": "Discover leads, qualify contacts, draft outreach/proposals, and create Captain approval packets.",
        "risk": "low",
        "approval_rule": "Discovery and drafting auto-run; external sends require approval execution.",
    },
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


class RevenueRunRequest(BaseModel):
    limit: int = Field(default=25, ge=1, le=100)
    create_proposals: bool = True


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

    if workflow_key == "local_market_discovery":
        result = await _run_local_market_discovery(db, req.input)
        run.status = "completed" if result.get("ok") else "blocked"
        run.steps_done = 1 if result.get("ok") else 0
        run.result = result.get("message")
        run.error = result.get("error")
        run.metadata_ = {**(run.metadata_ or {}), "internal_runner": True, "result": result}
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(run)
        return _serialize_run(run)

    if workflow_key == "revenue_engine":
        result = await _run_internal_revenue_engine(db, req.input)
        run.status = "completed" if result.get("ok") else "blocked"
        run.steps_done = 1 if result.get("ok") else 0
        run.result = result.get("message")
        run.error = result.get("error")
        run.metadata_ = {**(run.metadata_ or {}), "internal_runner": True, "result": result}
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(run)
        return _serialize_run(run)

    if workflow_key == "sales_war_room":
        result = await _run_sales_war_room(db)
        run.status = "completed"
        run.steps_done = 1
        run.result = result.get("message")
        run.metadata_ = {**(run.metadata_ or {}), "internal_runner": True, "result": result}
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(run)
        return _serialize_run(run)

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


@router.post("/revenue/run")
async def run_revenue(req: RevenueRunRequest = RevenueRunRequest(), db: AsyncSession = Depends(get_db)):
    from app.services.revenue.engine import run_revenue_engine

    result = await run_revenue_engine(db, limit=req.limit, create_proposals=req.create_proposals)
    await db.commit()
    return {"status": "completed", "result": result}


@router.post("/revenue/approvals/{approval_id}/execute")
async def execute_revenue_approval(approval_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.revenue.engine import execute_approved_outreach_batch

    result = await execute_approved_outreach_batch(db, approval_id)
    await db.commit()
    return result


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


async def _run_local_market_discovery(db: AsyncSession, payload: dict) -> dict:
    from app.api.v1.routes.discovery import LocalMarketRequest, local_market_discovery

    try:
        request = LocalMarketRequest(
            industry=payload.get("industry") or payload.get("market") or "clinics",
            location=payload.get("location") or "New York",
            service_angle=payload.get("service_angle") or "AI receptionist and appointment booking",
            limit=int(payload.get("limit") or 20),
        )
        result = await local_market_discovery(request, db)
        return {
            "ok": True,
            "message": f"Local Market Hunter completed: {result['created']} created, {result['updated']} updated from {result['total_candidates']} candidates.",
            "created": result["created"],
            "updated": result["updated"],
            "total_candidates": result["total_candidates"],
        }
    except HTTPException as exc:
        return {"ok": False, "error": str(exc.detail)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def _run_internal_revenue_engine(db: AsyncSession, payload: dict) -> dict:
    from app.services.revenue.engine import run_revenue_engine

    limit = int(payload.get("limit") or 25)
    create_proposals = bool(payload.get("create_proposals", True))
    try:
        result = await run_revenue_engine(db, limit=limit, create_proposals=create_proposals)
        blockers = result.get("blockers") or []
        return {
            "ok": True,
            "message": (
                f"Revenue Engine completed: {result.get('synced_contacts', 0)} synced, "
                f"{result.get('fallback_leads', 0)} fallback leads, "
                f"{result.get('drafts_created', 0)} drafts, {result.get('proposals_created', 0)} proposals, "
                f"{result.get('deals_created', 0)} deals."
                + (f" Blockers: {'; '.join(blockers)}" if blockers else "")
            ),
            **result,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def _run_sales_war_room(db: AsyncSession) -> dict:
    from app.models.approval import ApprovalRequest
    from app.models.crm import Deal
    from app.models.lead import Lead, WorkflowRun
    from app.services.contacts.sync import validate_apollo_access
    from app.services.storage.secure import get_credential

    async def scalar(stmt):
        return (await db.execute(stmt)).scalar() or 0

    total_leads = await scalar(select(func.count(Lead.id)))
    qualified_leads = await scalar(select(func.count(Lead.id)).where(Lead.status.in_(["qualified", "interested", "proposal"])))
    pending_approvals = await scalar(select(func.count(ApprovalRequest.id)).where(ApprovalRequest.status == "pending"))
    pipeline_value = await scalar(select(func.coalesce(func.sum(Deal.value), 0.0)).where(Deal.stage.notin_(["closed_lost"])))
    latest_runs_result = await db.execute(select(WorkflowRun).order_by(desc(WorkflowRun.started_at)).limit(5))
    latest_runs = [_serialize_run(run) for run in latest_runs_result.scalars().all()]

    blockers = []
    apollo_ok, apollo_message = await validate_apollo_access(db)
    if not apollo_ok:
        blockers.append(apollo_message)
    google_key = await get_credential(db, "GOOGLE_MAPS_API_KEY")
    if not google_key:
        blockers.append("GOOGLE_MAPS_API_KEY missing: local market discovery cannot pull live Google Places candidates.")
    gmail_password = await get_credential(db, "GMAIL_APP_PASSWORD")
    if not gmail_password:
        blockers.append("GMAIL_APP_PASSWORD missing: approved SMTP outreach cannot send.")

    message = (
        f"Sales War Room ready: {total_leads} total leads, {qualified_leads} qualified, "
        f"{pending_approvals} pending approvals, ${float(pipeline_value):,.0f} pipeline."
    )
    if blockers:
        message += " Current blockers: " + "; ".join(blockers)

    return {
        "ok": True,
        "message": message,
        "total_leads": total_leads,
        "qualified_leads": qualified_leads,
        "pending_approvals": pending_approvals,
        "pipeline_value": float(pipeline_value),
        "latest_runs": latest_runs,
        "blockers": blockers,
        "next_action": "Fix listed credential/account blockers, then run Revenue Engine and approve only reviewed outreach packets.",
    }
