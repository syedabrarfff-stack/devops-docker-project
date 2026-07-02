"""Shared rate limiter instance for JARVIS API.

Uses slowapi with Redis storage for distributed, restart-safe limiting.
Falls back to in-memory storage if Redis is unavailable at startup,
and gracefully degrades if Redis becomes unreachable at runtime.
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


def _build_limiter():
    """Build rate limiter with Redis if available, otherwise in-memory."""
    try:
        from slowapi import Limiter
        from app.core.config import settings

        storage_uri = settings.REDIS_URL or None

        if storage_uri:
            import redis as _redis
            try:
                r = _redis.from_url(storage_uri, socket_connect_timeout=2)
                r.ping()
                logger.info("Rate limiter: using Redis storage at %s", storage_uri.split("@")[-1])
            except Exception:
                logger.warning("Rate limiter: Redis unreachable, falling back to in-memory storage")
                storage_uri = "memory://"
        else:
            storage_uri = "memory://"
            logger.info("Rate limiter: no REDIS_URL configured, using in-memory storage")

        lim = Limiter(
            key_func=_get_client_ip,
            storage_uri=storage_uri,
            default_limits=["200/minute"],
        )
        return lim, True

    except ImportError:
        logger.warning("slowapi not installed — rate limiting disabled")
        return None, False


_result = _build_limiter()
_real_limiter = _result[0]
RATE_LIMITING_ENABLED = _result[1]

if _real_limiter is not None:
    limiter = _real_limiter
else:
    class _NoopLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    limiter = _NoopLimiter()  # type: ignore[assignment]
