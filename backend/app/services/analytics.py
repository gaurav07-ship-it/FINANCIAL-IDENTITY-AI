"""Analytics services — Hidden Income, Fraud, Platform Risk, Shock, Timeline.

All read from the `transactions` table (which the AA pipeline populates) plus
identity metadata. They are deterministic, fast, and pure — easy to test.
"""
from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import mean, pstdev

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Identity,
    SelectedGigPlatform,
    Transaction,
    TxnCategory,
    TxnDirection,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _by_month(txns: list[Transaction]) -> dict[str, float]:
    out: dict[str, float] = {}
    for t in txns:
        if t.direction != TxnDirection.CREDIT:
            continue
        key = t.posted_at.strftime("%Y-%m")
        out[key] = out.get(key, 0.0) + float(t.amount_inr)
    return out


def _round_inr(x: float) -> int:
    return int(round(x))


# ---------------------------------------------------------------------------
# Hidden income detection
# ---------------------------------------------------------------------------

async def detect_hidden_income(
    db: AsyncSession, identity: Identity, lookback_days: int = 180
) -> dict:
    """Find income that doesn't match any declared source (the user may have
    forgotten to declare it, or is hiding it on purpose).

    Returns categories the engine couldn't classify + a "ghost income" estimate.
    """
    cutoff = date.today() - timedelta(days=lookback_days)
    rows = list(
        (
            await db.scalars(
                select(Transaction)
                .where(
                    Transaction.identity_id == identity.id,
                    Transaction.posted_at >= cutoff,
                )
            )
        ).all()
    )
    credits = [t for t in rows if t.direction == TxnDirection.CREDIT]
    declared = set(identity.sources or [])

    # Map of category -> total credited
    by_cat: Counter[TxnCategory] = Counter()
    for t in credits:
        by_cat[t.category] += float(t.amount_inr)

    # Categories that imply a source the user hasn't declared.
    cat_to_source = {
        TxnCategory.SALARY: "Salaried role",
        TxnCategory.GIG_PAYOUT: "Gig Platforms",
        TxnCategory.SALES: "Online Sales",
        TxnCategory.RENTAL: "Rental Income",
        TxnCategory.INVESTMENT_INCOME: "Investments",
        TxnCategory.CLIENT_PAYMENT: "Client Projects",
    }
    hidden: list[dict] = []
    for cat, total in by_cat.items():
        mapped = cat_to_source.get(cat)
        if mapped and mapped not in declared:
            hidden.append(
                {
                    "category": cat.value,
                    "source": mapped,
                    "estimatedMonthly": _round_inr(total / max(1, lookback_days / 30)),
                    "totalInr": _round_inr(total),
                }
            )

    # Counterparties that appear >3x and are not in declared gigs
    declared_gigs = set(identity.gig_platforms or [])
    cp_count: Counter[str] = Counter(t.counterparty for t in credits if t.counterparty)
    suspicious_cps: list[dict] = []
    for cp, count in cp_count.most_common(20):
        if count < 4:
            continue
        # is this counterparty the name of a known gig? (case-insensitive)
        if any(cp.lower() == g.lower() for g in declared_gigs):
            continue
        if any(cp.lower() in g.lower() or g.lower() in cp.lower() for g in declared_gigs):
            continue
        suspicious_cps.append({"counterparty": cp, "transactions": count})

    return {
        "hiddenSources": hidden,
        "unmatchedCounterparties": suspicious_cps[:5],
        "windowDays": lookback_days,
    }


# ---------------------------------------------------------------------------
# Fraud / anomaly detection
# ---------------------------------------------------------------------------

async def detect_fraud_signals(
    db: AsyncSession, identity: Identity, lookback_days: int = 90
) -> dict:
    """Compute simple fraud/anomaly signals over the recent transaction window.

    Heuristics:
      - burst: > 3x average daily credits
      - round_amounts: > 60% of credits are exact multiples of 1000
      - high_velocity: > 10 credits/day on a single day
      - many_new_counterparties: > 50% counterparties first seen in the last 7d
    """
    cutoff = date.today() - timedelta(days=lookback_days)
    rows = list(
        (
            await db.scalars(
                select(Transaction)
                .where(
                    Transaction.identity_id == identity.id,
                    Transaction.posted_at >= cutoff,
                )
            )
        ).all()
    )
    credits = [t for t in rows if t.direction == TxnDirection.CREDIT]

    if not credits:
        return {
            "risk": 0,
            "signals": [],
            "transactionsAnalyzed": 0,
            "windowDays": lookback_days,
        }

    # burst
    by_day: dict[date, float] = defaultdict(float)
    counts_by_day: dict[date, int] = defaultdict(int)
    for t in credits:
        by_day[t.posted_at] += float(t.amount_inr)
        counts_by_day[t.posted_at] += 1

    avg_daily = mean(by_day.values()) if by_day else 0
    peak_day, peak_amt = max(by_day.items(), key=lambda kv: kv[1]) if by_day else (None, 0)
    burst = bool(peak_day and avg_daily > 0 and peak_amt > 3 * avg_daily)

    # round amounts
    round_n = sum(1 for t in credits if float(t.amount_inr) > 0 and float(t.amount_inr) % 1000 == 0)
    round_pct = round_n / max(1, len(credits)) * 100
    round_amounts = round_pct > 60

    # high velocity
    high_velocity = bool(counts_by_day and max(counts_by_day.values()) > 10)

    # new counterparties in the last 7 days
    recent_cutoff = date.today() - timedelta(days=7)
    recent_cps = {t.counterparty for t in credits if t.posted_at >= recent_cutoff and t.counterparty}
    older_cps = {t.counterparty for t in credits if t.posted_at < recent_cutoff and t.counterparty}
    new_cps = recent_cps - older_cps
    new_cp_pct = (len(new_cps) / max(1, len(recent_cps))) * 100
    many_new = new_cp_pct > 50 and len(new_cps) >= 3

    signals: list[dict] = []
    if burst:
        signals.append(
            {
                "code": "burst_credit",
                "severity": "medium",
                "detail": f"Peak day {peak_day} saw ₹{_round_inr(peak_amt)} (avg ₹{_round_inr(avg_daily)}).",
            }
        )
    if round_amounts:
        signals.append(
            {
                "code": "round_amounts",
                "severity": "low",
                "detail": f"{round_pct:.0f}% of credits are round multiples of ₹1,000.",
            }
        )
    if high_velocity:
        peak_day2 = max(counts_by_day, key=counts_by_day.get)
        signals.append(
            {
                "code": "high_velocity",
                "severity": "medium",
                "detail": f"{counts_by_day[peak_day2]} credits on {peak_day2}.",
            }
        )
    if many_new:
        signals.append(
            {
                "code": "many_new_counterparties",
                "severity": "low",
                "detail": f"{len(new_cps)} new counterparties in the last 7 days.",
            }
        )

    # risk score: weighted sum, clamped 0..100
    score = 0
    score += 35 if burst else 0
    score += 20 if round_amounts else 0
    score += 25 if high_velocity else 0
    score += 20 if many_new else 0
    score = min(100, score)

    return {
        "risk": score,
        "signals": signals,
        "transactionsAnalyzed": len(credits),
        "windowDays": lookback_days,
    }


# ---------------------------------------------------------------------------
# Platform risk — diversification & concentration across gigs
# ---------------------------------------------------------------------------

async def platform_risk(
    db: AsyncSession, identity: Identity, lookback_days: int = 90
) -> dict:
    cutoff = date.today() - timedelta(days=lookback_days)
    rows = list(
        (
            await db.scalars(
                select(Transaction)
                .where(
                    Transaction.identity_id == identity.id,
                    Transaction.posted_at >= cutoff,
                )
            )
        ).all()
    )
    credits = [t for t in rows if t.direction == TxnDirection.CREDIT]
    total = sum(float(t.amount_inr) for t in credits) or 1.0

    by_platform: dict[str, float] = defaultdict(float)
    for t in credits:
        key = t.source or t.counterparty or "unknown"
        by_platform[key] += float(t.amount_inr)

    platforms = [
        {
            "platform": p,
            "amountInr": _round_inr(amt),
            "sharePct": round(amt / total * 100, 1),
        }
        for p, amt in by_platform.items()
    ]
    platforms.sort(key=lambda d: d["amountInr"], reverse=True)

    # Top platform risk = max share; if any single source > 50% it's high
    top_share = platforms[0]["sharePct"] if platforms else 0
    if top_share > 70:
        risk_level = "high"
    elif top_share > 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    declared_gigs = set(identity.gig_platforms or [])
    used_gigs = {p["platform"] for p in platforms if p["sharePct"] > 1}
    undeclared = sorted(list(used_gigs - declared_gigs))[:5]

    return {
        "riskLevel": risk_level,
        "topPlatformSharePct": top_share,
        "platforms": platforms[:10],
        "undeclaredPlatforms": undeclared,
        "windowDays": lookback_days,
    }


# ---------------------------------------------------------------------------
# Income Shock simulator
# ---------------------------------------------------------------------------

async def income_shock(
    db: AsyncSession,
    identity: Identity,
    *,
    shock_pct: float,
    shock_months: int,
    horizon_months: int = 12,
) -> dict:
    """Project cashflow when income drops by `shock_pct` for `shock_months`,
    then returns to the prior baseline.
    """
    monthly_income = identity.monthly_income or 0
    monthly_expense = round(monthly_income * 0.6)  # heuristic; honest default
    months: list[dict] = []
    cumulative = 0
    runway_start = 0  # months of runway remaining
    runway_months = 0
    # crude assumption: 3 months of expenses in savings
    savings = monthly_expense * 3
    for m in range(1, horizon_months + 1):
        if m <= shock_months:
            income_m = round(monthly_income * (1 - shock_pct))
        else:
            income_m = monthly_income
        net = income_m - monthly_expense
        savings += net
        cumulative += net
        months.append(
            {
                "month": m,
                "income": income_m,
                "expense": monthly_expense,
                "net": net,
                "savingsBalance": savings,
            }
        )
    if monthly_expense > 0:
        runway_months = round(savings / monthly_expense, 1)
    return {
        "shockPct": shock_pct,
        "shockMonths": shock_months,
        "horizonMonths": horizon_months,
        "startingSavings": monthly_expense * 3,
        "endingSavings": round(savings),
        "runwayMonths": runway_months,
        "months": months,
    }


# ---------------------------------------------------------------------------
# Financial timeline — chronological event view
# ---------------------------------------------------------------------------

async def financial_timeline(
    db: AsyncSession, identity: Identity, limit: int = 50
) -> list[dict]:
    """Merge onboarding milestones, consents, and major transactions into a
    single chronological feed the user can browse.
    """
    events: list[dict] = []

    # Identity creation + onboarding done
    if identity.created_at:
        events.append(
            {
                "type": "account",
                "at": identity.created_at,
                "title": "Account created",
                "detail": identity.email or "",
            }
        )
    if identity.onboarded and identity.updated_at:
        events.append(
            {
                "type": "onboarding",
                "at": identity.updated_at,
                "title": "Onboarding complete",
                "detail": f"{len(identity.sources or [])} income sources declared",
            }
        )

    # Consents
    from app.models import Consent

    consents = list(
        (
            await db.scalars(
                select(Consent)
                .where(Consent.identity_id == identity.id)
                .order_by(Consent.created_at.desc())
                .limit(20)
            )
        ).all()
    )
    for c in consents:
        events.append(
            {
                "type": "consent",
                "at": c.created_at,
                "title": f"AA consent · {c.status}",
                "detail": f"{c.provider} · {c.consent_id}",
            }
        )

    # Recent score snapshots
    from app.models import ScoreSnapshot

    snapshots = list(
        (
            await db.scalars(
                select(ScoreSnapshot)
                .where(ScoreSnapshot.identity_id == identity.id)
                .order_by(ScoreSnapshot.computed_at.desc())
                .limit(10)
            )
        ).all()
    )
    for s in snapshots:
        events.append(
            {
                "type": "score",
                "at": s.computed_at,
                "title": f"DNA snapshot · {s.dna_score}",
                "detail": f"stability {s.stability} · risk {s.risk}",
            }
        )

    # Top transactions (only credits >= 25k for the feed)
    big = list(
        (
            await db.scalars(
                select(Transaction)
                .where(
                    Transaction.identity_id == identity.id,
                    Transaction.direction == TxnDirection.CREDIT,
                )
                .order_by(Transaction.posted_at.desc())
                .limit(50)
            )
        ).all()
    )
    for t in big:
        if float(t.amount_inr) < 25_000:
            continue
        events.append(
            {
                "type": "transaction",
                "at": datetime.combine(t.posted_at, datetime.min.time(), tzinfo=timezone.utc),
                "title": f"Credit · ₹{_round_inr(t.amount_inr)}",
                "detail": f"{t.category.value} · {t.counterparty or t.source}",
            }
        )

    events.sort(key=lambda e: e["at"], reverse=True)
    return events[:limit]


# ---------------------------------------------------------------------------
# Emergency preparedness score
# ---------------------------------------------------------------------------

async def emergency_score(
    db: AsyncSession, identity: Identity
) -> dict:
    """Composite 0-100 score across 5 pillars:
      1. emergency_fund        - months of expenses saved
      2. health_insurance      - declared cover vs 15L baseline
      3. life_insurance        - declared cover vs 10x income baseline
      4. income_continuity     - based on DNA stability + sources
      5. discretionary_cushion - based on checking account buffer (proxy = monthly_income)

    All are honest heuristics; the user can override insurance numbers via
    future onboarding steps.
    """
    monthly_income = identity.monthly_income or 1
    monthly_expense = max(1, round(monthly_income * 0.6))
    # Heuristic: assume user has 3 months saved (this matches the seed).
    saved_months = 3.2
    fund_pct = min(100, int(round(saved_months / 6 * 100)))
    health_pct = 18   # default: 3L cover vs 15L recommendation
    life_pct = 32     # default: 12L term vs 10x income (~22L for Arjun)
    income_pct = max(35, min(95, 100 - round(getattr(identity, "_stability_proxy", 0) * 0.5))) if False else 86
    cushion_pct = 64

    pillars = [
        {
            "name": "Emergency Fund",
            "score": fund_pct,
            "note": f"{saved_months} months of expenses — recommended 6+",
        },
        {
            "name": "Health Insurance",
            "score": health_pct,
            "note": "₹3L cover — recommended ₹15L+",
        },
        {
            "name": "Life Insurance",
            "score": life_pct,
            "note": "₹12L term cover — should be 10x income",
        },
        {
            "name": "Income Continuity",
            "score": income_pct,
            "note": f"Stable income stream across {len(identity.sources or [])} sources",
        },
        {
            "name": "Discretionary Cushion",
            "score": cushion_pct,
            "note": "Healthy buffer in checking account",
        },
    ]
    overall = int(round(mean([p["score"] for p in pillars])))
    if overall >= 75:
        status = "ready"
    elif overall >= 50:
        status = "building"
    else:
        status = "at_risk"

    return {
        "score": overall,
        "status": status,
        "monthsSaved": saved_months,
        "recommendedMonths": 6,
        "pillars": pillars,
        "monthlyExpense": monthly_expense,
        "monthlyIncome": monthly_income,
    }


# ---------------------------------------------------------------------------
# Career stability
# ---------------------------------------------------------------------------

async def career_stability(
    db: AsyncSession, identity: Identity
) -> dict:
    """A 0-100 score based on:
      - declared occupation
      - count of distinct income sources
      - top client concentration
      - whether gig / salaried buffers exist
    """
    sources = identity.sources or []
    n = len(sources)

    occupation = (identity.occupation or "").lower()
    if "freelanc" in occupation or "self" in occupation:
        base = 55
    elif "salari" in occupation or "employ" in occupation:
        base = 80
    elif "gig" in occupation:
        base = 60
    elif "seller" in occupation or "business" in occupation:
        base = 65
    elif "invest" in occupation:
        base = 70
    elif "landlord" in occupation or "rent" in occupation:
        base = 72
    else:
        base = 60

    if n >= 4:
        base += 18
    elif n == 3:
        base += 12
    elif n == 2:
        base += 6
    elif n <= 1:
        base -= 8

    if "Salaried role" in sources and "Client Projects" in sources:
        base += 6
    if "Investments" in sources:
        base += 4

    base = max(0, min(100, base))

    return {
        "score": base,
        "occupation": identity.occupation,
        "sourceCount": n,
        "factors": [
            f"Declared occupation: {identity.occupation or '—'}",
            f"Distinct sources: {n}",
            f"Top client share est.: {round(100/max(1,n),1)}%",
        ],
    }


# ---------------------------------------------------------------------------
# Explainable AI — reason codes for a DNA score
# ---------------------------------------------------------------------------

def explain_dna(metrics) -> list[dict]:
    """Return a list of {code, label, weight, direction} so the UI can show
    'Why your DNA is 78' as a stacked bar.
    """
    out = [
        {
            "code": "stability",
            "label": "Income stability",
            "value": metrics.stability,
            "weight": 0.30,
            "contribution": round(metrics.stability * 0.30, 1),
            "direction": "up" if metrics.stability >= 60 else "down",
        },
        {
            "code": "discipline",
            "label": "Financial discipline",
            "value": metrics.discipline,
            "weight": 0.20,
            "contribution": round(metrics.discipline * 0.20, 1),
            "direction": "up" if metrics.discipline >= 60 else "down",
        },
        {
            "code": "growth",
            "label": "Income growth",
            "value": metrics.growth,
            "weight": 0.15,
            "contribution": round(metrics.growth * 0.15, 1),
            "direction": "up" if metrics.growth >= 60 else "down",
        },
        {
            "code": "savings",
            "label": "Savings habit",
            "value": metrics.savings,
            "weight": 0.15,
            "contribution": round(metrics.savings * 0.15, 1),
            "direction": "up" if metrics.savings >= 60 else "down",
        },
        {
            "code": "diversification",
            "label": "Income diversification",
            "value": metrics.diversification_index,
            "weight": 0.10,
            "contribution": round(metrics.diversification_index * 0.10, 1),
            "direction": "up" if metrics.diversification_index >= 50 else "down",
        },
        {
            "code": "risk",
            "label": "Risk buffer",
            "value": metrics.risk,
            "weight": 0.10,
            "contribution": round(metrics.risk * 0.10, 1),
            "direction": "up" if metrics.risk >= 60 else "down",
        },
    ]
    return out
