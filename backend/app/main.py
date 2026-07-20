import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.database import init_db
from app.models import register_models
from app.api.v1 import api_router
from app.middleware import (
    ObservabilityRefreshMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    TenantContextMiddleware,
    http_exception_handler,
    setup_observability,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.core.rate_limit import limiter, RATE_LIMITING_ENABLED
import app.models  # noqa — registers all models with Base.metadata before init_db()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
register_models()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    logger.info("⚡ JARVIS booting up — Aliyar Solutions")

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.warning(f"DB init skipped: {e}")

    # ── Bootstrap master tenant (idempotent) ─────────────────────────────────
    try:
        import uuid as _uuid
        from app.core.database import AsyncSessionLocal
        from app.models.tenant import Tenant, PlanTier
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            configured_id = settings.JARVIS_DEFAULT_TENANT_ID
            tenant = None

            if configured_id:
                try:
                    result = await db.execute(select(Tenant).where(Tenant.id == _uuid.UUID(configured_id)))
                    tenant = result.scalar_one_or_none()
                except Exception as exc:
                    logger.warning("Default tenant lookup failed for %s: %s", configured_id, exc)

            if tenant is None:
                result = await db.execute(
                    select(Tenant)
                    .where(Tenant.is_active.is_(True))
                    .order_by(Tenant.created_at.asc())
                    .limit(1)
                )
                tenant = result.scalar_one_or_none()

            if tenant is None:
                tid = _uuid.UUID(configured_id) if configured_id else _uuid.uuid4()
                tenant = Tenant(
                    id=tid,
                    tenant_id=tid,
                    name=settings.COMPANY_NAME,
                    slug="aliyar-solutions",
                    plan_tier=PlanTier.ENTERPRISE,
                    api_key_hash=None,
                    settings={"limits": {"max_leads": None, "max_agents": None, "max_ai_calls": None}},
                    is_active=True,
                )
                db.add(tenant)
                await db.commit()
                await db.refresh(tenant)
                logger.info("✅ Master tenant bootstrapped — %s [%s]", tenant.name, tenant.id)

            if not settings.JARVIS_DEFAULT_TENANT_ID:
                settings.JARVIS_DEFAULT_TENANT_ID = str(tenant.id)
                logger.info("✅ JARVIS_DEFAULT_TENANT_ID auto-set → %s", tenant.id)

    except Exception as e:
        logger.warning("Tenant bootstrap skipped: %s", e)

    # ── Auto-seed service catalog (idempotent — skips if already seeded) ──────
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.catalog.catalog_service import seed_catalog, get_catalog_stats
        async with AsyncSessionLocal() as db:
            stats = await get_catalog_stats(db)
            if stats.get("total", 0) == 0:
                result = await seed_catalog(db)
                await db.commit()
                logger.info(f"✅ Service catalog seeded — {result} divisions")
            else:
                logger.info(f"✅ Service catalog ready — {stats['total']} divisions")
    except Exception as e:
        logger.warning(f"Catalog seed skipped: {e}")

    # ── Auto-seed team members (idempotent) ───────────────────────────────────
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.team.team_service import seed_team, get_team_stats
        async with AsyncSessionLocal() as db:
            ts = await get_team_stats(db)
            if ts.get("total", 0) == 0:
                result = await seed_team(db)
                await db.commit()
                logger.info(f"✅ Team registry seeded — {result.get('inserted', 0)} members")
            else:
                logger.info(f"✅ Team registry ready — {ts['total']} members")
    except Exception as e:
        logger.warning(f"Team seed skipped: {e}")

    # ── Seed JARVIS authority instructions into permanent memory ──────────────
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.memory.manager import store_instruction
        from app.services.intelligence.jarvis_authority import (
            JARVIS_FULL_AUTHORITY, CAPTAIN_APPROVAL_REQUIRED, JARVIS_ALERTS_CAPTAIN
        )
        async with AsyncSessionLocal() as db:
            await store_instruction(
                db,
                content=(
                    "JARVIS FULL AUTHORITY — execute immediately without asking Captain: "
                    + ", ".join(JARVIS_FULL_AUTHORITY)
                ),
                category="authority",
                priority=10,
                key="authority:jarvis_full_authority",
            )
            await store_instruction(
                db,
                content=(
                    "CAPTAIN APPROVAL REQUIRED — prepare fully, never execute without Captain sign-off: "
                    + ", ".join(CAPTAIN_APPROVAL_REQUIRED)
                ),
                category="authority",
                priority=10,
                key="authority:captain_approval_required",
            )
            await store_instruction(
                db,
                content=(
                    "ALERT CAPTAIN (execute + notify, do not stop): "
                    + ", ".join(JARVIS_ALERTS_CAPTAIN)
                ),
                category="authority",
                priority=9,
                key="authority:jarvis_alerts_captain",
            )
            await store_instruction(
                db,
                content=(
                    "COMPANY: Aliyar Solutions — global technology company. "
                    "CEO: Syed Abrar (Captain). "
                    "JARVIS: Supreme Operational Manager. "
                    "Never say 'I' in client-facing output — always say 'our team' or 'Aliyar Solutions'. "
                    "Never mention AI, bots, or automation to clients. "
                    "Never discuss pricing until Captain approves it. "
                    "Always offer a demo first. Never push for a sale."
                ),
                category="company",
                priority=10,
                key="authority:company_standing_orders",
            )
            await db.commit()
        logger.info("✅ JARVIS authority instructions seeded into memory")
    except Exception as e:
        logger.warning(f"Authority seeding skipped: {e}")

    # Seed M2 human intelligence and client liaison identities (idempotent)
    try:
        from app.services.agents.liaison import client_liaison_service
        from app.services.memory.human_intelligence import seed_human_intelligence

        tenant_id = settings.JARVIS_DEFAULT_TENANT_ID
        if tenant_id:
            human_result = await seed_human_intelligence(tenant_id)
            liaison_result = await client_liaison_service.seed_agents(tenant_id)
            logger.info(
                "Human intelligence and liaison agents ready: %s / %s",
                human_result.get("m2_ready"),
                liaison_result.get("agents"),
            )
    except Exception as e:
        logger.warning(f"Human intelligence and liaison seed skipped: {e}")

    # ── Task queue ────────────────────────────────────────────────────────────
    try:
        from app.services.tasks.queue import requeue_pending, worker
        await requeue_pending()
        logger.info("✅ Task queue initialized — starting worker")
        worker_task = asyncio.create_task(worker())
        worker_task.add_done_callback(
            lambda t: logger.error("Task worker exited unexpectedly: %s", t.exception()) if not t.cancelled() and t.exception() else logger.warning("Task worker stopped")
        )
    except Exception as e:
        logger.warning(f"Task worker skipped: {e}")
        worker_task = None

    # ── APScheduler (file-lock leader election) ────────────────────────────────
    # Only one gunicorn worker may run the scheduler. We use an exclusive file
    # lock: the first worker to acquire it starts APScheduler; the rest skip.
    # When the leader dies (recycling, shutdown), the OS releases the lock and
    # the next worker to start claims it.
    import fcntl as _fcntl
    _scheduler_lock_fd = None
    try:
        _scheduler_lock_fd = open("/tmp/jarvis_scheduler.lock", "w")
        _fcntl.flock(_scheduler_lock_fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        from app.services.scheduler.scheduler import start_scheduler
        await start_scheduler()
        logger.info("✅ Scheduler started (this worker is the scheduler leader)")

        try:
            from app.services.kernel.health_aggregator import get_health_aggregator
            from app.services.kernel.core_health_checks import register_core_checks
            _aggregator = get_health_aggregator()
            register_core_checks(_aggregator)
            await _aggregator.start()
            logger.info("✅ HealthAggregator started (this worker is the scheduler leader)")
        except Exception as e:
            logger.warning("HealthAggregator start skipped: %s", e)
    except BlockingIOError:
        logger.info("Scheduler running in another worker — skipping in this one")
        if _scheduler_lock_fd:
            _scheduler_lock_fd.close()
        _scheduler_lock_fd = None
    except Exception as e:
        logger.warning("Scheduler skipped (this worker holds the leader lock): %s", e)

    logger.info("🚀 JARVIS operational — Aliyar Solutions v9.0.0")
    yield

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    if worker_task:
        worker_task.cancel()
    if _scheduler_lock_fd:
        try:
            from app.services.scheduler.scheduler import stop_scheduler
            stop_scheduler()
        except Exception as exc:
            logger.warning("Scheduler stop failed during shutdown: %s", exc)
        try:
            from app.services.kernel.health_aggregator import get_health_aggregator
            await get_health_aggregator().stop()
        except Exception as exc:
            logger.warning("HealthAggregator stop failed during shutdown: %s", exc)
        _scheduler_lock_fd.close()
    logger.info("JARVIS shutting down cleanly")


app = FastAPI(
    title="JARVIS — Aliyar Solutions",
    description="Autonomous AI Operating System",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

app.state.limiter = limiter

if RATE_LIMITING_ENABLED:
    try:
        from slowapi import SlowAPIMiddleware
        from slowapi.errors import RateLimitExceeded
        from slowapi import _rate_limit_exceeded_handler
        app.add_middleware(SlowAPIMiddleware)
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    except ImportError:
        pass

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(ObservabilityRefreshMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Tenant-ID", "X-API-Key"],
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(api_router)
setup_observability(app)


@app.get("/health")
async def health():
    """Shallow liveness probe — fast, no DB required. Used by Docker HEALTHCHECK."""
    return {
        "status": "ok",
        "system": "JARVIS",
        "company": "Aliyar Solutions",
        "version": settings.APP_VERSION,
    }


@app.get("/readyz")
async def readyz():
    """
    Deep readiness probe — checks all critical subsystems.
    Returns 200 when fully ready to serve traffic, 503 if degraded.
    """
    import time
    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal
    from app.services.ai.router import ai_router as _ai_router

    checks: dict[str, dict] = {}
    overall_ok = True

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok", "latency_ms": int((time.monotonic() - t0) * 1000)}
    except Exception as e:
        logger.error("readyz: database check failed: %s", e)
        checks["database"] = {"status": "error", "error": "database_unavailable"}
        overall_ok = False

    # ── AI providers ──────────────────────────────────────────────────────────
    try:
        providers = _ai_router.get_provider_status()
        configured = [k for k, v in providers.items() if v.get("configured")]
        available = _ai_router.operational_providers()
        checks["ai_providers"] = {
            "status": "ok" if available else "degraded",
            "available": len(available),
            "configured": len(configured),
            "total": len(providers),
            "active": available,
            "configured_providers": configured,
        }
        # AI providers unavailable = degraded, not a hard failure.
        # System can still serve DB, leads, outreach scheduling, and CRM operations.
    except Exception as e:
        logger.error("readyz: AI provider status check failed: %s", e)
        checks["ai_providers"] = {"status": "error", "error": "provider_check_failed"}

    # ── Scheduler ─────────────────────────────────────────────────────────────
    try:
        from app.services.scheduler.scheduler import get_scheduler
        sched = get_scheduler()
        running = sched is not None and sched.running
        checks["scheduler"] = {"status": "ok" if running else "stopped", "running": running}
    except Exception as exc:
        logger.warning("readyz: scheduler check failed: %s", exc)
        checks["scheduler"] = {"status": "unknown"}

    # ── Team registry ─────────────────────────────────────────────────────────
    try:
        async with AsyncSessionLocal() as db:
            from app.services.team.team_service import get_team_stats
            ts = await get_team_stats(db)
            checks["team_registry"] = {"status": "ok", "members": ts.get("active", 0)}
    except Exception as exc:
        logger.warning("readyz: team registry check failed: %s", exc)
        checks["team_registry"] = {"status": "unknown"}

    # ── Evolution API (WhatsApp) ───────────────────────────────────────────────
    try:
        import httpx
        from app.core.config import settings as _s
        evol_url = (_s.EVOLUTION_API_URL or "http://evolution:8080").rstrip("/")
        evol_key = _s.EVOLUTION_API_KEY or ""
        instance = _s.WHATSAPP_INSTANCE_NAME or "jarvis-main"
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(
                f"{evol_url}/instance/connectionState/{instance}",
                headers={"apikey": evol_key},
            )
            if r.status_code == 200:
                state_data = r.json()
                state = (
                    state_data.get("instance", {}).get("state")
                    or state_data.get("state")
                    or "unknown"
                )
                checks["whatsapp"] = {
                    "status": "connected" if state == "open" else "disconnected",
                    "state": state,
                    "instance": instance,
                }
            else:
                checks["whatsapp"] = {"status": "unreachable", "http": r.status_code, "instance": instance}
    except Exception as exc:
        checks["whatsapp"] = {"status": "unreachable", "error": type(exc).__name__, "instance": settings.WHATSAPP_INSTANCE_NAME or "jarvis-main"}

    # ── Redis ─────────────────────────────────────────────────────────────────
    try:
        import asyncio as _asyncio
        from app.core.config import settings as _s
        if _s.REDIS_URL:
            import redis.asyncio as aioredis
            _t0 = time.monotonic()
            _client = aioredis.from_url(_s.REDIS_URL, socket_connect_timeout=2)
            await _asyncio.wait_for(_client.ping(), timeout=2.0)
            await _client.aclose()
            checks["redis"] = {"status": "ok", "latency_ms": int((time.monotonic() - _t0) * 1000)}
        else:
            checks["redis"] = {"status": "not_configured"}
    except Exception as exc:
        checks["redis"] = {"status": "error", "error": type(exc).__name__}

    # ── SES (email) ───────────────────────────────────────────────────────────
    try:
        import asyncio as _asyncio
        from app.services.outreach.email_transport import get_outbound_email_status
        ses = await _asyncio.wait_for(get_outbound_email_status(validate_provider=True), timeout=2.0)
        checks["ses"] = {
            "status": "connected" if ses.get("connected") else "not_connected",
            "send_mode": ses.get("send_mode") or ses.get("status"),
            "configured": bool(ses.get("configured")),
            "from_email": ses.get("from_email"),
            "blocker": ses.get("blocker_code"),
        }
    except Exception as exc:
        checks["ses"] = {"status": "unknown", "error": type(exc).__name__}

    status_code = 200 if overall_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if overall_ok else "degraded",
            "system": "JARVIS",
            "version": settings.APP_VERSION,
            "checks": checks,
        },
    )
