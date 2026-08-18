"""Tests for /api/v1/ports endpoints"""
import pytest
from tests.conftest import uid


# ── Unit tests ───────────────────────────────────────────────────────────────

def test_list_ports_empty(unit_client):
    r = unit_client.get("/api/v1/ports/")
    assert r.status_code == 200
    assert r.json() == []


def test_get_port_not_found(mock_db, unit_client):
    from unittest.mock import AsyncMock
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.get("/api/v1/ports/999")
    assert r.status_code == 404


def test_create_port_missing_required(auth_unit_client):
    r = auth_unit_client.post("/api/v1/ports/", json={})
    assert r.status_code == 422


def test_create_port_missing_name(auth_unit_client):
    r = auth_unit_client.post("/api/v1/ports/", json={"code": "TST", "country": "EG"})
    assert r.status_code == 422


def test_patch_port_not_found(mock_db, auth_unit_client):
    from unittest.mock import AsyncMock
    mock_db.get = AsyncMock(return_value=None)
    r = auth_unit_client.patch("/api/v1/ports/999", json={"city": "Cairo"})
    assert r.status_code == 404


def test_create_port_requires_auth(unit_client):
    r = unit_client.post("/api/v1/ports/", json={
        "code": "UNA", "name": "Unauth Port", "country": "EG",
    })
    assert r.status_code == 401


def test_update_port_requires_auth(unit_client):
    r = unit_client.patch("/api/v1/ports/1", json={"city": "Cairo"})
    assert r.status_code == 401


def test_delete_port_requires_auth(unit_client):
    r = unit_client.delete("/api/v1/ports/1")
    assert r.status_code == 401


# ── Integration tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
async def test_port_crud_lifecycle(auth_client):
    code = f"P{uid()[:4]}"
    # Create
    r = await auth_client.post("/api/v1/ports/", json={
        "code": code, "name": "Integration Port", "country": "EG",
        "city": "Alexandria", "timezone": "Africa/Cairo",
        "latitude": 31.2, "longitude": 29.9,
    })
    assert r.status_code == 201
    port = r.json()
    pid = port["id"]
    assert port["code"] == code
    assert port["country"] == "EG"

    # Read
    r = await auth_client.get(f"/api/v1/ports/{pid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Integration Port"

    # Update
    r = await auth_client.patch(f"/api/v1/ports/{pid}", json={"city": "Cairo"})
    assert r.status_code == 200
    assert r.json()["city"] == "Cairo"

    # List includes it
    r = await auth_client.get("/api/v1/ports/")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert pid in ids

    # 404
    r = await auth_client.get("/api/v1/ports/999999")
    assert r.status_code == 404
