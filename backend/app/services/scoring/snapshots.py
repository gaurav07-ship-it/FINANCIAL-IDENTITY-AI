"""Persist + retrieve score snapshots from DB. Used by /score/* endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ScoreSnapshot
from app.services.scoring.engine import ScoringEngine
from app.services.scoring.rules import DerivedMetrics


def to_snapshot_row(identity_id: uuid.UUID, m: DerivedMetrics) -> ScoreSnapshot:
    now = datetime.now(tz=timezone.utc)
    return ScoreSnapshot(
        identity_id=identity_id,
        computed_at=now,
        dna_score=m.dna_score,
        stability=m.stability,
        discipline=m.discipline,
        growth=m.growth,
        savings=m.savings,
        diversification=m.diversification,
        risk=m.risk,
        income_quality=m.income_quality,
        top_client_share=m.top_client_share,
        monthly_income=m.monthly_income,
        yoy=m.yoy,
        cv=m.cv,
        late_payouts=m.late_payouts,
        detail=m.as_dict(),
    )


async def get_latest(session: AsyncSession, identity_id: uuid.UUID) -> ScoreSnapshot | None:
    stmt = (
        select(ScoreSnapshot)
        .where(ScoreSnapshot.identity_id == identity_id)
        .order_by(ScoreSnapshot.computed_at.desc())
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_history(
    session: AsyncSession, identity_id: uuid.UUID, limit: int = 12
) -> list[ScoreSnapshot]:
    stmt = (
        select(ScoreSnapshot)
        .where(ScoreSnapshot.identity_id == identity_id)
        .order_by(ScoreSnapshot.computed_at.desc())
        .limit(limit)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def compute_and_persist(
    session: AsyncSession,
    engine: ScoringEngine,
    *,
    identity_id: uuid.UUID,
    monthly_income: int,
    sources: list[str],
    gig_platforms: list[str],
    has_primary_bank: bool,
    permissions_push: bool,
) -> DerivedMetrics:
    metrics = await engine.compute(
        monthly_income=monthly_income,
        sources=sources,
        gig_platforms=gig_platforms,
        has_primary_bank=has_primary_bank,
        permissions_push=permissions_push,
    )
    session.add(to_snapshot_row(identity_id, metrics))
    return metrics
