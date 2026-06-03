from collections.abc import AsyncGenerator
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.tenant_context import get_current_tenant_id
from app.models.base import JarvisBase


logger = logging.getLogger(__name__)


def _async_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL = _async_database_url(settings.DATABASE_URL)
_is_sqlite = DATABASE_URL.startswith("sqlite")


engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=not _is_sqlite,
    **({} if _is_sqlite else {"pool_size": 10, "max_overflow": 20}),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


Base = JarvisBase


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            tenant_id = get_current_tenant_id()
            if tenant_id:
                await set_tenant_context(session, tenant_id)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(JarvisBase.metadata.create_all)
        if not _is_sqlite:
            await conn.execute(
                text(
                    """
                    CREATE OR REPLACE FUNCTION set_tenant_context(tenant_uuid uuid)
                    RETURNS void AS $$
                    BEGIN
                        PERFORM set_config('app.current_tenant_id', tenant_uuid::text, true);
                    END;
                    $$ LANGUAGE plpgsql;
                    """
                )
            )
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                for table_name in (
                    "memories",
                    "memory_operational",
                    "memory_strategic",
                    "civilization_memory",
                    "memory_graph_nodes",
                ):
                    await conn.execute(
                        text(
                            f"ALTER TABLE {table_name} "
                            "ADD COLUMN IF NOT EXISTS embedding_vector vector(1536)"
                        )
                    )
            except Exception as exc:
                logger.warning("pgvector startup schema step skipped: %s", exc)
            try:
                await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS timezone VARCHAR(80)"))
                await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS qualification_status VARCHAR(40)"))
                await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS loss_reason VARCHAR(80)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_leads_timezone ON leads (timezone)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_leads_qualification_status ON leads (qualification_status)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_leads_loss_reason ON leads (loss_reason)"))
            except Exception as exc:
                logger.warning("lead safety column startup schema step skipped: %s", exc)


async def init_db() -> None:
    await create_tables()


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    await session.execute(
        text("SELECT set_tenant_context(:tenant_id)"),
        {"tenant_id": tenant_id},
    )
