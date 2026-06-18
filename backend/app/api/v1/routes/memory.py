from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.services.memory import manager as mem
from app.services.memory.graph import graph_status, search_memory_graph, seed_memory_graph
from app.services.memory.human_intelligence import HUMAN_INTELLIGENCE_KB, seed_human_intelligence

router = APIRouter(prefix="/memory", tags=["Memory"])


class MemoryIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=32_000)
    memory_type: Optional[str] = Field(default="episodic", max_length=50)
    session_id: Optional[str] = Field(default=None, max_length=120)
    importance: Optional[int] = Field(default=5, ge=1, le=10)
    tags: Optional[list[str]] = None


class InstructionIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=32_000)
    category: Optional[str] = Field(default="general", max_length=100)
    priority: Optional[int] = Field(default=5, ge=1, le=10)


class MemorySearchIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=2_000)
    limit: int = Field(default=5, ge=1, le=50)
    tenant_id: Optional[UUID] = None


@router.post("/store")
async def store_memory(body: MemoryIn, db: AsyncSession = Depends(get_db)):
    memory = await mem.store_memory(db, **body.model_dump(exclude_none=True))
    await db.commit()
    return {"id": memory.id, "memory_type": memory.memory_type}


@router.get("/recall")
async def recall_memory(
    query: str,
    session_id: Optional[str] = None,
    memory_type: Optional[str] = None,
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    memories = await mem.recall(db, query=query, session_id=session_id,
                                memory_type=memory_type, limit=limit)
    return [{
        "id": m.id, "content": m.content, "memory_type": m.memory_type,
        "importance": m.importance, "tags": m.tags or [],
        "created_at": str(m.created_at),
    } for m in memories]


@router.post("/instructions")
async def store_instruction(body: InstructionIn, db: AsyncSession = Depends(get_db)):
    memory = await mem.store_instruction(db, **body.model_dump(exclude_none=True))
    await db.commit()
    return {"id": memory.id, "category": memory.tags}


@router.get("/instructions")
async def get_instructions(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    instructions = await mem.get_instructions(db, category=category)
    return [{"id": i.id, "content": i.content, "priority": i.importance,
             "tags": i.tags or []} for i in instructions]


@router.get("/context")
async def build_context(
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    context = await mem.build_context(db, session_id=session_id)
    return {"context": context, "session_id": session_id}


@router.post("/summarize")
async def summarize_session(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await mem.maybe_summarise(db, session_id=session_id, force=True)
    await db.commit()
    return {"summarized": bool(result), "session_id": session_id}


@router.post("/seed")
async def seed_enterprise_memory(request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await seed_memory_graph(resolved_tenant_id)


@router.post("/search")
async def semantic_memory_search(body: MemorySearchIn, request: Request):
    resolved_tenant_id = _resolve_tenant_id(request, body.tenant_id)
    limit = max(1, min(body.limit, 25))
    return await search_memory_graph(body.query, resolved_tenant_id, limit=limit)


@router.get("/status")
async def enterprise_memory_status(request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await graph_status(resolved_tenant_id)


@router.post("/human-intelligence/seed")
async def seed_human_intelligence_memory(request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return await seed_human_intelligence(resolved_tenant_id)


@router.get("/human-intelligence")
async def get_human_intelligence():
    return HUMAN_INTELLIGENCE_KB


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
