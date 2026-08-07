"""Test fixtures.

The conftest here is engineered so a fresh checkout can run `pytest -q`
without docker-compose up. It defaults to:

- SQLite (in-memory) via aiosqlite, instead of Postgres
- fakeredis (lazy import), so we don't need Redis either

To exercise the real Postgres + Redis stack, set:
    FIA_TEST_DB=postgres  FIA_TEST_REDIS=1  pytest -q
"""
from __future__ import annotations

import asyncio
import os
from typing import AsyncIterator

# Tell the app to use SQLite before any app modules are imported.
os.environ.setdefault("ENV", "dev")
os.environ.setdefault("AGGREGATOR_PROVIDER", "mock")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings  # noqa: E402  — must come after env shim
from app.db import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

USE_SQLITE = settings.database_url.startswith("sqlite")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(settings.database_url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncIterator[AsyncSession]:
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as s:
        yield s
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def client(db_session) -> AsyncIterator[AsyncClient]:
    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()