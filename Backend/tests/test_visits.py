"""Tests for /api/v1/visits endpoints"""
import pytest
from datetime import datetime, timezone, timedelta
from tests.conftest import uid


def _future_dt(days=2) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Unit tests ---

def test_list_visits_empty(unit_client):
    r = unit_client.get("/api/v1/visits/")
    assert r.status_code == 200
    assert r.json() == []


def test_get_visit_not_found(mock_db, unit_client):
    from unittest.mock import AsyncMock
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.get("/api/v1/visits/999")
    assert r.status_code == 404
    assert r.json()["error"] == "Visit not found"


def test_create_visit_missing_required(unit_client):
    r = unit_client.post("/api/v1/visits/", json={})
    assert r.status_code == 422


def test_create_visit_invalid_cargo_type(unit_client):
    r = unit_client.post("/api/v1/visits/", json={
        "vessel_id": 1,
        "berth_id": 1,
        "eta": _future_dt(),
        "cargo_type": "antimatter",  # invalid
        "cargo_quantity": 100.0,
        "cargo_unit": "tons",
    })
    assert r.status_code == 422


def test_patch_visit_not_found(mock_db, unit_client):
    from unittest.mock import AsyncMock
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.patch("/api/v1/visits/999", json={"status": "in_port"})
    assert r.status_code == 404


# --- Integration tests ---

@pytest.mark.asyncio
@pytest.mark.integration
async def test_visit_crud_lifecycle(client):
    u = uid()
    # Prerequisite: create vessel + berth
    vessel_r = await client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{u}",
        "name": "Visit Test Vessel",
        "vessel_type": "bulk_carrier",
    })
    assert vessel_r.status_code == 201
    vid = vessel_r.json()["id"]

    berth_r = await client.post("/api/v1/berths/", json={
        "code": f"BV-{u}",
        "name": "Visit Test Berth",
        "berth_type": "bulk",
        "max_length": 200.0,
        "max_draft": 12.0,
    })
    assert berth_r.status_code == 201
    bid = berth_r.json()["id"]

    eta = _future_dt(days=3)

    # Create visit
    r = await client.post("/api/v1/visits/", json={
        "vessel_id": vid,
        "berth_id": bid,
        "eta": eta,
        "cargo_type": "bulk_dry",
        "cargo_quantity": 5000.0,
        "cargo_unit": "tons",
        "voyage_number": "VOY-2026-001",
    })
    assert r.status_code == 201
    visit = r.json()
    vsid = visit["id"]
    assert visit["status"] == "scheduled"
    assert visit["voyage_number"] == "VOY-2026-001"

    # Update to in_port with actual arrival
    ata = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = await client.patch(f"/api/v1/visits/{vsid}", json={
        "status": "in_port",
        "ata": ata,
    })
    assert r.status_code == 200
    assert r.json()["status"] == "in_port"
    assert r.json()["ata"] is not None

    # Filter by vessel_id
    r = await client.get(f"/api/v1/visits/?vessel_id={vid}")
    assert r.status_code == 200
    assert any(v["id"] == vsid for v in r.json())

    # 404 check
    r = await client.get("/api/v1/visits/999999")
    assert r.status_code == 404


@pytest.mark.asyncio
@pytest.mark.integration
async def test_berth_status_create_and_delete(client):
    """Creating a visit with a berth_id marks that berth OCCUPIED;
    deleting the visit marks it back to AVAILABLE."""
    u = uid()

    vessel_r = await client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO8{u}",
        "name": "Berth Sync Vessel",
        "vessel_type": "container",
    })
    assert vessel_r.status_code == 201
    vid = vessel_r.json()["id"]

    berth_r = await client.post("/api/v1/berths/", json={
        "code": f"BS-{u}",
        "name": "Berth Sync Test",
        "berth_type": "container",
        "max_length": 300.0,
        "max_draft": 14.0,
    })
    assert berth_r.status_code == 201
    bid = berth_r.json()["id"]
    assert berth_r.json()["status"] == "available"

    # Create visit → berth should become occupied
    visit_r = await client.post("/api/v1/visits/", json={
        "vessel_id": vid,
        "berth_id": bid,
        "eta": _future_dt(days=1),
    })
    assert visit_r.status_code == 201
    vsid = visit_r.json()["id"]

    berth_after_create = await client.get(f"/api/v1/berths/{bid}")
    assert berth_after_create.status_code == 200
    assert berth_after_create.json()["status"] == "occupied"

    # Delete visit → berth should become available again
    del_r = await client.delete(f"/api/v1/visits/{vsid}")
    assert del_r.status_code == 204

    berth_after_delete = await client.get(f"/api/v1/berths/{bid}")
    assert berth_after_delete.status_code == 200
    assert berth_after_delete.json()["status"] == "available"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_berth_status_released_on_completed(client):
    """Patching a visit's status to 'completed' releases its berth back to AVAILABLE."""
    u = uid()

    vessel_r = await client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO7{u}",
        "name": "Completion Vessel",
        "vessel_type": "tanker",
    })
    assert vessel_r.status_code == 201
    vid = vessel_r.json()["id"]

    berth_r = await client.post("/api/v1/berths/", json={
        "code": f"BC-{u}",
        "name": "Completion Berth",
        "berth_type": "tanker",
        "max_length": 250.0,
        "max_draft": 12.0,
    })
    assert berth_r.status_code == 201
    bid = berth_r.json()["id"]

    visit_r = await client.post("/api/v1/visits/", json={
        "vessel_id": vid,
        "berth_id": bid,
        "eta": _future_dt(days=1),
    })
    assert visit_r.status_code == 201
    vsid = visit_r.json()["id"]
    assert (await client.get(f"/api/v1/berths/{bid}")).json()["status"] == "occupied"

    # Complete the visit → berth should become available
    patch_r = await client.patch(f"/api/v1/visits/{vsid}", json={"status": "completed"})
    assert patch_r.status_code == 200

    berth_final = await client.get(f"/api/v1/berths/{bid}")
    assert berth_final.json()["status"] == "available"
