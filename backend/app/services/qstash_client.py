"""Upstash QStash client — used for nightly fan-out recompute jobs.

Why QStash? Vercel serverless can't run long-lived workers, so we use
QStash to fan out a single per-identity recompute via webhook deliveries.
Free tier covers 500 messages/day, enough for tens of thousands of
identities.

We use httpx instead of the upstash-qstash SDK to keep the dependency
surface small and the call sites explicit.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

import httpx

from app.config import settings


async def publish_json(target_url: str, body: dict[str, Any], *, delay_s: int = 0) -> dict:
    """Enqueue a single webhook delivery to ``target_url`` with ``body`` as JSON.

    Returns the QStash ``messageId`` envelope.
    """
    if not settings.qstash_token:
        # Local dev: short-circuit and return a fake message id.
        return {"messageId": "dev-noop", "noop": True}

    payload = json.dumps(body, default=str).encode()
    headers = {
        "Authorization": f"Bearer {settings.qstash_token}",
        "Content-Type": "application/json",
        "Upstash-Method": "POST",
        "Upstash-Url": target_url,
    }
    if delay_s:
        headers["Upstash-Delay"] = f"{delay_s}s"

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{settings.qstash_base_url}/v2/publish/{target_url}", headers=headers, content=payload)
        r.raise_for_status()
        return r.json()


def verify_qstash_signature(body: bytes, signature: str | None) -> bool:
    """Validate an incoming QStash webhook signature.

    QStash signs requests with HMAC-SHA256 of the raw body using the
    current signing key. Reference: https://upstash.com/docs/qstash/howto/signature
    """
    if not signature:
        return False
    if not settings.qstash_current_signing_key:
        # If we never configured a key, accept only in dev.
        return settings.is_dev

    expected = hmac.new(
        settings.qstash_current_signing_key.encode(),
        body,
        hashlib.sha256,
    ).digest()
    provided = base64.b64decode(signature) if signature else b""
    return hmac.compare_digest(expected, provided)
