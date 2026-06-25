"""
Tests for the standalone congestion_forecaster package.

These exercise the real trained model artifact (no mocking) — the goal is
to prove the Phase 3 structural refactor (moving the implementation out of
app/ml/congestion_predictor.py into this package) did not change any
prediction behavior, and that the compatibility re-export still works.
"""
import pytest

from congestion_forecaster.engine.predictor import (
    CongestionPredictor,
    VESSEL_TYPE_MAP,
    TRAFFIC_MAP,
    _congestion_label,
    _congestion_color,
    congestion_predictor,
)

SAMPLE_INPUT = {
    "port_id": "PORT_A",
    "vessel_type": "Container",
    "traffic_density": "Medium",
    "port_congestion_index": 0.5,
    "berth_queue_length": 3,
    "wave_height_m": 1.5,
    "wind_speed_knots": 12.0,
    "vessel_age_years": 8.0,
    "distance_to_port_nm": 80.0,
    "estimated_service_time_hours": 12.0,
}


class TestModelLoading:
    def test_singleton_loaded(self):
        assert congestion_predictor is not None

    def test_model_path_points_at_original_artifact(self):
        # Refactor must not move or duplicate the trained model file.
        assert congestion_predictor._path.name == "congestion_model.pkl"
        assert congestion_predictor._path.parent.name == "models"
        assert congestion_predictor._path.exists()


class TestPredict:
    def test_predict_returns_expected_keys(self):
        result = congestion_predictor.predict(SAMPLE_INPUT)
        expected_keys = {
            "congestion_level", "congestion_pct", "congestion_label", "congestion_color",
            "queue_length", "risk_score", "risk_pct", "confidence", "top_factors",
            "congestion_model", "queue_model",
        }
        assert expected_keys.issubset(result.keys())

    def test_congestion_level_in_valid_range(self):
        result = congestion_predictor.predict(SAMPLE_INPUT)
        assert 0.0 <= result["congestion_level"] <= 1.0
        assert 0.0 <= result["congestion_pct"] <= 100.0

    def test_queue_length_is_nonnegative_integer(self):
        result = congestion_predictor.predict(SAMPLE_INPUT)
        assert isinstance(result["queue_length"], int)
        assert result["queue_length"] >= 0

    def test_congestion_label_matches_level(self):
        result = congestion_predictor.predict(SAMPLE_INPUT)
        assert result["congestion_label"] == _congestion_label(result["congestion_level"])

    def test_congestion_color_matches_label(self):
        result = congestion_predictor.predict(SAMPLE_INPUT)
        assert result["congestion_color"] == _congestion_color(result["congestion_label"])

    def test_confidence_in_valid_range(self):
        result = congestion_predictor.predict(SAMPLE_INPUT)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_prediction_is_deterministic(self):
        """Same input must produce the same output — pure inference, no randomness."""
        r1 = congestion_predictor.predict(SAMPLE_INPUT)
        r2 = congestion_predictor.predict(SAMPLE_INPUT)
        assert r1 == r2

    def test_higher_congestion_index_does_not_decrease_predicted_congestion(self):
        """Sanity check on model direction: more current congestion shouldn't
        predict a lower future congestion level, all else equal."""
        low = congestion_predictor.predict({**SAMPLE_INPUT, "port_congestion_index": 0.1})
        high = congestion_predictor.predict({**SAMPLE_INPUT, "port_congestion_index": 0.9})
        assert high["congestion_level"] >= low["congestion_level"]


class TestLabelBoundaries:
    @pytest.mark.parametrize("level,expected", [
        (0.0, "Low"), (0.29, "Low"),
        (0.30, "Medium"), (0.54, "Medium"),
        (0.55, "High"), (0.74, "High"),
        (0.75, "Critical"), (1.0, "Critical"),
    ])
    def test_label_boundaries(self, level, expected):
        assert _congestion_label(level) == expected

    def test_every_label_has_a_color(self):
        for label in ["Low", "Medium", "High", "Critical"]:
            assert _congestion_color(label).startswith("#")


class TestModelInfo:
    def test_model_info_shape(self):
        info = congestion_predictor.model_info()
        assert "congestion_model_name" in info
        assert "queue_model_name" in info
        assert "metrics" in info
        assert "congestion" in info["metrics"]
        assert "queue" in info["metrics"]
        assert "feature_importance" in info


class TestVesselTypeNormalization:
    def test_known_lowercase_type_maps_to_titlecase(self):
        assert VESSEL_TYPE_MAP["container"] == "Container"
        assert VESSEL_TYPE_MAP["bulk_carrier"] == "Bulk Carrier"

    def test_unknown_type_falls_back_to_general_cargo(self):
        assert VESSEL_TYPE_MAP["other"] == "General Cargo"

    def test_traffic_density_normalization(self):
        assert TRAFFIC_MAP["low"] == "Low"
        assert TRAFFIC_MAP["High"] == "High"


class TestBackwardCompatibility:
    """The old import path must keep working after the Phase 3 refactor."""

    def test_app_ml_module_re_exports_same_singleton(self):
        from app.ml.congestion_predictor import congestion_predictor as legacy_singleton
        assert legacy_singleton is congestion_predictor

    def test_app_ml_module_re_exports_same_class(self):
        from app.ml.congestion_predictor import CongestionPredictor as LegacyClass
        assert LegacyClass is CongestionPredictor

    def test_app_ml_module_re_exports_vessel_type_map(self):
        from app.ml.congestion_predictor import VESSEL_TYPE_MAP as legacy_map
        assert legacy_map is VESSEL_TYPE_MAP
