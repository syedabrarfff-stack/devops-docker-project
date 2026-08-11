"""
An unreachable database or Redis must fail fast, not hang, in the call path.

Measured live against this exact deployment while RDS/ElastiCache were
unreachable: /readyz's own "SELECT 1" + "PING" checks took 8.4 seconds
combined to report failure, because neither the SQLAlchemy engine nor any of
the ad-hoc redis.asyncio.from_url() call sites across the codebase set an
explicit connect timeout. asyncpg's own default is 60 seconds; redis-py's is
effectively unbounded (the OS's own TCP timeout).

That mattered most in the one place it's least affordable: call setup hits
Redis twice (webhook validation write, media-stream validation read) and the
database once (clinic lookup) before Sarah can say a word. An outage there
didn't cost the caller milliseconds -- it silently added several extra
seconds to every call, indistinguishable from Sarah just being slow to
answer. This is very likely the dominant chunk of a "10 second" gap: it
dwarfs the ~2s of measured AI first-token latency (see
test_model_strings.py's sibling commit) by several times over.

These tests can't spin up a real unreachable Postgres/Redis in CI, so they
pin the configuration that determines whether a real outage fails in ~1-2s
or in tens of seconds -- the actual bug, verifiable without network access.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core import database as database_module
from app.core.redis import CONNECT_TIMEOUT_SECONDS, get_redis_client


def test_the_database_engine_will_not_wait_asyncpgs_60_second_default():
    """asyncpg.connect()'s own default timeout is 60 seconds -- confirmed
    against asyncpg's own source, not assumed. Every session checkout that
    needs a fresh connection (the entire pool, for as long as the database
    is unreachable) would otherwise pay up to that default before the caller
    sees any error.

    Asserted against database.py's own source rather than the constructed
    engine object: `connect_args` passed to create_async_engine ends up
    wrapped inside a closure on the connection pool with no stable,
    version-independent way to read it back out, so pinning the call site
    that sets it is the robust check here.
    """
    import inspect

    source = inspect.getsource(database_module)
    assert "connect_args" in source and '"timeout"' in source, (
        "no explicit connect timeout passed to create_async_engine -- "
        "falls back to asyncpg's 60s default"
    )


@pytest.mark.asyncio
async def test_every_redis_client_in_this_codebase_goes_through_one_bounded_factory():
    """A per-call-site redis_lib.from_url() is exactly how this went
    unbounded in the first place -- five separate construction sites, none
    of them setting a timeout, because there was no single place that made
    the timeout the default rather than something each call site had to
    remember. get_redis_client() is that place now."""
    client = get_redis_client()
    try:
        pool_kwargs = client.connection_pool.connection_kwargs
        assert pool_kwargs.get("socket_connect_timeout") == CONNECT_TIMEOUT_SECONDS
        assert pool_kwargs.get("socket_timeout") == CONNECT_TIMEOUT_SECONDS
    finally:
        await client.aclose()


def test_the_shared_timeout_is_short_enough_to_matter_for_a_live_call():
    """The whole point: bounded to comfortably under a second of *added*
    worst-case latency per Redis touch in the call path, not just "shorter
    than 60 seconds." A healthy in-VPC ElastiCache node answers a PING in
    single-digit milliseconds -- anything past ~1s is already a lost cause,
    not a connection worth waiting longer for."""
    assert CONNECT_TIMEOUT_SECONDS <= 1.5


def test_call_setup_uses_the_bounded_client_not_a_bare_from_url():
    """Pins that call_handler.py's two validation call sites -- the ones
    directly in front of Sarah's first word on every phone call -- were
    actually migrated, not just that the shared factory exists unused
    somewhere."""
    import inspect

    from app.routes import call_handler

    source = inspect.getsource(call_handler)
    assert "get_redis_client()" in source
    assert "redis_lib.from_url" not in source, (
        "call_handler.py still constructs an unbounded redis client directly"
    )
