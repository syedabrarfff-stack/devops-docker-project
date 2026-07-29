from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.core.rate_limit import limiter

router = APIRouter(prefix="/trust", tags=["trust"], dependencies=[Depends(get_current_captain)])


class BriefRequest(BaseModel):
    lead_id: Optional[UUID] = None
    company_name: str = Field(..., min_length=1, max_length=300)
    industry: str = Field(default="", max_length=150)
    pain_points: list[str] = Field(default_factory=list)
    tenant_id: Optional[UUID] = None


class EngagementEventRequest(BaseModel):
    lead_id: UUID
    event_type: str = Field(..., max_length=80)
    source: str = Field(default="", max_length=100)
    metadata: dict = {}


class ReferralGenerateRequest(BaseModel):
    client_id: UUID
    client_name: str = Field(..., max_length=200)
    company_name: str = Field(..., max_length=200)
    service_type: str = Field(..., max_length=200)
    mrr_usd: float = 0.0
    tenant_id: Optional[UUID] = None


@router.post("/briefs/generate")
@limiter.limit("10/minute")
async def generate_brief(request: Request, req: BriefRequest):
    from app.services.trust.brief_generator import brief_generator
    return await brief_generator.generate(
        company_name=req.company_name,
        industry=req.industry,
        pain_points=req.pain_points,
        lead_id=req.lead_id,
        tenant_id=req.tenant_id,
    )


@router.get("/briefs/{lead_id}")
async def list_briefs_for_lead(lead_id: UUID):
    from app.core.database import AsyncSessionLocal
    from app.models.trust_engine import ExecutiveOpportunityBrief
    from app.services.trust.brief_generator import brief_generator

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ExecutiveOpportunityBrief)
            .where(ExecutiveOpportunityBrief.lead_id == lead_id)
            .order_by(ExecutiveOpportunityBrief.created_at.desc())
            .limit(50)
        )
        briefs = result.scalars().all()
        return [brief_generator._serialize(b) for b in briefs]


@router.post("/engagement")
@limiter.limit("30/minute")
async def log_engagement_event(request: Request, req: EngagementEventRequest):
    from app.services.trust.scoring import log_event
    return await log_event(
        lead_id=req.lead_id,
        event_type=req.event_type,
        source=req.source,
        metadata=req.metadata,
    )


@router.get("/score/{lead_id}")
async def get_trust_score(lead_id: UUID):
    from app.services.trust.scoring import compute_scores
    return await compute_scores(lead_id)


@router.post("/referrals/generate")
@limiter.limit("5/minute")
async def generate_referrals(request: Request, req: ReferralGenerateRequest):
    from app.services.trust.referral_engine import referral_engine
    return await referral_engine.generate(
        client_id=req.client_id,
        client_name=req.client_name,
        company=req.company_name,
        service_type=req.service_type,
        mrr=req.mrr_usd,
        tenant_id=req.tenant_id,
    )


@router.get("/referrals")
async def list_referrals(status: Optional[str] = None):
    from app.core.database import AsyncSessionLocal
    from app.models.trust_engine import ReferralRequest

    async with AsyncSessionLocal() as db:
        q = select(ReferralRequest).order_by(ReferralRequest.created_at.desc()).limit(200)
        if status:
            q = q.where(ReferralRequest.status == status)
        result = await db.execute(q)
        records = result.scalars().all()
        return [
            {
                "id": r.id,
                "client_id": str(r.client_id) if r.client_id else None,
                "request_type": r.request_type,
                "content": r.content,
                "status": r.status,
                "response": r.response,
                "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                "responded_at": r.responded_at.isoformat() if r.responded_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in records
        ]
