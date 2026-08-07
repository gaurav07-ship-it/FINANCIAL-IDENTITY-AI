"""Opportunity engine — pick the most relevant plays for the user based on DNA gap."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_identity
from app.models import Identity, Opportunity
from app.services.scoring import get_scoring_engine

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("")
async def list_opportunities(
    limit: int = 6,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    metrics = await get_scoring_engine().compute(
        monthly_income=identity.monthly_income,
        sources=identity.sources or [],
        gig_platforms=identity.gig_platforms or [],
        has_primary_bank=bool(identity.permissions and (identity.permissions or {}).get("primary_bank")),
        permissions_push=bool(identity.permissions and (identity.permissions or {}).get("push")),
    )
    # Active ones from DB
    rows = list(
        (await db.scalars(select(Opportunity).where(Opportunity.active.is_(True)))).all()
    )

    # Naive but transparent scoring: bigger DNA gap = higher priority
    def _rank(o: Opportunity) -> tuple[int, int]:
        # tie-break on priority field already on the row
        score = 0
        kind = o.category
        if kind == "diversification" and metrics.diversification_index < 50:
            score += 50 - metrics.diversification_index
        if kind == "savings" and metrics.savings < 70:
            score += 70 - metrics.savings
        if kind == "growth" and metrics.growth < 70:
            score += 70 - metrics.growth
        if kind == "risk" and metrics.risk < 70:
            score += 70 - metrics.risk
        if kind == "income_quality" and metrics.income_quality < 70:
            score += 70 - metrics.income_quality
        if kind == "stability" and metrics.stability < 70:
            score += 70 - metrics.stability
        return (score, o.priority)

    rows.sort(key=_rank, reverse=True)
    return [
        {
            "id": str(o.id),
            "category": o.category,
            "ribbon": o.ribbon,
            "title": o.title,
            "description": o.description,
            "impact": o.impact,
            "price": o.price,
            "cta": o.cta,
            "icon": o.icon,
            "priority": o.priority,
        }
        for o in rows[:limit]
    ]
