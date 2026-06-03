"""
JARVIS Intelligence API — Tech Radar, Self-Optimization, Research Division.
Phase 5: Autonomous learning and continuous self-improvement.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    topic: str
    category: str = "market"


class StatusUpdate(BaseModel):
    status: str  # approved | implemented | dismissed


class TeachRequest(BaseModel):
    title: str
    learning: str
    category: str = "outreach_intelligence"
    source_type: str = "captain_manual"
    source_id: Optional[str] = None
    score: float = 80.0
    evidence: Optional[dict] = None
    applies_to: Optional[dict] = None
    tenant_id: Optional[UUID] = None


# ── Tech Radar ────────────────────────────────────────────────────────────────

@router.get("/radar")
async def get_tech_radar(db: AsyncSession = Depends(get_db)):
    from app.services.intelligence.tech_radar import get_radar
    return await get_radar(db)


@router.post("/radar/scan")
async def trigger_tech_scan(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.tech_radar import scan_technologies
        async with AsyncSessionLocal() as session:
            async with session.begin():
                count = await scan_technologies(session)
        return count

    background_tasks.add_task(_run)
    return {"queued": True, "message": "Tech radar scan initiated. Results will be available shortly."}


# ── Optimization Recommendations ──────────────────────────────────────────────

@router.get("/recommendations")
async def get_recommendations(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    from app.services.intelligence.optimizer import get_recommendations
    return {"recommendations": await get_recommendations(db, status=status)}


@router.post("/recommendations/analyze")
async def trigger_analysis(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.optimizer import analyze_system
        async with AsyncSessionLocal() as session:
            async with session.begin():
                count = await analyze_system(session)
        return count

    background_tasks.add_task(_run)
    return {"queued": True, "message": "System analysis initiated. Recommendations will appear shortly."}


@router.post("/recommendations/{rec_id}/approve")
async def approve_recommendation(rec_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.intelligence.optimizer import update_recommendation_status
    async with db.begin():
        ok = await update_recommendation_status(db, rec_id, "approved")
    if not ok:
        raise HTTPException(404, "Recommendation not found")
    return {"id": rec_id, "status": "approved"}


@router.post("/recommendations/{rec_id}/dismiss")
async def dismiss_recommendation(rec_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.intelligence.optimizer import update_recommendation_status
    async with db.begin():
        ok = await update_recommendation_status(db, rec_id, "dismissed")
    if not ok:
        raise HTTPException(404, "Recommendation not found")
    return {"id": rec_id, "status": "dismissed"}


@router.post("/recommendations/{rec_id}/implement")
async def mark_implemented(rec_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.intelligence.optimizer import update_recommendation_status
    async with db.begin():
        ok = await update_recommendation_status(db, rec_id, "implemented")
    if not ok:
        raise HTTPException(404, "Recommendation not found")
    return {"id": rec_id, "status": "implemented"}


# ── Research Reports ──────────────────────────────────────────────────────────

@router.get("/reports")
async def get_reports(limit: int = 20, db: AsyncSession = Depends(get_db)):
    from app.services.intelligence.research import get_reports
    return {"reports": await get_reports(db, limit=limit)}


@router.post("/reports/generate")
async def generate_report(
    req: ReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    async def _run(topic: str, category: str):
        from app.core.database import AsyncSessionLocal
        from app.services.intelligence.research import generate_report as _gen
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await _gen(session, topic, category)

    background_tasks.add_task(_run, req.topic, req.category)
    return {"queued": True, "topic": req.topic, "message": "Research report generation initiated."}


# ── System Pulse ─────────────────────────────────────────────────────────────

@router.get("/pulse")
async def intelligence_pulse(db: AsyncSession = Depends(get_db)):
    """Real-time snapshot of the intelligence layer health."""
    from app.services.ai.router import ai_router
    from sqlalchemy import select, func
    from app.models.intelligence import TechRadarEntry, OptimizationRecommendation, ResearchReport

    radar_count = (await db.execute(select(func.count()).select_from(TechRadarEntry))).scalar() or 0
    rec_count = (await db.execute(select(func.count()).select_from(OptimizationRecommendation))).scalar() or 0
    pending_recs = (
        await db.execute(
            select(func.count())
            .select_from(OptimizationRecommendation)
            .where(OptimizationRecommendation.status == "pending")
        )
    ).scalar() or 0
    report_count = (await db.execute(select(func.count()).select_from(ResearchReport))).scalar() or 0

    return {
        "status": "operational",
        "ai_providers": ai_router.get_provider_status(),
        "available_providers": ai_router.available_providers(),
        "intelligence": {
            "tech_radar_entries": radar_count,
            "optimization_recommendations": rec_count,
            "pending_recommendations": pending_recs,
            "research_reports": report_count,
        },
        "scheduled_jobs": [
            "weekly_tech_radar_scan (Mon 06:00 UTC)",
            "daily_optimization_review (23:00 UTC)",
            "biweekly_research_report (Sun 07:00 UTC)",
        ],
    }


@router.get("/competitors")
async def get_competitors(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.competitor_intel import list_competitor_profiles

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    profiles = await list_competitor_profiles(resolved_tenant_id)
    return {"count": len(profiles), "competitors": profiles}


@router.post("/competitors/seed")
async def seed_competitors(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.competitor_intel import (
        list_competitor_profiles,
        seed_competitor_profiles,
    )

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    seed_result = await seed_competitor_profiles(resolved_tenant_id)
    profiles = await list_competitor_profiles(resolved_tenant_id)
    return {**seed_result, "count": len(profiles), "competitors": profiles}


@router.get("/outreach-learnings")
async def get_outreach_learnings(
    request: Request,
    tenant_id: Optional[UUID] = None,
    category: Optional[str] = None,
    limit: int = 50,
):
    from app.services.revenue_activation.teaching_engine import teaching_engine

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await teaching_engine.list_learnings(
        resolved_tenant_id,
        category=category,
        limit=limit,
    )


@router.post("/teach")
async def teach_jarvis(request: Request, body: TeachRequest):
    from app.services.revenue_activation.teaching_engine import teaching_engine

    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    return await teaching_engine.teach(
        tenant_id=resolved_tenant_id,
        title=body.title,
        learning=body.learning,
        category=body.category,
        source_type=body.source_type,
        source_id=body.source_id,
        score=body.score,
        evidence=body.evidence,
        applies_to=body.applies_to,
        created_by="Captain",
    )


# ── Batch-2 Intelligence Engines ─────────────────────────────────────────────

class ProspectPsychologyRequest(BaseModel):
    lead_id: UUID
    tenant_id: Optional[UUID] = None
    use_ai: bool = False


class RevenueForecastRequest(BaseModel):
    tenant_id: Optional[UUID] = None
    iterations: int = 1000
    horizon_days: int = 90


class DynamicPricingRequest(BaseModel):
    service_type: str
    lead_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    context: Optional[dict] = None


class GovernanceEvaluateRequest(BaseModel):
    action_type: str
    payload: dict = {}
    tenant_id: Optional[UUID] = None


@router.post("/prospect-psychology")
async def prospect_psychology(
    req: ProspectPsychologyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from app.services.intelligence.prospect_psychology import prospect_psychology_engine
    from sqlalchemy import select
    from app.models.lead import Lead

    tenant_id = _resolve_tenant_id(request, req.tenant_id)

    result = await db.execute(
        select(Lead).where(Lead.id == req.lead_id, Lead.tenant_id == tenant_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = {
        "company_name": lead.company_name,
        "company": lead.company,
        "industry": lead.industry,
        "notes": lead.notes,
        "pain_points": lead.pain_points,
        "score": lead.score,
        "enrichment_data": lead.enrichment_data,
        "opportunity_type": lead.opportunity_type,
        "country": lead.country,
    }

    if req.use_ai:
        profile = await prospect_psychology_engine.analyze_with_ai(lead_data, tenant_id)
    else:
        profile = prospect_psychology_engine.profile(lead_data)

    return {"lead_id": str(req.lead_id), "tenant_id": str(tenant_id), "profile": profile}


@router.post("/revenue-forecast")
async def revenue_forecast(req: RevenueForecastRequest, request: Request):
    from app.services.intelligence.revenue_forecaster import revenue_forecaster

    tenant_id = _resolve_tenant_id(request, req.tenant_id)
    result = await revenue_forecaster.run_monte_carlo(
        tenant_id=tenant_id,
        iterations=req.iterations,
        horizon_days=req.horizon_days,
    )
    return {"tenant_id": str(tenant_id), "forecast": result}


@router.get("/self-assessment")
async def self_assessment(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.self_assessment import jarvis_self_assessment

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    report = await jarvis_self_assessment.run_assessment(resolved_tenant_id)
    return {"tenant_id": str(resolved_tenant_id), "assessment": report}


@router.post("/dynamic-pricing")
async def dynamic_pricing(
    req: DynamicPricingRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from app.services.intelligence.dynamic_pricing import dynamic_pricing_engine
    from sqlalchemy import select
    from app.models.lead import Lead

    tenant_id = _resolve_tenant_id(request, req.tenant_id)
    lead_data: dict = {}

    if req.lead_id:
        result = await db.execute(
            select(Lead).where(Lead.id == req.lead_id, Lead.tenant_id == tenant_id)
        )
        lead = result.scalar_one_or_none()
        if lead:
            lead_data = {
                "company_name": lead.company_name,
                "industry": lead.industry,
                "score": lead.score,
                "country": lead.country,
                "notes": lead.notes,
                "pain_points": lead.pain_points,
                "enrichment_data": lead.enrichment_data or {},
            }

    pricing = dynamic_pricing_engine.calculate_price(
        service_type=req.service_type,
        lead_data=lead_data,
        context=req.context,
    )
    return {
        "tenant_id": str(tenant_id),
        "lead_id": str(req.lead_id) if req.lead_id else None,
        "pricing": pricing,
    }


@router.post("/governance/evaluate")
async def governance_evaluate(req: GovernanceEvaluateRequest, request: Request):
    from app.services.governance.autonomous_governance import autonomous_governance

    tenant_id = _resolve_tenant_id(request, req.tenant_id)
    evaluation = autonomous_governance.evaluate_action(
        action_type=req.action_type,
        payload=req.payload,
        tenant_id=tenant_id,
    )
    return {"tenant_id": str(tenant_id), "evaluation": evaluation}


@router.get("/governance/summary")
async def governance_summary(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.governance.autonomous_governance import autonomous_governance

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    summary = await autonomous_governance.get_governance_summary(resolved_tenant_id)
    return {"tenant_id": str(resolved_tenant_id), **summary}


@router.get("/client-health")
async def client_health_all(request: Request, tenant_id: Optional[UUID] = None):
    from app.services.intelligence.client_health import client_health_scorer

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    scores = await client_health_scorer.score_all_clients(resolved_tenant_id)
    return {
        "tenant_id": str(resolved_tenant_id),
        "count": len(scores),
        "clients": scores,
        "at_risk": [c for c in scores if c["health_tier"] in ("AT_RISK", "CRITICAL")],
    }


@router.get("/pricing/catalog")
async def pricing_catalog():
    from app.services.intelligence.dynamic_pricing import dynamic_pricing_engine
    return dynamic_pricing_engine.get_service_catalog_pricing()


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
