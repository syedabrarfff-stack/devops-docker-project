"""Frontier intelligence API routes for the advanced JARVIS systems."""
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from app.api.v1.routes.auth import get_current_captain
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.services.aionx.frontier_intelligence import (
    agent_capacity,
    approve_agent_proposal,
    approve_service_concept,
    assign_variant,
    build_psychology_profile,
    captain_mirror_profile,
    cascade_intelligence,
    create_experiment,
    create_knowledge_artifact,
    frontier_status,
    generate_service_concept,
    get_experiment_winner,
    list_agent_proposals,
    list_cascade_events,
    list_experiments,
    list_service_concepts,
    list_threats,
    personalize_message,
    predict_captain_decision,
    recall_knowledge,
    record_captain_decision,
    record_experiment_outcome,
    resolve_threat,
    scan_threats,
    what_worked,
)

router = APIRouter(tags=["Frontier Intelligence"], dependencies=[Depends(get_current_captain)])


@router.get("/frontier/status")
async def get_frontier_status(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await frontier_status(db)


@router.get("/captain/mirror/profile")
async def get_captain_mirror_profile(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await captain_mirror_profile(db)


@router.post("/captain/mirror/record")
@limiter.limit("20/minute")
async def post_captain_decision(payload: dict[str, Any], request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await record_captain_decision(db, payload)


@router.post("/captain/mirror/predict")
@limiter.limit("10/minute")
async def post_captain_prediction(payload: dict[str, Any], request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await predict_captain_decision(db, payload)


@router.get("/captain/mirror/patterns")
async def get_captain_patterns(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await captain_mirror_profile(db)


@router.get("/experiments")
async def get_experiments(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await list_experiments(db)


@router.post("/experiments")
@limiter.limit("20/minute")
async def post_experiment(payload: dict[str, Any], request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await create_experiment(db, payload)


@router.post("/experiments/{experiment_id}/assign")
@limiter.limit("30/minute")
async def post_assign_variant(experiment_id: str, payload: dict[str, Any], request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await assign_variant(db, experiment_id, str(payload.get("prospect_id", "unknown")))


@router.post("/experiments/{experiment_id}/outcome")
@limiter.limit("30/minute")
async def post_experiment_outcome(experiment_id: str, payload: dict[str, Any], request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await record_experiment_outcome(db, experiment_id, payload)


@router.get("/experiments/{experiment_id}/winner")
async def get_winner(experiment_id: str, promote: bool = False, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await get_experiment_winner(db, experiment_id, promote=promote)


@router.post("/experiments/{experiment_id}/promote")
@limiter.limit("10/minute")
async def post_promote_winner(experiment_id: str, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await get_experiment_winner(db, experiment_id, promote=True)


@router.get("/services/concepts")
async def get_service_concepts(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await list_service_concepts(db)


@router.post("/services/concepts/generate")
@limiter.limit("5/minute")
async def post_service_concept(request: Request, payload: dict[str, Any] | None = None, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await generate_service_concept(db, payload)


@router.post("/services/concepts/{concept_id}/approve")
@limiter.limit("10/minute")
async def post_approve_service(concept_id: str, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await approve_service_concept(db, concept_id)


@router.get("/leads/{lead_id}/psychology")
async def get_lead_psychology(lead_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await build_psychology_profile(db, lead_id, {})


@router.post("/leads/{lead_id}/psychology")
@limiter.limit("10/minute")
async def post_lead_psychology(lead_id: str, payload: dict[str, Any], request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await build_psychology_profile(db, lead_id, payload)


@router.post("/leads/{lead_id}/personalize-message")
@limiter.limit("10/minute")
async def post_personalize_message(lead_id: str, payload: dict[str, Any], request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await personalize_message(db, lead_id, payload)


@router.get("/threats/active")
async def get_active_threats(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await list_threats(db, active_only=True)


@router.get("/threats/history")
async def get_threat_history(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await list_threats(db, active_only=False)


@router.post("/threats/scan")
@limiter.limit("5/minute")
async def post_threat_scan(request: Request, payload: dict[str, Any] | None = None, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await scan_threats(db, payload)


@router.post("/threats/{threat_id}/resolve")
@limiter.limit("20/minute")
async def post_resolve_threat(threat_id: str, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await resolve_threat(db, threat_id)


@router.get("/intelligence/cascade/events")
async def get_cascade_events(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await list_cascade_events(db)


@router.post("/intelligence/cascade/trigger")
@limiter.limit("5/minute")
async def post_cascade_event(payload: dict[str, Any], request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await cascade_intelligence(db, payload)


@router.get("/brain/recall")
async def get_brain_recall(q: str = Query("what worked", max_length=500), db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await recall_knowledge(db, q)


@router.post("/brain/artifacts")
@limiter.limit("20/minute")
async def post_brain_artifact(payload: dict[str, Any], request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await create_knowledge_artifact(db, payload)


@router.get("/brain/artifacts")
async def get_brain_artifacts(q: str = Query("", max_length=500), db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await recall_knowledge(db, q or "lesson")


@router.get("/brain/what-worked")
async def get_what_worked(
    industry: str | None = Query(default=None, max_length=100),
    service_type: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await what_worked(db, industry=industry, service_type=service_type)


@router.get("/agents/capacity")
async def get_agents_capacity(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await agent_capacity(db)


@router.post("/agents/capacity/check")
@limiter.limit("20/minute")
async def post_agents_capacity(payload: dict[str, Any], request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await agent_capacity(db, payload)


@router.get("/agents/proposals")
async def get_agents_proposals(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await list_agent_proposals(db)


@router.post("/agents/proposals/{proposal_id}/approve")
@limiter.limit("10/minute")
async def post_approve_agent(proposal_id: str, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await approve_agent_proposal(db, proposal_id)


@router.get("/agents/performance")
async def get_agents_performance() -> dict[str, Any]:
    return {
        "status": "performance_tracking_ready",
        "metrics": ["task_completion_rate", "quality_score", "response_time", "council_escalations"],
        "note": "Performance scores activate as agent execution volume accumulates.",
    }
