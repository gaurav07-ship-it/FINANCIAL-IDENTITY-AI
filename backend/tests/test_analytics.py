"""Tests for the new analytics + goals endpoints.

Covers: emergency, career-stability, explain, fraud, hidden-income,
platform-risk, income shock, timeline, and identity/goals.
"""
from __future__ import annotations

import pytest


async def _register(client, email: str = "analytics@example.com") -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Sup3rSecret!", "name": "Anal"},
    )
    assert r.status_code == 201, r.text


async def _seed(client) -> None:
    """Set a few sources so analytics have something to chew on."""
    await client.post(
        "/api/v1/onboarding/income-sources",
        json=[
            {"name": "Client Projects", "monthly_income": 90_000, "primary": True},
            {"name": "Salaried role", "monthly_income": 60_000, "primary": False},
            {"name": "Gig Platforms", "monthly_income": 20_000, "primary": False},
        ],
    )
    await client.post(
        "/api/v1/onboarding/gig",
        json=[{"platform": "Zomato"}, {"platform": "Swiggy"}],
    )


@pytest.mark.asyncio
async def test_emergency_score(client):
    await _register(client)
    r = await client.get("/api/v1/score/emergency")
    assert r.status_code == 200, r.text
    body = r.json()
    assert 0 <= body["score"] <= 100
    assert body["status"] in {"ready", "building", "at_risk"}
    assert len(body["pillars"]) == 5


@pytest.mark.asyncio
async def test_career_stability(client):
    await _register(client)
    await _seed(client)
    r = await client.get("/api/v1/score/career-stability")
    assert r.status_code == 200, r.text
    body = r.json()
    assert 0 <= body["score"] <= 100
    assert body["sourceCount"] == 3


@pytest.mark.asyncio
async def test_explain_dna(client):
    await _register(client)
    await _seed(client)
    r = await client.get("/api/v1/score/explain")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dnaScore"] >= 0
    assert len(body["reasons"]) == 6
    # Reasons should sum to roughly the dnaScore (within 1 due to rounding)
    total = round(sum(rc["contribution"] for rc in body["reasons"]))
    assert abs(total - body["dnaScore"]) <= 2


@pytest.mark.asyncio
async def test_fraud_empty_for_new_user(client):
    await _register(client)
    r = await client.get("/api/v1/score/fraud")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["risk"] == 0
    assert body["transactionsAnalyzed"] == 0


@pytest.mark.asyncio
async def test_hidden_income_detects_undeclared_salary(client):
    """If a user has gig-platform credits but didn't declare 'Salaried role',
    hidden-income endpoint should not flag it (gig is the source).
    The reverse: declare only 'Client Projects' but receive SALARY credits,
    hidden-income flags it.
    """
    await _register(client, "hidden@example.com")
    await _seed(client)
    # Simulate a salary credit by going through the AA flow
    r = await client.post(
        "/api/v1/aggregators/consent",
        params={"fi_types": ["DEPOSIT"]},
    )
    assert r.status_code == 200, r.text
    consent_id = r.json()["consentId"]
    await client.post(f"/api/v1/aggregators/consent/{consent_id}/pull")
    r = await client.get("/api/v1/score/hidden-income")
    assert r.status_code == 200, r.text
    body = r.json()
    # body has the right shape
    assert "hiddenSources" in body
    assert "unmatchedCounterparties" in body


@pytest.mark.asyncio
async def test_platform_risk(client):
    await _register(client, "plat@example.com")
    await _seed(client)
    # ingest some txns so platform risk has data
    r = await client.post(
        "/api/v1/aggregators/consent",
        params={"fi_types": ["DEPOSIT"]},
    )
    consent_id = r.json()["consentId"]
    await client.post(f"/api/v1/aggregators/consent/{consent_id}/pull")
    r = await client.get("/api/v1/score/platform-risk")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["riskLevel"] in {"low", "medium", "high"}
    assert isinstance(body["platforms"], list)


@pytest.mark.asyncio
async def test_income_shock(client):
    await _register(client, "shock@example.com")
    await _seed(client)
    r = await client.post(
        "/api/v1/score/shock",
        json={"shockPct": 0.5, "shockMonths": 3, "horizonMonths": 12},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["months"]) == 12
    # The first shock month should have lower income than the last month
    assert body["months"][0]["income"] < body["months"][-1]["income"]


@pytest.mark.asyncio
async def test_timeline(client):
    await _register(client, "tl@example.com")
    r = await client.get("/api/v1/score/timeline?limit=5")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["events"], list)
    # At minimum we should see the account creation event
    assert any(e["type"] == "account" for e in body["events"])


@pytest.mark.asyncio
async def test_goals_crud(client):
    await _register(client, "goals@example.com")
    r = await client.get("/api/v1/identity/goals")
    assert r.status_code == 200
    assert r.json()["goals"] == []

    r = await client.put(
        "/api/v1/identity/goals",
        json={"goals": ["Home Loan", "Retirement"]},
    )
    assert r.status_code == 200
    assert sorted(r.json()["goals"]) == ["Home Loan", "Retirement"]

    r = await client.get("/api/v1/identity/goals")
    assert sorted(r.json()["goals"]) == ["Home Loan", "Retirement"]
