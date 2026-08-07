"""Lender offers — list active lenders with computed approval / EMI for the user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_identity
from app.models import Identity, Lender, LenderOffer
from app.services.lenders import compute_offers
from app.services.scoring import get_scoring_engine

router = APIRouter(prefix="/lenders", tags=["lenders"])


@router.get("/offers")
async def list_offers(
    amount: int | None = None,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    lenders = list((await db.scalars(select(Lender).where(Lender.active.is_(True)))).all())
    metrics = await get_scoring_engine().compute(
        monthly_income=identity.monthly_income,
        sources=identity.sources or [],
        gig_platforms=identity.gig_platforms or [],
        has_primary_bank=bool(identity.permissions and (identity.permissions or {}).get("primary_bank")),
        permissions_push=bool(identity.permissions and (identity.permissions or {}).get("push")),
    )
    offers = compute_offers(identity, metrics, lenders, requested_amount=amount)
    return [
        {
            "lenderId": str(o.lender.id),
            "name": o.lender.name,
            "logoGradient": o.lender.logo_gradient,
            "approvedAmount": o.approved_amount,
            "tenureMonths": o.tenure_months,
            "rateApr": o.rate_apr,
            "emi": o.emi,
            "approvalPct": o.approval_pct,
            "disbursalHours": o.disbursal_hours,
            "reasonCodes": o.reason_codes,
        }
        for o in offers
    ]


@router.post("/offer/{lender_id}/persist")
async def persist_offer(
    lender_id: str,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Recompute + save an offer for the user. Used when they 'request pre-approval'."""
    from uuid import UUID as _UUID
    from datetime import datetime, timezone

    try:
        lender_uuid = _UUID(lender_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid lender id")

    lender = await db.get(Lender, lender_uuid)
    if lender is None or not lender.active:
        raise HTTPException(status_code=404, detail="Lender not found")

    metrics = await get_scoring_engine().compute(
        monthly_income=identity.monthly_income,
        sources=identity.sources or [],
        gig_platforms=identity.gig_platforms or [],
        has_primary_bank=bool(identity.permissions and (identity.permissions or {}).get("primary_bank")),
        permissions_push=bool(identity.permissions and (identity.permissions or {}).get("push")),
    )
    offer = compute_offers(identity, metrics, [lender])[0]
    row = LenderOffer(
        identity_id=identity.id,
        lender_id=lender.id,
        amount_inr=offer.approved_amount,
        tenure_months=offer.tenure_months,
        rate_apr=offer.rate_apr,
        emi_inr=offer.emi,
        approval_pct=offer.approval_pct,
        disbursal_hours=offer.disbursal_hours,
        reason_codes=offer.reason_codes,
        computed_at=datetime.now(tz=timezone.utc),
    )
    db.add(row)
    await db.commit()
    return {"persisted": True, "lenderId": str(lender.id), "approvalPct": offer.approval_pct}
