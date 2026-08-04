"""
Refresh-token issuance, verification, rotation, and revocation.

Opaque random strings, stored in Redis keyed by their hash, mapped to the
user_id they authenticate. Never JWTs -- refresh tokens live in the browser
for weeks, and a stolen JWT can be verified offline forever regardless of
what we do server-side. An opaque token means every use is a Redis lookup:
revoke it there, and every subsequent use fails.

Stored as SHA-256 hashes rather than raw values: a Redis snapshot (backup,
memory dump, log leak) then reveals nothing usable to hit the API with,
same reason password hashes exist.

Rotation on every use ("refresh-token rotation") means a stolen token is
useful for at most one refresh before the theft is detected -- the
legitimate client's next refresh will fail, which is the observable signal.
"""

import hashlib
import logging
import secrets
from typing import Optional

import redis.asyncio as redis_lib

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# Longer than any refresh-token TTL so Redis is authoritative on expiry --
# we don't want to accept a "not-yet-expired" token that's already gone from
# Redis due to a shorter TTL there.
_REDIS_KEY_PREFIX = "auth:refresh:"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _key(token: str) -> str:
    return _REDIS_KEY_PREFIX + _hash(token)


async def issue_refresh_token(user_id: str) -> str:
    """Create a fresh refresh token, store its hash in Redis, return the
    plaintext (only time it's ever readable)."""
    settings = get_settings()
    token = secrets.token_urlsafe(48)  # ~64 chars, 384 bits of entropy
    r = redis_lib.from_url(settings.redis_url)
    try:
        await r.set(
            _key(token),
            user_id,
            ex=settings.refresh_token_expire_days * 24 * 60 * 60,
        )
    finally:
        await r.aclose()
    return token


async def consume_refresh_token(token: str) -> Optional[str]:
    """Verify + delete a refresh token in a single atomic Redis operation.

    Returns the user_id it identifies, or None if it's unknown, expired, or
    already used. Deleting inside the same pipeline enforces one-time use:
    a stolen token can be redeemed at most once before it's gone.
    """
    if not token:
        return None
    settings = get_settings()
    r = redis_lib.from_url(settings.redis_url)
    try:
        pipe = r.pipeline()
        await pipe.get(_key(token))
        await pipe.delete(_key(token))
        results = await pipe.execute()
        user_id = results[0]
        deleted = results[1]
        if not deleted:
            return None
        return user_id.decode() if isinstance(user_id, bytes) else user_id
    finally:
        await r.aclose()


async def revoke_refresh_token(token: str) -> None:
    """Idempotent revoke -- deletes the key whether it exists or not."""
    if not token:
        return
    settings = get_settings()
    r = redis_lib.from_url(settings.redis_url)
    try:
        await r.delete(_key(token))
    finally:
        await r.aclose()
