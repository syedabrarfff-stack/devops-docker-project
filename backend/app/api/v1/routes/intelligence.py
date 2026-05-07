"""
JARVIS Intelligence API — Tech Radar, Self-Optimization, Research Division.
Phase 5: Autonomous learning and continuous self-improvement.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    topic: str
    category: str = "market"


class StatusUpdate(BaseModel):
    status: str  # approved | implemented | dismissed


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
