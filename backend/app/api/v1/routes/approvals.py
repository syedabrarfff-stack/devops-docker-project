from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.approval import ApprovalRequest, ApprovalStatus
from app.services.governance.captain_queue import captain_queue

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    action_type: str = Field(..., max_length=100)
    summary: str = Field(..., min_length=1, max_length=5_000)
    risk_level: str = Field(default="medium", max_length=20)
    estimated_cost: Optional[str] = Field(default=None, max_length=100)
    benefits: Optional[str] = Field(default=None, max_length=5_000)
    risks: Optional[str] = Field(default=None, max_length=5_000)
    rollback_plan: Optional[str] = Field(default=None, max_length=5_000)
    payload: dict = {}
    tenant_id: Optional[UUID] = None


class ApprovalDecision(BaseModel):
    status: str = Field(..., max_length=50)
    captain_note: Optional[str] = Field(default=None, max_length=2_000)
    tenant_id: Optional[UUID] = None


class ApprovalAction(BaseModel):
    captain_note: Optional[str] = Field(default=None, max_length=2_000)
    reason: Optional[str] = Field(default=None, max_length=2_000)
    tenant_id: Optional[UUID] = None


@router.get("")
async def list_approvals(request: Request, status: str = "pending", tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    status_enum = _status_enum(status)

    if status_enum == ApprovalStatus.PENDING:
        rows = await captain_queue.get_pending(resolved_tenant_id)
        return [_serialize(row) for row in rows]

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(resolved_tenant_id))
            rows = (
                await session.execute(
                    select(ApprovalRequest)
                    .where(ApprovalRequest.tenant_id == resolved_tenant_id, ApprovalRequest.status == status_enum)
                    .order_by(ApprovalRequest.created_at.desc())
                    .limit(50)
                )
            ).scalars().all()
            return [_serialize(row) for row in rows]


@router.get("/pending")
async def pending_approvals(request: Request, tenant_id: Optional[UUID] = None):
    return await list_approvals(request, status="pending", tenant_id=tenant_id)


@router.post("")
async def create_approval(request: Request, data: ApprovalCreate):
    resolved_tenant_id = _resolve_tenant_id(request, data.tenant_id)
    payload = {
        **(data.payload or {}),
        "tenant_id": str(resolved_tenant_id),
        "estimated_cost": data.estimated_cost,
        "benefits": data.benefits,
        "risks": data.risks,
        "rollback_plan": data.rollback_plan,
    }
    approval = await captain_queue.add_item(
        action_type=data.action_type,
        title=data.title,
        summary=data.summary,
        payload=payload,
        risk_level=data.risk_level,
        tenant_id=resolved_tenant_id,
    )

    if data.estimated_cost or data.benefits or data.risks or data.rollback_plan:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await set_tenant_context(session, str(resolved_tenant_id))
                live = await session.scalar(
                    select(ApprovalRequest).where(
                        ApprovalRequest.tenant_id == resolved_tenant_id,
                        ApprovalRequest.id == approval.id,
                    )
                )
                if live:
                    live.estimated_cost = data.estimated_cost
                    live.benefits = data.benefits
                    live.risks = data.risks
                    live.rollback_plan = data.rollback_plan
                    approval = live

    return _serialize(approval)


@router.post("/{approval_id}/decide")
async def decide_approval(
    approval_id: str,
    request: Request,
    decision: ApprovalDecision = Body(...),
    _: dict = Depends(get_current_captain),
):
    resolved_tenant_id = _resolve_tenant_id(request, decision.tenant_id)
    status = decision.status.lower().strip()
    try:
        if status == "approved":
            return await captain_queue.approve(approval_id, decision.captain_note, resolved_tenant_id)
        if status == "rejected":
            return await captain_queue.reject(approval_id, decision.captain_note, resolved_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    raise HTTPException(status_code=400, detail="status must be approved or rejected")


@router.post("/{approval_id}/approve")
async def approve_approval(
    approval_id: str,
    request: Request,
    action: ApprovalAction = Body(default_factory=ApprovalAction),
    _: dict = Depends(get_current_captain),
):
    resolved_tenant_id = _resolve_tenant_id(request, action.tenant_id)
    try:
        return await captain_queue.approve(approval_id, action.captain_note, resolved_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{approval_id}/reject")
async def reject_approval(
    approval_id: str,
    request: Request,
    action: ApprovalAction = Body(default_factory=ApprovalAction),
    _: dict = Depends(get_current_captain),
):
    resolved_tenant_id = _resolve_tenant_id(request, action.tenant_id)
    note = action.reason or action.captain_note
    try:
        return await captain_queue.reject(approval_id, note, resolved_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/count")
async def approval_count(request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return {"pending": await captain_queue.pending_count(resolved_tenant_id)}


def _resolve_tenant_id(request: Request, explicit_tenant_id: Optional[UUID]) -> UUID:
    from app.core.config import settings

    tenant_id = (
        explicit_tenant_id
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc


def _status_enum(status: str) -> ApprovalStatus:
    normalized = status.upper().strip()
    try:
        return ApprovalStatus(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="status must be pending, approved, or rejected") from exc


def _serialize(approval: ApprovalRequest) -> dict:
    status = approval.status.value if hasattr(approval.status, "value") else str(approval.status)
    return {
        "id": str(approval.id),
        "title": approval.title,
        "action_type": approval.action_type,
        "summary": approval.summary,
        "risk_level": (approval.risk_level or "medium").lower(),
        "priority": approval.priority,
        "estimated_cost": approval.estimated_cost,
        "benefits": approval.benefits,
        "risks": approval.risks,
        "rollback_plan": approval.rollback_plan,
        "payload": approval.payload or {},
        "status": status.lower(),
        "captain_note": approval.captain_note,
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
    }
