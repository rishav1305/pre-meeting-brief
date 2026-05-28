"""Async SQLAlchemy session factory.

Use `get_session()` as a FastAPI dependency. Use POSTGRES_URL (pooled) at runtime;
Alembic uses POSTGRES_URL_NON_POOLING separately for DDL.
"""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import settings


def _engine_url() -> str:
    # Use psycopg3 (postgresql+psycopg) for async. asyncpg rejects Neon's
    # channel_binding=require query param; psycopg3 handles it natively.
    url = settings.postgres_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_async_engine(_engine_url(), echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
