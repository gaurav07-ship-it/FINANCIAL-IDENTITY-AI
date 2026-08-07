"""Schemas for the analytics endpoints (hidden income, fraud, timeline, etc.)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ----- Hidden income -----
class HiddenSourceItem(BaseModel):
    category: str
    source: str
    estimatedMonthly: int
    totalInr: int


class HiddenCounterpartyItem(BaseModel):
    counterparty: str
    transactions: int


class HiddenIncomeResponse(BaseModel):
    hiddenSources: list[HiddenSourceItem]
    unmatchedCounterparties: list[HiddenCounterpartyItem]
    windowDays: int


# ----- Fraud -----
class FraudSignalItem(BaseModel):
    code: str
    severity: Literal["low", "medium", "high"]
    detail: str


class FraudResponse(BaseModel):
    risk: int
    signals: list[FraudSignalItem]
    transactionsAnalyzed: int
    windowDays: int


# ----- Platform risk -----
class PlatformRiskItem(BaseModel):
    platform: str
    amountInr: int
    sharePct: float


class PlatformRiskResponse(BaseModel):
    riskLevel: Literal["low", "medium", "high"]
    topPlatformSharePct: float
    platforms: list[PlatformRiskItem]
    undeclaredPlatforms: list[str]
    windowDays: int


# ----- Income shock -----
class IncomeShockRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shockPct: float = Field(0.5, ge=0.0, le=1.0, alias="shockPct")
    shockMonths: int = Field(3, ge=1, le=24, alias="shockMonths")
    horizonMonths: int = Field(12, ge=1, le=60, alias="horizonMonths")


class IncomeShockMonth(BaseModel):
    month: int
    income: int
    expense: int
    net: int
    savingsBalance: int


class IncomeShockResponse(BaseModel):
    shockPct: float
    shockMonths: int
    horizonMonths: int
    startingSavings: int
    endingSavings: int
    runwayMonths: float
    months: list[IncomeShockMonth]


# ----- Timeline -----
class TimelineEvent(BaseModel):
    type: Literal["account", "onboarding", "consent", "score", "transaction"]
    at: datetime
    title: str
    detail: str


class TimelineResponse(BaseModel):
    events: list[TimelineEvent]


# ----- Emergency preparedness -----
class EmergencyPillar(BaseModel):
    name: str
    score: int
    note: str


class EmergencyResponse(BaseModel):
    score: int
    status: Literal["ready", "building", "at_risk"]
    monthsSaved: float
    recommendedMonths: int
    pillars: list[EmergencyPillar]
    monthlyExpense: int
    monthlyIncome: int


# ----- Career stability -----
class CareerStabilityResponse(BaseModel):
    score: int
    occupation: str
    sourceCount: int
    factors: list[str]


# ----- Explainable AI -----
class DnaReasonCode(BaseModel):
    code: str
    label: str
    value: int
    weight: float
    contribution: float
    direction: Literal["up", "down"]


class ExplainResponse(BaseModel):
    dnaScore: int
    reasons: list[DnaReasonCode]
    summary: str


# ----- Goals -----
class GoalsRequest(BaseModel):
    goals: list[str] = Field(default_factory=list, max_length=20)


class GoalsResponse(BaseModel):
    goals: list[str]
