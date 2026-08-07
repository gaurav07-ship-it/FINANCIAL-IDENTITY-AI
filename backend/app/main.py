"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import api_v1
from app.config import settings
from app.logging_setup import configure_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_size import RequestSizeLimitMiddleware

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # Sentry initialised lazily so dev (where DSN is empty) stays a no-op.
    if settings.sentry_dsn and settings.is_prod:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                integrations=[FastApiIntegration(), SqlalchemyIntegration()],
                traces_sample_rate=0.1,
                environment=settings.env,
                release=app.version,
            )
            log.info("sentry_initialised")
        except ImportError:
            log.warning("sentry_sdk_missing")
    yield


app = FastAPI(
    title="Financial Identity AI",
    version="0.1.0",
    docs_url="/docs" if settings.is_dev else None,
    redoc_url=None,
    lifespan=lifespan,
)

# Middleware order matters — outermost first.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_body_bytes=100 * 1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-CSRF-Token"],
    expose_headers=["Set-Cookie"],
)

app.include_router(api_v1, prefix="/api")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "path": str(request.url.path)},
        headers=exc.headers or None,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import structlog

    log = structlog.get_logger("unhandled")
    log.exception("unhandled_error", path=str(request.url.path), exc=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": str(request.url.path)},
    )


@app.get("/health")
async def health() -> dict:
    """Liveness + DB + Neo4j readiness in a single probe."""
    db_ok = True
    neo4j_ok: bool | None = None
    try:
        from sqlalchemy import text

        async with SessionLocal() as s:  # type: ignore[name-defined]
            await s.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    if settings.neo4j_enabled:
        try:
            from app.services.neo4j_client import neo4j_ping

            neo4j_ok = await neo4j_ping()
        except Exception:
            neo4j_ok = False

    status = "ok" if db_ok and (neo4j_ok is not False) else "degraded"
    code = 200 if status == "ok" else 503
    payload = {
        "status": status,
        "env": settings.env,
        "version": app.version,
        "checks": {"db": db_ok, "neo4j": neo4j_ok},
    }
    return JSONResponse(status_code=code, content=payload)


@app.get("/")
async def root() -> dict:
    return {
        "service": "financial-identity-ai",
        "version": app.version,
        "docs": "/docs" if settings.is_dev else None,
    }


# Local import to avoid circular reference with the health endpoint.
from app.db import SessionLocal  # noqa: E402
