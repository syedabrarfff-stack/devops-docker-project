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
    TenantContextMiddleware,
    http_exception_handler,
    setup_observability,
    validation_exception_handler,
    unhandled_exception_handler,
)
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

    # ── Task queue ────────────────────────────────────────────────────────────
    try:
        from app.services.tasks.queue import requeue_pending, worker
        await requeue_pending()
        logger.info("✅ Task queue initialized — starting worker")
        worker_task = asyncio.create_task(worker())
    except Exception as e:
        logger.warning(f"Task worker skipped: {e}")
        worker_task = None

    # ── APScheduler ───────────────────────────────────────────────────────────
    try:
        from app.services.scheduler.scheduler import start_scheduler
        await start_scheduler()
        logger.info("✅ Scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler skipped: {e}")

    logger.info("🚀 JARVIS operational — Aliyar Solutions v9.0.0")
    yield

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    if worker_task:
        worker_task.cancel()
    try:
        from app.services.scheduler.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    logger.info("JARVIS shutting down cleanly")


app = FastAPI(
    title="JARVIS — Aliyar Solutions",
    description="Autonomous AI Operating System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

app.add_middleware(TenantContextMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(ObservabilityRefreshMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        checks["database"] = {"status": "error", "error": str(e)}
        overall_ok = False

    # ── AI providers ──────────────────────────────────────────────────────────
    try:
        providers = _ai_router.get_provider_status()
        available = [k for k, v in providers.items() if v["available"]]
        checks["ai_providers"] = {
            "status": "ok" if available else "degraded",
            "available": len(available),
            "total": len(providers),
            "active": available,
        }
        if not available:
            overall_ok = False
    except Exception as e:
        checks["ai_providers"] = {"status": "error", "error": str(e)}

    # ── Scheduler ─────────────────────────────────────────────────────────────
    try:
        from app.services.scheduler.scheduler import get_scheduler
        sched = get_scheduler()
        running = sched is not None and sched.running
        checks["scheduler"] = {"status": "ok" if running else "stopped", "running": running}
    except Exception:
        checks["scheduler"] = {"status": "unknown"}

    # ── Team registry ─────────────────────────────────────────────────────────
    try:
        async with AsyncSessionLocal() as db:
            from app.services.team.team_service import get_team_stats
            ts = await get_team_stats(db)
            checks["team_registry"] = {"status": "ok", "members": ts.get("active", 0)}
    except Exception:
        checks["team_registry"] = {"status": "unknown"}

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
