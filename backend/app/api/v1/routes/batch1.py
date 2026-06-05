"""AIONX Batch 1 client pipeline API."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.aionx.batch1_client_pipeline import (
    advance_stage,
    create_pipeline,
    get_pipeline_board,
    get_pipeline_workflow,
    get_pipeline,
    get_stage_history,
)

router = APIRouter(prefix="/batch1", tags=["AIONX Batch 1"])


@router.get("/workflow")
async def workflow_definition() -> dict[str, Any]:
    return get_pipeline_workflow()


@router.get("/board")
async def pipeline_board(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await get_pipeline_board(db)


@router.post("/pipeline")
async def create_client_pipeline(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        client_id = uuid.UUID(payload["client_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="client_id is required") from exc
    return await create_pipeline(db, client_id=client_id, scope=payload.get("scope") or {})


@router.post("/pipeline/stage-transition")
async def stage_transition(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        client_id = uuid.UUID(payload["client_id"])
        target_stage = int(payload["target_stage"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="client_id and target_stage are required") from exc

    try:
        mission_id = uuid.UUID(payload["mission_id"]) if payload.get("mission_id") else None
        return await advance_stage(
            db,
            client_id=client_id,
            target_stage=target_stage,
            engagement_score=payload.get("engagement_score"),
            mission_id=mission_id,
            metadata=payload.get("metadata") or {},
            reason=payload.get("reason"),
            actor=payload.get("actor", "JARVIS"),
            captain_approved=bool(payload.get("captain_approved", False)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pipeline/{client_id}/history")
async def pipeline_history(
    client_id: uuid.UUID,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await get_stage_history(db, client_id, limit=limit)


@router.get("/pipeline/{client_id}")
async def client_pipeline(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await get_pipeline(db, client_id)
