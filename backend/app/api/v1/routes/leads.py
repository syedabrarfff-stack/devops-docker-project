from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.services.leads import engine as leads
from app.services.leads.discovery import lead_discovery_engine

router = APIRouter(prefix="/leads", tags=["Leads"])


class LeadIn(BaseModel):
    company: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    pain_points: Optional[list[str]] = None
    opportunity_type: Optional[str] = None
    source: Optional[str] = "manual"
    notes: Optional[str] = None


class DiscoverLeadsRequest(BaseModel):
    limit: int = 50
    industry: Optional[str] = None
    country: Optional[str] = None
    location: Optional[str] = None
    query: Optional[str] = None
    targets: Optional[list[dict]] = None
    tenant_id: Optional[UUID] = None


@router.post("/")
async def create_lead(
    body: LeadIn,
    background_tasks: BackgroundTasks,
    auto_score: bool = True,
    db: AsyncSession = Depends(get_db),
):
    lead = await leads.create_lead(db, body.model_dump(exclude_none=True))
    await db.commit()
    if auto_score:
        background_tasks.add_task(_score_in_background, lead.id)
    return {"id": lead.id, "company": lead.company, "status": lead.status}


async def _score_in_background(lead_id: int):
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await leads.qualify_and_score(db, lead_id)


@router.get("/")
async def list_leads(
    status: Optional[str] = None,
    min_score: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    rows = await leads.list_leads(db, status=status, min_score=min_score, limit=limit)
    return [{
        "id": l.id, "company": l.company, "contact_name": l.contact_name,
        "email": l.email, "industry": l.industry, "country": l.country,
        "score": l.score, "tier": l.tier, "status": l.status,
        "outreach_sent": l.outreach_sent, "source": l.source,
        "pain_points": l.pain_points or [],
    } for l in rows]


@router.post("/{lead_id}/score")
async def score_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    lead = await leads.qualify_and_score(db, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    await db.commit()
    return {"id": lead.id, "score": lead.score, "tier": lead.tier,
            "status": lead.status, "ai_analysis": lead.ai_analysis}


@router.post("/bulk-score")
async def bulk_score(limit: int = Query(20, le=50), db: AsyncSession = Depends(get_db)):
    count = await leads.bulk_score(db, limit=limit)
    await db.commit()
    return {"scored": count}


@router.post("/score-all")
async def score_all(limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    count = await leads.bulk_score(db, limit=limit)
    await db.commit()
    return {"scored": count, "limit": limit, "status": "complete"}


@router.post("/discover")
async def discover_leads(body: DiscoverLeadsRequest, request: Request):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    limit = max(1, min(body.limit, 100))
    targets = body.targets or _default_discovery_targets(limit)
    if body.query or body.industry or body.country or body.location:
        targets = [{
            "query": body.query or body.industry or "business operations automation",
            "industry": body.industry,
            "country": body.country,
            "location": body.location or body.country,
            "limit": limit,
        }]

    inserted = await lead_discovery_engine.run_daily_discovery(tenant_id, targets)
    return {
        "tenant_id": str(tenant_id),
        "inserted": inserted,
        "targets": len(targets),
        "limit": limit,
        "status": "complete",
    }


@router.get("/stats")
async def lead_stats(db: AsyncSession = Depends(get_db)):
    return await leads.lead_stats(db)


@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: UUID,
    status: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.lead import Lead
    from app.services.demos.builder import demo_builder

    tenant_id = _resolve_tenant_id(request, None)
    next_status = _normalise_lead_status(status)
    lead = await db.scalar(
        select(Lead).where(Lead.tenant_id == tenant_id, Lead.id == lead_id)
    )
    if not lead:
        raise HTTPException(404, "Lead not found")
    lead.status = next_status
    await db.commit()
    demo_package_id = None
    if status.lower().strip() in {"demo_scheduled", "demo", "call_scheduled"}:
        demo = await demo_builder.generate(
            tenant_id,
            lead_id=lead.id,
            industry=lead.industry,
            pain_points=lead.pain_points or [],
            company_name=lead.company_name or lead.company,
        )
        demo_package_id = str(demo.id)
    return {"id": str(lead.id), "status": lead.status.value, "demo_package_id": demo_package_id}


def _normalise_lead_status(status: str):
    from app.models.lead import LeadStatus

    value = status.strip().upper()
    aliases = {
        "DEMO_SCHEDULED": LeadStatus.DEMO,
        "CALL_SCHEDULED": LeadStatus.DEMO,
        "INTERESTED": LeadStatus.DEMO,
    }
    if value in aliases:
        return aliases[value]
    try:
        return LeadStatus(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unsupported lead status: {status}") from exc


def _resolve_tenant_id(request: Request, explicit_tenant_id: Optional[UUID]) -> UUID:
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


def _default_discovery_targets(limit: int) -> list[dict]:
    per_target = max(1, min(25, limit // 4 or limit))
    return [
        {
            "query": "SaaS companies operations automation",
            "industry": "SaaS",
            "country": "United Kingdom",
            "location": "London",
            "limit": per_target,
        },
        {
            "query": "professional services appointment workflow",
            "industry": "Professional Services",
            "country": "United Arab Emirates",
            "location": "Dubai",
            "limit": per_target,
        },
        {
            "query": "home services booking automation",
            "industry": "Home Services",
            "country": "United States",
            "location": "Austin",
            "limit": per_target,
        },
        {
            "query": "recruitment agency CRM automation",
            "industry": "Recruitment",
            "country": "Canada",
            "location": "Toronto",
            "limit": per_target,
        },
    ]
