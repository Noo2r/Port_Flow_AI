"""Tests for /api/v1/berths endpoints"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from tests.conftest import uid

from app.models.berth import Berth, BerthType, BerthStatus


def _berth_mock(id=1):
    b = MagicMock(spec=Berth)
    b.id = id
    b.code = "B-01"
    b.name = "Test Berth"
    b.berth_type = BerthType.CONTAINER
    b.terminal = None
    b.max_length = 300.0
    b.max_beam = None
    b.max_draft = 14.0
    b.max_tonnage = None
    b.has_crane = True
    b.crane_capacity_tons = None
    b.has_pipeline = False
    b.status = BerthStatus.AVAILABLE
    b.is_active = True
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    b.created_at = now
    b.updated_at = now
    return b


# --- Unit tests ---

def test_list_berths_empty(unit_client):
    r = unit_client.get("/api/v1/berths/")
    assert r.status_code == 200
    assert r.json() == []


def test_get_berth_not_found(mock_db, unit_client):
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.get("/api/v1/berths/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Berth not found"


def test_create_berth_missing_fields(unit_client):
    r = unit_client.post("/api/v1/berths/", json={})
    assert r.status_code == 422


def test_create_berth_invalid_type(unit_client):
    r = unit_client.post("/api/v1/berths/", json={
        "code": "X1",
        "name": "Bad Berth",
        "berth_type": "submarine_dock",
        "max_length": 200.0,
        "max_draft": 10.0,
    })
    assert r.status_code == 422


def test_patch_berth_not_found(mock_db, unit_client):
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.patch("/api/v1/berths/999", json={"status": "occupied"})
    assert r.status_code == 404


# --- Integration tests ---

@pytest.mark.asyncio
@pytest.mark.integration
async def test_berth_crud_lifecycle(client):
    code = f"B-{uid()}"
    # Create
    r = await client.post("/api/v1/berths/", json={
        "code": code,
        "name": "Integration Berth",
        "berth_type": "container",
        "max_length": 250.0,
        "max_draft": 13.5,
        "has_crane": True,
    })
    assert r.status_code == 201
    berth = r.json()
    bid = berth["id"]
    assert berth["status"] == "available"
    assert berth["has_crane"] is True

    # Read
    r = await client.get(f"/api/v1/berths/{bid}")
    assert r.status_code == 200
    assert r.json()["code"] == code

    # Update status to occupied
    r = await client.patch(f"/api/v1/berths/{bid}", json={"status": "occupied"})
    assert r.status_code == 200
    assert r.json()["status"] == "occupied"

    # Confirm persisted
    r = await client.get(f"/api/v1/berths/{bid}")
    assert r.json()["status"] == "occupied"

    # 404 on non-existent
    r = await client.get("/api/v1/berths/999999")
    assert r.status_code == 404
