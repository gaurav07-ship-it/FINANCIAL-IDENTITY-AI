"""Lender offer computation — simple deterministic rules over the DNA score.

Not a real underwriting engine. Just a per-lender approval % + emi so the
loan-eligibility page has something honest to render.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models import Identity, Lender, LenderOffer
from app.services.scoring.engine import ScoringEngine
from app.services.scoring.rules import DerivedMetrics


@dataclass
class Offer:
    lender: Lender
    approved_amount: int
    tenure_months: int
    rate_apr: float
    emi: int
    approval_pct: int
    disbursal_hours: int
    reason_codes: list[str]


def _emi(principal: int, rate_pct: float, months: int) -> int:
    if principal <= 0 or months <= 0:
        return 0
    r = rate_pct / 12 / 100
    if r == 0:
        return round(principal / months)
    return round(principal * r * (1 + r) ** months / ((1 + r) ** months - 1))


def compute_offers(
    identity: Identity, metrics: DerivedMetrics, lenders: list[Lender], requested_amount: int | None = None
) -> list[Offer]:
    score = metrics.dna_score
    out: list[Offer] = []
    for lender in lenders:
        if not lender.active:
            continue
        # Amount: capped by lender range AND monthly income heuristic
        if requested_amount:
            principal = min(requested_amount, lender.max_amount_inr)
        else:
            principal = min(lender.max_amount_inr, max(lender.min_amount_inr, metrics.monthly_income * 12))
        principal = max(principal, lender.min_amount_inr)

        # Approval % tied to dna + diversification, with a lender-specific floor
        base = score
        if metrics.diversification_index < 30:
            base -= 15
        if metrics.top_client_share > 70:
            base -= 8
        approval = max(40, min(99, base))

        # Tenure: longer for higher amounts
        if principal > 500_000:
            tenure = min(lender.max_tenure_months, 36)
        else:
            tenure = min(lender.max_tenure_months, 24)
        tenure = max(tenure, lender.min_tenure_months)

        # Rate: interpolate within the lender's published range
        rate = lender.rate_min + (lender.rate_max - lender.rate_min) * (1 - approval / 100)

        emi = _emi(principal, rate, tenure)
        reasons: list[str] = []
        if metrics.top_client_share > 70:
            reasons.append("Client concentration high")
        if metrics.income_quality >= 70:
            reasons.append("Income quality strong")
        if metrics.diversification_index >= 50:
            reasons.append("Diversified income")
        if metrics.cv <= 12:
            reasons.append("Low income volatility")
        if not reasons:
            reasons.append("Meets lender baseline")

        disbursal_hours = 24 if approval >= 85 else 48 if approval >= 70 else 72

        out.append(
            Offer(
                lender=lender,
                approved_amount=principal,
                tenure_months=tenure,
                rate_apr=round(rate, 2),
                emi=emi,
                approval_pct=approval,
                disbursal_hours=disbursal_hours,
                reason_codes=reasons,
            )
        )
    out.sort(key=lambda o: o.approval_pct, reverse=True)
    return out
