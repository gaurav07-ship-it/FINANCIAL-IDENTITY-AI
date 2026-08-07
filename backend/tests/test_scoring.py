"""Scoring parity tests.

The rule-based engine is a 1:1 port of store.js's computeDerived(). If you
ever change the formulas, update BOTH sides and rerun these tests.
"""
from __future__ import annotations

import pytest

from app.services.scoring.engine import RuleBasedScoringEngine
from app.services.scoring.rules import derive


engine = RuleBasedScoringEngine()


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(monthly_income=180_000, sources=[], gig_platforms=[], has_primary_bank=False, permissions_push=False),
        dict(monthly_income=180_000, sources=["Salaried role"], gig_platforms=[], has_primary_bank=True, permissions_push=True),
        dict(monthly_income=185_000, sources=["Client Projects", "Salaried role", "Gig Platforms", "Investments"], gig_platforms=["Zomato", "Swiggy"], has_primary_bank=True, permissions_push=True),
        dict(monthly_income=50_000, sources=["Gig Platforms"], gig_platforms=["Zomato"], has_primary_bank=False, permissions_push=False),
        dict(monthly_income=240_000, sources=["Client Projects", "Salaried role", "Online Sales", "Investments", "Rental Income"], gig_platforms=[], has_primary_bank=True, permissions_push=True),
    ],
)
@pytest.mark.asyncio
async def test_engine_matches_pure_derive(kwargs):
    a = await engine.compute(**kwargs)
    b = derive(**kwargs)
    assert a.dna_score == b.dna_score
    assert a.income_quality == b.income_quality
    assert a.top_client_share == b.top_client_share
    assert a.diversification_index == b.diversification_index
    assert a.clients == b.clients
    assert a.sorted_clients == b.sorted_clients


@pytest.mark.asyncio
async def test_dna_is_bounded_and_deterministic():
    m1 = await engine.compute(
        monthly_income=100_000,
        sources=["Client Projects", "Salaried role", "Gig Platforms"],
        gig_platforms=["Zomato", "Swiggy"],
        has_primary_bank=True,
        permissions_push=True,
    )
    m2 = await engine.compute(
        monthly_income=100_000,
        sources=["Client Projects", "Salaried role", "Gig Platforms"],
        gig_platforms=["Zomato", "Swiggy"],
        has_primary_bank=True,
        permissions_push=True,
    )
    assert m1.dna_score == m2.dna_score
    assert 0 <= m1.dna_score <= 100
    assert 0 <= m1.income_quality <= 100
    assert 0 <= m1.stability <= 100
    assert 0 <= m1.risk <= 100


@pytest.mark.asyncio
async def test_more_sources_higher_dna():
    low = await engine.compute(
        monthly_income=100_000,
        sources=["Salaried role"],
        gig_platforms=[],
        has_primary_bank=True,
        permissions_push=True,
    )
    high = await engine.compute(
        monthly_income=100_000,
        sources=["Salaried role", "Client Projects", "Gig Platforms", "Investments"],
        gig_platforms=["Zomato", "Swiggy"],
        has_primary_bank=True,
        permissions_push=True,
    )
    assert high.dna_score > low.dna_score


@pytest.mark.asyncio
async def test_top_client_share_is_share_of_largest_client():
    m = await engine.compute(
        monthly_income=180_000,
        sources=["Client Projects", "Salaried role"],
        gig_platforms=[],
        has_primary_bank=True,
        permissions_push=True,
    )
    assert m.top_client_share == m.sorted_clients[0].share
    assert abs(sum(c.share for c in m.clients) - 100) < 0.5  # re-normalised


@pytest.mark.asyncio
async def test_push_permission_raises_discipline():
    no_push = await engine.compute(
        monthly_income=180_000,
        sources=["Salaried role"],
        gig_platforms=[],
        has_primary_bank=True,
        permissions_push=False,
    )
    with_push = await engine.compute(
        monthly_income=180_000,
        sources=["Salaried role"],
        gig_platforms=[],
        has_primary_bank=True,
        permissions_push=True,
    )
    assert with_push.discipline > no_push.discipline
