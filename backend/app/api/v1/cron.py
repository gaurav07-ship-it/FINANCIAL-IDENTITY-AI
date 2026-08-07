"""Vercel Cron + QStash fan-out endpoints.

- POST /api/v1/cron/recompute-all   — Vercel Cron at 03:17 UTC nightly.
  Reads all identity ids from Postgres, fans out one QStash message per id.
- POST /api/v1/cron/recompute-one   — QStash webhook target. Verifies
  signature, runs the scoring recompute + persists a fresh snapshot.
- POST /api/v1/cron/graph-rebuild   — Admin-only. Rebuilds Neo4j from PG.

All endpoints require either the Vercel-Cron header (set automatically by
Vercel) OR a Bearer ``CRON_SECRET`` for manual triggering.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import Identity, ScoreSnapshot
from app.services.scoring import get_scoring_engine
from app.services.scoring.snapshots import compute_and_persist
from app.services.qstash_client import publish_json, verify_qstash_signature
from app.models.user import User

router = APIRouter(prefix="/cron", tags=["cron"])


def _authorised(vercel_cron: str | None, authorization: str | None) -> None:
    """Accept either the Vercel-Cron header (set automatically) or Bearer CRON_SECRET."""
    if vercel_cron == "1":
        return
    if not settings.cron_secret:
        if settings.is_dev:
            return
        raise HTTPException(status_code=503, detail="CRON_SECRET not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, settings.cron_secret):
        raise HTTPException(status_code=401, detail="Invalid cron token")


@router.post("/recompute-all")
async def recompute_all(
    request: Request,
    db: AsyncSession = Depends(get_db),
    vercel_cron: str | None = Header(default=None, alias="x-vercel-cron"),
    authorization: str | None = Header(default=None),
) -> dict:
    """Fan out a per-identity recompute via QStash.

    Vercel calls this at 03:17 UTC nightly via vercel.json crons entry.
    """
    _authorised(vercel_cron, authorization)
    ids = list((await db.scalars(select(Identity.id))).all())

    # Use the request's host so this works behind preview deploys too.
    base = str(request.base_url).rstrip("/")
    target = f"{base}/api/v1/cron/recompute-one"

    queued = 0
    for i in ids:
        await publish_json(target, {"identity_id": str(i)})
        queued += 1
    return {"queued": queued}


@router.post("/recompute-one")
async def recompute_one(
    request: Request,
    db: AsyncSession = Depends(get_db),
    upstash_signature: str | None = Header(default=None, alias="upstash-signature"),
    vercel_cron: str | None = Header(default=None, alias="x-vercel-cron"),
    authorization: str | None = Header(default=None),
) -> dict:
    """Run a single identity's recompute. Called by QStash."""
    raw = await request.body()
    if upstash_signature and not verify_qstash_signature(raw, upstash_signature):
        raise HTTPException(status_code=401, detail="Invalid QStash signature")
    elif not upstash_signature:
        # Fall back to cron auth for direct triggers.
        _authorised(vercel_cron, authorization)

    import json

    body = json.loads(raw or b"{}")
    identity_id = body.get("identity_id")
    if not identity_id:
        raise HTTPException(status_code=400, detail="identity_id required")

    identity = await db.get(Identity, uuid.UUID(identity_id))
    if identity is None:
        return {"ok": False, "reason": "identity not found"}

    metrics = await compute_and_persist(
        db,
        get_scoring_engine(),
        identity_id=identity.id,
        monthly_income=identity.monthly_income,
        sources=identity.sources or [],
        gig_platforms=identity.gig_platforms or [],
        has_primary_bank=bool(identity.permissions and (identity.permissions or {}).get("primary_bank")),
        permissions_push=bool(identity.permissions and (identity.permissions or {}).get("push")),
    )
    await db.commit()
    return {"ok": True, "identity_id": str(identity.id), "dnaScore": metrics.dna_score}


@router.post("/graph-rebuild")
async def graph_rebuild(
    vercel_cron: str | None = Header(default=None, alias="x-vercel-cron"),
    authorization: str | None = Header(default=None),
    admin: User = Depends(get_current_user),
) -> dict:
    """Admin-only: rebuild Neo4j from Postgres truth."""
    if not admin.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    _authorised(vercel_cron, authorization)

    from app.services.neo4j_sync import rebuild_graph

    counts = await rebuild_graph()
    return {"ok": True, **counts}
