"""Normalise aggregator payloads into our Transaction rows + recompute scores."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Identity, Transaction, TxnCategory, TxnDirection
from app.services.scoring import get_scoring_engine
from app.services.scoring.snapshots import compute_and_persist


# Map aggregator category strings to our enum. Mock returns these directly; Setu
# would return standardised codes we'd map here.
_CATEGORY_MAP: dict[str, TxnCategory] = {
    "client_payment": TxnCategory.CLIENT_PAYMENT,
    "salary": TxnCategory.SALARY,
    "gig_payout": TxnCategory.GIG_PAYOUT,
    "sales": TxnCategory.SALES,
    "investment_income": TxnCategory.INVESTMENT_INCOME,
    "rental": TxnCategory.RENTAL,
    "emi": TxnCategory.EMI,
    "utility": TxnCategory.UTILITY,
    "other": TxnCategory.OTHER,
}


def _parse_date(s: str) -> date:
    """Accept ISO date or ISO datetime string. Return a `date` object."""
    # Try full datetime first; if it has a time component, extract the date.
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        pass
    # Plain ISO date e.g. "2026-01-15"
    return date.fromisoformat(s)


def _parse_direction(s: str) -> TxnDirection:
    s = (s or "").lower()
    return TxnDirection.CREDIT if s == "credit" else TxnDirection.DEBIT


async def ingest_payload(
    db: AsyncSession, identity: Identity, provider: str, payload: dict
) -> int:
    """Insert transactions from a provider payload. Returns the count inserted."""
    txns = payload.get("transactions", [])
    if not txns:
        return 0

    inserted = 0
    for tx in txns:
        try:
            # Use uppercase enum member (TxnCategory.OTHER, not TxnCategory.other)
            cat = _CATEGORY_MAP.get(tx.get("category", "other"), TxnCategory.OTHER)
            direction = _parse_direction(tx.get("direction", "credit"))
            posted_at = _parse_date(tx["posted_at"])
            amount = float(tx["amount"])
        except (KeyError, ValueError, TypeError):
            continue

        db.add(
            Transaction(
                identity_id=identity.id,
                posted_at=posted_at,
                amount_inr=amount,
                direction=direction,
                category=cat,
                counterparty=tx.get("counterparty") or "",
                source=tx.get("source") or provider,
                raw=tx,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        inserted += 1

    if inserted:
        await db.flush()

    # Recompute monthly income from the new transactions (credits only) — simple avg
    credits = [t for t in txns if (t.get("direction") or "").lower() == "credit"]
    if credits:
        from collections import defaultdict

        monthly: dict[str, float] = defaultdict(float)
        for t in credits:
            try:
                d = _parse_date(t["posted_at"])
                monthly[d.strftime("%Y-%m")] += float(t["amount"])
            except (KeyError, ValueError, TypeError):
                continue
        if monthly:
            avg_monthly = round(sum(monthly.values()) / max(1, len(monthly)))
            identity.monthly_income = max(identity.monthly_income, int(avg_monthly))

    # Recompute a fresh DNA snapshot now that we have real data
    await compute_and_persist(
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
    return inserted
