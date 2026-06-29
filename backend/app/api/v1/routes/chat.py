import asyncio
import logging
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.routes.auth import get_current_captain
from app.core.config import settings
from app.core.database import get_db, set_tenant_context
from app.core.rate_limit import limiter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai.router import ai_router, JARVIS_SYSTEM_PROMPT
from app.services.ai.base_provider import Message, TaskType
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(get_current_captain)])


@router.post("", response_model=ChatResponse)
@limiter.limit("60/minute")
async def chat(request: Request, req: ChatRequest, db: AsyncSession = Depends(get_db)):
    tenant_id = settings.JARVIS_DEFAULT_TENANT_ID
    if tenant_id:
        await set_tenant_context(db, tenant_id)

    messages = [Message(role=m.role, content=m.content) for m in req.history]
    messages.append(Message(role="user", content=req.message))
    requested_task_type = _task_type_from_request(req.task_type)

    try:
        response, task_type = await asyncio.wait_for(
            ai_router.chat(
                messages=messages,
                task_type=requested_task_type,
                force_provider=req.force_provider,
                force_model=req.force_model,
                system_prompt=JARVIS_SYSTEM_PROMPT,
                auto_detect=req.auto_route and not req.force_provider and requested_task_type is None,
            ),
            timeout=55.0,
        )
        response_text = response.content or (f"JARVIS offline — {response.error}" if response.error else "JARVIS is momentarily unavailable. All systems reconnecting.")
    except Exception as exc:
        logger.warning("Chat AI call failed: %s", exc)
        response_text = "JARVIS is momentarily unavailable. All systems reconnecting."
        response = type("_R", (), {"model": "unavailable", "provider": "unavailable", "task_type": None, "tokens_used": 0})()
        task_type = str(requested_task_type) if requested_task_type else "GENERAL"

    # Persist to DB
    if tenant_id:
        try:
            db.add(Conversation(tenant_id=tenant_id, session_id=req.session_id, role="user", content=req.message))
            db.add(Conversation(
                tenant_id=tenant_id, session_id=req.session_id, role="jarvis", content=response_text,
                model_used=response.model, task_type=task_type, tokens_used=response.tokens_used,
            ))
            await db.flush()
        except Exception as exc:
            await db.rollback()
            logger.warning("Chat conversation persistence failed for session %s: %s", req.session_id, exc)

    return ChatResponse(
        response=response_text,
        model=response.model,
        provider=response.provider,
        task_type=task_type,
        tokens_used=response.tokens_used,
        demo=response.demo,
        session_id=req.session_id,
    )


@router.get("/providers")
@limiter.limit("30/minute")
async def get_providers(request: Request):
    return ai_router.get_provider_status()


@router.get("/history/{session_id}")
@limiter.limit("30/minute")
async def get_history(request: Request, session_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    tenant_id = settings.JARVIS_DEFAULT_TENANT_ID
    if tenant_id:
        await set_tenant_context(db, tenant_id)
    query = select(Conversation).where(Conversation.session_id == session_id)
    if tenant_id:
        query = query.where(Conversation.tenant_id == tenant_id)
    result = await db.execute(query.order_by(Conversation.created_at.asc()).limit(100))
    rows = result.scalars().all()
    return [{"role": r.role, "content": r.content, "model": r.model_used,
             "created_at": r.created_at} for r in rows]


def _task_type_from_request(value: str | None) -> TaskType | None:
    if not value:
        return None
    normalized = value.strip().lower()
    try:
        return TaskType(normalized)
    except ValueError:
        return None
