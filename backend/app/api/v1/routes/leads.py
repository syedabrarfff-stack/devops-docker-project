import csv
import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, BackgroundTasks, Request, UploadFile
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.services.leads import engine as leads
from app.services.leads.discovery import lead_discovery_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leads", tags=["Leads"], dependencies=[Depends(get_current_captain)])

_BATCH_IMPORT_MAX = 500

_CSV_COLUMN_MAP: dict[str, str] = {
    "company": "company", "company_name": "company", "organisation": "company",
    "organization": "company", "business": "company", "firm": "company",
    "contact_name": "contact_name", "contact": "contact_name", "name": "contact_name",
    "full_name": "contact_name", "person": "contact_name", "first_name": "contact_name",
    "email": "email", "email_address": "email", "contact_email": "email",
    "phone": "phone", "telephone": "phone", "mobile": "phone",
    "whatsapp": "phone", "whatsapp_number": "phone",
    "website": "website", "url": "website", "domain": "website", "web": "website",
    "industry": "industry", "sector": "industry", "vertical": "industry",
    "country": "country", "region": "country", "location": "country",
    "source": "source", "lead_source": "source",
    "notes": "notes", "description": "notes", "comments": "notes",
    "pain_points": "pain_points", "pain points": "pain_points",
    "challenges": "pain_points", "problems": "pain_points",
    "linkedin": "linkedin_url", "linkedin_url": "linkedin_url", "linkedin_profile": "linkedin_url",
    "opportunity_type": "opportunity_type", "service": "opportunity_type",
    "service_type": "opportunity_type", "interest": "opportunity_type",
}

CSV_TEMPLATE_HEADERS = [
    "company", "contact_name", "email", "phone", "website",
    "industry", "country", "opportunity_type", "pain_points", "notes", "linkedin_url",
]


class LeadIn(BaseModel):
    company: str = Field(..., min_length=1, max_length=500)
    contact_name: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=320)
    website: Optional[str] = Field(default=None, max_length=2_000)
    industry: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    pain_points: Optional[list[str]] = None
    opportunity_type: Optional[str] = Field(default=None, max_length=100)
    source: Optional[str] = Field(default="manual", max_length=100)
    notes: Optional[str] = Field(default=None, max_length=10_000)


class DiscoverLeadsRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)
    industry: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=200)
    query: Optional[str] = Field(default=None, max_length=2_000)
    targets: Optional[list[dict]] = None
    tenant_id: Optional[UUID] = None


class LeadLossIn(BaseModel):
    tenant_id: Optional[UUID] = None
    reason: str = Field(..., min_length=1, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=5_000)


@router.post("/")
@limiter.limit("30/minute")
async def create_lead(
    request: Request,
    body: LeadIn,
    background_tasks: BackgroundTasks,
    auto_score: bool = True,
    db: AsyncSession = Depends(get_db),
):
    try:
        lead = await leads.create_lead(db, body.model_dump(exclude_none=True))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Lead with this email already exists")
    if auto_score:
        background_tasks.add_task(_score_in_background, lead.id)
    background_tasks.add_task(_notify_captain_new_lead, _lead_company(lead), lead.email, body.source, lead.contact_name)
    return {"id": lead.id, "company": _lead_company(lead), "status": lead.status}


async def _notify_captain_new_lead(company: str, email: str | None, source: str | None, contact: str | None) -> None:
    try:
        from app.services.notifications.telegram import notify_telegram
        src_label = "🌐 Website Contact" if source == "website_contact" else f"📥 {source or 'manual'}"
        contact_line = f"\n👤 *Contact:* {contact}" if contact else ""
        email_line = f"\n📧 *Email:* {email}" if email else ""
        msg = (
            f"🔔 *New Lead — {company}*\n"
            f"*Source:* {src_label}"
            f"{contact_line}"
            f"{email_line}\n\n"
            "Open JARVIS → Leads to score and action."
        )
        await notify_telegram(msg)
    except Exception as exc:
        logger.warning("Telegram lead notification failed: %s", exc)


async def _score_in_background(lead_id: UUID):
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await leads.qualify_and_score(db, lead_id)


async def _trigger_auto_outreach(lead_id: UUID, lead, tenant_id: UUID):
    """Background task: send auto-outreach email when lead qualifies."""
    from app.core.database import AsyncSessionLocal
    from app.services.outreach.auto_outreach import trigger_auto_outreach_for_lead
    import logging
    logger = logging.getLogger(__name__)

    try:
        async with AsyncSessionLocal() as db:
            lead_data = {
                "name": lead.contact_name or _lead_company(lead),
                "email": lead.email,
                "company": _lead_company(lead),
                "quality_score": float(lead.score or 0.75),
                "status": str(lead.status),
                "domain_age_days": getattr(lead, "domain_age_days", 400),
                "context": lead.notes or "",
                "tenant_id": tenant_id,
            }
            result = await trigger_auto_outreach_for_lead(
                lead_id=lead_id,
                lead_data=lead_data,
                db=db,
            )
            if result["success"]:
                logger.info("Auto-outreach triggered for lead %s", lead_id)
            else:
                logger.debug("Auto-outreach skipped for lead %s: %s", lead_id, result.get("reason"))
    except Exception as exc:
        logger.error("Auto-outreach trigger failed: %s", exc)


@router.get("/")
async def list_leads(
    status: Optional[str] = None,
    min_score: int = 0,
    limit: int = Query(50, ge=1, le=200),
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
@limiter.limit("20/minute")
async def score_lead(request: Request, lead_id: UUID, db: AsyncSession = Depends(get_db)):
    lead = await leads.qualify_and_score(db, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    await db.commit()
    return {"id": str(lead.id), "company": _lead_company(lead), "score": lead.score, "tier": lead.tier,
            "status": lead.status.value if hasattr(lead.status, "value") else lead.status, "ai_analysis": lead.ai_analysis}


@router.post("/bulk-score")
@limiter.limit("5/minute")
async def bulk_score(request: Request, limit: int = Query(20, ge=1, le=50), db: AsyncSession = Depends(get_db)):
    count = await leads.bulk_score(db, limit=limit)
    await db.commit()
    return {"scored": count}


@router.post("/score-all")
@limiter.limit("3/minute")
async def score_all(request: Request, limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    count = await leads.bulk_score(db, limit=limit)
    await db.commit()
    return {"scored": count, "limit": limit, "status": "complete"}


@router.post("/discover")
@limiter.limit("3/minute")
async def discover_leads(request: Request, body: DiscoverLeadsRequest):
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
@limiter.limit("2/minute")
async def bulk_discover_leads(
    request: Request,
    background_tasks: BackgroundTasks,
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
@limiter.limit("3/minute")
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

    if len(leads_data) > _BATCH_IMPORT_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"Batch too large: {len(leads_data)} records (max {_BATCH_IMPORT_MAX})",
        )

    inserted = skipped = 0

    for raw in leads_data:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        email = str(raw.get("email") or "").strip().lower() or None
        company = str(raw.get("company") or raw.get("company_name") or "").strip() or None
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

        phone = raw.get("phone") or raw.get("whatsapp") or raw.get("whatsapp_number")
        whatsapp = raw.get("whatsapp_number") or raw.get("whatsapp") or phone
        lead = Lead(
            tenant_id=resolved_tenant_id,
            company_name=company,
            company=company,
            contact_name=raw.get("contact_name") or raw.get("name"),
            email=email,
            phone=phone,
            whatsapp_number=whatsapp,
            linkedin_url=raw.get("linkedin_url"),
            website=raw.get("website"),
            industry=raw.get("industry"),
            country=raw.get("country"),
            source=raw.get("source") or "batch_import",
            notes=raw.get("notes"),
            pain_points=raw.get("pain_points") or [],
            status=LeadStatus.NEW,
        )
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


@router.get("/csv-template")
async def csv_template():
    """Download a blank CSV template with the correct column headers."""
    from fastapi.responses import StreamingResponse
    content = ",".join(CSV_TEMPLATE_HEADERS) + "\n"
    content += ",".join([
        "Acme Corp", "Jane Smith", "jane@acme.com", "+1-555-0100",
        "acme.com", "SaaS", "USA", "AI Automation", "manual processes|no reporting", "",
        "https://linkedin.com/in/janesmith",
    ]) + "\n"
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jarvis_leads_template.csv"},
    )


@router.post("/import-csv")
@limiter.limit("3/minute")
async def import_leads_csv(
    request: Request,
    file: UploadFile = File(...),
    tenant_id: Optional[UUID] = None,
    auto_score: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    bg: BackgroundTasks,
):
    """
    Import leads from a CSV file. Accepts any column order; maps common header variants.
    Deduplicates by email then company name. Optionally triggers AI scoring in background.
    Max 500 rows per upload.
    """
    from app.models.lead import Lead, LeadStatus
    from sqlalchemy import select

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv file")

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)

    raw_bytes = await file.read()
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        return {"inserted": 0, "skipped": 0, "errors": 0, "total": 0, "message": "CSV file is empty"}

    if len(rows) > _BATCH_IMPORT_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"CSV has {len(rows)} rows — maximum is {_BATCH_IMPORT_MAX}. Split into smaller files.",
        )

    def _map_row(raw_row: dict) -> dict:
        mapped: dict = {}
        for col, val in raw_row.items():
            key = _CSV_COLUMN_MAP.get(col.strip().lower().replace(" ", "_"))
            if key and val and val.strip():
                mapped[key] = val.strip()
        return mapped

    inserted = skipped = errors = 0

    for raw_row in rows:
        try:
            row = _map_row(raw_row)
            company = row.get("company", "").strip() or None
            if not company:
                skipped += 1
                continue

            email = row.get("email", "").strip().lower() or None

            existing = None
            if email:
                existing = await db.scalar(
                    select(Lead).where(Lead.tenant_id == resolved_tenant_id, Lead.email == email)
                )
            if not existing:
                existing = await db.scalar(
                    select(Lead).where(
                        Lead.tenant_id == resolved_tenant_id, Lead.company_name == company
                    )
                )
            if existing:
                skipped += 1
                continue

            pain_raw = row.get("pain_points", "")
            pain_points = [p.strip() for p in pain_raw.replace("|", ",").split(",") if p.strip()]

            lead = Lead(
                tenant_id=resolved_tenant_id,
                company_name=company,
                company=company,
                contact_name=row.get("contact_name") or None,
                email=email,
                phone=row.get("phone") or None,
                whatsapp_number=row.get("phone") or None,
                website=row.get("website") or None,
                industry=row.get("industry") or None,
                country=row.get("country") or None,
                source=row.get("source") or "csv_import",
                notes=row.get("notes") or None,
                pain_points=pain_points,
                opportunity_type=row.get("opportunity_type") or None,
                linkedin_url=row.get("linkedin_url") or None,
                status=LeadStatus.NEW,
            )
            db.add(lead)
            inserted += 1
        except Exception as exc:
            logger.warning("CSV row error: %s — %s", raw_row, exc)
            errors += 1

    await db.commit()

    if auto_score and inserted > 0 and bg is not None:
        bg.add_task(_score_newly_imported, resolved_tenant_id, min(inserted, 50))

    msg = f"Imported {inserted} lead{'s' if inserted != 1 else ''}"
    if skipped:
        msg += f", skipped {skipped} duplicate{'s' if skipped != 1 else ''}"
    if errors:
        msg += f", {errors} row error{'s' if errors != 1 else ''}"
    if auto_score and inserted > 0:
        msg += ". AI scoring running in background."

    return {
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "total": len(rows),
        "tenant_id": str(resolved_tenant_id),
        "message": msg,
    }


async def _score_newly_imported(tenant_id: UUID, limit: int) -> None:
    from app.core.database import AsyncSessionLocal
    from app.models.lead import Lead, LeadStatus
    from app.services.leads import engine as leads_engine
    from sqlalchemy import select
    try:
        async with AsyncSessionLocal() as db:
            unscored = await db.scalars(
                select(Lead)
                .where(Lead.tenant_id == tenant_id, Lead.score == 0, Lead.status == LeadStatus.NEW)
                .order_by(Lead.created_at.desc())
                .limit(limit)
            )
            for lead in unscored.all():
                try:
                    await leads_engine.score_lead(db, lead)
                except Exception as exc:
                    logger.warning("Background scoring failed for lead %s: %s", lead.id, exc)
            await db.commit()
    except Exception as exc:
        logger.warning("Background CSV scoring failed: %s", exc)


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


@router.get("/{lead_id}")
async def get_lead_profile(
    lead_id: UUID,
    request: Request,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """Full 360° lead profile: lead data + proposals + trust brief + outreach history."""
    from sqlalchemy import select
    from app.core.database import set_tenant_context
    from app.models.lead import Lead
    from app.models.governance import Proposal, Contract
    from app.models.trust_engine import ExecutiveOpportunityBrief
    from app.models.revenue import OutreachLog

    resolved = _resolve_tenant_id(request, tenant_id)
    await set_tenant_context(db, str(resolved))

    lead = await db.scalar(
        select(Lead).where(Lead.tenant_id == resolved, Lead.id == lead_id)
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    proposals_rows = (await db.scalars(
        select(Proposal)
        .where(Proposal.tenant_id == resolved, Proposal.lead_id == lead_id)
        .order_by(Proposal.created_at.desc())
        .limit(10)
    )).all()

    brief = await db.scalar(
        select(ExecutiveOpportunityBrief)
        .where(ExecutiveOpportunityBrief.lead_id == lead_id)
        .order_by(ExecutiveOpportunityBrief.created_at.desc())
        .limit(1)
    )

    outreach_rows = (await db.scalars(
        select(OutreachLog)
        .where(OutreachLog.tenant_id == resolved, OutreachLog.lead_id == lead_id)
        .order_by(OutreachLog.sent_at.desc())
        .limit(8)
    )).all()

    contracts_rows = (await db.scalars(
        select(Contract)
        .where(
            Contract.tenant_id == resolved,
            Contract.proposal_id.in_([p.id for p in proposals_rows]) if proposals_rows else False,
        )
        .order_by(Contract.created_at.desc())
        .limit(5)
    )).all() if proposals_rows else []

    return {
        "lead": {
            "id": str(lead.id),
            "company": _lead_company(lead),
            "contact_name": lead.contact_name,
            "email": lead.email,
            "phone": lead.phone,
            "whatsapp_number": getattr(lead, "whatsapp_number", None),
            "linkedin_url": getattr(lead, "linkedin_url", None),
            "website": lead.website or lead.company_website,
            "industry": lead.industry,
            "country": lead.country,
            "score": lead.score,
            "tier": lead.tier,
            "status": lead.status.value if hasattr(lead.status, "value") else lead.status,
            "source": lead.source,
            "pain_points": lead.pain_points or [],
            "signal_breakdown": lead.signal_breakdown or {},
            "assigned_persona": lead.assigned_persona,
            "qualification_status": lead.qualification_status,
            "outreach_eligible": lead.outreach_eligible,
            "outreach_count": lead.outreach_count,
            "last_contact": (lead.last_contact or lead.last_contacted).isoformat() if (lead.last_contact or lead.last_contacted) else None,
            "notes": lead.notes,
            "ai_analysis": getattr(lead, "ai_analysis", None),
            "loss_reason": getattr(lead, "loss_reason", None),
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
        },
        "proposals": [
            {
                "id": p.id,
                "title": p.title,
                "package_tier": p.package_tier,
                "service_type": p.service_type,
                "status": p.status,
                "invoice_number": p.invoice_number,
                "pdf_url": p.pdf_url,
                "pricing": p.pricing or {},
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in proposals_rows
        ],
        "contracts": [
            {
                "id": c.id,
                "client_company": c.client_company,
                "service_type": c.service_type,
                "status": c.status,
                "proposal_id": c.proposal_id,
                "signed_at": c.signed_at.isoformat() if c.signed_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in contracts_rows
        ],
        "trust_brief": {
            "narrative": brief.narrative,
            "opportunities": brief.opportunities or [],
            "quick_wins": brief.quick_wins or [],
            "estimated_roi": brief.estimated_roi,
            "trust_score_at_creation": brief.trust_score_at_creation,
            "created_at": brief.created_at.isoformat() if brief.created_at else None,
        } if brief else None,
        "outreach": [
            {
                "id": str(o.id),
                "channel": o.channel.value if hasattr(o.channel, "value") else o.channel,
                "subject": o.subject,
                "status": o.status.value if hasattr(o.status, "value") else o.status,
                "sent_from_persona": o.sent_from_persona,
                "sequence_step": o.sequence_step,
                "sent_at": o.sent_at.isoformat() if o.sent_at else None,
            }
            for o in outreach_rows
        ],
    }


@router.post("/{lead_id}/loss")
@limiter.limit("10/minute")
async def record_lead_loss(
    request: Request,
    lead_id: UUID,
    body: LeadLossIn,
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
    await db.commit()
    return {"id": str(lead.id), "status": lead.status.value, "loss_reason": lead.loss_reason}


@router.patch("/{lead_id}/status")
@limiter.limit("20/minute")
async def update_lead_status(
    request: Request,
    lead_id: UUID,
    status: str,
    background_tasks: BackgroundTasks,
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

    # Trigger auto-outreach if lead qualifies
    if status.lower().strip() in {"qualified", "hot", "active"}:
        background_tasks.add_task(_trigger_auto_outreach, lead_id, lead, tenant_id)

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
