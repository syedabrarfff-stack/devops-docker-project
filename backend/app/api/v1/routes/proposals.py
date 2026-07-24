import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from app.api.v1.routes.auth import get_current_captain
from app.core.rate_limit import limiter
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db, set_tenant_context
from app.models.governance import Proposal
from app.models.lead import Lead
from app.services.governance.proposal_generator import proposal_generator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/proposals", tags=["Proposals"], dependencies=[Depends(get_current_captain)])


class GenerateProposalRequest(BaseModel):
    lead_id: UUID
    package_tier: str = Field("STARTER", pattern="^(STARTER|GROWTH|ENTERPRISE|starter|growth|enterprise)$")
    tenant_id: Optional[UUID] = None


class ProposalActionRequest(BaseModel):
    tenant_id: Optional[UUID] = None


@router.post("/generate")
@limiter.limit("30/minute")
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
        logger.error("Proposal generation failed for lead %s: %s", body.lead_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Proposal generation failed") from exc

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


@router.get("/{proposal_id}/preview")
async def preview_proposal(proposal_id: int, request: Request, tenant_id: Optional[UUID] = None):
    resolved = _resolve_tenant_id(request, tenant_id)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(resolved))
            proposal = await session.scalar(
                select(Proposal).where(Proposal.id == proposal_id, Proposal.tenant_id == resolved)
            )
            if not proposal:
                raise HTTPException(status_code=404, detail="Proposal not found")
    return {
        "proposal_id": proposal.id,
        "client_company": proposal.client_company or proposal.client_name,
        "client_name": proposal.client_name,
        "client_email": proposal.client_email,
        "package_tier": proposal.package_tier,
        "invoice_number": proposal.invoice_number,
        "status": proposal.status,
        "pdf_url": proposal.pdf_url,
        "content": proposal.content or "",
        "pricing": proposal.pricing or {},
        "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
    }


@router.post("/{proposal_id}/approve")
@limiter.limit("10/minute")
async def approve_proposal(proposal_id: int, request: Request, body: ProposalActionRequest = Body(default_factory=ProposalActionRequest)):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        approval = await proposal_generator.submit_for_approval(proposal_id, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Approval submission failed for proposal %s: %s", proposal_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Approval submission failed") from exc
    return {"proposal_id": proposal_id, "tenant_id": str(tenant_id), "approval": approval}


@router.post("/{proposal_id}/send")
@limiter.limit("5/minute")
async def send_proposal(proposal_id: int, request: Request, body: ProposalActionRequest = Body(default_factory=ProposalActionRequest)):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        result = await proposal_generator.send(proposal_id, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Proposal send failed for proposal %s: %s", proposal_id, exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Proposal delivery failed") from exc
    return {"tenant_id": str(tenant_id), **result}


@router.post("/{proposal_id}/generate-contract")
@limiter.limit("10/minute")
async def generate_contract_from_proposal(
    proposal_id: int,
    request: Request,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """Generate a contract from an approved (or pending) proposal in one click."""
    from app.services.governance.document_gen import generate_contract

    resolved = _resolve_tenant_id(request, tenant_id)
    await set_tenant_context(db, str(resolved))

    proposal = await db.scalar(
        select(Proposal).where(Proposal.id == proposal_id, Proposal.tenant_id == resolved)
    )
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if not (proposal.client_name or proposal.client_email or proposal.client_company):
        raise HTTPException(status_code=400, detail="Proposal has no client details — cannot generate contract")

    existing = await db.scalar(
        select(Proposal).where(Proposal.id == proposal_id)  # reuse to get contract model
    )
    from app.models.governance import Contract
    existing_contract = await db.scalar(
        select(Contract).where(Contract.proposal_id == proposal_id)
    )

    service_type = (
        proposal.service_type
        or (proposal.package_tier + " — Aliyar Solutions" if proposal.package_tier else "Technology Services")
    )
    scope = proposal.scope or proposal.content or "As per the approved proposal."
    if isinstance(scope, str) and len(scope) > 1500:
        scope = scope[:1500] + "…"

    contract = await generate_contract(
        db=db,
        proposal_id=proposal_id,
        client_name=proposal.client_name or "",
        client_email=proposal.client_email or "",
        client_company=proposal.client_company or "",
        service_type=service_type,
        scope=scope,
        pricing=proposal.pricing or {},
    )
    await db.commit()

    return {
        "generated": True,
        "proposal_id": proposal_id,
        "contract_id": contract["id"],
        "contract_status": contract["status"],
        "client_company": proposal.client_company or proposal.client_name,
        "package_tier": proposal.package_tier,
        "content_preview": (contract.get("content") or "")[:300],
        "already_existed": existing_contract is not None,
        "next_step": "Review the contract, then use POST /governance/contracts/{id}/status to mark as 'sent' after delivering to client.",
    }


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
