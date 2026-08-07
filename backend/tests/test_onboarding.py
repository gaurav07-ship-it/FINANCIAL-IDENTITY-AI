"""Onboarding autosave + scored identity round-trip."""
from __future__ import annotations

import pytest


async def _register(client, email: str = "onboard@example.com") -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Sup3rSecret!", "name": "Onboard Me"},
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_onboarding_personal_step_returns_progress(client):
    await _register(client)
    r = await client.post(
        "/api/v1/onboarding/personal",
        json={"name": "Onboard Me", "phone": "+919876543210", "city": "Bengaluru"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["last_step"] >= 2
    assert "next_step" in body


@pytest.mark.asyncio
async def test_income_sources_persisted_and_dna_computed(client):
    await _register(client)
    r = await client.post(
        "/api/v1/onboarding/income-sources",
        json=[
            {"name": "Salaried role", "monthly_income": 80_000, "primary": True},
            {"name": "Gig Platforms", "monthly_income": 30_000, "primary": False},
        ],
    )
    assert r.status_code == 200

    identity = (await client.get("/api/v1/identity/me")).json()
    assert identity["monthlyIncome"] == 110_000
    assert set(identity["sources"]) == {"Salaried role", "Gig Platforms"}

    dna = (await client.get("/api/v1/score/dna")).json()
    assert 0 <= dna["dnaScore"] <= 100
    assert dna["monthlyIncome"] == 110_000
    assert len(dna["clients"]) >= 2


@pytest.mark.asyncio
async def test_twin_simulation_returns_cashflow(client):
    await _register(client)
    r = await client.post(
        "/api/v1/score/twin/simulate",
        json={
            "monthlyIncome": 120_000,
            "sources": ["Salaried role", "Gig Platforms"],
            "gigPlatforms": ["Zomato"],
            "hasPrimaryBank": True,
            "permissionsPush": True,
            "emiMonthly": 20_000,
            "savingsRate": 0.2,
            "horizonMonths": 12,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["cashFlow"] == 120_000 * 12
    assert len(body["months"]) == 12
    assert body["months"][0]["month"] == 1
    assert body["emiImpact"] == 20_000 * 12
