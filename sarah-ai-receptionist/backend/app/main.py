import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.routes import call_handler, appointments, dashboard, auth, admin

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Sarah AI Receptionist starting — env={settings.app_env}")
    yield
    logger.info("Sarah AI Receptionist shutting down")


app = FastAPI(
    title="Sarah AI Receptionist",
    description="Multi-tenant AI voice receptionist platform by Aliyar Solutions",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.aliyarsolutions.com",
        "https://admin.aliyarsolutions.com",
    ] if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(call_handler.router)
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(appointments.router, prefix="/api/v1/appointments")
app.include_router(dashboard.router, prefix="/api/v1/dashboard")
app.include_router(admin.router, prefix="/api/v1/admin")


@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok", "service": "sarah-ai-receptionist"}


@app.get("/readyz")
async def readyz():
    """Deep readiness probe — verifies DB connectivity."""
    from sqlalchemy import text
    from app.core.database import get_db_context

    try:
        async with get_db_context() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "error": str(e)}


@app.get("/")
async def root():
    return {"service": "Sarah AI Receptionist", "company": "Aliyar Solutions", "status": "operational"}
