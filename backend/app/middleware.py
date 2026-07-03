from __future__ import annotations

import collections
import json
import logging
import time
import uuid
from datetime import datetime, timezone
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
from app.models.lead import Lead
from app.models.revenue import Client, ClientStatus
from app.services.tenancy import PLAN_LIMITS, TenantManager

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
_tenant_ai_usage: dict[tuple[str, str], int] = {}

# ── Security headers injected on every response ───────────────────────────────
_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    # HSTS: 1 year, include subdomains. Only meaningful over HTTPS (ALB terminates TLS).
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    # CSP is deliberately permissive here — the React dashboard loads fonts/scripts from CDN.
    # A stricter per-route policy should be set at the ALB response headers rule level.
    "Content-Security-Policy": "frame-ancestors 'none'",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject OWASP-recommended security headers on every outbound response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

AI_METERED_PATH_PREFIXES = (
    "/api/v1/chat",
    "/api/v1/council",
    "/api/v1/proposals/generate",
)
LEAD_METERED_PATH_PREFIXES = (
    "/api/v1/leads",
    "/api/v1/discover",
    "/api/v1/discovery",
)


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
            tenant_id = getattr(request.state, "tenant_id", "-")
            auth_method = getattr(request.state, "tenant_auth_method", "-")
            client_ip = (request.client.host if request.client else "-")
            logger.info(
                "%s %s -> %s [%sms] req=%s tenant=%s auth=%s ip=%s",
                request.method,
                path,
                response.status_code,
                latency_ms,
                request_id,
                tenant_id,
                auth_method,
                client_ip,
            )
        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant, auth_method = await _resolve_tenant_context(request)
        tenant_id = str(tenant.id) if tenant else _tenant_id_from_jwt(request.headers.get("authorization", ""))
        token = set_current_tenant_id(tenant_id)
        request.state.tenant_id = tenant_id
        request.state.tenant_auth_method = auth_method
        request.state.tenant_plan_tier = tenant.plan_tier.value if tenant else None
        request.state.tenant_limits = _limits_for_tenant(tenant) if tenant else None
        try:
            limit_response = await _enforce_tenant_limits(request, tenant)
            if limit_response:
                return limit_response
            return await call_next(request)
        finally:
            reset_current_tenant_id(token)


async def _resolve_tenant_context(request: Request):
    manager = TenantManager()
    api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if api_key:
        tenant = await manager.get_tenant_from_api_key(api_key.strip())
        if tenant:
            return tenant, "api_key"

    tenant_id = _tenant_id_from_jwt(request.headers.get("authorization", ""))
    if tenant_id:
        try:
            tenant = await manager.get_tenant_by_id(tenant_id)
        except ValueError:
            tenant = None
        return tenant, "jwt"
    return None, None


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

    tenant_id = claims.get("tenant_id") or claims.get("tid") or claims.get("sub")
    return str(tenant_id) if tenant_id else None


def _limits_for_tenant(tenant) -> dict[str, int | None]:
    if not tenant:
        return {}
    tenant_settings = tenant.settings or {}
    plan_tier = tenant.plan_tier.value
    default_limits = PLAN_LIMITS["ENTERPRISE"] if plan_tier == "INDUSTRY_OS" else PLAN_LIMITS["STARTER"]
    return dict(tenant_settings.get("limits") or PLAN_LIMITS.get(plan_tier, default_limits))


async def _enforce_tenant_limits(request: Request, tenant) -> JSONResponse | None:
    if not tenant:
        return None

    limits = _limits_for_tenant(tenant)
    path = request.url.path
    if request.method.upper() == "POST" and path.startswith(LEAD_METERED_PATH_PREFIXES):
        max_leads = limits.get("max_leads")
        if max_leads is not None and await _monthly_lead_count(str(tenant.id)) >= int(max_leads):
            return _limit_response("Monthly lead limit reached", str(tenant.id), limits)

    if request.method.upper() == "POST" and path.startswith(AI_METERED_PATH_PREFIXES):
        max_ai_calls = limits.get("max_ai_calls")
        if max_ai_calls is not None:
            usage_key = (str(tenant.id), datetime.now(timezone.utc).strftime("%Y-%m-%d"))
            used = _tenant_ai_usage.get(usage_key, 0)
            if used >= int(max_ai_calls):
                return _limit_response("Daily AI call limit reached", str(tenant.id), limits)
            _tenant_ai_usage[usage_key] = used + 1

    return None


async def _monthly_lead_count(tenant_id: str) -> int:
    from app.core.database import AsyncSessionLocal

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    async with AsyncSessionLocal() as db:
        count = await db.scalar(
            select(func.count()).select_from(Lead).where(
                Lead.tenant_id == uuid.UUID(tenant_id),
                Lead.created_at >= month_start,
            )
        )
    return int(count or 0)


def _limit_response(message: str, tenant_id: str, limits: dict) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": message,
            "tenant_id": tenant_id,
            "limits": limits,
        },
    )


# ── O5-5: IP Rate Limiting Middleware ─────────────────────────────────────────
#
# Sliding window per client IP.  Window = 60 seconds.
# - Global limit:         300 requests / 60s per IP
# - Sensitive-path limit:  20 requests / 60s per IP
#
# "Sensitive" paths are any /api/v1/ routes that modify state (POST/PUT/PATCH/DELETE)
# or any path whose prefix is in _SENSITIVE_PREFIXES.
#
# Implementation: in-process dict of deque[float] (arrival timestamps).
# Fine for single-process deployments (ECS single-task) and development.
# In a multi-replica deployment replace with a Redis INCR + EXPIRE approach.

_IP_WINDOW_SECS   = 60
_IP_GLOBAL_LIMIT  = 300
_IP_SENSITIVE_LIMIT = 20

_SENSITIVE_PREFIXES = (
    "/api/v1/captain",
    "/api/v1/kernel",
    "/api/v1/council",
    "/api/v1/approvals",
    "/api/v1/emergency",
    "/api/v1/scheduler",
    "/api/v1/ai-ops",
)

# deque of (window_key, timestamps) — one deque per (ip, bucket) pair
_ip_windows: dict[str, collections.deque] = collections.defaultdict(collections.deque)

_audit_log = logging.getLogger("jarvis.request_audit")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_sensitive(request: Request) -> bool:
    path = request.url.path
    if any(path.startswith(p) for p in _SENSITIVE_PREFIXES):
        return True
    if path.startswith("/api/v1/") and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        return True
    return False


def _sliding_window_check(key: str, limit: int, now: float) -> bool:
    """Return True if the request should be allowed, False if rate-limited."""
    window = _ip_windows[key]
    cutoff = now - _IP_WINDOW_SECS
    while window and window[0] < cutoff:
        window.popleft()
    if len(window) >= limit:
        return False
    window.append(now)
    return True


class IPRateLimitMiddleware(BaseHTTPMiddleware):
    """O5-5: Per-IP sliding-window rate limiter.

    Two-tier: global 300/min per IP, sensitive-path 20/min per IP.
    Health and metrics endpoints are exempt.
    """

    _EXEMPT_PATHS = frozenset({"/health", "/readyz", "/metrics", "/favicon.ico"})

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in self._EXEMPT_PATHS:
            return await call_next(request)

        ip = _client_ip(request)
        now = time.monotonic()

        # Sensitive-path check first (stricter).
        if _is_sensitive(request):
            if not _sliding_window_check(f"{ip}:sensitive", _IP_SENSITIVE_LIMIT, now):
                logger.warning("rate_limit: sensitive path blocked ip=%s path=%s", ip, path)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "detail": f"Max {_IP_SENSITIVE_LIMIT} requests/min on this endpoint.",
                        "retry_after": _IP_WINDOW_SECS,
                    },
                    headers={"Retry-After": str(_IP_WINDOW_SECS)},
                )

        # Global per-IP check.
        if not _sliding_window_check(f"{ip}:global", _IP_GLOBAL_LIMIT, now):
            logger.warning("rate_limit: global limit exceeded ip=%s path=%s", ip, path)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Max {_IP_GLOBAL_LIMIT} requests/min per IP.",
                    "retry_after": _IP_WINDOW_SECS,
                },
                headers={"Retry-After": str(_IP_WINDOW_SECS)},
            )

        return await call_next(request)


# ── O5-6: Structured Request Audit Logging Middleware ─────────────────────────
#
# Emits a structured JSON audit record for every non-health request.
# For mutating requests (POST/PUT/PATCH/DELETE) on /api/v1/ paths it also
# writes an append-only record to the kernel audit_log table via AuditLogger
# (K1-8) — giving Captain a queryable record of every system mutation.
#
# The structured log line goes to the "jarvis.request_audit" logger.
# JSON format:
#   {ts, method, path, status, latency_ms, ip, request_id, tenant_id, actor}

_MUTATION_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_AUDIT_SKIP_PATHS = frozenset({"/health", "/readyz", "/metrics", "/favicon.ico"})


class RequestAuditMiddleware(BaseHTTPMiddleware):
    """O5-6: Structured request audit logging (K1-8 integration).

    Every request → structured JSON log.
    Every mutation on /api/v1/ → also persisted to audit_log table.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in _AUDIT_SKIP_PATHS:
            return await call_next(request)

        t0 = time.monotonic()
        response = await call_next(request)
        latency_ms = int((time.monotonic() - t0) * 1000)

        ip         = _client_ip(request)
        request_id = getattr(request.state, "request_id", "-")
        tenant_id  = getattr(request.state, "tenant_id", "-")
        method     = request.method
        status_code = response.status_code

        record = {
            "ts":         datetime.now(tz=timezone.utc).isoformat(),
            "method":     method,
            "path":       path,
            "status":     status_code,
            "latency_ms": latency_ms,
            "ip":         ip,
            "request_id": request_id,
            "tenant_id":  tenant_id,
        }
        _audit_log.info(json.dumps(record))

        # Persist to audit_log table for API mutations.
        if method in _MUTATION_METHODS and path.startswith("/api/v1/"):
            await self._persist_audit(
                request_id=request_id,
                method=method,
                path=path,
                status_code=status_code,
                latency_ms=latency_ms,
                ip=ip,
                tenant_id=tenant_id,
            )

        return response

    @staticmethod
    async def _persist_audit(
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        latency_ms: int,
        ip: str,
        tenant_id: str,
    ) -> None:
        """Write one audit record to the kernel audit_log table (non-blocking)."""
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.kernel.audit_logger import AuditLogger
            async with AsyncSessionLocal() as db:
                audit = AuditLogger(db)
                outcome = "COMPLETED" if status_code < 400 else (
                    "BLOCKED" if status_code in (401, 403, 429) else "FAILED"
                )
                await audit.write(
                    action_type=f"http.{method.lower()}",
                    actor=f"tenant:{tenant_id}",
                    outcome=outcome,
                    details={
                        "path":       path,
                        "status":     status_code,
                        "latency_ms": latency_ms,
                        "ip":         ip,
                        "request_id": request_id,
                    },
                )
                await db.commit()
        except Exception as exc:
            # Never block a response for an audit write failure.
            logger.debug("request_audit: db write failed (non-fatal) — %s", exc)


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
