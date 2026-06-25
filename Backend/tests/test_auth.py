"""Tests for /api/v1/auth endpoints"""
import pytest
from tests.conftest import uid


# ── Unit tests (no real DB) ─────────────────────────────────────────────────

def test_register_missing_email(unit_client):
    r = unit_client.post("/api/v1/auth/register", json={"password": "Test1234!"})
    assert r.status_code == 422


def test_register_weak_password(unit_client):
    r = unit_client.post("/api/v1/auth/register", json={
        "email": "x@x.com", "password": "abc"
    })
    assert r.status_code == 422


def test_register_invalid_role(unit_client):
    r = unit_client.post("/api/v1/auth/register", json={
        "email": "x@x.com", "password": "Test1234!", "role": "god_mode"
    })
    assert r.status_code == 422


def test_login_requires_form_fields(unit_client):
    # JSON body should be rejected (expects form encoding)
    r = unit_client.post("/api/v1/auth/token", json={"username": "a@b.com", "password": "x"})
    assert r.status_code == 422


def test_refresh_missing_token(unit_client):
    r = unit_client.post("/api/v1/auth/refresh", json={})
    assert r.status_code == 422


def test_forgot_password_missing_email(unit_client):
    r = unit_client.post("/api/v1/auth/forgot-password", json={})
    assert r.status_code == 422


def test_reset_password_missing_fields(unit_client):
    r = unit_client.post("/api/v1/auth/reset-password", json={"token": "abc"})
    assert r.status_code == 422


# ── Integration tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
async def test_register_and_login(client):
    email = f"auth_{uid()}@portflow.io"
    # Register
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Test1234!", "full_name": "Auth Tester", "role": "readonly"
    })
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == email
    assert data["role"] == "readonly"

    # Login
    r = await client.post("/api/v1/auth/token",
        data={"username": email, "password": "Test1234!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert r.status_code == 200
    tokens = r.json()
    assert tokens["access_token"]
    assert tokens["token_type"] == "bearer"
    return tokens["access_token"], tokens.get("refresh_token")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_me_endpoint(client):
    email = f"me_{uid()}@portflow.io"
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Test1234!", "full_name": "Me Tester", "role": "readonly"
    })
    r = await client.post("/api/v1/auth/token",
        data={"username": email, "password": "Test1234!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = r.json()["access_token"]

    me = await client.get("/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == email


@pytest.mark.asyncio
@pytest.mark.integration
async def test_change_password(client):
    email = f"pw_{uid()}@portflow.io"
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "OldPass1!", "full_name": "PW Tester", "role": "readonly"
    })
    r = await client.post("/api/v1/auth/token",
        data={"username": email, "password": "OldPass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # Change password
    r = await client.post("/api/v1/auth/me/change-password", json={
        "current_password": "OldPass1!", "new_password": "NewPass2!"
    }, headers=auth)
    assert r.status_code == 204

    # Old password fails
    r = await client.post("/api/v1/auth/token",
        data={"username": email, "password": "OldPass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert r.status_code == 401

    # New password works
    r = await client.post("/api/v1/auth/token",
        data={"username": email, "password": "NewPass2!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert r.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration
async def test_api_key_lifecycle(client):
    email = f"key_{uid()}@portflow.io"
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Test1234!", "full_name": "Key Tester", "role": "port_manager"
    })
    r = await client.post("/api/v1/auth/token",
        data={"username": email, "password": "Test1234!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # Create key
    r = await client.post("/api/v1/auth/me/api-keys",
        json={"name": "test-key"}, headers=auth
    )
    assert r.status_code == 201
    key = r.json()
    assert key["name"] == "test-key"
    key_id = key["id"]

    # List keys
    r = await client.get("/api/v1/auth/me/api-keys", headers=auth)
    assert r.status_code == 200
    assert any(k["id"] == key_id for k in r.json())

    # Delete key
    r = await client.delete(f"/api/v1/auth/me/api-keys/{key_id}", headers=auth)
    assert r.status_code in (200, 204)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_forgot_password_always_202(client):
    """Forgot-password always 202 regardless of whether email exists (security)."""
    r = await client.post("/api/v1/auth/forgot-password",
        json={"email": "doesnotexist@example.com"}
    )
    assert r.status_code == 202


@pytest.mark.asyncio
@pytest.mark.integration
async def test_protected_endpoint_rejects_no_token(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
async def test_protected_endpoint_rejects_bad_token(client):
    r = await client.get("/api/v1/auth/me",
        headers={"Authorization": "Bearer totallyinvalidtoken"}
    )
    assert r.status_code == 401
