"""
AI Operations API — provider health, circuit breakers, cost tracking, credential audit, request log.
"""
import time
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.ai.base_provider import Message
from app.services.ai.router import ai_router as jarvis_router
from app.services.ai.health_monitor import health_monitor
from app.services.ai.cost_tracker import (
    get_daily_cost, get_audit_log, get_cost_summary,
)
from app.services.security.credential_validator import run_credential_audit

router = APIRouter(prefix="/ai-ops", tags=["AI Operations"])


@router.get("/health")
async def provider_health():
    """Circuit breaker state + latency stats for all AI providers."""
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
        "circuit_healthy": len([s for s in statuses if s["available"]]),
        "providers": jarvis_router.get_provider_status(),
        "circuit_breakers": statuses,
    }


@router.get("/test-bedrock")
async def test_bedrock():
    """Invoke Bedrock directly so configured vs. genuinely callable is clear."""
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
        "response": response.content[:500],
        "tokens_used": response.tokens_used,
    }


@router.post("/health/{provider}/reset")
async def reset_circuit(provider: str):
    """Captain override — manually reset a provider's circuit breaker."""
    health_monitor.reset(provider)
    return {"message": f"Circuit breaker for '{provider}' reset by Captain", "provider": provider}


@router.get("/cost/today")
async def cost_today(db: AsyncSession = Depends(get_db)):
    """Today's AI spend breakdown by provider with surge alert."""
    return await get_daily_cost(db)


@router.get("/cost/summary")
async def cost_summary(days: int = Query(7, ge=1, le=30), db: AsyncSession = Depends(get_db)):
    """Rolling N-day cost summary with daily breakdown."""
    return await get_cost_summary(db, days)


@router.get("/audit")
async def request_audit(
    limit: int = Query(50, ge=1, le=500),
    provider: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """AI request audit log — latest N calls with latency, cost, success status."""
    logs = await get_audit_log(db, limit=limit, provider=provider)
    return {"total": len(logs), "logs": logs}


@router.get("/credentials")
async def credential_audit():
    """Startup credential audit — which API keys are configured vs. missing."""
    return run_credential_audit()


@router.get("/routing-table")
async def routing_table():
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


@router.get("/pulse")
async def ai_ops_pulse(db: AsyncSession = Depends(get_db)):
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
