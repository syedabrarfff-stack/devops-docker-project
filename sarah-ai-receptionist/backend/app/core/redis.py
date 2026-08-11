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

import redis.asyncio as redis_lib

from app.config.settings import get_settings

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
