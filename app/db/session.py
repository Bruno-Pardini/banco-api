"""Motor asíncrono y fábrica de sesiones (SQLAlchemy 2.0 + asyncpg)."""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    s = get_settings()
    return create_async_engine(
        s.DATABASE_URL,
        echo=s.DB_ECHO,
        pool_size=s.DB_POOL_SIZE,
        max_overflow=s.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia de FastAPI: una sesión por petición."""
    async with get_sessionmaker()() as session:
        yield session
