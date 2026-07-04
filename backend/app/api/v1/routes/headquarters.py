"""HQ-5 Route: Headquarters Chat API — the single endpoint the Headquarters
Chat UI talks to.

POST /api/v1/headquarters/chat            — send a message
POST /api/v1/headquarters/approve/{id}    — approve a PENDING_APPROVAL request
POST /api/v1/headquarters/reject/{id}     — reject a PENDING_APPROVAL request
GET  /api/v1/headquarters/history         — recent requests for a session
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.headquarters import HQActionRequest
from app.services.headquarters.orchestrator import HeadquartersOrchestrator

router = APIRouter(prefix="/headquarters", tags=["Headquarters"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=1, max_length=100)


@router.post("/chat")
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    orchestrator = HeadquartersOrchestrator(db)
    return await orchestrator.handle_message(body.message, body.session_id)


@router.post("/approve/{request_id}")
async def approve(request_id: UUID, db: AsyncSession = Depends(get_db)):
    orchestrator = HeadquartersOrchestrator(db)
    return await orchestrator.approve(request_id)


@router.post("/reject/{request_id}")
async def reject(request_id: UUID, db: AsyncSession = Depends(get_db)):
    orchestrator = HeadquartersOrchestrator(db)
    return await orchestrator.reject(request_id)


@router.get("/history")
async def history(session_id: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HQActionRequest)
        .where(HQActionRequest.session_id == session_id)
        .order_by(HQActionRequest.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "request_text": r.request_text,
                "kind": r.kind,
                "status": r.status,
                "tier": r.tier,
                "answer_text": r.answer_text,
                "plan": r.plan,
                "driver_model": r.driver_model,
                "reviewer_model": r.reviewer_model,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }
