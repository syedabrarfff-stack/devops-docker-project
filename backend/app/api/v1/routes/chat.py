from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai.router import ai_router, JARVIS_SYSTEM_PROMPT
from app.services.ai.base_provider import Message
from app.models.conversation import Conversation

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    messages = [Message(role=m.role, content=m.content) for m in req.history]
    messages.append(Message(role="user", content=req.message))

    response, task_type = await ai_router.chat(
        messages=messages,
        force_provider=req.force_provider,
        force_model=req.force_model,
        system_prompt=JARVIS_SYSTEM_PROMPT,
        auto_detect=req.auto_route and not req.force_provider,
    )

    # Persist to DB
    try:
        db.add(Conversation(session_id=req.session_id, role="user", content=req.message))
        db.add(Conversation(
            session_id=req.session_id, role="jarvis", content=response.content,
            model_used=response.model, task_type=task_type, tokens_used=response.tokens_used,
        ))
        await db.flush()
    except Exception:
        pass

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
async def get_providers():
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
