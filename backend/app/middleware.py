"""
JARVIS middleware stack:
- RequestIDMiddleware  — attaches X-Request-ID to every request/response
- GlobalExceptionHandler — standardized JSON error envelope
"""
import uuid
import logging
import time
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# ── Request-ID + latency middleware ───────────────────────────────────────────

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        t0 = time.monotonic()

        response = await call_next(request)

        latency_ms = int((time.monotonic() - t0) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{latency_ms}ms"

        # Log non-health requests at INFO
        path = request.url.path
        if path not in ("/health", "/readyz", "/favicon.ico"):
            logger.info(
                f"{request.method} {path} → {response.status_code} [{latency_ms}ms] req={request_id}"
            )
        return response


# ── Exception handlers ────────────────────────────────────────────────────────

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
        {"field": ".".join(str(l) for l in e["loc"]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(422, "Validation error", request, detail=errors),
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unhandled exception req={request_id}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(500, "Internal server error", request),
        headers={"X-Request-ID": request_id},
    )
