"""Tests for /api/v1/voyages endpoints"""
import pytest
from datetime import datetime, timezone, timedelta
from tests.conftest import uid


def _future(hours=4) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Unit tests ───────────────────────────────────────────────────────────────

def test_list_voyages_empty(unit_client):
    r = unit_client.get("/api/v1/voyages/")
    assert r.status_code == 200
    assert r.json() == []


def test_get_voyage_not_found(mock_db, unit_client):
    from unittest.mock import AsyncMock
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.get("/api/v1/voyages/999")
    assert r.status_code == 404


def test_create_voyage_missing_required(unit_client):
    r = unit_client.post("/api/v1/voyages/", json={})
    assert r.status_code == 422


def test_create_voyage_invalid_status(unit_client):
    r = unit_client.post("/api/v1/voyages/", json={
        "voyage_number": "VOY-BAD", "vessel_id": 1, "status": "flying"
    })
    assert r.status_code == 422


def test_patch_voyage_not_found(mock_db, unit_client):
    from unittest.mock import AsyncMock
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.patch("/api/v1/voyages/999", json={"status": "underway"})
    assert r.status_code == 404


# ── Integration tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
async def test_voyage_crud_lifecycle(client):
    u = uid()
    # Create vessel first
    vr = await client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{u}", "name": "Voyage Test Ship",
        "vessel_type": "container", "flag": "EG",
    })
    assert vr.status_code == 201
    vessel_id = vr.json()["id"]

    # Create voyage
    r = await client.post("/api/v1/voyages/", json={
        "voyage_number": f"VOY-{u}",
        "vessel_id": vessel_id,
        "status": "planned",
        "planned_departure": _future(2),
        "planned_arrival": _future(48),
    })
    assert r.status_code == 201
    voy = r.json()
    voy_id = voy["id"]
    assert voy["status"] == "planned"
    assert voy["voyage_number"] == f"VOY-{u}"

    # Read
    r = await client.get(f"/api/v1/voyages/{voy_id}")
    assert r.status_code == 200
    assert r.json()["vessel_id"] == vessel_id

    # Advance to underway
    r = await client.patch(f"/api/v1/voyages/{voy_id}", json={"status": "underway"})
    assert r.status_code == 200
    assert r.json()["status"] == "underway"

    # Complete it
    r = await client.patch(f"/api/v1/voyages/{voy_id}", json={"status": "completed"})
    assert r.status_code == 200
    assert r.json()["status"] == "completed"

    # List
    r = await client.get("/api/v1/voyages/?limit=1000")
    assert r.status_code == 200
    ids = [v["id"] for v in r.json()]
    assert voy_id in ids

    # 404
    r = await client.get("/api/v1/voyages/999999")
    assert r.status_code == 404
