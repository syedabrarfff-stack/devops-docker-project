from __future__ import annotations

import logging
import time
import uuid
from inspect import isawaitable

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.tenant_context import reset_current_tenant_id, set_current_tenant_id
from app.models.approval import ApprovalRequest, ApprovalStatus
from app.models.revenue import Client, ClientStatus

logger = logging.getLogger(__name__)

METRICS_REFRESH_SECONDS = 15
APPROVAL_RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN")

JARVIS_LEADS_DISCOVERED_TOTAL = Counter(
    "jarvis_leads_discovered_total",
    "Leads discovered and persisted by JARVIS.",
    ["source", "country"],
)
JARVIS_OUTREACH_SENT_TOTAL = Counter(
    "jarvis_outreach_sent_total",
    "Outbound outreach messages sent by JARVIS.",
    ["channel", "persona"],
)
JARVIS_AI_COST_USD_TOTAL = Counter(
    "jarvis_ai_cost_usd_total",
    "Estimated AI provider cost in USD.",
    ["provider", "model", "task_type"],
)
JARVIS_AI_LATENCY_SECONDS = Histogram(
    "jarvis_ai_latency_seconds",
    "AI provider response latency in seconds.",
    ["provider", "model"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 30, 60),
)
JARVIS_COUNCIL_SESSIONS_TOTAL = Counter(
    "jarvis_council_sessions_total",
    "AI council sessions completed by final decision.",
    ["decision"],
)
JARVIS_APPROVALS_PENDING = Gauge(
    "jarvis_approvals_pending",
    "Pending Captain approvals by risk level.",
    ["risk_level"],
)
JARVIS_CLIENTS_ACTIVE = Gauge(
    "jarvis_clients_active",
    "Active clients currently tracked by JARVIS.",
)
JARVIS_MRR_USD = Gauge(
    "jarvis_mrr_usd",
    "Current monthly recurring revenue in USD.",
)
JARVIS_DB_CONNECTIONS_ACTIVE = Gauge(
    "jarvis_db_connections_active",
    "Active checked-out SQLAlchemy database connections.",
)
JARVIS_REDIS_MEMORY_BYTES = Gauge(
    "jarvis_redis_memory_bytes",
    "Redis memory usage in bytes.",
)

_last_metrics_refresh = 0.0


def _label(value, fallback: str = "unknown") -> str:
    text = str(value or fallback).strip() or fallback
    return text[:96]


def record_lead_discovered(source: str | None, country: str | None) -> None:
    JARVIS_LEADS_DISCOVERED_TOTAL.labels(_label(source), _label(country)).inc()


def record_outreach_sent(channel: str | None, persona: str | None) -> None:
    JARVIS_OUTREACH_SENT_TOTAL.labels(_label(channel), _label(persona)).inc()


def record_ai_cost(provider: str | None, model: str | None, task_type: str | None, cost_usd: float | None) -> None:
    cost = max(0.0, float(cost_usd or 0.0))
    if cost:
        JARVIS_AI_COST_USD_TOTAL.labels(_label(provider), _label(model), _label(task_type)).inc(cost)


def observe_ai_latency(provider: str | None, model: str | None, latency_ms: int | float | None) -> None:
    seconds = max(0.0, float(latency_ms or 0) / 1000.0)
    JARVIS_AI_LATENCY_SECONDS.labels(_label(provider), _label(model)).observe(seconds)


def record_council_session(decision: str | None) -> None:
    JARVIS_COUNCIL_SESSIONS_TOTAL.labels(_label(decision)).inc()


def setup_observability(app) -> None:
    """Expose Prometheus metrics for HTTP, business, AI, and runtime signals."""
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


class ObservabilityRefreshMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        await refresh_observability_metrics(force=request.url.path == "/metrics")
        return await call_next(request)


async def refresh_observability_metrics(force: bool = False) -> None:
    global _last_metrics_refresh

    now = time.monotonic()
    if not force and now - _last_metrics_refresh < METRICS_REFRESH_SECONDS:
        return
    _last_metrics_refresh = now

    _refresh_db_pool_metrics()
    await _refresh_redis_metrics()
    await _refresh_business_metrics()


def _refresh_db_pool_metrics() -> None:
    try:
        from app.core.database import engine

        checkedout = getattr(engine.pool, "checkedout", None)
        JARVIS_DB_CONNECTIONS_ACTIVE.set(float(checkedout() if callable(checkedout) else 0))
    except Exception as exc:
        logger.debug("DB pool metric refresh skipped: %s", exc)


async def _refresh_redis_metrics() -> None:
    if not settings.REDIS_URL:
        JARVIS_REDIS_MEMORY_BYTES.set(0)
        return

    client = None
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        info = await client.info("memory")
        JARVIS_REDIS_MEMORY_BYTES.set(float(info.get("used_memory") or 0))
    except Exception as exc:
        logger.debug("Redis metric refresh skipped: %s", exc)
    finally:
        if client is not None:
            close = getattr(client, "aclose", None) or getattr(client, "close", None)
            if close:
                result = close()
                if isawaitable(result):
                    await result


async def _refresh_business_metrics() -> None:
    try:
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            pending_rows = (
                await db.execute(
                    select(ApprovalRequest.risk_level, func.count())
                    .where(ApprovalRequest.status == ApprovalStatus.PENDING)
                    .group_by(ApprovalRequest.risk_level)
                )
            ).all()

            for risk_level in APPROVAL_RISK_LEVELS:
                JARVIS_APPROVALS_PENDING.labels(risk_level).set(0)
            for risk_level, count in pending_rows:
                JARVIS_APPROVALS_PENDING.labels(_label(risk_level, "UNKNOWN").upper()).set(float(count or 0))

            active_clients = await db.scalar(
                select(func.count()).select_from(Client).where(Client.status == ClientStatus.ACTIVE)
            )
            mrr_usd = await db.scalar(
                select(func.coalesce(func.sum(Client.mrr_usd), 0.0)).where(Client.status == ClientStatus.ACTIVE)
            )
            JARVIS_CLIENTS_ACTIVE.set(float(active_clients or 0))
            JARVIS_MRR_USD.set(float(mrr_usd or 0))
    except Exception as exc:
        logger.debug("Business metric refresh skipped: %s", exc)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        t0 = time.monotonic()

        response = await call_next(request)

        latency_ms = int((time.monotonic() - t0) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{latency_ms}ms"

        path = request.url.path
        if path not in ("/health", "/readyz", "/favicon.ico"):
            logger.info(
                "%s %s -> %s [%sms] req=%s",
                request.method,
                path,
                response.status_code,
                latency_ms,
                request_id,
            )
        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = _tenant_id_from_jwt(request.headers.get("authorization", ""))
        token = set_current_tenant_id(tenant_id)
        request.state.tenant_id = tenant_id
        try:
            return await call_next(request)
        finally:
            reset_current_tenant_id(token)


def _tenant_id_from_jwt(authorization: str) -> str | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        logger.warning("Invalid JWT received; tenant context not set")
        return None

    tenant_id = claims.get("tenant_id") or claims.get("tid")
    return str(tenant_id) if tenant_id else None


def _error_body(status_code: int, message: str, request: Request, detail=None) -> dict:
    body = {
        "error": message,
        "status": status_code,
        "path": str(request.url.path),
        "request_id": getattr(request.state, "request_id", None),
    }
    if detail:
        body["detail"] = detail
    return body


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.status_code, str(exc.detail), request),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(location) for location in error["loc"]), "message": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(422, "Validation error", request, detail=errors),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled exception req=%s: %s", request_id, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(500, "Internal server error", request),
        headers={"X-Request-ID": request_id},
    )
