"""
JARVIS Knowledge System API — SOPs, learning records, and operational knowledge base.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class SOPRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    category: str = Field(default="general", max_length=100)
    context: str = Field(default="", max_length=8_000)


class LearningRequest(BaseModel):
    category: str = Field(..., max_length=100)
    event_type: str = Field(..., max_length=50)
    title: str = Field(..., min_length=1, max_length=300)
    what_happened: str = Field(..., max_length=10_000)
    lesson: str = Field(..., max_length=5_000)
    what_worked: str = Field(default="", max_length=5_000)
    what_failed: str = Field(default="", max_length=5_000)
    impact_score: int = Field(default=5, ge=1, le=10)
    source: str = Field(default="system", max_length=100)


class KnowledgeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    category: str = Field(..., max_length=100)
    content: str = Field(..., min_length=1, max_length=100_000)
    tags: List[str] = Field(default_factory=list)
    source: str = Field(default="manual", max_length=100)


@router.get("/sops")
async def list_sops(category: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    from app.services.knowledge.manager import get_sops
    return {"sops": await get_sops(db, category=category)}


@router.post("/sops/generate")
async def generate_sop(req: SOPRequest, db: AsyncSession = Depends(get_db)):
    from app.services.knowledge.manager import generate_sop
    async with db.begin():
        sop = await generate_sop(db, req.title, req.category, req.context)
    if not sop:
        from fastapi import HTTPException
        raise HTTPException(500, "SOP generation failed — check AI provider configuration")
    return {"sop": sop}


@router.get("/learnings")
async def list_learnings(
    category: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    from app.services.knowledge.manager import get_learnings
    return {"learnings": await get_learnings(db, category=category, limit=limit)}


@router.post("/learnings")
async def log_learning(req: LearningRequest, db: AsyncSession = Depends(get_db)):
    from app.services.knowledge.manager import log_learning
    async with db.begin():
        record = await log_learning(
            db,
            category=req.category,
            event_type=req.event_type,
            title=req.title,
            what_happened=req.what_happened,
            lesson=req.lesson,
            what_worked=req.what_worked,
            what_failed=req.what_failed,
            impact_score=req.impact_score,
            source=req.source,
        )
    return {"learning": record}


@router.get("/search")
async def search_knowledge(q: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    from app.services.knowledge.manager import search_knowledge
    return {"results": await search_knowledge(db, query=q, limit=limit)}


@router.post("/entries")
async def add_knowledge_entry(req: KnowledgeRequest, db: AsyncSession = Depends(get_db)):
    from app.services.knowledge.manager import add_knowledge
    async with db.begin():
        entry = await add_knowledge(db, req.title, req.category, req.content, req.tags, req.source)
    return {"entry": entry}


@router.get("/stats")
async def knowledge_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, func
    from app.models.knowledge import SOPDocument, LearningRecord, KnowledgeBase

    sop_count = (await db.execute(select(func.count()).select_from(SOPDocument).where(SOPDocument.is_active == True))).scalar() or 0
    learning_count = (await db.execute(select(func.count()).select_from(LearningRecord))).scalar() or 0
    kb_count = (await db.execute(select(func.count()).select_from(KnowledgeBase))).scalar() or 0
    top_lessons = await (lambda: db.execute(
        select(LearningRecord).order_by(LearningRecord.impact_score.desc()).limit(3)
    ))()
    top = [{"title": r.title, "lesson": r.lesson, "score": r.impact_score} for r in top_lessons.scalars().all()]

    return {
        "active_sops": sop_count,
        "learning_records": learning_count,
        "knowledge_entries": kb_count,
        "top_lessons": top,
    }
