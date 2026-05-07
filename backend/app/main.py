import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    logger.info("⚡ JARVIS booting up — Aliyar Solutions")
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.warning(f"DB init skipped: {e}")

    # Requeue any tasks stuck in 'running' state from a previous crash
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.tasks.queue import requeue_pending, worker
        async with AsyncSessionLocal() as db:
            async with db.begin():
                await requeue_pending(db)
        logger.info("✅ Task queue initialized — starting worker")
        worker_task = asyncio.create_task(worker())
    except Exception as e:
        logger.warning(f"Task worker skipped: {e}")
        worker_task = None

    # Start APScheduler
    try:
        from app.services.scheduler.engine import start_scheduler
        await start_scheduler()
    except Exception as e:
        logger.warning(f"Scheduler skipped: {e}")

    yield

    if worker_task:
        worker_task.cancel()
    try:
        from app.services.scheduler.engine import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    logger.info("JARVIS shutting down")


app = FastAPI(
    title="JARVIS — Aliyar Solutions",
    description="Autonomous AI Operating System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    from app.services.ai.router import ai_router
    providers = ai_router.get_provider_status()
    available = [k for k, v in providers.items() if v["available"]]
    return {
        "status": "operational",
        "system": "JARVIS",
        "company": "Aliyar Solutions",
        "version": "3.0.0",
        "ai_providers": {"available": len(available), "total": len(providers), "active": available},
    }
