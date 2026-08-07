"""Twin simulator — what-if cashflow projection."""
from __future__ import annotations

from dataclasses import dataclass

from app.services.scoring.engine import ScoringEngine
from app.services.scoring.rules import DerivedMetrics


@dataclass
class TwinResult:
    metrics: DerivedMetrics
    monthly_net: float
    yearly_net: float
    cash_flow: float
    emi_impact: float
    savings_rate: float
    months: list[dict]


async def simulate(
    engine: ScoringEngine,
    *,
    monthly_income: int,
    sources: list[str],
    gig_platforms: list[str],
    has_primary_bank: bool,
    permissions_push: bool,
    emi_monthly: int,
    savings_rate: float,
    horizon_months: int,
) -> TwinResult:
    metrics = await engine.compute(
        monthly_income=monthly_income,
        sources=sources,
        gig_platforms=gig_platforms,
        has_primary_bank=has_primary_bank,
        permissions_push=permissions_push,
    )
    monthly_savings = round(monthly_income * savings_rate)
    monthly_net = monthly_income - monthly_savings - emi_monthly
    yearly_net = monthly_net * 12
    cash_flow = monthly_income * 12  # kept consistent with financial-twin.html fix
    emi_impact = round(emi_monthly * 12)
    months: list[dict] = []
    for m in range(1, horizon_months + 1):
        # tiny growth model so the chart isn't a flat line
        income_month = round(monthly_income * (1 + 0.005 * (m - 1)))
        savings_month = round(income_month * savings_rate)
        net_month = income_month - savings_month - emi_monthly
        months.append(
            {
                "month": m,
                "income": income_month,
                "savings": savings_month,
                "net": net_month,
            }
        )
    return TwinResult(
        metrics=metrics,
        monthly_net=monthly_net,
        yearly_net=yearly_net,
        cash_flow=cash_flow,
        emi_impact=emi_impact,
        savings_rate=savings_rate,
        months=months,
    )
