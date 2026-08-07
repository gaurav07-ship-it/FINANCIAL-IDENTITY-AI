"""Async SQLAlchemy engine and session factory.

Serverless-safe: uses NullPool so connections are opened and closed per-request,
which avoids holding idle sockets across serverless invocations. We also set
``statement_cache_size=0`` so asyncpg plays nicely with Neon's pgbouncer-style
pooler endpoint.

The engine is created at module import (once per cold instance) and reused
across warm invocations — Vercel's runtime caches the import.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings


def _build_engine_kwargs() -> dict:
    """Pick pool/connect_args per dialect.

    - SQLite (tests): no pool, no statement cache kwarg.
    - Postgres (Neon in prod): NullPool + statement_cache_size=0.
    """
    url = settings.database_url
    if url.startswith("sqlite"):
        return {"future": True}

    connect_args: dict = {}
    if url.startswith("postgresql"):
        # asyncpg-specific: disable prepared statement cache for Neon pgbouncer.
        connect_args["statement_cache_size"] = 0
        connect_args["ssl"] = True
    return {
        "future": True,
        "poolclass": NullPool,
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }


engine = create_async_engine(settings.database_url, **_build_engine_kwargs())

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an AsyncSession and ensures cleanup."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
