"""Scoring engine interface. Lets us swap rule-based for an ML model later."""
from __future__ import annotations

from typing import Protocol

from app.services.scoring.rules import DerivedMetrics


class ScoringEngine(Protocol):
    async def compute(
        self,
        *,
        monthly_income: int,
        sources: list[str],
        gig_platforms: list[str],
        has_primary_bank: bool,
        permissions_push: bool,
    ) -> DerivedMetrics: ...


class RuleBasedScoringEngine:
    """Direct port of computeDerived() from store.js. Parity-tested."""

    async def compute(
        self,
        *,
        monthly_income: int,
        sources: list[str],
        gig_platforms: list[str],
        has_primary_bank: bool,
        permissions_push: bool,
    ) -> DerivedMetrics:
        from app.services.scoring.rules import derive  # local to avoid cycles

        return derive(
            monthly_income=monthly_income,
            sources=sources,
            gig_platforms=gig_platforms,
            has_primary_bank=has_primary_bank,
            permissions_push=permissions_push,
        )
