from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    # asyncpg's own default connect timeout is 60 seconds -- unbounded for
    # any practical purpose. Every session checkout that needs a fresh
    # connection (the whole pool, whenever the database is unreachable) pays
    # up to that default before the caller sees any error. Confirmed live
    # against this exact deployment: with RDS unreachable, /readyz's own
    # "SELECT 1" check contributed multiple seconds to an 8.4s total before
    # failing -- and that path sits inline before Sarah can speak a word on
    # every call that reaches _load_clinic_config. A short, explicit timeout
    # turns an outage into a fast, loud failure instead of several extra
    # seconds of silent hang stacked onto a caller's wait.
    connect_args={"timeout": 2},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
