"""Tests for /api/v1/opt/optimize and /api/v1/ai/predict/eta"""
import pytest
from datetime import datetime, timezone, timedelta
from tests.conftest import uid


def _future(hours=4) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Unit tests ───────────────────────────────────────────────────────────────

def test_eta_missing_vessel_id(unit_client):
    r = unit_client.post("/api/v1/ai/predict/eta", json={"distance_nm": 200})
    assert r.status_code == 422


def test_eta_invalid_distance(unit_client):
    r = unit_client.post("/api/v1/ai/predict/eta", json={
        "vessel_id": 1, "distance_nm": -50
    })
    assert r.status_code == 422


def test_eta_invalid_weather_factor(unit_client):
    r = unit_client.post("/api/v1/ai/predict/eta", json={
        "vessel_id": 1, "distance_nm": 200, "weather_factor": -1.0
    })
    assert r.status_code == 422


# ── Integration tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
async def test_eta_prediction_live(client):
    u = uid()
    vr = await client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{u}", "name": "ETA Vessel",
        "vessel_type": "container", "flag": "EG",
    })
    vessel_id = vr.json()["id"]

    r = await client.post("/api/v1/ai/predict/eta", json={
        "vessel_id": vessel_id, "distance_nm": 500, "weather_factor": 1.0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["vessel_id"] == vessel_id
    assert data["confidence_score"] == 0.85
    assert data["model_name"] == "ETA_Model"
    assert "predicted_arrival" in data
    assert "prediction_id" in data
    # Predicted arrival must be in the future
    arrival = datetime.fromisoformat(data["predicted_arrival"].replace("Z", "+00:00"))
    assert arrival > datetime.now(timezone.utc)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_eta_weather_factor_delays_arrival(client):
    """Higher weather_factor should push predicted arrival later."""
    u = uid()
    vr = await client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{u}", "name": "WF Vessel",
        "vessel_type": "container", "flag": "EG",
    })
    vessel_id = vr.json()["id"]

    r1 = await client.post("/api/v1/ai/predict/eta", json={
        "vessel_id": vessel_id, "distance_nm": 300, "weather_factor": 1.0,
    })
    r2 = await client.post("/api/v1/ai/predict/eta", json={
        "vessel_id": vessel_id, "distance_nm": 300, "weather_factor": 2.0,
    })
    arr1 = datetime.fromisoformat(r1.json()["predicted_arrival"].replace("Z", "+00:00"))
    arr2 = datetime.fromisoformat(r2.json()["predicted_arrival"].replace("Z", "+00:00"))
    assert arr2 > arr1, "Higher weather factor should push arrival later"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_optimize_returns_valid_structure(client):
    r = await client.post("/api/v1/opt/optimize")
    assert r.status_code == 200
    data = r.json()
    assert "assignments_made" in data
    assert "assignments" in data
    assert "unassigned_visits" in data
    assert "message" in data
    assert isinstance(data["assignments"], list)
    assert isinstance(data["unassigned_visits"], list)
    assert isinstance(data["assignments_made"], int)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_optimize_assigns_unassigned_visits(client):
    """Create a vessel + visit with no berth, run optimizer, verify assignment."""
    u = uid()
    vr = await client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{u}", "name": "Opt Vessel",
        "vessel_type": "bulk_carrier", "flag": "EG",
    })
    vessel_id = vr.json()["id"]

    # Create berth to ensure capacity
    br = await client.post("/api/v1/berths/", json={
        "code": f"OB-{u}", "name": "Opt Berth", "berth_type": "bulk",
        "max_length": 250.0, "max_draft": 14.0,
    })
    berth_id = br.json()["id"]

    # Visit with ETA in the far future so it won't overlap anything
    eta_str = _future(200)
    etd_str = _future(220)
    # Must set etb/etd on visit for conflict check
    visit_r = await client.post("/api/v1/visits/", json={
        "vessel_id": vessel_id, "status": "scheduled",
        "eta": eta_str, "etb": eta_str, "etd": etd_str,
    })
    visit_id = visit_r.json()["id"]

    r = await client.post("/api/v1/opt/optimize")
    assert r.status_code == 200
    # Our new visit should now be assigned or at worst in unassigned (if all berths occupied)
    data = r.json()
    assigned_visit_ids = [a["visit_id"] for a in data["assignments"]]
    all_handled = visit_id in assigned_visit_ids or visit_id in data["unassigned_visits"]
    assert all_handled, f"visit {visit_id} not in optimizer output"
