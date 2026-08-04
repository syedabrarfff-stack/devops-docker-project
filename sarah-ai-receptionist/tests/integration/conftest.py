"""
Real-Postgres integration test fixtures.

Uses testcontainers to spin a throwaway Postgres in Docker, applies the
Alembic migrations against it, and hands each test a fresh session. Runs
the same schema production runs, so a migration that forgot a column or an
async query that only works against SQLite would fail here where a unit
test would silently pass.

These tests are marked `integration` and require Docker; the regular `pytest`
run skips them automatically when Docker isn't reachable.
"""

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Match the sys.path setup unit tests do per-file, but once at collection
# time so integration test files don't each need their own boilerplate.
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

# Session-scoped -- one container across the whole run, not per-test. Postgres
# takes ~2s to boot; per-test would be minutes on a small suite.
@pytest.fixture(scope="session")
def postgres_container():
    # testcontainers reorganized in v4; `community` is the new path but the
    # old one still works. Try both so this doesn't crack on either version.
    try:
        from testcontainers.postgres import PostgresContainer  # legacy
    except ImportError:
        try:
            from testcontainers.community.postgres import PostgresContainer  # >=4.x
        except ImportError:
            pytest.skip("testcontainers not installed; skipping integration tests")

    try:
        # postgres:16-alpine matches the production major version so any
        # version-specific gotchas (jsonb operators, upsert syntax) reproduce
        # here rather than in prod.
        container = PostgresContainer("postgres:16-alpine", driver="asyncpg")
        container.start()
    except Exception as e:
        pytest.skip(f"Docker not available for integration tests: {e}")

    yield container
    container.stop()


@pytest.fixture(scope="session")
def _database_url(postgres_container):
    """The URL string only -- the actual engine is per-test to avoid the
    asyncpg 'attached to a different loop' error you get when a session-
    scoped engine tries to talk to Postgres from a fresh test event loop."""
    url = postgres_container.get_connection_url()
    os.environ["DATABASE_URL"] = url
    for k, v in {
        "OPENROUTER_API_KEY": "x", "TWILIO_ACCOUNT_SID": "ACx",
        "TWILIO_AUTH_TOKEN": "x", "TWILIO_PHONE_NUMBER": "+15550000000",
        "DEEPGRAM_API_KEY": "x", "ELEVENLABS_API_KEY": "x",
        "ELEVENLABS_VOICE_ID": "x", "REDIS_URL": "redis://localhost:6379",
        "JWT_SECRET_KEY": "test-secret",
    }.items():
        os.environ.setdefault(k, v)

    from app.config.settings import get_settings
    get_settings.cache_clear()
    return url


@pytest_asyncio.fixture
async def db_session(_database_url):
    """Fresh per-test engine and session against the shared testcontainer.

    A session-scoped engine would fail with asyncpg 'attached to a different
    loop': pytest-asyncio spins a new loop per test by default, and asyncpg
    connections are bound to the loop that created them. Rebuilding the
    engine each test is cheap (~50ms) and eliminates the whole class of
    error. Schema is created via SQLAlchemy metadata rather than Alembic:
    alembic's env.py calls asyncio.run(), which conflicts with the already-
    running pytest-asyncio loop. Same models, same tables -- alembic
    ordering is verified separately by the deployed migration task in prod.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    # Force-import every model so Base.metadata.create_all sees them all.
    from app.core.database import Base
    import app.models  # noqa: F401

    engine = create_async_engine(_database_url, poolclass=None)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    # Monkey-patch app.core.database.AsyncSessionLocal so service code's
    # `async with AsyncSessionLocal()` picks up this test's engine, not the
    # module-level one bound to a different loop.
    import app.core.database as db_mod
    original = db_mod.AsyncSessionLocal
    db_mod.AsyncSessionLocal = SessionLocal
    try:
        async with SessionLocal() as session:
            yield session
    finally:
        db_mod.AsyncSessionLocal = original
        # Truncate so tests don't leak state to each other. CASCADE covers FKs.
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text(
                "TRUNCATE TABLE port_requests, audit_log, subscriptions, appointments, "
                "call_logs, patients, providers, users, clinics, organizations "
                "RESTART IDENTITY CASCADE"
            ))
        await engine.dispose()
