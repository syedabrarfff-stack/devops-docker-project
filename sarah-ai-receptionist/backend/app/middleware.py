"""
Request tracing, timing, and a structured error envelope.

Without this, an unhandled exception fell through to FastAPI's bare default
500 -- no request ID, no elapsed time, nothing to correlate a failure back to
a specific line in CloudWatch. On a system that will eventually be debugging
a failed live call under time pressure, that gap costs real minutes.
"""

import contextvars
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

# Read by a logging filter so every log line emitted while handling a request
# carries its ID, not just the ones that explicitly pass it in.
_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIDLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        return True


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request ID (or trusts an inbound one from the ALB/CloudFront),
    times the request, and stamps both onto the response headers.

    An inbound X-Request-ID is honored rather than always minting a new one,
    so a single ID can be traced across CloudFront -> ALB -> this service in
    front-to-back log correlation, instead of a fresh one appearing at every hop.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        # Starlette's exception-handling layer sits *outside* this middleware
        # (it wraps it, not the other way round) -- resetting the contextvar
        # in a finally here would revert it to "-" while the exception is
        # still propagating outward, before install_error_handling's handler
        # ever runs. request.state isn't subject to that ordering: it's set
        # once, here, and any layer holding the same `request` object -- the
        # handler included -- reads the same value regardless of when this
        # middleware's own frame unwinds.
        request.state.request_id = request_id
        token = _request_id_ctx.set(request_id)
        start = time.monotonic()
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        elapsed_ms = (time.monotonic() - start) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
        # request_id is passed explicitly rather than left to the logging
        # filter: this line runs after the finally above has already reset
        # the contextvar, so the filter would stamp "-" here even though the
        # ID is right there in scope.
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} "
            f"({elapsed_ms:.1f}ms) [{request_id}]"
        )
        return response


def install_error_handling(app: FastAPI) -> None:
    """Replaces FastAPI's bare default 500 with a JSON envelope carrying the
    request ID, so a caller (or a support ticket) can reference one identifier
    that a log search actually finds -- and the traceback still goes to
    CloudWatch, it's just never handed to the client."""

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception):
        # request.state, not the contextvar: RequestContextMiddleware's own
        # finally has already reset the contextvar to "-" by the time this
        # handler runs (it lives in a Starlette layer outside that
        # middleware), but request.state was set once, directly on this same
        # request object, and isn't subject to that unwind-order problem.
        request_id = getattr(request.state, "request_id", "-")
        logger.exception(f"Unhandled exception on {request.method} {request.url.path} [{request_id}]")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal server error",
                    "request_id": request_id,
                }
            },
            headers={REQUEST_ID_HEADER: request_id},
        )
