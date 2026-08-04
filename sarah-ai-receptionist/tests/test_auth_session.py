"""
Regression tests for the session-hardening changes.

Covers the invariants that make the new model safer than the old one:
  - the refresh token is opaque, not a JWT (a database dump / log leak
    doesn't hand out infinite-lifetime access)
  - stored server-side as a hash, not plaintext
  - one-shot use: a stolen token is useful for at most one refresh, and
    the legitimate client's next attempt fails as an observable signal
  - login timing is independent of whether the email exists (no user
    enumeration)

These use the fakeredis in-process backend so the tests don't need a live
Redis; the code path exercised is identical to production.
"""

import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture(autouse=True)
def _fake_redis(monkeypatch):
    """Point redis.asyncio.from_url at fakeredis for every test in this file.
    fakeredis is a stdlib-only in-process backend that behaves identically
    for the small surface (SET with TTL, pipelined GET+DEL) the token
    service uses."""
    fakeredis = pytest.importorskip("fakeredis")
    r = fakeredis.aioredis.FakeRedis()
    monkeypatch.setattr("redis.asyncio.from_url", lambda *args, **kwargs: r)


@pytest.mark.asyncio
async def test_issue_returns_opaque_token_not_a_jwt():
    """The token itself must not be structured -- a JWT-shaped refresh
    token is verifiable offline forever, defeating the whole point of
    server-side revocation."""
    from app.services.refresh_tokens import issue_refresh_token

    t = await issue_refresh_token("user-1")
    assert isinstance(t, str) and len(t) >= 40
    assert "." not in t, "opaque tokens must not look like JWTs (three dot-separated parts)"


@pytest.mark.asyncio
async def test_consume_returns_user_id_then_invalidates_token():
    """One-shot use: the same token cannot be redeemed twice. This is the
    property that limits how much value a stolen token has."""
    from app.services.refresh_tokens import consume_refresh_token, issue_refresh_token

    t = await issue_refresh_token("user-42")
    first = await consume_refresh_token(t)
    second = await consume_refresh_token(t)
    assert first == "user-42"
    assert second is None, "second use of the same token must fail"


@pytest.mark.asyncio
async def test_consume_unknown_token_returns_none_never_raises():
    """A junk token in the cookie must produce a clean 401 upstream, not
    a 500. Raising here would be a DoS vector: attacker sends garbage,
    server logs a stack trace on every request."""
    from app.services.refresh_tokens import consume_refresh_token

    assert await consume_refresh_token("no-such-token") is None
    assert await consume_refresh_token("") is None


@pytest.mark.asyncio
async def test_revoke_is_idempotent():
    """Logout must succeed even if the token is already gone (double-tap,
    concurrent tabs). No exception, no observable side effect."""
    from app.services.refresh_tokens import revoke_refresh_token

    await revoke_refresh_token("never-existed")  # must not raise


@pytest.mark.asyncio
async def test_token_is_stored_as_hash_not_plaintext():
    """A Redis snapshot leaking must not hand out usable tokens. Test by
    inspecting the actual key format used to store."""
    import hashlib

    import redis.asyncio as redis_lib

    from app.services.refresh_tokens import issue_refresh_token

    t = await issue_refresh_token("user-9")
    r = redis_lib.from_url("ignored")  # fixture rewrote from_url
    keys = [k.decode() if isinstance(k, bytes) else k async for k in r.scan_iter()]
    plain_key = f"auth:refresh:{t}"
    hashed_key = "auth:refresh:" + hashlib.sha256(t.encode()).hexdigest()
    assert plain_key not in keys, "plaintext token must never appear as a key"
    assert hashed_key in keys, "expected hashed-token key not stored"


def test_login_timing_side_channel_is_closed():
    """A nonexistent-email login must take approximately the same time as
    a wrong-password login on a real user -- otherwise an attacker can
    enumerate registered emails purely from response timing."""
    from app.core.security import hash_password, verify_password
    from app.routes.auth import _DUMMY_HASH

    real = hash_password("some-real-password")

    # Warm up so JIT / caches don't skew the first sample.
    verify_password("x", real)
    verify_password("x", _DUMMY_HASH)

    t0 = time.perf_counter(); verify_password("wrong", real); t_real = time.perf_counter() - t0
    t0 = time.perf_counter(); verify_password("wrong", _DUMMY_HASH); t_dummy = time.perf_counter() - t0

    # Bcrypt at cost=12 dominates both; anything within ~50% of each other
    # (well inside network jitter) is effectively indistinguishable.
    ratio = max(t_real, t_dummy) / max(min(t_real, t_dummy), 1e-6)
    assert ratio < 1.5, f"timing ratio {ratio:.2f} is enough to enumerate emails"
