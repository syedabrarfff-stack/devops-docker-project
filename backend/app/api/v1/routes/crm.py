from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.services.crm import service as crm

router = APIRouter(prefix="/crm", tags=["CRM"])


class ContactIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = Field(default=None, max_length=320)
    phone: Optional[str] = Field(default=None, max_length=30)
    title: Optional[str] = Field(default=None, max_length=200)
    linkedin: Optional[str] = Field(default=None, max_length=500)
    company_id: Optional[int] = None
    country: Optional[str] = Field(default=None, max_length=100)
    source: Optional[str] = Field(default="manual", max_length=100)
    notes: Optional[str] = Field(default=None, max_length=10_000)
    tags: Optional[list[str]] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=320)
    phone: Optional[str] = Field(default=None, max_length=30)
    title: Optional[str] = Field(default=None, max_length=200)
    status: Optional[str] = Field(default=None, max_length=50)
    score: Optional[int] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = Field(default=None, max_length=10_000)
    tags: Optional[list[str]] = None


class CompanyIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    domain: Optional[str] = Field(default=None, max_length=253)
    industry: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    size: Optional[str] = Field(default=None, max_length=50)
    revenue_range: Optional[str] = Field(default=None, max_length=100)
    tech_stack: Optional[list[str]] = None
    pain_points: Optional[list[str]] = None
    notes: Optional[str] = Field(default=None, max_length=10_000)


class DealIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    contact_id: Optional[int] = None
    company_id: Optional[int] = None
    value: Optional[float] = Field(default=0.0, ge=0)
    currency: Optional[str] = Field(default="USD", max_length=10)
    stage: Optional[str] = Field(default="discovery", max_length=50)
    probability: Optional[int] = Field(default=20, ge=0, le=100)
    service_type: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=10_000)


class DealUpdate(BaseModel):
    stage: Optional[str] = Field(default=None, max_length=50)
    value: Optional[float] = Field(default=None, ge=0)
    probability: Optional[int] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = Field(default=None, max_length=10_000)


# ── Contacts ────────────────────────────────────────────────────────────────

@router.post("/contacts")
@limiter.limit("20/minute")
async def create_contact(request: Request, body: ContactIn, db: AsyncSession = Depends(get_db)):
    try:
        contact = await crm.create_contact(db, body.model_dump(exclude_none=True))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Contact with this email already exists")
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail="Database error") from exc
    return {"id": contact.id, "name": contact.name, "email": contact.email}


@router.get("/contacts")
async def list_contacts(
    status: Optional[str] = None,
    company_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    contacts = await crm.list_contacts(db, status=status, company_id=company_id, limit=limit)
    return [{"id": c.id, "name": c.name, "email": c.email, "title": c.title,
             "country": c.country, "status": c.status, "score": c.score,
             "tags": c.tags or [], "source": c.source} for c in contacts]


@router.patch("/contacts/{contact_id}")
@limiter.limit("30/minute")
async def update_contact(contact_id: int, request: Request, body: ContactUpdate, db: AsyncSession = Depends(get_db)):
    resolved = _resolve_crm_tenant_id(request, None)
    contact = await crm.update_contact(db, contact_id, body.model_dump(exclude_none=True), tenant_id=resolved)
    if not contact:
        raise HTTPException(404, "Contact not found")
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Update conflicts with existing record")
    return {"id": contact.id, "status": contact.status}


@router.get("/contacts/stats")
async def contact_stats(db: AsyncSession = Depends(get_db)):
    return await crm.contact_stats(db)


# ── Companies ────────────────────────────────────────────────────────────────

@router.post("/companies")
@limiter.limit("20/minute")
async def create_company(request: Request, body: CompanyIn, db: AsyncSession = Depends(get_db)):
    try:
        company = await crm.create_company(db, body.model_dump(exclude_none=True))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Company already exists")
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail="Database error") from exc
    return {"id": company.id, "name": company.name}


@router.get("/companies")
async def list_companies(
    industry: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    companies = await crm.list_companies(db, industry=industry, country=country, limit=limit)
    return [{"id": c.id, "name": c.name, "domain": c.domain, "industry": c.industry,
             "country": c.country, "size": c.size, "score": c.score} for c in companies]


# ── Deals ────────────────────────────────────────────────────────────────────

@router.post("/deals")
@limiter.limit("20/minute")
async def create_deal(request: Request, body: DealIn, db: AsyncSession = Depends(get_db)):
    try:
        deal = await crm.create_deal(db, body.model_dump(exclude_none=True))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Deal already exists")
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail="Database error") from exc
    return {"id": deal.id, "title": deal.title, "stage": deal.stage}


@router.get("/deals")
async def list_deals(
    stage: Optional[str] = None,
    min_value: float = 0,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    deals = await crm.list_deals(db, stage=stage, min_value=min_value, limit=limit)
    return [{"id": d.id, "title": d.title, "stage": d.stage, "value": d.value,
             "currency": d.currency, "probability": d.probability,
             "service_type": d.service_type} for d in deals]


@router.patch("/deals/{deal_id}")
@limiter.limit("30/minute")
async def update_deal(deal_id: int, request: Request, body: DealUpdate, db: AsyncSession = Depends(get_db)):
    resolved = _resolve_crm_tenant_id(request, None)
    deal = await crm.update_deal(db, deal_id, body.model_dump(exclude_none=True), tenant_id=resolved)
    if not deal:
        raise HTTPException(404, "Deal not found")
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail="Database error") from exc
    return {"id": deal.id, "stage": deal.stage, "value": deal.value}


@router.get("/deals/pipeline")
async def pipeline_stats(db: AsyncSession = Depends(get_db)):
    return await crm.pipeline_stats(db)


# ── Relationship Graph ────────────────────────────────────────────────────────

class RelationshipNodeIn(BaseModel):
    entity_type: str = Field(..., max_length=100)
    entity_id: str = Field(..., max_length=200)
    attributes: dict = {}
    tenant_id: Optional[UUID] = None


class RelationshipEdgeIn(BaseModel):
    from_node_id: str = Field(..., max_length=200)
    to_node_id: str = Field(..., max_length=200)
    relationship_type: str = Field(..., max_length=100)
    strength: float = 1.0
    tenant_id: Optional[UUID] = None


def _resolve_crm_tenant_id(request: Request, explicit: Optional[UUID]) -> UUID:
    from app.core.config import settings
    tenant_id = (
        explicit
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    try:
        return UUID(str(tenant_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")


@router.get("/relationship-graph")
async def get_relationship_graph(
    request: Request,
    tenant_id: Optional[UUID] = None,
    entity_type: Optional[str] = None,
):
    """Get relationship graph summary and node list."""
    from app.services.crm.relationship_graph import relationship_graph

    resolved = _resolve_crm_tenant_id(request, tenant_id)
    summary = await relationship_graph.get_graph_summary(resolved)
    nodes = await relationship_graph.list_nodes(resolved, entity_type=entity_type)
    return {**summary, "nodes": nodes}


@router.post("/relationship-graph/node")
@limiter.limit("20/minute")
async def add_relationship_node(request: Request, body: RelationshipNodeIn):
    """Add or update a node in the relationship graph."""
    from app.services.crm.relationship_graph import relationship_graph

    resolved = _resolve_crm_tenant_id(request, body.tenant_id)
    result = await relationship_graph.add_node(
        resolved, body.entity_type, body.entity_id, body.attributes
    )
    return result


@router.post("/relationship-graph/edge")
@limiter.limit("20/minute")
async def add_relationship_edge(request: Request, body: RelationshipEdgeIn):
    """Add a relationship edge between two nodes."""
    from app.services.crm.relationship_graph import relationship_graph

    resolved = _resolve_crm_tenant_id(request, body.tenant_id)
    result = await relationship_graph.add_edge(
        resolved, body.from_node_id, body.to_node_id, body.relationship_type, body.strength
    )
    return result


@router.get("/relationship-graph/warm-intros/{lead_id}")
async def get_warm_intros(
    lead_id: str,
    request: Request,
    tenant_id: Optional[UUID] = None,
):
    """Find warm introduction paths from existing contacts to a target lead."""
    from app.services.crm.relationship_graph import relationship_graph

    resolved = _resolve_crm_tenant_id(request, tenant_id)
    intros = await relationship_graph.get_warm_intros(resolved, lead_id)
    return {
        "tenant_id": str(resolved),
        "target_lead_id": lead_id,
        "intro_paths": intros,
        "count": len(intros),
    }


class HubSpotSyncRequest(BaseModel):
    tenant_id: Optional[UUID] = None


@router.post("/hubspot-sync")
@limiter.limit("5/minute")
async def sync_to_hubspot(request: Request, body: HubSpotSyncRequest):
    """Push qualified JARVIS leads to HubSpot CRM as contacts and deals."""
    from app.services.integrations.hubspot_sync import hubspot_sync

    resolved = _resolve_crm_tenant_id(request, body.tenant_id)
    result = await hubspot_sync.sync_all_qualified_leads(tenant_id=resolved)
    return {
        "tenant_id": str(resolved),
        **result,
        "message": f"HubSpot sync complete — {result.get('synced', 0)} leads pushed, {result.get('errors', 0)} errors.",
    }


@router.post("/hubspot-sync/{lead_id}")
@limiter.limit("10/minute")
async def sync_single_lead_to_hubspot(request: Request, lead_id: UUID, tenant_id: Optional[UUID] = None):
    """Push one specific lead to HubSpot immediately."""
    from app.services.integrations.hubspot_sync import hubspot_sync

    resolved = _resolve_crm_tenant_id(request, tenant_id)
    result = await hubspot_sync.push_single_lead(lead_id, resolved)
    return {"lead_id": str(lead_id), "tenant_id": str(resolved), **result}
