"""Aggregator (Account Aggregator / UPI) endpoints.

In dev we use the MockProvider; in prod we'd swap to Setu/Finbox by setting
AGGREGATOR_PROVIDER in .env. The router doesn't care which one is wired.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_identity
from app.models import Consent, Identity
from app.services.aggregators import get_provider
from app.services.aggregators.base import (
    AggregatorProvider,
    ConsentHandle,
    ConsentRequest,
)
from app.services.aggregation import ingest_payload

router = APIRouter(prefix="/aggregators", tags=["aggregators"])


@router.post("/consent")
async def create_consent(
    fi_types: list[str] = ["DEPOSIT", "TERM_DEPOSIT", "MUTUAL_FUNDS"],
    from_date: str | None = None,
    to_date: str | None = None,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> dict:
    provider: AggregatorProvider = get_provider()
    handle: ConsentHandle = await provider.create_consent(
        ConsentRequest(
            identity_id=identity.id,
            fi_types=fi_types,
            from_date=from_date,
            to_date=to_date,
        )
    )
    consent = Consent(
        identity_id=identity.id,
        provider=provider.name(),
        consent_id=handle.consent_id,
        status=handle.status,
        data_range_from=handle.data_range_from,
        data_range_to=handle.data_range_to,
        fi_types=fi_types,  # JSONB list
        payload=handle.payload,
        expires_at=handle.expires_at,
    )
    db.add(consent)
    identity.permissions = {
        **(identity.permissions or {}),
        "aa_consent": False,  # flips true on the webhook once user approves
    }
    await db.commit()
    return {
        "consentId": handle.consent_id,
        "status": handle.status,
        "redirectUrl": handle.redirect_url,
        "expiresAt": handle.expires_at,
    }


@router.post("/consent/{consent_id}/pull")
async def pull_data(
    consent_id: str,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Pull FI data for a previously created consent.

    `consent_id` is the AA provider's consent identifier (e.g. "mock-abc123"),
    stored in `Consent.consent_id`, NOT the DB primary key.  We query by that
    column so the lookup works for both UUID-shaped and non-UUID provider IDs.
    """
    consent = await db.scalar(
        select(Consent).where(
            Consent.consent_id == consent_id,
            Consent.identity_id == identity.id,
        )
    )
    if consent is None:
        raise HTTPException(status_code=404, detail="Consent not found")
    if consent.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Consent not active")

    provider: AggregatorProvider = get_provider()
    result = await provider.fetch_data(consent.consent_id)
    ingested = await ingest_payload(db, identity, provider.name(), result)
    return {
        "consentId": consent.consent_id,
        "fetchedAccounts": len(result.get("accounts", [])),
        "ingestedTransactions": ingested,
    }


@router.get("/consents")
async def list_consents(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.scalars(
            select(Consent)
            .where(Consent.identity_id == identity.id)
            .order_by(Consent.created_at.desc())
        )
    ).all()
    return [
        {
            "consentId": c.consent_id,  # return the AA provider ID, not the DB UUID
            "provider": c.provider,
            "status": c.status,
            "fiTypes": c.fi_types,
            "createdAt": c.created_at,
            "expiresAt": c.expires_at,
        }
        for c in rows
    ]
