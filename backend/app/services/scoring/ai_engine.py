"""AI-backed scoring engine.

Implements the ``ScoringEngine`` protocol from ``engine.py`` but uses the
Anthropic API to derive the metrics from a structured feature bundle. The
output shape matches ``DerivedMetrics`` exactly so the rest of the
application (lenders, twin, analytics) doesn't need to know which engine
ran.

Graceful degradation: if the AI is disabled or the API call fails, this
engine transparently falls back to ``RuleBasedScoringEngine`` so the user
never sees a broken dashboard.
"""
from __future__ import annotations

import json

from app.config import settings
from app.services.ai_client import ai_client
from app.services.scoring.engine import ScoringEngine
from app.services.scoring.rules import DerivedMetrics, derive
from app.services.scoring.rules import Client


SYSTEM_PROMPT = """\
You are a financial DNA scoring engine.

Input: a JSON object with the user's declared features and recent
transaction-derived statistics.

Output: a JSON object with EXACTLY these keys and value ranges:
- dna_score              (int 0..100)
- stability              (int 0..100)
- discipline             (int 0..100)
- growth                 (int 0..100)
- savings                (int 0..100)
- diversification_index  (int 0..100)
- risk                   (int 0..100)
- income_quality         (int 0..100)
- top_client_share       (float 0..100, percent)
- cv                     (float, coefficient of variation in percent)
- yoy                    (float, year-over-year growth in percent)
- late_payouts           (float, average days late)

Constraints:
- Use ONLY the supplied features; never invent numbers.
- Blend the rules-of-thumb below when the features are sparse:
  * more income sources → higher income_quality, lower top_client_share
  * permissions_push=True → discipline=78, else 70
  * Gig diversity bonus: +6 to income_quality when gig_count >= 2
  * Investments declared → savings=76
- Reply with JSON only, no commentary, no markdown fences.
"""


class AIScoringEngine:
    """Uses Anthropic Claude to derive a `DerivedMetrics` object."""

    async def compute(
        self,
        *,
        monthly_income: int,
        sources: list[str],
        gig_platforms: list[str],
        has_primary_bank: bool,
        permissions_push: bool,
    ) -> DerivedMetrics:
        if not ai_client.enabled:
            # Graceful fallback — never let a missing API key break the dashboard.
            return derive(
                monthly_income=monthly_income,
                sources=sources,
                gig_platforms=gig_platforms,
                has_primary_bank=has_primary_bank,
                permissions_push=permissions_push,
            )

        features = {
            "monthly_income": monthly_income,
            "source_count": len(sources),
            "sources": sources,
            "gig_count": len(gig_platforms),
            "gig_platforms": gig_platforms,
            "has_primary_bank": has_primary_bank,
            "permissions_push": permissions_push,
        }
        try:
            text = await ai_client.complete(
                system=SYSTEM_PROMPT,
                user=json.dumps(features),
                max_tokens=400,
            )
            payload = json.loads(text)
            return _metrics_from_payload(payload, monthly_income, sources, gig_platforms)
        except Exception:
            # Any error (timeout, parse failure, rate limit) → rules fallback.
            return derive(
                monthly_income=monthly_income,
                sources=sources,
                gig_platforms=gig_platforms,
                has_primary_bank=has_primary_bank,
                permissions_push=permissions_push,
            )


def _metrics_from_payload(
    p: dict, monthly_income: int, sources: list[str], gig_platforms: list[str]
) -> DerivedMetrics:
    """Coerce the AI JSON into a fully-populated ``DerivedMetrics``.

    AI output intentionally omits the per-client share list; we rebuild it
    from the declared sources via the rule helper so the front-end
    bubble chart still has data.
    """
    from app.services.scoring.rules import _build_clients

    clients = _build_clients(sources, gig_platforms)
    sorted_clients = sorted(clients, key=lambda c: c.share, reverse=True)
    top = float(p.get("top_client_share", sorted_clients[0].share if sorted_clients else 0))
    herfindahl = round(sum(c.share ** 2 for c in clients))

    return DerivedMetrics(
        monthly_income=monthly_income,
        clients=clients,
        sorted_clients=sorted_clients,
        top_client_share=top,
        herfindahl=herfindahl,
        diversification_index=int(p.get("diversification_index", 50)),
        stability=int(p.get("stability", 60)),
        discipline=int(p.get("discipline", 70)),
        growth=int(p.get("growth", 65)),
        savings=int(p.get("savings", 60)),
        diversification=int(p.get("diversification_index", 50)),
        risk=int(p.get("risk", 60)),
        dna_score=int(p.get("dna_score", 60)),
        income_quality=int(p.get("income_quality", 60)),
        cv=float(p.get("cv", 16)),
        yoy=float(p.get("yoy", 8)),
        late_payouts=float(p.get("late_payouts", 4)),
    )
