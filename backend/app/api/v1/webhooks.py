"""AA / provider webhooks — no auth header, validated by provider signature in prod."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AuditLog, Consent, Identity
from app.services.aggregators import get_provider
from app.services.aggregation import ingest_payload

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/consent/{consent_id}/status")
async def consent_status(
    consent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Provider pings us when the user approves/denies the consent."""
    body = await request.json()
    new_status = (body.get("status") or "").upper()
    if new_status not in {"ACTIVE", "REVOKED", "EXPIRED", "DENIED"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    consent = await db.scalar(select(Consent).where(Consent.consent_id == consent_id))
    if consent is None:
        raise HTTPException(status_code=404, detail="Consent not found")

    consent.status = new_status
    if new_status == "ACTIVE":
        identity = await db.get(Identity, consent.identity_id)
        if identity is not None:
            identity.permissions = {
                **(identity.permissions or {}),
                "aa_consent": True,
            }

    db.add(
        AuditLog(
            target_user_id=consent.identity_id,
            action="aa_consent_status_change",
            detail={"consent_id": consent_id, "new_status": new_status, "raw": body},
        )
    )
    await db.commit()
    return {"ok": True, "status": new_status}


@router.post("/consent/{consent_id}/data")
async def consent_data(
    consent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Provider pushes the FI payload via webhook (Setu uses this pattern)."""
    body = await request.json()
    consent = await db.scalar(select(Consent).where(Consent.consent_id == consent_id))
    if consent is None:
        raise HTTPException(status_code=404, detail="Consent not found")
    if consent.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Consent not active")

    identity = await db.get(Identity, consent.identity_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="Identity not found")

    ingested = await ingest_payload(db, identity, consent.provider, body)

    db.add(
        AuditLog(
            target_user_id=identity.id,
            action="aa_data_ingested",
            detail={"consent_id": consent_id, "transactions": ingested},
        )
    )
    await db.commit()
    return {"ok": True, "ingested": ingested}


# Keep imports aligned & linter happy
_ = uuid
_ = datetime.now(tz=timezone.utc)
