"""Scoring API DTOs. Field names match STORE.computeDerived() output exactly."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Client(BaseModel):
    name: str
    kind: Literal["project", "salary", "gig", "sales", "investment", "rental"]
    share: float


class DnaResponse(BaseModel):
    """Mirrors the object returned by STORE.computeDerived()."""

    model_config = ConfigDict(from_attributes=True)

    dnaScore: int
    stability: int
    discipline: int
    growth: int
    savings: int
    diversification: int
    risk: int
    monthlyIncome: int
    topClientShare: float
    diversificationIndex: int
    herfindahl: int
    clients: list[_Client]
    sortedClients: list[_Client]
    computedAt: datetime | None = None


class IncomeQualityResponse(BaseModel):
    incomeQuality: int
    cv: int
    yoy: int
    latePayouts: float
    topClientShare: float


class TwinSimulateRequest(BaseModel):
    """What-if scenario. Mirrors the financial-twin.html slider state."""

    monthly_income: int = Field(ge=0, alias="monthlyIncome")
    sources: list[str] = []
    gig_platforms: list[str] = Field([], alias="gigPlatforms")
    has_primary_bank: bool = Field(False, alias="hasPrimaryBank")
    permissions_push: bool = Field(False, alias="permissionsPush")
    emi_monthly: int = Field(0, ge=0, alias="emiMonthly")
    savings_rate: float = Field(0.0, ge=0.0, le=1.0, alias="savingsRate")
    horizon_months: int = Field(12, ge=1, le=60, alias="horizonMonths")


class TwinSimulateResponse(BaseModel):
    """Simulation result. Same metric names + a tiny month-by-month cashflow series."""

    dnaScore: int
    stability: int
    discipline: int
    growth: int
    savings: int
    diversification: int
    risk: int
    incomeQuality: int
    monthlyNet: float
    yearlyNet: float
    cashFlow: float
    emiImpact: float
    savingsRate: float
    months: list[dict]  # [{ "month": 1, "income": int, "savings": int, "net": int }]


class TransactionAnomaly(BaseModel):
    amount: float
    direction: Literal["credit", "debit"]
    category: str


class AnomalyScoreRequest(BaseModel):
    transactions: list[TransactionAnomaly]


class AnomalyScoreResponse(BaseModel):
    anomalyScore: int = Field(alias="anomaly_score")
    isAnomalous: bool = Field(alias="is_anomalous")
    anomalousTransactionCount: int = Field(alias="anomalous_transaction_count")
    riskLevel: str = Field(alias="risk_level")