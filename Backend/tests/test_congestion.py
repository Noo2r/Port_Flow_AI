"""
Tests for /api/v1/congestion endpoints (Stage 3 — Congestion Forecast).

These hit the real congestion_predictor singleton (no mocking of the model
itself) via unit_client's mocked DB session — /predict, /model-info, and
/evaluation are pure ML inference with no DB dependency, so they exercise
real model behavior safely without touching the database.
"""
import pytest


# ── /predict ────────────────────────────────────────────────────────────────────

def test_predict_with_defaults(unit_client):
    r = unit_client.post("/api/v1/congestion/predict", json={})
    assert r.status_code == 200
    data = r.json()
    assert 0.0 <= data["congestion_level"] <= 1.0
    assert data["queue_length"] >= 0
    assert data["congestion_label"] in ("Low", "Medium", "High", "Critical")
    assert data["port_id"] == "PORT_A"  # schema default


def test_predict_returns_top_factors(unit_client):
    r = unit_client.post("/api/v1/congestion/predict", json={})
    assert r.status_code == 200
    factors = r.json()["top_factors"]
    assert isinstance(factors, list)
    assert len(factors) > 0
    assert "feature" in factors[0]


def test_predict_invalid_vessel_type_falls_back_to_container(unit_client):
    """The endpoint's field_validator normalizes unknown vessel types instead
    of rejecting them (matches VESSEL_TYPE_MAP's fallback behavior)."""
    r = unit_client.post("/api/v1/congestion/predict", json={"vessel_type": "submarine"})
    assert r.status_code == 200  # not 422 — validator silently normalizes


def test_predict_invalid_traffic_density_falls_back_to_medium(unit_client):
    r = unit_client.post("/api/v1/congestion/predict", json={"traffic_density": "extreme"})
    assert r.status_code == 200
    assert r.json() is not None


def test_predict_out_of_range_value_rejected(unit_client):
    r = unit_client.post("/api/v1/congestion/predict", json={"port_congestion_index": 5.0})
    assert r.status_code == 422  # outside Field(..., ge=0, le=1)


def test_predict_higher_congestion_input_does_not_lower_forecast(unit_client):
    """Sanity check the live endpoint end-to-end, mirroring the direct-model
    test in congestion_forecaster/tests/test_predictor.py."""
    low = unit_client.post("/api/v1/congestion/predict", json={"port_congestion_index": 0.1}).json()
    high = unit_client.post("/api/v1/congestion/predict", json={"port_congestion_index": 0.9}).json()
    assert high["congestion_level"] >= low["congestion_level"]


# ── /model-info ───────────────────────────────────────────────────────────────

def test_model_info_shape(unit_client):
    r = unit_client.get("/api/v1/congestion/model-info")
    assert r.status_code == 200
    data = r.json()
    assert "congestion_model_name" in data
    assert "queue_model_name" in data
    assert "feature_importance" in data
    assert "congestion" in data["feature_importance"]
    assert "queue" in data["feature_importance"]


# ── /evaluation ───────────────────────────────────────────────────────────────

def test_evaluation_describes_three_stage_pipeline(unit_client):
    r = unit_client.get("/api/v1/congestion/evaluation")
    assert r.status_code == 200
    data = r.json()
    assert "models" in data
    assert "congestion" in data["models"]
    assert "queue" in data["models"]
    assert "Stage 1" in data["pipeline"] and "Stage 3" in data["pipeline"]


def test_evaluation_grades_are_consistent_with_r2(unit_client):
    r = unit_client.get("/api/v1/congestion/evaluation")
    data = r.json()["models"]
    if data["congestion"]["R2"] >= 0.90:
        assert data["congestion"]["grade"] == "Excellent"
    if data["queue"]["R2"] >= 0.50:
        assert data["queue"]["grade"] == "Good"


# ── /port-overview ────────────────────────────────────────────────────────────

def test_port_overview_empty_db_returns_empty_list(unit_client):
    """unit_client's mocked DB has no ports by default — endpoint must
    degrade gracefully rather than error."""
    r = unit_client.get("/api/v1/congestion/port-overview")
    assert r.status_code == 200
    data = r.json()
    assert data["ports"] == []
    assert data["count"] == 0
    assert "generated" in data
