"""
AI Operations API — provider health, circuit breakers, cost tracking, credential audit, request log.
"""
import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.routes.auth import get_current_captain
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.services.ai.base_provider import Message
from app.services.ai.router import ai_router as jarvis_router
from app.services.ai.health_monitor import health_monitor
from app.services.ai.cost_governance import claude_governance_status
from app.services.ai.cost_tracker import (
    get_daily_cost, get_audit_log, get_cost_summary,
)
from app.services.security.credential_validator import run_credential_audit

router = APIRouter(prefix="/ai-ops", tags=["AI Operations"], dependencies=[Depends(get_current_captain)])
logger = logging.getLogger(__name__)


@router.get("/health")
@limiter.limit("30/minute")
async def provider_health(request: Request):
    """Circuit breaker state + latency stats for all AI providers."""
    try:
        statuses = health_monitor.all_status()
        if not statuses:
            # Populate from known providers if monitor hasn't seen any traffic yet
            for p in jarvis_router.available_providers():
                health_monitor.get(p)
            statuses = health_monitor.all_status()
        operational = jarvis_router.operational_providers()
        configured = jarvis_router.available_providers()
        return {
            "total_providers": len(jarvis_router._providers),
            "configured": len(configured),
            "available": len(operational),
            "active_providers": operational,
            "configured_providers": configured,
            "circuit_healthy": len(operational),
            "providers": jarvis_router.get_provider_status(),
            "circuit_breakers": statuses,
        }
    except Exception as exc:
        logger.error("AI Ops health check failed: %s", exc, exc_info=True)
        return {
            "total_providers": len(getattr(jarvis_router, "_providers", {})),
            "configured": 0,
            "available": 0,
            "active_providers": [],
            "configured_providers": [],
            "circuit_healthy": 0,
            "providers": {},
            "circuit_breakers": [],
            "error": str(exc),
        }


@router.get("/test-bedrock")
@limiter.limit("5/minute")
async def test_bedrock(request: Request):
    """Invoke Bedrock directly so configured vs. genuinely callable is clear."""
    try:
        return await _test_bedrock_impl()
    except Exception as exc:
        logger.error("test-bedrock failed: %s", exc, exc_info=True)
        return {
            "provider": "bedrock",
            "configured": False,
            "invoked": False,
            "status": "error",
            "error": str(exc),
        }


async def _test_bedrock_impl() -> dict:
    provider = jarvis_router._providers.get("bedrock")
    if provider is None:
        return {
            "provider": "bedrock",
            "configured": False,
            "invoked": False,
            "status": "missing_provider",
        }

    model_id = provider.models.get("claude-sonnet") or next(iter(provider.models.values()))
    started = time.monotonic()
    response = await provider.chat(
        messages=[Message(role="user", content="Return READY.")],
        model_id=model_id,
        system_prompt="Return exactly READY.",
        max_tokens=8,
    )
    latency_ms = int((time.monotonic() - started) * 1000)

    if response.error:
        account_blocked = _is_bedrock_account_blocked(response.error)
        for _ in range(3 if account_blocked else 1):
            health_monitor.record_failure("bedrock", latency_ms)
        return {
            "provider": "bedrock",
            "configured": provider.is_available(),
            "invoked": False,
            "status": "failed",
            "account_blocked": account_blocked,
            "action_required": _bedrock_action_required(response.error) if account_blocked else None,
            "model_id": model_id,
            "latency_ms": latency_ms,
            "error": response.error[:1000],
        }

    health_monitor.record_success("bedrock", latency_ms)
    return {
        "provider": "bedrock",
        "configured": provider.is_available(),
        "invoked": True,
        "status": "ok",
        "model_id": model_id,
        "latency_ms": latency_ms,
        "response": (response.content or "")[:500],
        "tokens_used": response.tokens_used,
    }


@router.post("/health/{provider}/reset")
@limiter.limit("10/minute")
async def reset_circuit(request: Request, provider: str):
    """Captain override — manually reset a provider's circuit breaker."""
    health_monitor.reset(provider)
    return {"message": f"Circuit breaker for '{provider}' reset by Captain", "provider": provider}


@router.get("/cost/today")
@limiter.limit("30/minute")
async def cost_today(request: Request, db: AsyncSession = Depends(get_db)):
    """Today's AI spend breakdown by provider with surge alert."""
    return await get_daily_cost(db)


@router.get("/cost/summary")
@limiter.limit("20/minute")
async def cost_summary(request: Request, days: int = Query(7, ge=1, le=30), db: AsyncSession = Depends(get_db)):
    """Rolling N-day cost summary with daily breakdown."""
    return await get_cost_summary(db, days)


@router.get("/audit")
@limiter.limit("20/minute")
async def request_audit(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    provider: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """AI request audit log — latest N calls with latency, cost, success status."""
    logs = await get_audit_log(db, limit=limit, provider=provider)
    return {"total": len(logs), "logs": logs}


@router.get("/credentials")
@limiter.limit("10/minute")
async def credential_audit(request: Request):
    """Startup credential audit — which API keys are configured vs. missing."""
    return run_credential_audit()


@router.get("/routing-table")
@limiter.limit("30/minute")
async def routing_table(request: Request):
    """Current task-type → provider routing table with health overlay."""
    from app.services.ai.router import ROUTING_TABLE
    table = {}
    for task_type, route in ROUTING_TABLE.items():
        table[task_type.value] = [
            {
                "provider": p,
                "model_key": m,
                "circuit_state": health_monitor.get(p).state,
                "available": health_monitor.is_available(p),
                "avg_latency_ms": round(health_monitor.get(p).avg_latency_ms, 1),
            }
            for p, m in route
        ]
    return {"routing_table": table}


@router.get("/governance")
@limiter.limit("20/minute")
async def ai_governance(request: Request):
    """Cost governance status for premium model usage."""
    return {
        "claude": await claude_governance_status(),
        "routing_policy": {
            "default": "cheap_provider_first",
            "claude_role": "supreme_architect_only",
            "lightweight_council": ["deepseek", "groq", "one premium only if policy allows"],
            "full_council": "manual or high-impact escalation only",
        },
    }


@router.get("/pulse")
@limiter.limit("20/minute")
async def ai_ops_pulse(request: Request, db: AsyncSession = Depends(get_db)):
    """One-stop summary: provider health + today's cost + credential status."""
    credentials = run_credential_audit()
    cost = await get_daily_cost(db)
    available = jarvis_router.operational_providers()
    open_circuits = [s for s in health_monitor.all_status() if s["state"] == "OPEN"]
    return {
        "ai_providers_available": len(available),
        "ai_providers_total": len(jarvis_router._providers),
        "active_providers": available,
        "open_circuits": len(open_circuits),
        "open_circuit_providers": [s["provider"] for s in open_circuits],
        "today_cost_usd": cost["total_cost_usd"],
        "cost_surge_alert": cost["surge_alert"],
        "credentials_configured": credentials["configured"],
        "credentials_total": credentials["total"],
        "system_ready": credentials["system_ready"],
    }


def _is_bedrock_account_blocked(error: str) -> bool:
    markers = (
        "INVALID_PAYMENT_INSTRUMENT",
        "AWS Marketplace subscription",
        "aws-marketplace:Subscribe",
        "aws-marketplace:ViewSubscriptions",
        "Marketplace",
    )
    return any(marker in error for marker in markers)


def _bedrock_action_required(error: str) -> str:
    if "INVALID_PAYMENT_INSTRUMENT" in error:
        return (
            "AWS account payment instrument is invalid for Bedrock Marketplace model subscription. "
            "Fix Billing payment method, then subscribe/enable the selected Bedrock Anthropic model."
        )
    return (
        "Attach Marketplace subscription permissions to the EC2 role and enable the selected "
        "Bedrock Anthropic model in AWS Bedrock Marketplace."
    )
