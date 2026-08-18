"""Tests for /api/v1/ops endpoints (AIS, weather impact, conflict detection)"""
import pytest
from datetime import datetime, timezone, timedelta
from tests.conftest import uid


def _future(hours=4) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Unit tests ───────────────────────────────────────────────────────────────

def test_ais_update_missing_fields(auth_unit_client):
    r = auth_unit_client.post("/api/v1/ops/visits/1/ais", json={})
    assert r.status_code == 422


def test_ais_update_invalid_lat(auth_unit_client):
    r = auth_unit_client.post("/api/v1/ops/visits/1/ais", json={
        "latitude": 9999, "longitude": 30.0, "speed_knots": 12.0,
        "heading": 180.0, "timestamp": datetime.now(timezone.utc).isoformat()
    })
    assert r.status_code == 422


def test_ais_update_invalid_lon(auth_unit_client):
    r = auth_unit_client.post("/api/v1/ops/visits/1/ais", json={
        "latitude": 31.0, "longitude": 9999, "speed_knots": 12.0,
        "heading": 180.0, "timestamp": datetime.now(timezone.utc).isoformat()
    })
    assert r.status_code == 422


def test_ais_update_requires_auth(unit_client):
    r = unit_client.post("/api/v1/ops/visits/1/ais", json={
        "latitude": 31.0, "longitude": 29.9, "speed_knots": 12.0,
        "heading": 180.0, "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    assert r.status_code == 401


# ── Integration tests ────────────────────────────────────────────────────────

@pytest.fixture
async def _ops_visit(client):
    u = uid()
    vr = await client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{u}", "name": "Ops Test Vessel",
        "vessel_type": "tanker", "flag": "EG",
    })
    vessel_id = vr.json()["id"]
    visit_r = await client.post("/api/v1/visits/", json={
        "vessel_id": vessel_id, "status": "scheduled", "eta": _future(8),
    })
    return vessel_id, visit_r.json()["id"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ais_update_live(auth_client):
    u = uid()
    vr = await auth_client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{u}", "name": "AIS Vessel",
        "vessel_type": "tanker", "flag": "EG",
    })
    vessel_id = vr.json()["id"]
    visit_r = await auth_client.post("/api/v1/visits/", json={
        "vessel_id": vessel_id, "status": "scheduled", "eta": _future(8),
    })
    visit_id = visit_r.json()["id"]

    r = await auth_client.post(f"/api/v1/ops/visits/{visit_id}/ais", json={
        "latitude": 31.2001, "longitude": 29.9187,
        "speed_knots": 14.5, "heading": 270.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    assert r.status_code == 200
    data = r.json()
    assert data["vessel_id"] == vessel_id
    assert abs(data["latitude"] - 31.2001) < 0.001
    assert abs(data["longitude"] - 29.9187) < 0.001
    assert data["speed_knots"] == 14.5


@pytest.mark.asyncio
@pytest.mark.integration
async def test_weather_impact_live(auth_client):
    u = uid()
    vr = await auth_client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{u}", "name": "Weather Vessel",
        "vessel_type": "bulk_carrier", "flag": "EG",
    })
    vessel_id = vr.json()["id"]
    visit_r = await auth_client.post("/api/v1/visits/", json={
        "vessel_id": vessel_id, "status": "scheduled", "eta": _future(12),
    })
    visit_id = visit_r.json()["id"]

    r = await auth_client.get(f"/api/v1/ops/visits/{visit_id}/weather-impact")
    assert r.status_code == 200
    data = r.json()
    assert data["visit_id"] == visit_id
    assert "delay_hours" in data
    assert "weather_factor" in data
    assert isinstance(data["delay_hours"], (int, float))


@pytest.mark.asyncio
@pytest.mark.integration
async def test_conflict_detection_live(client):
    """Conflict detection on an existing berth returns well-formed response.
    GET endpoint — unauthenticated client is fine (read-only, not being protected)."""
    r = await client.get("/api/v1/ops/berths/1/conflicts")
    assert r.status_code == 200
    data = r.json()
    assert "berth_id" in data
    assert "conflicts" in data
    assert isinstance(data["conflicts"], list)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ais_update_not_found(auth_client):
    r = await auth_client.post("/api/v1/ops/visits/999999/ais", json={
        "latitude": 31.0, "longitude": 29.9,
        "speed_knots": 10.0, "heading": 90.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    assert r.status_code == 404
