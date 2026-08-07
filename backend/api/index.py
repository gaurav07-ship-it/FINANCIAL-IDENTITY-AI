"""Vercel serverless entrypoint.

Vercel discovers Python functions by looking for files under ``/api``.
We re-export the FastAPI ``app`` here so Vercel's ASGI runtime picks it
up directly (no Mangum adapter needed as of 2026).

Environment contract:
- DATABASE_URL must be a Neon postgresql+asyncpg URL.
- COOKIE_SECURE=true in production.
- All other secrets are read via app.config.settings.

The deploy is preceded by `alembic upgrade head` in CI so the schema is
already current when this function is invoked.
"""
from __future__ import annotations

from app.main import app  # noqa: F401 — Vercel picks this up as the ASGI handler
