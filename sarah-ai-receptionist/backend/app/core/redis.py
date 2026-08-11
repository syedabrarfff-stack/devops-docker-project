"""
Shared Redis client factory.

Every redis.asyncio.from_url() call site in this codebase used to construct
its own client with no connect or socket timeout. redis-py's default for an
unspecified socket_connect_timeout is to block on the OS's own TCP timeout,
which is not bounded by anything this application controls -- confirmed live
against this exact deployment: /readyz (which does a bare `PING`) took 8.4
seconds to report Redis and the database both unreachable, not milliseconds.

That mattered most in the one place it's least affordable: call setup hits
Redis twice before Sarah can say a word (the webhook write in
_mark_call_validated, then the media-stream read in
_consume_call_validation), with no timeout on either. An unreachable Redis
didn't fail fast there -- it silently added several seconds to every single
call, indistinguishable from Sarah just being slow.
"""

from typing import TYPE_CHECKING

import redis.asyncio as redis_lib

from app.config.settings import get_settings

if TYPE_CHECKING:
    from arq.connections import RedisSettings

# Deliberately short: every call site here talks to an in-VPC ElastiCache
# node, not a service across the public internet. A healthy Redis answers a
# PING in single-digit milliseconds; a connection that hasn't been accepted
# within one second is not going to become healthy by waiting longer; it is
# just adding directly to whatever a caller is waiting on.
CONNECT_TIMEOUT_SECONDS = 1.0


def get_redis_client() -> redis_lib.Redis:
    settings = get_settings()
    return redis_lib.from_url(
        settings.redis_url,
        socket_connect_timeout=CONNECT_TIMEOUT_SECONDS,
        socket_timeout=CONNECT_TIMEOUT_SECONDS,
    )


def get_request_scoped_arq_settings() -> "RedisSettings":
    """RedisSettings for a request-path arq pool -- /readyz's own check and
    call_recorder.py's post-call summary enqueue, NOT the long-running worker
    process (see worker.py, deliberately untouched below).

    arq's own defaults -- confirmed against the installed package, not
    assumed -- are conn_timeout=1s, conn_retries=5, conn_retry_delay=1s. Against
    a genuinely unreachable Redis that is up to ~9 seconds of retrying before
    arq's own create_pool() gives up, which is most of the gap between
    get_redis_client()'s 1s bound and /readyz's still-slow ~7.9s measured
    total after every OTHER Redis call site in this codebase was fixed.
    Retrying five times makes sense for a worker process that should ride out
    a transient blip over its whole lifetime; it makes no sense for a
    request that's already decided to give up after one failure everywhere
    else in the app.

    conn_retries=1 (not 0): arq's RedisSettings doesn't treat 0 as "no
    retries" cleanly in every version, so 1 is the safe way to say "try
    once, don't keep going."

    Import is deliberately local, not at module top: this module is on the
    long-running worker process's own mandatory startup import chain
    (worker.py -> tasks.py -> notification_service.py -> here), and that
    process's ECS container health check is a bare `python -c "import
    app.workers.worker"` -- any new top-level import added here becomes a
    new way for that specific health check to fail. This function is the
    only thing in this module that needs arq at all; nothing about the
    worker's own startup should depend on it.
    """
    from arq.connections import RedisSettings

    settings = get_settings()
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    redis_settings.conn_timeout = int(CONNECT_TIMEOUT_SECONDS)
    redis_settings.conn_retries = 1
    return redis_settings
