from __future__ import annotations

import asyncio
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.api.v1.routes.auth import get_current_captain
from fastapi.responses import StreamingResponse
from app.core.rate_limit import limiter
from pydantic import BaseModel, Field

from app.services.ai.council import intelligence_council

router = APIRouter(prefix="/council", tags=["AI Council"], dependencies=[Depends(get_current_captain)])


class CouncilConveneRequest(BaseModel):
    question: str = Field(min_length=3, max_length=8000)
    context: dict = Field(default_factory=dict)
    council_type: str = Field(default="standard", max_length=80)
    tenant_id: Optional[UUID] = None


@router.post("/convene")
@limiter.limit("20/minute")
async def convene_council(request: Request, body: CouncilConveneRequest):
    tenant_id = _resolve_tenant_id(request, body.tenant_id)
    try:
        result = await intelligence_council.convene(
            question=body.question,
            context=body.context,
            council_type=body.council_type,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.model_dump()


@router.post("/stream")
@limiter.limit("20/minute")
async def convene_council_stream(request: Request, body: CouncilConveneRequest):
    """
    SSE streaming council endpoint. Fires all council members in parallel and
    streams each vote back as it arrives, then delivers the final result.

    Stream protocol:
      data: {"type":"start","total":8}
      data: {"type":"vote","vote":{...},"done":1,"total":8}
      ...
      data: {"type":"result","decision":"APPROVE","score":82,...}
      data: {"type":"done"}
    """
    tenant_id = _resolve_tenant_id(request, body.tenant_id)

    async def generate():
        queue: asyncio.Queue[dict | None] = asyncio.Queue()
        total = 8  # COUNCIL_MEMBERS count — sent immediately for progress bar

        yield "data: " + json.dumps({"type": "start", "total": total}) + "\n\n"

        async def on_vote(vote: dict, done: int, total_count: int) -> None:
            await queue.put({"type": "vote", "vote": vote, "done": done, "total": total_count})

        async def run_convene() -> None:
            try:
                result = await intelligence_council.convene_streaming(
                    question=body.question,
                    context=body.context,
                    council_type=body.council_type,
                    tenant_id=tenant_id,
                    on_vote=on_vote,
                )
                await queue.put({"type": "result", **result.model_dump()})
            except Exception as exc:
                await queue.put({"type": "error", "message": str(exc)})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_convene())

        while True:
            event = await queue.get()
            if event is None:
                yield "data: " + json.dumps({"type": "done"}) + "\n\n"
                break
            yield "data: " + json.dumps(event, default=str) + "\n\n"

        await task

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions")
async def council_sessions(
    request: Request,
    tenant_id: Optional[UUID] = None,
    limit: int = Query(default=25, ge=1, le=100),
):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    return {"sessions": await intelligence_council.recent_sessions(resolved_tenant_id, limit=limit)}


@router.get("/health")
async def council_health(request: Request, tenant_id: Optional[UUID] = None):
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id, required=False)
    return await intelligence_council.health(resolved_tenant_id)


@router.get("/status")
async def council_status(request: Request, tenant_id: Optional[UUID] = None):
    """Compatibility status endpoint for dashboard and operating-system health checks."""
    resolved_tenant_id = _resolve_tenant_id(request, tenant_id, required=False)
    health = await intelligence_council.health(resolved_tenant_id)
    return {
        **health,
        "status": health.get("status", "operational"),
        "endpoint": "council/status",
        "council_live": True,
    }


def _resolve_tenant_id(request: Request, explicit_tenant_id: Optional[UUID], required: bool = True) -> UUID | None:
    from app.core.config import settings

    tenant_id = (
        explicit_tenant_id
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tenant_id:
        if required:
            raise HTTPException(status_code=400, detail="tenant_id is required")
        return None
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="tenant_id must be a valid UUID") from exc
