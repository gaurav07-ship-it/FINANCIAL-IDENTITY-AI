"""Neo4j client — per-request driver.

In serverless (Vercel) we deliberately avoid caching the driver at module
level: each invocation is short-lived, connections should be opened and
closed within the request, and we don't want stale TCP sockets hanging
around between cold/warm cycles.

For local dev or single-VM deploys you can still call ``GraphDatabase``
yourself and cache the driver if you prefer.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from app.config import settings


@asynccontextmanager
async def neo4j_session() -> AsyncIterator[AsyncSession]:
    """Yield an async Neo4j session, closing the driver afterwards."""
    if not settings.neo4j_enabled:
        raise RuntimeError("Neo4j is disabled (set NEO4J_ENABLED=true)")
    if not settings.neo4j_password:
        raise RuntimeError("NEO4J_PASSWORD not configured")

    driver: AsyncDriver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    try:
        async with driver.session() as session:
            yield session
    finally:
        await driver.close()


async def neo4j_ping() -> bool:
    """Used by /health to surface the Neo4j readiness status."""
    if not settings.neo4j_enabled:
        return False
    try:
        async with neo4j_session() as session:
            result = await session.run("RETURN 1 AS ok")
            record = await result.single()
            return bool(record and record["ok"] == 1)
    except Exception:
        return False
