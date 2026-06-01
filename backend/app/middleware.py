from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.tenant_context import reset_current_tenant_id, set_current_tenant_id

logger = logging.getLogger(__name__)


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
