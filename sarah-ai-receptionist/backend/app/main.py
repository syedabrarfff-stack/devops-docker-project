import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import get_settings
from app.middleware import RequestContextMiddleware, RequestIDLogFilter, install_error_handling
from app.routes import admin, appointments, auth, billing, call_handler, dashboard, voice_widget

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] [%(request_id)s] %(message)s",
)
# Applied to the root logger's handlers so request_id is available on every
# record, including ones logged deep in a service module that never touches
# the request object directly.
for _handler in logging.getLogger().handlers:
    _handler.addFilter(RequestIDLogFilter())
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
        "https://www.aliyarsolutions.com",
        "https://aliyarsolutions.com",
    ] if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Runs on HTTP request/response routes only -- BaseHTTPMiddleware does not
# wrap WebSocket connections, so /media-stream is unaffected and keeps its
# own call_sid-based logging.
app.add_middleware(RequestContextMiddleware)
install_error_handling(app)

app.include_router(call_handler.router)
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(appointments.router, prefix="/api/v1/appointments")
app.include_router(dashboard.router, prefix="/api/v1/dashboard")
app.include_router(admin.router, prefix="/api/v1/admin")
app.include_router(billing.router, prefix="/api/v1/billing")
app.include_router(voice_widget.router, prefix="/api/v1/voice-widget")


@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok", "service": "sarah-ai-receptionist"}


@app.get("/readyz")
async def readyz():
    """Deep readiness probe — verifies DB connectivity."""
    from sqlalchemy import text

    from app.core.database import get_db_context

    checks = {"database": False, "redis": False}

    try:
        async with get_db_context() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error(f"Readiness check failed (database): {e}")

    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await redis.ping()
        await redis.close()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Readiness check failed (redis): {e}")

    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})


@app.get("/")
async def root():
    return {"service": "Sarah AI Receptionist", "company": "Aliyar Solutions", "status": "operational"}
