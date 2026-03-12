"""Tests for /api/v1/vessels endpoints"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from tests.conftest import uid

from app.main import app
from app.database import get_db
from app.models.vessel import Vessel, VesselType, VesselStatus


def _vessel_mock(id=1, imo="IMO9999999", name="Test Ship"):
    v = MagicMock(spec=Vessel)
    v.id = id
    v.imo_number = imo
    v.mmsi = None
    v.name = name
    v.vessel_type = VesselType.CONTAINER
    v.flag = "EG"
    v.length_overall = 200.0
    v.beam = None
    v.max_draft = 12.0
    v.gross_tonnage = None
    v.deadweight_tonnage = None
    v.status = VesselStatus.AT_SEA
    v.current_lat = None
    v.current_lon = None
    v.current_speed = None
    v.current_heading = None
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    v.created_at = now
    v.updated_at = now
    return v


# --- Unit tests ---

def test_list_vessels_empty(unit_client):
    r = unit_client.get("/api/v1/vessels/")
    assert r.status_code == 200
    assert r.json() == []


def test_list_vessels_returns_items(mock_db, unit_client):
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [_vessel_mock()]))
    )
    r = unit_client.get("/api/v1/vessels/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["imo_number"] == "IMO9999999"


def test_get_vessel_not_found(mock_db, unit_client):
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.get("/api/v1/vessels/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Vessel not found"


def test_create_vessel_missing_required_fields(unit_client):
    r = unit_client.post("/api/v1/vessels/", json={})
    assert r.status_code == 422  # Unprocessable Entity


def test_create_vessel_invalid_type(unit_client):
    r = unit_client.post("/api/v1/vessels/", json={
        "imo_number": "IMO9999999",
        "name": "Bad Ship",
        "vessel_type": "spaceship",  # not a valid enum value
    })
    assert r.status_code == 422


def test_patch_vessel_not_found(mock_db, unit_client):
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.patch("/api/v1/vessels/999", json={"flag": "SA"})
    assert r.status_code == 404


# --- Integration tests ---

@pytest.mark.asyncio
@pytest.mark.integration
async def test_vessel_crud_lifecycle(client):
    imo = f"IMO9{uid()}"
    # Create
    r = await client.post("/api/v1/vessels/", json={
        "imo_number": imo,
        "name": "Integration Vessel",
        "vessel_type": "container",
        "flag": "EG",
        "max_draft": 11.0,
    })
    assert r.status_code == 201
    vessel = r.json()
    vid = vessel["id"]
    assert vessel["status"] == "at_sea"
    assert vessel["flag"] == "EG"

    # Read
    r = await client.get(f"/api/v1/vessels/{vid}")
    assert r.status_code == 200
    assert r.json()["imo_number"] == imo

    # Update
    r = await client.patch(f"/api/v1/vessels/{vid}", json={"flag": "SA", "status": "berthed"})
    assert r.status_code == 200
    updated = r.json()
    assert updated["flag"] == "SA"
    assert updated["status"] == "berthed"

    # Confirm update persisted
    r = await client.get(f"/api/v1/vessels/{vid}")
    assert r.json()["flag"] == "SA"

    # List includes it
    r = await client.get("/api/v1/vessels/")
    assert r.status_code == 200
    ids = [v["id"] for v in r.json()]
    assert vid in ids

    # 404 on non-existent
    r = await client.get("/api/v1/vessels/999999")
    assert r.status_code == 404
