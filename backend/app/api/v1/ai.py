"""AI assistant endpoints.

- POST /api/v1/ai/chat         — conversational assistant grounded in the
  user's latest DNA + analytics.
- GET  /api/v1/ai/explain      — natural-language explanation of the DNA.
- POST /api/v1/ai/simulate     — conversational what-if on the Twin sliders.
- POST /api/v1/ai/lender-reasons — 3-bullet justification for an offer.

All endpoints stream SSE chunks (text/event-stream). If Anthropic is
unreachable the routes return 503 with a static fallback message.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_identity
from app.models import Identity
from app.services.ai_client import ai_client
from app.services.scoring import get_scoring_engine
from app.services.analytics import explain_dna, detect_hidden_income, detect_fraud_signals

router = APIRouter(prefix="/ai", tags=["ai"])


async def _grounding_context(db: AsyncSession, identity: Identity) -> dict:
    """Build the structured features bundle sent to Claude.

    Only derived numerics + declared categories are sent — no raw txn text,
    no PII. Keeps PII risk minimal and prompt cache-friendly.
    """
    perms = identity.permissions or {}
    metrics = await get_scoring_engine().compute(
        monthly_income=identity.monthly_income,
        sources=identity.sources or [],
        gig_platforms=identity.gig_platforms or [],
        has_primary_bank=bool(perms.get("primary_bank")),
        permissions_push=bool(perms.get("push")),
    )
    reasons = explain_dna(metrics)
    hidden = await detect_hidden_income(db, identity, lookback_days=180)
    fraud = await detect_fraud_signals(db, identity, lookback_days=90)
    return {
        "monthly_income": identity.monthly_income,
        "source_count": len(identity.sources or []),
        "sources": identity.sources or [],
        "gig_count": len(identity.gig_platforms or []),
        "dna_score": metrics.dna_score,
        "stability": metrics.stability,
        "discipline": metrics.discipline,
        "growth": metrics.growth,
        "savings": metrics.savings,
        "diversification_index": metrics.diversification_index,
        "risk": metrics.risk,
        "income_quality": metrics.income_quality,
        "reasons_top3": sorted(reasons, key=lambda r: r["contribution"], reverse=True)[:3],
        "hidden_source_count": len(hidden.get("hiddenSources", [])),
        "fraud_risk": fraud.get("risk", 0),
    }


@router.post("/chat")
async def chat(
    body: dict,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    if not ai_client.enabled:
        raise HTTPException(status_code=503, detail="AI not configured")
    message = (body or {}).get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message required")

    context = await _grounding_context(db, identity)

    async def gen() -> AsyncIterator[bytes]:
        async for chunk in ai_client.stream_chat(message=message, context=context):
            yield f"data: {chunk}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/explain")
async def explain(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Plain JSON summary. Falls back to deterministic reasons if AI is off."""
    context = await _grounding_context(db, identity)
    if not ai_client.enabled:
        return {"summary": _static_summary(context), "ai": False}
    text = await ai_client.complete(
        system="You are a financial DNA explainer. Reply in 3 short sentences.",
        user=json.dumps(context),
        max_tokens=200,
    )
    return {"summary": text, "ai": True}


@router.post("/simulate")
async def simulate(
    body: dict,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not ai_client.enabled:
        raise HTTPException(status_code=503, detail="AI not configured")
    context = await _grounding_context(db, identity)
    context["scenario"] = body or {}
    text = await ai_client.complete(
        system="You are a financial twin simulator. Reply in 2-3 sentences grounded only in the supplied features. Never invent numbers.",
        user=json.dumps(context),
        max_tokens=250,
    )
    return {"summary": text}


@router.post("/lender-reasons")
async def lender_reasons(
    body: dict,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not ai_client.enabled:
        raise HTTPException(status_code=503, detail="AI not configured")
    context = await _grounding_context(db, identity)
    context["offer"] = body or {}
    text = await ai_client.complete(
        system="You are a loan offer explainer. Produce exactly 3 bullet points prefixed with '- '. Never invent figures; use only the supplied features.",
        user=json.dumps(context),
        max_tokens=200,
    )
    return {"bullets": text}


def _static_summary(ctx: dict) -> str:
    top = ctx["reasons_top3"][0]["label"] if ctx["reasons_top3"] else "income mix"
    return (
        f"Your DNA of {ctx['dna_score']} is driven mainly by {top}. "
        f"You have {ctx['source_count']} declared income sources. "
        f"Emergency-fund and concentration risks remain the main levers."
    )
