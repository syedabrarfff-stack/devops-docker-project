"""Shared rate limiter instance for JARVIS API.

Uses slowapi with Redis storage for distributed, restart-safe limiting.
Falls back to in-memory if Redis is unavailable.
"""
from __future__ import annotations

import logging
from fastapi import Request

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For from nginx."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


try:
    from slowapi import Limiter
    from app.core.config import settings

    _redis_url = None
    if settings.REDIS_URL:
        _redis_url = settings.REDIS_URL

    limiter = Limiter(
        key_func=_get_client_ip,
        storage_uri=_redis_url,
        default_limits=["200/minute"],
    )
    RATE_LIMITING_ENABLED = True
except ImportError:
    logger.warning("slowapi not installed — rate limiting disabled")
    RATE_LIMITING_ENABLED = False

    class _NoopLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    limiter = _NoopLimiter()  # type: ignore[assignment]
