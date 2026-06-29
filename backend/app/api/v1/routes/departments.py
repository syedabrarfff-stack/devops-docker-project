"""
6-Layer Autonomous Intelligence System — API Routes

/departments/dios          — Department Intelligence Officers
/departments/milestones    — Milestone Council Loop
/departments/tech          — Technology Evolution Engine
/departments/calls         — Client Call Intelligence
/departments/strategy      — Strategy Oversight Reports
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.api.v1.routes.auth import get_current_captain
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/departments", tags=["6-Layer Intelligence"], dependencies=[Depends(get_current_captain)])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tenant(request: Request, explicit: Optional[UUID] = None) -> str:
    from app.core.config import settings
    tid = (
        explicit
        or getattr(request.state, "tenant_id", None)
        or request.headers.get("X-Tenant-ID")
        or settings.JARVIS_DEFAULT_TENANT_ID
    )
    if not tid:
        raise HTTPException(status_code=400, detail="tenant_id required")
    return str(tid)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — Department Intelligence Officers
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/dios/initialize")
@limiter.limit("3/minute")
async def initialize_dios(
    request: Request,
    tenant_id: Optional[UUID] = None,
):
    """
    Initialize or refresh all 25 canonical Department Intelligence Officers.
    Creates DIO records for all departments. Idempotent — safe to re-run.
    """
    from app.services.departments.department_agent_service import department_agent_service
    tid = _tenant(request, tenant_id)
    try:
        created = await department_agent_service.initialize_all_dios(tid)
        return {
            "status": "initialized",
            "tenant_id": tid,
            "dios_configured": 25,
            "new_created": len(created),
        }
    except Exception as exc:
        logger.error("departments endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Operation failed") from exc


@router.get("/dios")
async def list_dios(
    request: Request,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all Department Intelligence Officers and their status."""
    from app.services.departments.department_agent_service import department_agent_service
    tid = _tenant(request, tenant_id)
    dios = await department_agent_service.get_all_dios(db, tid)
    return {"dios": dios, "total": len(dios)}


@router.get("/dios/{department_code}")
async def get_dio(
    department_code: str,
    request: Request,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get status and details of a specific Department Intelligence Officer."""
    from app.services.departments.department_agent_service import department_agent_service
    tid = _tenant(request, tenant_id)
    return await department_agent_service.get_dio_status(db, tid, department_code)


@router.post("/dios/collect-metrics")
@limiter.limit("5/minute")
async def collect_metrics(
    request: Request,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI-powered metrics collection across all departments."""
    from app.services.departments.department_agent_service import department_agent_service
    tid = _tenant(request, tenant_id)
    try:
        metrics = await department_agent_service.collect_department_metrics(db, tid)
        return metrics
    except Exception as exc:
        logger.error("departments endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Operation failed") from exc


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — Milestone Council Intelligence Loop
# ═══════════════════════════════════════════════════════════════════════════════

class MilestoneSubmitRequest(BaseModel):
    department_code: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=5, max_length=300)
    description: str = Field(min_length=10, max_length=20_000)
    milestone_type: str = Field(default="achievement", max_length=100)
    metrics: dict = Field(default_factory=dict)
    evidence_data: dict = Field(default_factory=dict)
    tenant_id: Optional[UUID] = None


class ImplementMilestoneRequest(BaseModel):
    notes: str = Field(min_length=5, max_length=10_000)
    tenant_id: Optional[UUID] = None


@router.post("/milestones/submit")
@limiter.limit("10/minute")
async def submit_milestone(
    request: Request,
    body: MilestoneSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """DIO submits a milestone for Council review."""
    from app.services.departments.department_agent_service import department_agent_service
    tid = _tenant(request, body.tenant_id)
    try:
        milestone = await department_agent_service.submit_milestone(
            db, tid,
            department_code=body.department_code,
            title=body.title,
            description=body.description,
            milestone_type=body.milestone_type,
            metrics=body.metrics,
            evidence_data=body.evidence_data,
        )
        return {
            "milestone_id": str(milestone.id),
            "status": milestone.status,
            "impact_score": milestone.impact_score,
            "message": "Milestone submitted — queued for Council review",
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("departments endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Operation failed") from exc


@router.post("/milestones/{milestone_id}/council-review")
@limiter.limit("5/minute")
async def run_milestone_council_review(
    request: Request,
    milestone_id: str,
    tenant_id: Optional[UUID] = None,
):
    """
    Execute the full Council Intelligence Loop for a milestone:
    Generate PDF → Council reviews → Improvement PDF → back to DIO.
    """
    from app.services.departments.milestone_engine import milestone_engine
    tid = _tenant(request, tenant_id)
    try:
        result = await milestone_engine.run_milestone_council_loop(tid, milestone_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("departments endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Operation failed") from exc


@router.post("/milestones/bulk-review")
@limiter.limit("3/minute")
async def bulk_milestone_review(
    request: Request,
    tenant_id: Optional[UUID] = None,
):
    """Process all pending milestones awaiting Council review."""
    from app.services.departments.milestone_engine import milestone_engine
    tid = _tenant(request, tenant_id)
    try:
        result = await milestone_engine.run_bulk_milestone_review(tid)
        return result
    except Exception as exc:
        logger.error("departments endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Operation failed") from exc


@router.get("/milestones")
async def list_milestones(
    request: Request,
    tenant_id: Optional[UUID] = None,
    department_code: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List milestones across all or a specific department."""
    from app.services.departments.department_agent_service import department_agent_service
    tid = _tenant(request, tenant_id)
    return {
        "milestones": await department_agent_service.get_milestones(
            db, tid, department_code=department_code, limit=limit
        )
    }


@router.get("/milestones/report")
async def milestone_report(
    request: Request,
    tenant_id: Optional[UUID] = None,
    department_code: Optional[str] = Query(None),
):
    """Generate comprehensive milestone performance report."""
    from app.services.departments.milestone_engine import milestone_engine
    tid = _tenant(request, tenant_id)
    return await milestone_engine.generate_department_milestone_report(
        tid, department_code=department_code
    )


@router.post("/milestones/{milestone_id}/implement")
@limiter.limit("5/minute")
async def implement_milestone(
    request: Request,
    milestone_id: str,
    body: ImplementMilestoneRequest,
    db: AsyncSession = Depends(get_db),
):
    """Mark a Council-reviewed milestone as implemented."""
    from app.services.departments.department_agent_service import department_agent_service
    tid = _tenant(request, body.tenant_id)
    try:
        result = await department_agent_service.implement_council_recommendation(
            db, tid, milestone_id, body.notes
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — Technology Evolution Engine
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/tech/discover")
@limiter.limit("5/minute")
async def trigger_tech_discovery(
    request: Request,
    tenant_id: Optional[UUID] = None,
):
    """Trigger a full technology discovery and evaluation cycle."""
    from app.services.departments.tech_evolution_engine import tech_evolution_engine
    tid = _tenant(request, tenant_id)
    try:
        result = await tech_evolution_engine.run_discovery_cycle(tid)
        return result
    except Exception as exc:
        logger.error("departments endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Operation failed") from exc


@router.get("/tech/discoveries")
async def list_tech_discoveries(
    request: Request,
    tenant_id: Optional[UUID] = None,
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List technology discoveries from the evolution engine."""
    from app.services.departments.tech_evolution_engine import tech_evolution_engine
    tid = _tenant(request, tenant_id)
    return {
        "discoveries": await tech_evolution_engine.get_discoveries(
            db, tid, category=category, status=status, priority=priority, limit=limit
        )
    }


@router.get("/tech/landscape")
async def tech_landscape(
    request: Request,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """Technology landscape dashboard — categorized by adoption status."""
    from app.services.departments.tech_evolution_engine import tech_evolution_engine
    tid = _tenant(request, tenant_id)
    return await tech_evolution_engine.get_tech_landscape(db, tid)


@router.post("/tech/{tech_id}/evaluate")
@limiter.limit("5/minute")
async def evaluate_technology(
    request: Request,
    tech_id: str,
    tenant_id: Optional[UUID] = None,
):
    """Generate a full adoption guide for a discovered technology."""
    from app.services.departments.tech_evolution_engine import tech_evolution_engine
    tid = _tenant(request, tenant_id)
    try:
        return await tech_evolution_engine.evaluate_technology(tid, tech_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tech/{tech_id}/council-review")
@limiter.limit("5/minute")
async def submit_tech_to_council(
    request: Request,
    tech_id: str,
    tenant_id: Optional[UUID] = None,
):
    """Submit a technology to the AI Council for strategic adoption decision."""
    from app.services.departments.tech_evolution_engine import tech_evolution_engine
    tid = _tenant(request, tenant_id)
    try:
        return await tech_evolution_engine.submit_for_council_review(tid, tech_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("departments endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Operation failed") from exc


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 5 — Client Call Intelligence
# ═══════════════════════════════════════════════════════════════════════════════

class ScheduleCallRequest(BaseModel):
    department_code: str = Field(min_length=2, max_length=50)
    client_name: str = Field(min_length=2, max_length=200)
    client_company: str = Field(min_length=2, max_length=200)
    client_email: Optional[str] = Field(default=None, max_length=320)
    scheduled_at: datetime
    call_topic: str = Field(min_length=5, max_length=300)
    call_objective: Optional[str] = Field(default=None, max_length=2_000)
    tenant_id: Optional[UUID] = None


class CallOutcomeRequest(BaseModel):
    outcome: str = Field(min_length=3, max_length=50)
    transcript: Optional[str] = Field(default=None, max_length=500_000)
    recording_url: Optional[str] = Field(default=None, max_length=2_000)
    tenant_id: Optional[UUID] = None


@router.post("/calls/schedule")
@limiter.limit("10/minute")
async def schedule_call(
    request: Request,
    body: ScheduleCallRequest,
    db: AsyncSession = Depends(get_db),
):
    """Schedule a client call and register it in the intelligence system."""
    from app.services.departments.call_intelligence_service import call_intelligence_service
    tid = _tenant(request, body.tenant_id)
    try:
        call = await call_intelligence_service.schedule_call(
            db, tid,
            department_code=body.department_code,
            client_name=body.client_name,
            client_company=body.client_company,
            client_email=body.client_email,
            scheduled_at=body.scheduled_at,
            call_topic=body.call_topic,
            call_objective=body.call_objective,
        )
        return {
            "call_id": str(call.id),
            "status": call.status,
            "scheduled_at": call.scheduled_at.isoformat(),
            "message": "Call registered — briefing will be generated 1 hour before",
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/calls/{call_id}/generate-briefing")
@limiter.limit("5/minute")
async def generate_briefing(
    request: Request,
    call_id: str,
    tenant_id: Optional[UUID] = None,
):
    """Generate the pre-call intelligence briefing and submit to Council for review."""
    from app.services.departments.call_intelligence_service import call_intelligence_service
    tid = _tenant(request, tenant_id)
    try:
        return await call_intelligence_service.generate_pre_call_briefing(tid, call_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("departments endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Operation failed") from exc


@router.post("/calls/{call_id}/council-review")
@limiter.limit("5/minute")
async def council_review_call(
    request: Request,
    call_id: str,
    tenant_id: Optional[UUID] = None,
):
    """Council reviews and refines the call briefing."""
    from app.services.departments.call_intelligence_service import call_intelligence_service
    tid = _tenant(request, tenant_id)
    try:
        return await call_intelligence_service.council_review_briefing(tid, call_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("departments endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Operation failed") from exc


@router.post("/calls/{call_id}/deploy-voice-agent")
@limiter.limit("3/minute")
async def deploy_voice_agent(
    request: Request,
    call_id: str,
    tenant_id: Optional[UUID] = None,
):
    """Deploy ElevenLabs voice agent with the Council-approved call script."""
    from app.services.departments.call_intelligence_service import call_intelligence_service
    tid = _tenant(request, tenant_id)
    try:
        return await call_intelligence_service.deploy_elevenlabs_agent(tid, call_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/calls/{call_id}/outcome")
@limiter.limit("20/minute")
async def record_outcome(
    request: Request,
    call_id: str,
    body: CallOutcomeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record post-call outcome and trigger debrief generation."""
    from app.services.departments.call_intelligence_service import call_intelligence_service
    tid = _tenant(request, body.tenant_id)
    try:
        return await call_intelligence_service.record_call_outcome(
            db, tid, call_id,
            outcome=body.outcome,
            transcript=body.transcript,
            recording_url=body.recording_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/calls")
async def list_calls(
    request: Request,
    tenant_id: Optional[UUID] = None,
    upcoming_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all client calls."""
    from app.services.departments.call_intelligence_service import call_intelligence_service
    tid = _tenant(request, tenant_id)
    if upcoming_only:
        calls = await call_intelligence_service.get_upcoming_calls(db, tid, limit=limit)
    else:
        calls = await call_intelligence_service.get_all_calls(db, tid, limit=limit)
    return {"calls": calls, "total": len(calls)}


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 6 — Strategy Oversight Reports
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/strategy/daily-report")
@limiter.limit("5/minute")
async def generate_daily_report(
    request: Request,
    tenant_id: Optional[UUID] = None,
):
    """
    Generate the daily strategy report:
    Collect all dept data → Council review → Cascade directives → Notify Captain.
    """
    from app.services.departments.strategy_report_service import strategy_report_service
    tid = _tenant(request, tenant_id)
    try:
        result = await strategy_report_service.generate_daily_strategy_report(tid)
        return result
    except Exception as exc:
        logger.error("departments endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Operation failed") from exc


@router.post("/strategy/weekly-report")
@limiter.limit("2/minute")
async def generate_weekly_report(
    request: Request,
    tenant_id: Optional[UUID] = None,
):
    """Generate the weekly strategic review with 30/60/90 day horizon."""
    from app.services.departments.strategy_report_service import strategy_report_service
    tid = _tenant(request, tenant_id)
    try:
        result = await strategy_report_service.generate_weekly_strategy_report(tid)
        return result
    except Exception as exc:
        logger.error("departments endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Operation failed") from exc


@router.get("/strategy/reports")
async def list_strategy_reports(
    request: Request,
    tenant_id: Optional[UUID] = None,
    report_type: Optional[str] = Query(None),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List strategy reports."""
    from app.services.departments.strategy_report_service import strategy_report_service
    tid = _tenant(request, tenant_id)
    return {
        "reports": await strategy_report_service.get_reports(
            db, tid, report_type=report_type, limit=limit
        )
    }


@router.get("/strategy/dashboard")
async def strategy_dashboard(
    request: Request,
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """Strategy dashboard — latest report, active milestones, Council directives."""
    from app.services.departments.strategy_report_service import strategy_report_service
    tid = _tenant(request, tenant_id)
    return await strategy_report_service.get_strategy_dashboard(db, tid)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM HEALTH & STATUS
# ═══════════════════════════════════════════════════════════════════════════════

# ============================================================================
# AXIOM COMMERCIAL OPERATING MODEL
# ============================================================================

@router.get("/axiom/operating-model")
async def axiom_operating_model():
    """AXIOM commercial brand layer: 25 departments, managers, consultants, gateways."""
    from app.services.departments.axiom_operating_model import operating_model
    return operating_model()


@router.get("/axiom/departments")
async def axiom_departments():
    """The canonical 25 AXIOM departments with manager and consultant ownership."""
    from app.services.departments.axiom_operating_model import AXIOM_DEPARTMENTS
    return {"status": "operational", "total": len(AXIOM_DEPARTMENTS), "departments": AXIOM_DEPARTMENTS}


@router.get("/axiom/pulse")
async def axiom_pulse():
    """15-minute department pulse model with health and escalation thresholds."""
    from app.services.departments.axiom_operating_model import pulse_snapshot
    return pulse_snapshot()


@router.post("/axiom/diagnose")
@limiter.limit("5/minute")
async def axiom_diagnose(request: Request, payload: dict):
    """Diagnosis-first commercial engine: profile -> gateways -> prescribed departments."""
    from app.services.departments.axiom_operating_model import diagnose_client
    return diagnose_client(payload)


@router.get("/axiom/consultants")
async def axiom_consultants():
    """Specialized consultant prompts and reporting doctrine for all 25 departments."""
    from app.services.departments.axiom_operating_model import consultant_prompts
    prompts = consultant_prompts()
    return {"status": "operational", "total": len(prompts), "consultants": prompts}


@router.post("/axiom/milestone-report")
@limiter.limit("5/minute")
async def axiom_milestone_report(request: Request, payload: dict):
    """Consultant -> Council direct milestone reporting path."""
    from app.services.departments.axiom_operating_model import milestone_report
    return milestone_report(payload)


@router.get("/health")
async def departments_health():
    """6-Layer Intelligence System health check."""
    return {
        "status": "operational",
        "layers": {
            "layer_1_dio": "active",
            "layer_2_milestone_council": "active",
            "layer_3_outreach_intelligence": "active",
            "layer_4_tech_evolution": "active",
            "layer_5_call_intelligence": "active",
            "layer_6_strategy_oversight": "active",
        },
        "departments_monitored": 25,
        "council_members": 8,
        "system": "JARVIS 25-Module Department Intelligence",
    }
