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


def test_create_port_missing_required(unit_client):
    r = unit_client.post("/api/v1/ports/", json={})
    assert r.status_code == 422


def test_create_port_missing_name(unit_client):
    r = unit_client.post("/api/v1/ports/", json={"code": "TST", "country": "EG"})
    assert r.status_code == 422


def test_patch_port_not_found(mock_db, unit_client):
    from unittest.mock import AsyncMock
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.patch("/api/v1/ports/999", json={"city": "Cairo"})
    assert r.status_code == 404


# ── Integration tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
async def test_port_crud_lifecycle(client):
    code = f"P{uid()[:4]}"
    # Create
    r = await client.post("/api/v1/ports/", json={
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
    r = await client.get(f"/api/v1/ports/{pid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Integration Port"

    # Update
    r = await client.patch(f"/api/v1/ports/{pid}", json={"city": "Cairo"})
    assert r.status_code == 200
    assert r.json()["city"] == "Cairo"

    # List includes it
    r = await client.get("/api/v1/ports/")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert pid in ids

    # 404
    r = await client.get("/api/v1/ports/999999")
    assert r.status_code == 404
