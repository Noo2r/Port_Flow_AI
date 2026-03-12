"""Tests for /api/v1/predictions endpoints"""
import pytest
from tests.conftest import uid


# --- Unit tests ---

def test_list_predictions_empty(unit_client):
    r = unit_client.get("/api/v1/predictions/")
    assert r.status_code == 200
    assert r.json() == []


def test_get_prediction_not_found(mock_db, unit_client):
    from unittest.mock import AsyncMock
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.get("/api/v1/predictions/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Prediction not found"


def test_create_prediction_missing_required(unit_client):
    r = unit_client.post("/api/v1/predictions/", json={})
    assert r.status_code == 422


def test_create_prediction_invalid_type(unit_client):
    r = unit_client.post("/api/v1/predictions/", json={
        "vessel_id": 1,
        "prediction_type": "telepathy",  # invalid
    })
    assert r.status_code == 422


def test_patch_prediction_not_found(mock_db, unit_client):
    from unittest.mock import AsyncMock
    mock_db.get = AsyncMock(return_value=None)
    r = unit_client.patch("/api/v1/predictions/999", json={"status": "completed"})
    assert r.status_code == 404


# --- Integration tests ---

@pytest.mark.asyncio
@pytest.mark.integration
async def test_prediction_crud_lifecycle(client):
    from datetime import datetime, timezone, timedelta

    # Create vessel
    vr = await client.post("/api/v1/vessels/", json={
        "imo_number": f"IMO9{uid()}",
        "name": "Prediction Test Vessel",
        "vessel_type": "tanker",
    })
    assert vr.status_code == 201
    vid = vr.json()["id"]

    # Create prediction
    r = await client.post("/api/v1/predictions/", json={
        "vessel_id": vid,
        "prediction_type": "eta",
        "model_name": "xgboost",
        "model_version": "1.0.0",
        "input_features": {"speed": 12.5, "distance_nm": 300},
    })
    assert r.status_code == 201
    pred = r.json()
    pid = pred["id"]
    assert pred["status"] == "pending"
    assert pred["model_name"] == "xgboost"
    assert pred["input_features"]["speed"] == 12.5

    # Simulate model completing — update with result
    predicted_dt = (datetime.now(timezone.utc) + timedelta(hours=25)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = await client.patch(f"/api/v1/predictions/{pid}", json={
        "status": "completed",
        "predicted_datetime": predicted_dt,
        "confidence_score": 0.87,
        "lower_bound": 24.0,
        "upper_bound": 26.0,
    })
    assert r.status_code == 200
    updated = r.json()
    assert updated["status"] == "completed"
    assert updated["confidence_score"] == 0.87

    # Filter by vessel_id
    r = await client.get(f"/api/v1/predictions/?vessel_id={vid}")
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.json())

    # 404 check
    r = await client.get("/api/v1/predictions/999999")
    assert r.status_code == 404
