from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai.router import ai_router, JARVIS_SYSTEM_PROMPT
from app.services.ai.base_provider import Message
from app.models.conversation import Conversation
from app.services.operations.capabilities import build_operating_context
from app.services.operations.runtime_config import hydrate_runtime_settings
from app.services.memory import manager as memory_manager

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    await hydrate_runtime_settings(db)
    messages = [Message(role=m.role, content=m.content) for m in req.history]
    messages.append(Message(role="user", content=req.message))
    operating_context = await build_operating_context(db)
    memory_context = await memory_manager.build_context(db, session_id=req.session_id, query=req.message)

    context_parts = [JARVIS_SYSTEM_PROMPT, operating_context]
    if memory_context:
        context_parts.append(
            "LONG-TERM MEMORY CONTEXT\n"
            "Use this to remember previous conversations, active work, Captain preferences, "
            "and unfinished tasks. If Captain asks about previous work, continue from this context.\n\n"
            f"{memory_context}"
        )

    response, task_type = await ai_router.chat(
        messages=messages,
        force_provider=req.force_provider,
        force_model=req.force_model,
        system_prompt="\n\n".join(part for part in context_parts if part),
        auto_detect=req.auto_route and not req.force_provider,
    )

    # Persist the conversation and memory before returning so JARVIS can resume later.
    try:
        db.add(Conversation(session_id=req.session_id, role="user", content=req.message))
        db.add(Conversation(
            session_id=req.session_id, role="jarvis", content=response.content,
            model_used=response.model, task_type=task_type, tokens_used=response.tokens_used,
        ))
        await memory_manager.store_memory(
            db,
            key=f"Conversation turn in {req.session_id}",
            value=f"Captain: {req.message}\nJARVIS: {response.content}",
            memory_type="episodic",
            session_id=req.session_id,
            importance=0.65,
            tags=["chat", task_type],
        )
        await memory_manager.maybe_summarise(db, session_id=req.session_id)
        await db.flush()
        await db.commit()
    except Exception:
        await db.rollback()

    return ChatResponse(
        response=response.content,
        model=response.model,
        provider=response.provider,
        task_type=task_type,
        tokens_used=response.tokens_used,
        demo=response.demo,
        session_id=req.session_id,
    )


@router.get("/providers")
async def get_providers(db: AsyncSession = Depends(get_db)):
    await hydrate_runtime_settings(db)
    return ai_router.get_provider_status()


@router.get("/history/{session_id}")
async def get_history(session_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.asc())
        .limit(100)
    )
    rows = result.scalars().all()
    return [{"role": r.role, "content": r.content, "model": r.model_used,
             "created_at": r.created_at} for r in rows]
