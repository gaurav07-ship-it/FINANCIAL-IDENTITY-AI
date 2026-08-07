"""Pure functions for the scoring engine.

PORTED FROM `assets/store.js` (frontend) — keep in sync. Parity tests in
tests/test_scoring.py assert identical outputs for any given inputs.

Rule summary (verbatim from store.js):
  - clients list is built from the selected sources
  - shares are renormalised to sum to 100
  - stability / discipline / growth / savings / diversification / risk are 0-100
  - dna = weighted blend: stability 30 + discipline 20 + growth 15 +
          savings 15 + diversification 10 + risk 10
  - incomeQuality uses a step ladder by source count, with bonuses / penalties
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Client:
    name: str
    kind: str          # project | salary | gig | sales | investment | rental
    share: float = 0.0 # percent (0..100)


@dataclass
class DerivedMetrics:
    monthly_income: int
    clients: list[Client]
    sorted_clients: list[Client]
    top_client_share: float
    herfindahl: int
    diversification_index: int
    stability: int
    discipline: int
    growth: int
    savings: int
    diversification: int
    risk: int
    dna_score: int
    income_quality: int
    cv: int
    yoy: int
    late_payouts: float

    def as_dict(self) -> dict:
        d = asdict(self)
        d["sortedClients"] = d.pop("sorted_clients")
        d["dnaScore"] = d.pop("dna_score")
        d["incomeQuality"] = d.pop("income_quality")
        d["topClientShare"] = d.pop("top_client_share")
        d["diversificationIndex"] = d.pop("diversification_index")
        d["monthlyIncome"] = d.pop("monthly_income")
        d["latePayouts"] = d.pop("late_payouts")
        return d


def _build_clients(sources: list[str], gig_platforms: list[str]) -> list[Client]:
    clients: list[Client] = []
    if "Client Projects" in sources:
        clients.append(Client("Client A", "project", 70))
    if "Salaried role" in sources:
        clients.append(Client("Employer", "salary", 100))
    if "Gig Platforms" in sources:
        gigs = gig_platforms[:3]
        gigs_to_show = gigs if gigs else ["Zomato"]
        share_each = 100 / len(gigs_to_show)
        for g in gigs_to_show:
            clients.append(Client(g, "gig", share_each))
    if "Online Sales" in sources:
        clients.append(Client("Marketplace", "sales", 60))
    if "Investments" in sources:
        clients.append(Client("Portfolio", "investment", 100))
    if "Rental Income" in sources:
        clients.append(Client("Tenants", "rental", 100))

    # renormalise
    total = sum(c.share for c in clients) or 1
    for c in clients:
        c.share = round(c.share / total * 100, 1)
    return clients


def derive(
    *,
    monthly_income: int,
    sources: list[str],
    gig_platforms: list[str],
    has_primary_bank: bool,
    permissions_push: bool,
) -> DerivedMetrics:
    n = len(sources)

    clients = _build_clients(sources, gig_platforms)
    sorted_clients = sorted(clients, key=lambda c: c.share, reverse=True)
    top_client_share = sorted_clients[0].share if sorted_clients else 0
    herfindahl = round(sum(c.share ** 2 for c in clients))
    if n <= 1:
        diversification_index = 18
    else:
        diversification_index = min(95, 30 + (n - 1) * 12 + (8 if len(sorted_clients) > 2 else 0))

    stability = max(30, 100 - round(top_client_share * 0.5))
    discipline = 78 if permissions_push else 70
    growth = min(95, 65 + n * 4)
    if "Investments" in sources:
        savings = 76
    elif "Salaried role" in sources:
        savings = 68
    else:
        savings = 54
    risk = max(35, 95 - round(top_client_share * 0.6) - (0 if has_primary_bank else 6))

    dna_score = round(
        stability * 0.30
        + discipline * 0.20
        + growth * 0.15
        + savings * 0.15
        + diversification_index * 0.10
        + risk * 0.10
    )

    if n == 0:
        income_quality = 0
    elif n == 1:
        income_quality = 35
    elif n == 2:
        income_quality = 55
    elif n >= 4:
        income_quality = 82
    else:
        income_quality = 70
    if "Gig Platforms" in sources and len(gig_platforms) >= 2:
        income_quality += 6
    if "Investments" in sources:
        income_quality += 4
    if top_client_share > 60:
        income_quality -= 12
    if top_client_share > 80:
        income_quality -= 10
    income_quality = max(0, min(100, income_quality))

    if n <= 1:
        cv = 24
    elif n == 2:
        cv = 16
    elif n == 3:
        cv = 11
    else:
        cv = 7

    yoy = 6 + n * 2
    late_payouts = max(0.5, round(8 - n * 1.2, 1))

    return DerivedMetrics(
        monthly_income=monthly_income,
        clients=clients,
        sorted_clients=sorted_clients,
        top_client_share=top_client_share,
        herfindahl=herfindahl,
        diversification_index=diversification_index,
        stability=stability,
        discipline=discipline,
        growth=growth,
        savings=savings,
        diversification=diversification_index,
        risk=risk,
        dna_score=dna_score,
        income_quality=income_quality,
        cv=cv,
        yoy=yoy,
        late_payouts=late_payouts,
    )
