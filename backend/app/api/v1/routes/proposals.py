from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.governance import Proposal
from app.models.lead import Lead
from app.services.governance.proposal_generator import proposal_generator

router = APIRouter(prefix="/proposals", tags=["Proposals"])


class GenerateProposalRequest(BaseModel):
    lead_id: UUID
    package_tier: str = Field("STARTER", pattern="^(STARTER|GROWTH|ENTERPRISE|starter|growth|enterprise)$")
    tenant_id: Optional[UUID] = None


class ProposalActionRequest(BaseModel):
    tenant_id: Optional[UUID] = None


@router.post("/generate")
async def generate_proposal(request: Request, body: GenerateProposalRequest):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_id))
            lead = await session.scalar(
                select(Lead).where(Lead.tenant_id == tenant_id, Lead.id == body.lead_id)
            )
            if not lead:
                raise HTTPException(status_code=404, detail="Lead not found")

    try:
        pdf_path = await proposal_generator.generate(lead, body.package_tier, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Proposal generation failed: {exc}") from exc

    proposal = await _latest_proposal_for_lead(tenant_id, body.lead_id)
    return {
        "generated": True,
        "tenant_id": str(tenant_id),
        "lead_id": str(body.lead_id),
        "proposal_id": proposal.id if proposal else None,
        "package_tier": body.package_tier.upper(),
        "pdf_path": pdf_path,
        "pdf_url": proposal.pdf_url if proposal else pdf_path,
        "invoice_number": proposal.invoice_number if proposal else None,
        "requires_captain_approval": True,
    }


@router.post("/{proposal_id}/approve")
async def approve_proposal(proposal_id: int, request: Request, body: ProposalActionRequest = Body(default_factory=ProposalActionRequest)):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        approval = await proposal_generator.submit_for_approval(proposal_id, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Approval request failed: {exc}") from exc
    return {"proposal_id": proposal_id, "tenant_id": str(tenant_id), "approval": approval}


@router.post("/{proposal_id}/send")
async def send_proposal(proposal_id: int, request: Request, body: ProposalActionRequest = Body(default_factory=ProposalActionRequest)):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        result = await proposal_generator.send(proposal_id, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Proposal send failed: {exc}") from exc
    return {"tenant_id": str(tenant_id), **result}


async def _latest_proposal_for_lead(tenant_id: UUID, lead_id: UUID) -> Proposal | None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_id))
            return await session.scalar(
                select(Proposal)
                .where(Proposal.tenant_id == tenant_id, Proposal.lead_id == lead_id)
                .order_by(Proposal.created_at.desc())
                .limit(1)
            )


def _resolve_tenant_id(request: Request, explicit_tenant_id: Optional[UUID]) -> UUID:
    tenant_id = (
        explicit_tenant_id
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
    )
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc
