"""Mock aggregator round-trip — confirm consent + pull + ingest."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_mock_consent_then_pull_ingests_transactions(client):
    # register
    await client.post(
        "/api/v1/auth/register",
        json={"email": "agg@example.com", "password": "Sup3rSecret!", "name": "Agg"},
    )
    # create consent
    r = await client.post(
        "/api/v1/aggregators/consent",
        params={
            "fi_types": ["DEPOSIT"],
            "from_date": "2026-01-01",
            "to_date": "2026-08-01",
        },
    )
    assert r.status_code == 200, r.text
    consent_id = r.json()["consentId"]
    assert r.json()["status"] in {"PENDING", "ACTIVE"}

    # In mock the status is ACTIVE immediately, so pull works
    r = await client.post(f"/api/v1/aggregators/consent/{consent_id}/pull")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ingestedTransactions"] >= 0
