"""
Connector Hub API routes — JARVIS ↔ Claude connector bridge.

POST /connector-hub/ingest           Trigger full daily ingestion from /jarvis-data/
POST /connector-hub/intelligence     Trigger market intelligence generation
GET  /connector-hub/status           Get today's ingestion status
GET  /connector-hub/outputs          Get JARVIS outputs for today
POST /connector-hub/council-review   Send content to AI Council for quality gate
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from app.api.v1.routes.auth import get_current_captain
from app.core.rate_limit import limiter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connector-hub", tags=["Connector Hub"], dependencies=[Depends(get_current_captain)])

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


# ------------------------------------------------------------------
# Request / Response models
# ------------------------------------------------------------------

class IngestRequest(BaseModel):
    tenant_id: UUID = Field(default=SYSTEM_TENANT_ID)
    date_str: str | None = Field(default=None, description="YYYY-MM-DD, defaults to today")
    auto: bool = Field(default=False, description="Called by automated scheduler")


class IntelligenceRequest(BaseModel):
    tenant_id: UUID = Field(default=SYSTEM_TENANT_ID)
    output_dir: str | None = Field(default=None, description="Override output directory")


class CouncilReviewRequest(BaseModel):
    tenant_id: UUID = Field(default=SYSTEM_TENANT_ID)
    content_type: str = Field(..., description="outreach_email|proposal|market_report|lead_score")
    content: dict[str, Any] = Field(..., description="Content to review")


class IngestResponse(BaseModel):
    status: str
    tenant_id: str
    date: str
    leads: dict[str, Any] = Field(default_factory=dict)
    sequences: dict[str, Any] = Field(default_factory=dict)
    decks: dict[str, Any] = Field(default_factory=dict)
    intelligence: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/ingest", response_model=IngestResponse, summary="Trigger daily connector hub ingestion")
@limiter.limit("5/minute")
async def trigger_ingestion(http_request: Request, request: IngestRequest, background_tasks: BackgroundTasks):
    """
    Trigger full daily ingestion from /jarvis-data/ folder.
    Called by Codex at 14:30 UTC (20:00 IST) daily, or manually by Captain.
    """
    from app.services.integrations.connector_hub import connector_hub

    logger.info(
        "[ConnectorHub API] Ingest triggered — tenant=%s date=%s auto=%s",
        request.tenant_id, request.date_str, request.auto,
    )

    try:
        result = await connector_hub.ingest_daily_package(
            tenant_id=request.tenant_id,
            date_str=request.date_str,
        )
        return IngestResponse(
            status="success",
            tenant_id=str(request.tenant_id),
            date=result.get("date", date.today().isoformat()),
            leads=result.get("leads", {}),
            sequences=result.get("sequences", {}),
            decks=result.get("decks", {}),
            intelligence=result.get("intelligence", {}),
            errors=result.get("errors", []),
            duration_seconds=result.get("duration_seconds"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[ConnectorHub API] Ingestion failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Connector hub ingestion failed") from exc


@router.post("/intelligence", summary="Trigger market intelligence generation")
@limiter.limit("5/minute")
async def trigger_intelligence(http_request: Request, request: IntelligenceRequest):
    """
    Trigger daily market intelligence report and opportunity scan.
    Writes reports to /jarvis-data/intelligence/.
    """
    from app.services.integrations.market_intelligence_engine import market_intelligence_engine
    from app.services.integrations.github_bridge import github_bridge
    import os

    output_dir = request.output_dir or os.path.join(
        github_bridge.REPO_DATA_PATH, "intelligence"
    )

    logger.info("[ConnectorHub API] Intelligence generation triggered — tenant=%s", request.tenant_id)

    try:
        result = await market_intelligence_engine.write_github_intelligence_package(
            tenant_id=request.tenant_id,
            output_dir=output_dir,
        )
        return {
            "status": "success",
            "files_written": result.get("files_written", []),
            "total_insights": result.get("total_insights", 0),
            "generated_at": result.get("generated_at"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[ConnectorHub API] Intelligence generation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Intelligence generation failed") from exc


@router.get("/status", summary="Get today's ingestion status")
async def get_status(tenant_id: UUID = Query(default=SYSTEM_TENANT_ID)):
    """
    Returns today's ingestion status and summary statistics.
    """
    from app.services.integrations.github_bridge import github_bridge

    today = date.today().isoformat()

    bridge_health = github_bridge.health_check()

    # Try to load today's leads count from the data folder
    package_info: dict[str, Any] = {"date": today, "bridge": bridge_health}

    try:
        daily_package = await github_bridge.read_daily_package(today)
        package_info["leads_available"] = len(daily_package.get("leads", []))
        package_info["sequences_available"] = len(daily_package.get("sequences", []))
        package_info["decks_available"] = len(daily_package.get("decks", []))
        package_info["has_market_report"] = bool(daily_package.get("market_report"))
    except Exception as exc:
        logger.warning("[ConnectorHub API] Could not read daily package: %s", exc)
        package_info["read_error"] = "package_unavailable"

    # Try to get DB ingestion record
    try:
        from app.models.connector_hub import ConnectorHubIngestion
        from app.core.database import AsyncSessionLocal, set_tenant_context
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            try:
                await set_tenant_context(db, str(tenant_id))
            except Exception as exc:
                logger.warning("set_tenant_context failed for tenant %s: %s", tenant_id, exc)
            result = await db.execute(
                select(ConnectorHubIngestion).where(
                    ConnectorHubIngestion.tenant_id == tenant_id,
                    ConnectorHubIngestion.date == date.fromisoformat(today),
                ).order_by(ConnectorHubIngestion.created_at.desc()).limit(1)
            )
            record = result.scalar_one_or_none()
            if record:
                package_info["ingestion_status"] = record.status
                package_info["leads_processed"] = record.leads_processed
                package_info["sequences_loaded"] = record.sequences_loaded
                package_info["decks_matched"] = record.decks_matched
                package_info["outreach_triggered"] = record.outreach_triggered
                package_info["council_approvals"] = record.council_approvals
                package_info["last_ingestion"] = record.created_at.isoformat() if record.created_at else None
            else:
                package_info["ingestion_status"] = "not_run"
    except ImportError:
        package_info["ingestion_status"] = "db_model_pending"
    except Exception as exc:
        package_info["ingestion_status"] = "error"
        package_info["status_error"] = str(exc)

    return package_info


@router.get("/outputs", summary="Get JARVIS outputs for today")
async def get_outputs(
    tenant_id: UUID = Query(default=SYSTEM_TENANT_ID),
    date_str: str | None = Query(default=None),
):
    """
    Returns JARVIS processing outputs written back to /jarvis-data/outputs/.
    These are what JARVIS produced today: leads_processed, outreach_sent, proposals_generated.
    """
    from app.services.integrations.github_bridge import github_bridge

    effective_date = date_str or date.today().isoformat()
    outputs = github_bridge.get_outputs_for_date(effective_date)

    return {
        "date": effective_date,
        "outputs": outputs,
        "count": len(outputs),
    }


@router.post("/council-review", summary="Send content to AI Council for quality gate")
@limiter.limit("5/minute")
async def council_review(http_request: Request, request: CouncilReviewRequest):
    """
    Sends content through the JARVIS AI Council for quality review.
    content_type: outreach_email | proposal | market_report | lead_score
    Returns: verdict (APPROVE/REVISE/REJECT), confidence, improvements.
    """
    from app.services.integrations.connector_hub import connector_hub

    valid_types = {"outreach_email", "proposal", "market_report", "lead_score"}
    if request.content_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"content_type must be one of: {', '.join(valid_types)}",
        )

    try:
        result = await connector_hub.run_council_review(
            tenant_id=request.tenant_id,
            content_type=request.content_type,
            content=request.content,
        )
        return result
    except Exception as exc:
        logger.error("[ConnectorHub API] Council review failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Council review failed") from exc


@router.get("/bridge-health", summary="Check GitHub bridge health")
async def bridge_health():
    """
    Returns the health status of the GitHub data bridge on EC2.
    Checks if /jarvis-data/ directory and subdirectories exist.
    """
    from app.services.integrations.github_bridge import github_bridge
    return github_bridge.health_check()
