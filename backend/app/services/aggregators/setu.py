"""Setu (Account Aggregator) provider — production skeleton.

Wires the AggregatorProvider interface to Setu's AA APIs. Requires SETU_CLIENT_ID
and SETU_CLIENT_SECRET in production. The class is importable today; actual
network calls stay behind the AGGREGATOR_PROVIDER=setu flag.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.services.aggregators.base import (
    AggregatorProvider,
    ConsentHandle,
    ConsentRequest,
)


class SetuProvider:
    def name(self) -> str:
        return "setu"

    def _ensure_config(self) -> None:
        if not (settings.setu_client_id and settings.setu_client_secret):
            raise RuntimeError(
                "SetuProvider requires SETU_CLIENT_ID and SETU_CLIENT_SECRET in .env"
            )

    async def create_consent(self, req: ConsentRequest) -> ConsentHandle:
        """
        Real call (sketched):
          POST {SETU_BASE_URL}/v2/Consent
          body: {
            "Detail": {
              "consentStart": "...",
              "consentExpiry": "...",
              "Customer": {"id": str(req.identity_id)},
              "FIDataRange": {...},
              "FITypes": req.fi_types,
            },
            "url": "https://app.example.com/aa/callback",
          }
          headers: Authorization: Bearer <client_credentials_token>
        The endpoint returns a consent id + redirect URL for the AA app.
        """
        self._ensure_config()
        consent_id = f"setu-{uuid.uuid4().hex[:16]}"
        # TODO: real HTTP call when Setu credentials are added.
        await asyncio.sleep(0.05)
        return ConsentHandle(
            consent_id=consent_id,
            status="PENDING",
            redirect_url=f"{settings.setu_base_url}/v2/Consent/{consent_id}/redirect",
            data_range_from=req.from_date,
            data_range_to=req.to_date,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(days=365),
            payload={"stub": True, "provider": "setu"},
        )

    async def fetch_data(self, consent_id: str) -> dict:
        """
        Real call (sketched):
          POST {SETU_BASE_URL}/v2/FI/request
          body: { "consentId": consent_id, "FI": "DEPOSIT" }
          then poll {SETU_BASE_URL}/v2/FI/fetch/{session_id}
        Then map Setu's FI response to our internal {accounts, transactions} shape.
        """
        self._ensure_config()
        # TODO: real HTTP call when Setu credentials are added.
        await asyncio.sleep(0.1)
        return {"consent_id": consent_id, "accounts": [], "transactions": []}

    async def revoke_consent(self, consent_id: str) -> bool:
        self._ensure_config()
        # TODO: real DELETE {SETU_BASE_URL}/v2/Consent/{consent_id}
        await asyncio.sleep(0.05)
        return True
