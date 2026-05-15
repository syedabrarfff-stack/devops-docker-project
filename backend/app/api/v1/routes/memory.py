from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.memory import manager as mem

router = APIRouter(prefix="/memory", tags=["Memory"])


class MemoryIn(BaseModel):
    content: str
    key: Optional[str] = None
    memory_type: Optional[str] = "episodic"
    session_id: Optional[str] = None
    importance: Optional[float] = 0.5
    tags: Optional[list[str]] = None


class InstructionIn(BaseModel):
    content: str
    key: Optional[str] = None
    category: Optional[str] = "general"
    priority: Optional[float] = 1.0


@router.post("/store")
async def store_memory(body: MemoryIn, db: AsyncSession = Depends(get_db)):
    memory = await mem.store_memory(
        db,
        key=body.key or body.content[:120],
        value=body.content,
        memory_type=body.memory_type or "episodic",
        session_id=body.session_id,
        importance=body.importance or 0.5,
        tags=body.tags or [],
    )
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
        "id": m.id, "key": m.key, "content": m.value, "memory_type": m.memory_type,
        "importance": m.importance, "tags": m.tags or [],
        "created_at": str(m.created_at),
    } for m in memories]


@router.post("/instructions")
async def store_instruction(body: InstructionIn, db: AsyncSession = Depends(get_db)):
    memory = await mem.store_instruction(
        db,
        key=body.key or body.category or "general",
        instruction=body.content,
        category=body.category or "general",
        priority=body.priority or 1.0,
    )
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
