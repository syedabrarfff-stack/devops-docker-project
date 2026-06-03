from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.leads import engine as leads

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


@router.get("/stats")
async def lead_stats(db: AsyncSession = Depends(get_db)):
    return await leads.lead_stats(db)


@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, update
    from app.models.lead import Lead
    result = await db.execute(
        update(Lead).where(Lead.id == lead_id).values(status=status).returning(Lead.id, Lead.status)
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Lead not found")
    await db.commit()
    return {"id": row.id, "status": row.status}
