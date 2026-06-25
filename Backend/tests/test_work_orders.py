"""Tests for work order endpoints"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from tests.conftest import uid
from datetime import datetime, timezone, timedelta


def _future(hours=4) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Unit tests ───────────────────────────────────────────────────────────────

def test_list_work_orders_empty(unit_client):
    r = unit_client.get("/api/v1/work-orders")
    assert r.status_code == 200
    assert r.json() == []


def test_get_work_order_not_found(mock_db, unit_client):
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.get("/api/v1/work-orders/999")
    assert r.status_code == 404


def test_create_work_order_missing_required(mock_db, auth_unit_client):
    r = auth_unit_client.post("/api/v1/work-orders", json={})
    assert r.status_code == 422


def test_create_work_order_invalid_type(mock_db, auth_unit_client):
    r = auth_unit_client.post("/api/v1/work-orders", json={
        "visit_id": 1, "vessel_id": 1, "order_type": "alien_docking", "title": "Test"
    })
    assert r.status_code == 422


def test_patch_work_order_not_found(mock_db, auth_unit_client):
    mock_db.get = AsyncMock(return_value=None)
    r = auth_unit_client.patch("/api/v1/work-orders/999", json={"status": "in_progress"})
    assert r.status_code == 404


def test_list_visit_work_orders_empty(unit_client):
    r = unit_client.get("/api/v1/visits/999/work-orders")
    assert r.status_code == 200
    assert r.json() == []


# ── Integration tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
async def test_auto_create_work_orders(auth_client):
    u = uid()
    vr = await auth_client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{u}", "name": "WO Auto Vessel",
        "vessel_type": "general_cargo", "flag": "EG",
    })
    vessel_id = vr.json()["id"]

    br = await auth_client.post("/api/v1/berths/", json={
        "code": f"WA-{u}", "name": "WO Auto Berth", "berth_type": "general",
        "max_length": 250.0, "max_draft": 12.0,
    })
    berth_id = br.json()["id"]

    visit_r = await auth_client.post("/api/v1/visits/", json={
        "vessel_id": vessel_id, "status": "scheduled",
        "eta": _future(6), "etd": _future(24),
    })
    visit_id = visit_r.json()["id"]
    await auth_client.patch(f"/api/v1/visits/{visit_id}", json={"berth_id": berth_id})

    # Auto-create
    r = await auth_client.post(f"/api/v1/visits/{visit_id}/work-orders/auto")
    assert r.status_code == 201
    orders = r.json()
    assert len(orders) == 8  # standard set

    types = {o["order_type"] for o in orders}
    assert "pilotage" in types
    assert "mooring" in types
    assert "customs_inspection" in types
    assert "cargo_handling" in types
    assert "unmooring" in types

    # Idempotent: second call returns same 8 orders
    r2 = await auth_client.post(f"/api/v1/visits/{visit_id}/work-orders/auto")
    assert r2.status_code == 201
    assert len(r2.json()) == 8


@pytest.mark.asyncio
@pytest.mark.integration
async def test_work_order_status_lifecycle(auth_client):
    """PENDING → IN_PROGRESS (actual_start stamped) → COMPLETED (actual_end stamped)."""
    u = uid()
    vr = await auth_client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{u}", "name": "WO Status Vessel",
        "vessel_type": "general_cargo", "flag": "EG",
    })
    vessel_id = vr.json()["id"]
    br = await auth_client.post("/api/v1/berths/", json={
        "code": f"WS-{u}", "name": "WO Status Berth", "berth_type": "general",
        "max_length": 250.0, "max_draft": 12.0,
    })
    berth_id = br.json()["id"]
    visit_r = await auth_client.post("/api/v1/visits/", json={
        "vessel_id": vessel_id, "status": "scheduled",
        "eta": _future(6), "etd": _future(24),
    })
    visit_id = visit_r.json()["id"]
    await auth_client.patch(f"/api/v1/visits/{visit_id}", json={"berth_id": berth_id})
    orders_r = await auth_client.post(f"/api/v1/visits/{visit_id}/work-orders/auto")
    assert orders_r.status_code == 201
    orders = orders_r.json()
    order_id = orders[0]["id"]

    # Start
    r = await auth_client.patch(f"/api/v1/work-orders/{order_id}", json={"status": "in_progress"})
    assert r.status_code == 200
    started = r.json()
    assert started["status"] == "in_progress"
    assert started["actual_start"] is not None   # auto-stamped ✓

    # Complete with notes
    r = await auth_client.patch(f"/api/v1/work-orders/{order_id}", json={
        "status": "completed", "completion_notes": "All done"
    })
    assert r.status_code == 200
    done = r.json()
    assert done["status"] == "completed"
    assert done["actual_end"] is not None        # auto-stamped ✓
    assert done["completion_notes"] == "All done"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_auto_create_requires_berth(auth_client):
    """Auto-create should 409 if visit has no berth assigned."""
    u = uid()
    vr = await auth_client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{u}", "name": "No Berth Vessel",
        "vessel_type": "general_cargo", "flag": "EG",
    })
    visit_r = await auth_client.post("/api/v1/visits/", json={
        "vessel_id": vr.json()["id"], "status": "scheduled", "eta": _future(6),
    })
    r = await auth_client.post(f"/api/v1/visits/{visit_r.json()['id']}/work-orders/auto")
    assert r.status_code == 409
