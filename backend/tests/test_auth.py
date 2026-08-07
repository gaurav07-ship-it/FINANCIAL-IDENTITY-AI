"""E2E auth flow — register, login, logout, refresh."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_register_login_logout_flow(client):
    email = "tester+reg@example.com"
    password = "Sup3rSecret!"

    # register
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Tester"},
    )
    assert r.status_code == 201, r.text
    assert "fia_access" in r.cookies
    assert "fia_refresh" in r.cookies

    # /me should work with the cookie
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == email

    # login again (re-using the same email)
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200

    # logout
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 204

    # /me should now be 401
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    email = "tester+dup@example.com"
    pwd = "Sup3rSecret!"
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "X"})
    assert r.status_code == 201
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "X"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    email = "tester+wp@example.com"
    pwd = "Sup3rSecret!"
    await client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "X"})
    # log out to clear cookies
    await client.post("/api/v1/auth/logout")
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "wrongpassword123"})
    assert r.status_code == 401
