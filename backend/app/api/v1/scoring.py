"""Scoring endpoints — DNA, IQ, history, twin, plus analytics extensions:
emergency, career stability, explainability, fraud, hidden income, platform
risk, income shock, and the financial timeline.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_identity
from app.models import Identity
from app.schemas import (
    CareerStabilityResponse,
    DnaResponse,
    EmergencyResponse,
    ExplainResponse,
    FraudResponse,
    HiddenIncomeResponse,
    IncomeQualityResponse,
    IncomeShockRequest,
    IncomeShockResponse,
    PlatformRiskResponse,
    TimelineResponse,
    TwinSimulateRequest,
    TwinSimulateResponse,
    AnomalyScoreRequest,
    AnomalyScoreResponse,
)
from app.services.analytics import (
    career_stability,
    detect_fraud_signals,
    detect_hidden_income,
    emergency_score,
    explain_dna,
    financial_timeline,
    income_shock,
    platform_risk,
)
from app.services.scoring import get_scoring_engine
from app.services.scoring.snapshots import compute_and_persist, get_history, get_latest
from app.services.twin import simulate

router = APIRouter(prefix="/score", tags=["scoring"])


def _permissions(identity: Identity) -> tuple[bool, bool]:
    perms = identity.permissions or {}
    return bool(perms.get("primary_bank")), bool(perms.get("push"))


def _metrics_to_dna(m, computed_at=None) -> DnaResponse:
    return DnaResponse(
        dnaScore=m.dna_score,
        stability=m.stability,
        discipline=m.discipline,
        growth=m.growth,
        savings=m.savings,
        diversification=m.diversification,
        risk=m.risk,
        monthlyIncome=m.monthly_income,
        topClientShare=m.top_client_share,
        diversificationIndex=m.diversification_index,
        herfindahl=m.herfindahl,
        clients=[{"name": c.name, "kind": c.kind, "share": c.share} for c in m.clients],
        sortedClients=[{"name": c.name, "kind": c.kind, "share": c.share} for c in m.sorted_clients],
        computedAt=computed_at,
    )


# ---------------------------------------------------------------------------
# DNA + income quality
# ---------------------------------------------------------------------------

@router.get("/dna", response_model=DnaResponse)
async def get_dna(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> DnaResponse:
    """Compute a fresh snapshot on every read; cheap because the engine is pure."""
    has_bank, has_push = _permissions(identity)
    metrics = await compute_and_persist(
        db,
        get_scoring_engine(),
        identity_id=identity.id,
        monthly_income=identity.monthly_income,
        sources=identity.sources or [],
        gig_platforms=identity.gig_platforms or [],
        has_primary_bank=has_bank,
        permissions_push=has_push,
    )
    await db.commit()
    return _metrics_to_dna(metrics)


@router.get("/history")
async def get_history_endpoint(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
    limit: int = 12,
) -> list[dict]:
    rows = await get_history(db, identity.id, limit=limit)
    return [
        {
            "computedAt": r.computed_at,
            "dnaScore": r.dna_score,
            "stability": r.stability,
            "discipline": r.discipline,
            "growth": r.growth,
            "savings": r.savings,
            "diversification": r.diversification,
            "risk": r.risk,
            "incomeQuality": r.income_quality,
        }
        for r in rows
    ]


@router.get("/income-quality", response_model=IncomeQualityResponse)
async def get_income_quality(
    identity: Identity = Depends(get_current_identity),
) -> IncomeQualityResponse:
    has_bank, has_push = _permissions(identity)
    metrics = await get_scoring_engine().compute(
        monthly_income=identity.monthly_income,
        sources=identity.sources or [],
        gig_platforms=identity.gig_platforms or [],
        has_primary_bank=has_bank,
        permissions_push=has_push,
    )
    return IncomeQualityResponse(
        incomeQuality=metrics.income_quality,
        cv=metrics.cv,
        yoy=metrics.yoy,
        latePayouts=metrics.late_payouts,
        topClientShare=metrics.top_client_share,
    )


# ---------------------------------------------------------------------------
# Twin / shock / explain
# ---------------------------------------------------------------------------

@router.post("/twin/simulate", response_model=TwinSimulateResponse)
async def twin_simulate(
    body: TwinSimulateRequest,
    identity: Identity = Depends(get_current_identity),
) -> TwinSimulateResponse:
    result = await simulate(
        get_scoring_engine(),
        monthly_income=body.monthly_income,
        sources=body.sources,
        gig_platforms=body.gig_platforms,
        has_primary_bank=body.has_primary_bank,
        permissions_push=body.permissions_push,
        emi_monthly=body.emi_monthly,
        savings_rate=body.savings_rate,
        horizon_months=body.horizon_months,
    )
    m = result.metrics
    return TwinSimulateResponse(
        dnaScore=m.dna_score,
        stability=m.stability,
        discipline=m.discipline,
        growth=m.growth,
        savings=m.savings,
        diversification=m.diversification,
        risk=m.risk,
        incomeQuality=m.income_quality,
        monthlyNet=result.monthly_net,
        yearlyNet=result.yearly_net,
        cashFlow=result.cash_flow,
        emiImpact=result.emi_impact,
        savingsRate=result.savings_rate,
        months=result.months,
    )


@router.post("/shock", response_model=IncomeShockResponse)
async def shock(
    body: IncomeShockRequest,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> IncomeShockResponse:
    return await income_shock(
        db,
        identity,
        shock_pct=body.shockPct,
        shock_months=body.shockMonths,
        horizon_months=body.horizonMonths,
    )


@router.get("/explain", response_model=ExplainResponse)
async def explain(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> ExplainResponse:
    has_bank, has_push = _permissions(identity)
    metrics = await get_scoring_engine().compute(
        monthly_income=identity.monthly_income,
        sources=identity.sources or [],
        gig_platforms=identity.gig_platforms or [],
        has_primary_bank=has_bank,
        permissions_push=has_push,
    )
    reasons = explain_dna(metrics)
    summary = (
        f"DNA of {metrics.dna_score} is driven mostly by "
        f"{max(reasons, key=lambda r: r['contribution'])['label']}."
    )
    return ExplainResponse(dnaScore=metrics.dna_score, reasons=reasons, summary=summary)


# ---------------------------------------------------------------------------
# Analytics: emergency, career, fraud, hidden income, platform risk, timeline
# ---------------------------------------------------------------------------

@router.get("/emergency", response_model=EmergencyResponse)
async def emergency(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> EmergencyResponse:
    return await emergency_score(db, identity)


@router.get("/career-stability", response_model=CareerStabilityResponse)
async def career(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> CareerStabilityResponse:
    return await career_stability(db, identity)


@router.get("/fraud", response_model=FraudResponse)
async def fraud(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> FraudResponse:
    return await detect_fraud_signals(db, identity)


@router.get("/hidden-income", response_model=HiddenIncomeResponse)
async def hidden_income(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> HiddenIncomeResponse:
    return await detect_hidden_income(db, identity)


@router.get("/platform-risk", response_model=PlatformRiskResponse)
async def platform_risk_endpoint(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> PlatformRiskResponse:
    return await platform_risk(db, identity)


@router.get("/timeline", response_model=TimelineResponse)
async def timeline(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
) -> TimelineResponse:
    events = await financial_timeline(db, identity, limit=limit)
    return TimelineResponse(events=events)


@router.post("/anomaly-score", response_model=AnomalyScoreResponse)
async def compute_anomaly_score(
    body: AnomalyScoreRequest,
    identity: Identity = Depends(get_current_identity),
) -> AnomalyScoreResponse:
    from app.services.scoring.ai_engine import analyze_transactions
    
    # Convert Pydantic models to dicts for the analyzer
    transactions = [t.model_dump() for t in body.transactions]
    
    result = analyze_transactions(transactions)
    return AnomalyScoreResponse(**result)

