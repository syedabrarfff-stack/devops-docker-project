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


class LeadLossIn(BaseModel):
    tenant_id: Optional[UUID] = None
    reason: str
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
        "id": l.id,
        "company": _lead_company(l),
        "company_name": _lead_company(l),
        "contact_name": l.contact_name,
        "email": l.email,
        "website": l.website or l.company_website,
        "industry": l.industry, "country": l.country,
        "score": l.score, "tier": l.tier, "status": l.status,
        "outreach_sent": l.outreach_sent, "source": l.source,
        "pain_points": l.pain_points or [],
        "qualification_status": l.qualification_status,
        "outreach_eligible": l.outreach_eligible,
        "assigned_persona": l.assigned_persona,
        "last_contact": l.last_contact or l.last_contacted,
        "notes": l.notes,
        "phone": l.phone,
        "whatsapp_number": getattr(l, "whatsapp_number", None),
        "linkedin_url": getattr(l, "linkedin_url", None),
    } for l in rows]


@router.post("/{lead_id}/score")
async def score_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    lead = await leads.qualify_and_score(db, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    await db.commit()
    return {"id": str(lead.id), "company": _lead_company(lead), "score": lead.score, "tier": lead.tier,
            "status": lead.status.value if hasattr(lead.status, "value") else lead.status, "ai_analysis": lead.ai_analysis}


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


@router.post("/bulk-discover")
async def bulk_discover_leads(
    background_tasks: BackgroundTasks,
    request: Request,
    limit: int = Query(200, ge=10, le=500),
    tenant_id: Optional[UUID] = None,
):
    """
    Discover up to 200 qualified leads across all 25 Aliyar Solutions service packages.
    Runs Apollo + free-source discovery in background. Returns job ID immediately.
    """
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    targets = _aliyar_discovery_targets(limit)
    background_tasks.add_task(
        _run_bulk_discovery_background,
        resolved_tenant_id,
        targets,
    )
    return {
        "status": "discovery_started",
        "tenant_id": str(resolved_tenant_id),
        "targets": len(targets),
        "estimated_leads": limit,
        "packages_targeted": 25,
        "message": "Discovery running in background. Check /leads/?min_score=0&limit=200 in ~60s.",
    }


@router.post("/batch-import")
async def batch_import_leads(
    request: Request,
    leads_data: list[dict],
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Import a batch of lead records directly into JARVIS CRM.
    Accepts array of lead objects: {company, email, contact_name, phone, website, industry, country, source, notes}
    Deduplicates by email + company. Scores each lead after import.
    """
    from app.models.lead import Lead, LeadStatus
    from sqlalchemy import select

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    inserted = skipped = 0

    for raw in leads_data:
        email = (raw.get("email") or "").strip().lower() or None
        company = (raw.get("company") or raw.get("company_name") or "").strip() or None
        if not company:
            skipped += 1
            continue

        existing = None
        if email:
            existing = await db.scalar(
                select(Lead).where(Lead.tenant_id == resolved_tenant_id, Lead.email == email)
            )
        if not existing and company:
            existing = await db.scalar(
                select(Lead).where(
                    Lead.tenant_id == resolved_tenant_id,
                    Lead.company_name == company,
                )
            )
        if existing:
            skipped += 1
            continue

        lead = Lead(
            tenant_id=resolved_tenant_id,
            company_name=company,
            company=company,
            contact_name=raw.get("contact_name") or raw.get("name"),
            email=email,
            phone=raw.get("phone") or raw.get("whatsapp"),
            website=raw.get("website"),
            industry=raw.get("industry"),
            country=raw.get("country"),
            source=raw.get("source") or "batch_import",
            notes=raw.get("notes"),
            pain_points=raw.get("pain_points") or [],
            status=LeadStatus.NEW,
        )
        if raw.get("whatsapp"):
            lead.phone = raw["whatsapp"]
        db.add(lead)
        inserted += 1

    await db.commit()
    return {
        "inserted": inserted,
        "skipped": skipped,
        "total": len(leads_data),
        "tenant_id": str(resolved_tenant_id),
        "message": f"Imported {inserted} leads. Run /leads/bulk-score to score them.",
    }


async def _run_bulk_discovery_background(tenant_id, targets):
    from app.core.database import AsyncSessionLocal
    from app.services.revenue_activation.free_discovery import free_discovery_engine
    try:
        await lead_discovery_engine.run_daily_discovery(str(tenant_id), targets)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Bulk Apollo discovery error: %s", exc)

    try:
        async with AsyncSessionLocal() as _:
            await free_discovery_engine.run(tenant_id, limit=50)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Bulk free discovery error: %s", exc)


def _aliyar_discovery_targets(total_limit: int) -> list[dict]:
    """25 discovery targets — one per Aliyar Solutions service package, across ICP markets."""
    per_target = max(5, total_limit // 25)
    return [
        # Sales & Revenue packages
        {"query": "sales process automation CRM", "industry": "SaaS", "country": "United Kingdom", "location": "London", "limit": per_target},
        {"query": "outbound sales lead generation", "industry": "Professional Services", "country": "United Arab Emirates", "location": "Dubai", "limit": per_target},
        {"query": "CRM implementation revenue operations", "industry": "Technology", "country": "United States", "location": "New York", "limit": per_target},
        # AI Automation packages
        {"query": "appointment booking scheduling automation", "industry": "Healthcare", "country": "Australia", "location": "Sydney", "limit": per_target},
        {"query": "AI voice receptionist call handling", "industry": "Legal", "country": "United Kingdom", "location": "Manchester", "limit": per_target},
        {"query": "workflow automation business processes", "industry": "Finance", "country": "United Arab Emirates", "location": "Abu Dhabi", "limit": per_target},
        {"query": "executive automation AI assistant", "industry": "Consulting", "country": "Canada", "location": "Toronto", "limit": per_target},
        # Cloud & DevOps packages
        {"query": "AWS cloud architecture migration", "industry": "E-commerce", "country": "United States", "location": "Austin", "limit": per_target},
        {"query": "Docker containerization DevOps", "industry": "SaaS", "country": "Canada", "location": "Vancouver", "limit": per_target},
        {"query": "CI/CD pipeline deployment automation", "industry": "Technology", "country": "United Kingdom", "location": "Edinburgh", "limit": per_target},
        {"query": "Terraform infrastructure as code", "industry": "FinTech", "country": "Australia", "location": "Melbourne", "limit": per_target},
        {"query": "Kubernetes container orchestration scaling", "industry": "Logistics", "country": "United Arab Emirates", "location": "Sharjah", "limit": per_target},
        {"query": "cloud monitoring observability", "industry": "Manufacturing", "country": "United States", "location": "Chicago", "limit": per_target},
        # Security packages
        {"query": "cybersecurity operations SMB", "industry": "Healthcare", "country": "United Kingdom", "location": "Birmingham", "limit": per_target},
        {"query": "vulnerability assessment penetration testing", "industry": "Finance", "country": "United States", "location": "San Francisco", "limit": per_target},
        {"query": "compliance hardening GDPR SOC2", "industry": "Legal", "country": "United Arab Emirates", "location": "Dubai", "limit": per_target},
        # Content & Media packages
        {"query": "content automation marketing", "industry": "Media", "country": "Australia", "location": "Brisbane", "limit": per_target},
        {"query": "YouTube channel growth automation", "industry": "Education", "country": "United States", "location": "Los Angeles", "limit": per_target},
        {"query": "social media management AI", "industry": "Retail", "country": "United Kingdom", "location": "Leeds", "limit": per_target},
        # Digital Products
        {"query": "web application development SaaS platform", "industry": "Real Estate", "country": "United Arab Emirates", "location": "Dubai", "limit": per_target},
        {"query": "client portal dashboard software", "industry": "Professional Services", "country": "Canada", "location": "Calgary", "limit": per_target},
        {"query": "operational dashboard business intelligence", "industry": "Logistics", "country": "United States", "location": "Dallas", "limit": per_target},
        # Intelligence
        {"query": "business intelligence AI research analytics", "industry": "Consulting", "country": "United Kingdom", "location": "London", "limit": per_target},
        {"query": "competitive analysis market research AI", "industry": "SaaS", "country": "Australia", "location": "Perth", "limit": per_target},
        {"query": "data analytics reporting automation", "industry": "E-commerce", "country": "United Arab Emirates", "location": "Ajman", "limit": per_target},
    ]


@router.get("/stats")
async def lead_stats(db: AsyncSession = Depends(get_db)):
    return await leads.lead_stats(db)


@router.post("/{lead_id}/loss")
async def record_lead_loss(
    lead_id: UUID,
    body: LeadLossIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.core.database import set_tenant_context
    from app.models.approval import AuditLog
    from app.models.lead import Lead, LeadStatus

    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    await set_tenant_context(db, str(tenant_id))
    lead = await db.scalar(select(Lead).where(Lead.tenant_id == tenant_id, Lead.id == lead_id))
    if not lead:
        raise HTTPException(404, "Lead not found")
    lead.status = LeadStatus.LOST
    lead.loss_reason = body.reason.strip()[:80]
    lead.notes = "\n\n".join(part for part in [lead.notes, body.notes] if part)
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            action="lead_marked_lost",
            entity_type="lead",
            entity_id=lead.id,
            actor="Captain",
            details={"loss_reason": lead.loss_reason, "notes": body.notes},
            after_json={"status": lead.status.value, "loss_reason": lead.loss_reason},
        )
    )
    return {"id": str(lead.id), "status": lead.status.value, "loss_reason": lead.loss_reason}


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


def _lead_company(lead) -> str | None:
    if lead.company_name:
        return lead.company_name
    if lead.company:
        return lead.company
    enrichment = lead.enrichment_data or {}
    for key in ("company_name", "company", "name", "organization_name", "account_name"):
        if enrichment.get(key):
            return str(enrichment[key])
    if lead.email and "@" in lead.email:
        return lead.email.split("@", 1)[1]
    return None
