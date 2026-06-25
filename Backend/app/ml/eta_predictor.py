"""
ETA Predictor — Production ML Module
=====================================
Wraps the trained CatBoost model (MAE ≈ 6.5 min, R² ≈ 0.82).

Usage
-----
    from app.ml.eta_predictor import eta_predictor
    result = eta_predictor.predict(input_dict)

The singleton is loaded once at module import time (thread-safe for async).
"""

from __future__ import annotations

import math
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
_MODEL_PATH = Path(__file__).parent / "models" / "eta_best_model.pkl"

# ── Constants that mirror the training pipeline ────────────────────────────────
_DATETIME_COLS   = ["timestamp", "scheduled_eta", "berth_available_from"]
_CATEGORICAL_COLS = ["vessel_type", "port_id", "traffic_density"]
_LEAKAGE_COLS = [
    "actual_delay_minutes", "actual_arrival_time", "berth_waiting_time",
    "berth_conflict_flag", "congestion_level_future", "queue_length_future",
    "assigned_berth", "berth_id", "vessel_id", "mmsi",
    "timestamp", "scheduled_eta", "berth_available_from",
]

# Map from DB vessel_type enum → model categorical string
VESSEL_TYPE_MAP: dict[str, str] = {
    "container":     "Container",
    "bulk_carrier":  "Bulk Carrier",
    "tanker":        "Tanker",
    "ro_ro":         "RoRo",
    "general_cargo": "General Cargo",
    "other":         "General Cargo",
    # pass-through if already in model format
    "Container":     "Container",
    "Bulk Carrier":  "Bulk Carrier",
    "Tanker":        "Tanker",
    "RoRo":          "RoRo",
    "General Cargo": "General Cargo",
    "Car Carrier":   "Car Carrier",
    "Cruise":        "Cruise",
    "Feeder":        "Feeder",
    "LNG Carrier":   "LNG Carrier",
    "VLCC":          "VLCC",
}


class ETAPredictor:
    """
    Thread-safe, singleton-style ETA prediction wrapper.
    Loaded once at startup; predict() is pure (no side effects).
    Active model can be switched at runtime via set_active_model().
    """

    def __init__(self, model_path: Path = _MODEL_PATH):
        self._path = model_path
        self._artifact: dict | None = None
        self._active_model_name: str | None = None
        self._load()

    # ── Loading ────────────────────────────────────────────────────────────────
    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"ETA model not found at {self._path}")
        with open(self._path, "rb") as fh:
            self._artifact = pickle.load(fh)
        self._active_model_name = self._artifact["model_name"]

    @property
    def model_name(self) -> str:
        return self._active_model_name or self._artifact["model_name"]

    @property
    def available_models(self) -> list[str]:
        return list(self._artifact.get("all_models", {self._artifact["model_name"]: None}).keys())

    def set_active_model(self, name: str) -> None:
        all_models = self._artifact.get("all_models", {})
        if all_models and name not in all_models:
            raise ValueError(f"Model '{name}' not found. Available: {list(all_models.keys())}")
        if all_models:
            self._artifact["model"] = all_models[name]
        self._active_model_name = name

    @property
    def feature_names(self) -> list[str]:
        return self._artifact["feature_names"]

    @property
    def cat_encoders(self) -> dict[str, dict]:
        return self._artifact["cat_encoders"]

    @property
    def metrics(self) -> dict[str, dict]:
        # Return all_metrics if available (multi-model artifact), else legacy single-model
        return self._artifact.get("all_metrics") or self._artifact.get("metrics", {})

    @property
    def mae(self) -> float:
        return self.metrics.get(self.model_name, {}).get("MAE", 0.0)

    @property
    def r2(self) -> float:
        """Best model R²."""
        return self.metrics[self.model_name]["R2"]

    @property
    def saved_at(self) -> str:
        return self._artifact.get("saved_at", "")

    @property
    def model_age_days(self) -> int:
        """Days elapsed since the model artifact was saved."""
        try:
            saved = datetime.fromisoformat(self.saved_at)
            now = datetime.now(timezone.utc) if saved.tzinfo else datetime.utcnow()
            return max(0, (now - saved).days)
        except Exception:
            return -1

    @property
    def _cat_feature_indices(self) -> list[int]:
        """Positions of categorical features within feature_names."""
        return [i for i, f in enumerate(self.feature_names) if f in _CATEGORICAL_COLS]

    # ── Global feature importance (for /model-info) ────────────────────────────
    def get_feature_importance(self, top_n: int = 15) -> list[dict]:
        # Use pre-computed importance from multi-model artifact when available
        stored = self._artifact.get("feature_importance")
        if stored:
            return stored[:top_n]

        model = self._artifact["model"]
        if hasattr(model, "get_feature_importance"):
            imp = model.get_feature_importance()
        elif hasattr(model, "feature_importances_"):
            imp = model.feature_importances_
        else:
            return []

        total = sum(imp) or 1.0
        pairs = sorted(zip(self.feature_names, imp), key=lambda x: x[1], reverse=True)
        return [
            {"feature": f, "importance_pct": round(v / total * 100, 2)}
            for f, v in pairs[:top_n]
        ]

    # ── Per-prediction SHAP explanations ──────────────────────────────────────
    def _get_shap_factors(self, row: "pd.DataFrame") -> list[dict]:
        """SHAP via CatBoost's native TreeSHAP; falls back to global importance for other models."""
        if self.model_name == "CatBoost":
            try:
                from catboost import Pool
                model = self._artifact["model"]
                pool = Pool(row, cat_features=self._cat_feature_indices)
                shap_matrix = model.get_feature_importance(data=pool, type="ShapValues")
                shap_vals = shap_matrix[0, :-1]
                pairs = sorted(
                    zip(self.feature_names, shap_vals),
                    key=lambda x: abs(x[1]),
                    reverse=True,
                )[:5]
                return [
                    {
                        "feature": feat,
                        "contribution_minutes": round(float(val), 2),
                        "direction": "increases_delay" if val >= 0 else "reduces_delay",
                    }
                    for feat, val in pairs
                ]
            except Exception:
                pass
        # Fallback: global feature importance
        return [
            {"feature": d["feature"], "contribution_minutes": None, "direction": "unknown"}
            for d in self.get_feature_importance(top_n=5)
        ]

    # ── Core prediction ────────────────────────────────────────────────────────
    def predict(self, raw: dict[str, Any], include_shap: bool = True) -> dict[str, Any]:
        """
        Run the ETA model on a single vessel input dict.

        Parameters
        ----------
        raw : dict
            Must contain the operational fields. See ETAPredictRequest schema.

        Returns
        -------
        dict with:
            predicted_delay_minutes  float
            predicted_eta            str (ISO) or None
            confidence_score         float  (model R²)
            lower_bound_minutes      float
            upper_bound_minutes      float
            model_used               str
            top_factors              list[dict]
        """
        row = pd.DataFrame([raw.copy()])

        # ── 1. Parse datetimes ─────────────────────────────────────────────
        for col in _DATETIME_COLS:
            if col in row.columns:
                row[col] = pd.to_datetime(row[col], utc=True, errors="coerce")

        # ── 2. Temporal features ───────────────────────────────────────────
        if "timestamp" in row.columns and "scheduled_eta" in row.columns:
            row["hours_to_eta"] = (
                (row["scheduled_eta"] - row["timestamp"]).dt.total_seconds() / 3600
            ).clip(lower=0)
        else:
            row["hours_to_eta"] = 0.0

        if "berth_available_from" in row.columns and "scheduled_eta" in row.columns:
            row["berth_lead_time_h"] = (
                (row["berth_available_from"] - row["scheduled_eta"]).dt.total_seconds() / 3600
            ).clip(-48, 48)
        else:
            row["berth_lead_time_h"] = 0.0

        # Auto-derive month / hour / day_of_week from scheduled_eta if missing
        if "scheduled_eta" in row.columns:
            sched = row["scheduled_eta"].iloc[0]
            if pd.notna(sched):
                if "month" not in row.columns or pd.isna(row["month"].iloc[0]):
                    row["month"] = sched.month
                if "hour" not in row.columns or pd.isna(row["hour"].iloc[0]):
                    row["hour"] = sched.hour
                if "day_of_week" not in row.columns or pd.isna(row["day_of_week"].iloc[0]):
                    row["day_of_week"] = sched.weekday()
                if "is_weekend" not in row.columns or pd.isna(row["is_weekend"].iloc[0]):
                    row["is_weekend"] = int(sched.weekday() >= 5)
                if "is_night" not in row.columns or pd.isna(row["is_night"].iloc[0]):
                    row["is_night"] = int(sched.hour < 6 or sched.hour > 20)

        # Cyclic encoding
        if "hour" in row.columns:
            row["hour_sin"] = np.sin(2 * np.pi * row["hour"] / 24)
            row["hour_cos"] = np.cos(2 * np.pi * row["hour"] / 24)
        if "month" in row.columns:
            row["month_sin"] = np.sin(2 * np.pi * row["month"] / 12)
            row["month_cos"] = np.cos(2 * np.pi * row["month"] / 12)

        # ── 3. Interaction features ────────────────────────────────────────
        wave      = float(row.get("wave_height_m",         pd.Series([0.0])).iloc[0] or 0.0)
        cong      = float(row.get("port_congestion_index", pd.Series([0.0])).iloc[0] or 0.0)
        queue     = float(row.get("berth_queue_length",    pd.Series([0  ])).iloc[0] or 0.0)
        age       = float(row.get("vessel_age_years",      pd.Series([10.])).iloc[0] or 10.0)
        dist      = float(row.get("distance_to_port_nm",   pd.Series([0.0])).iloc[0] or 0.0)
        wind      = float(raw.get("wind_speed_knots") or 0.0)
        crane     = float(raw.get("crane_availability_ratio") or 0.8)
        speed_val = float(raw.get("speed_knots") or 10.0)
        service_h = float(raw.get("estimated_service_time_hours") or 12.0)

        # Original interaction features
        row["wave_x_congestion"]  = wave * cong
        row["queue_x_congestion"] = queue * cong
        row["age_x_distance"]     = age * dist

        # 4 features computed in retrain_model.py but missing from inference (bug fix)
        row["delay_x_congestion"]  = 0.0                          # eta_prediction_minutes unavailable at inference
        row["queue_load_factor"]   = queue * service_h / 24.0
        row["weather_severity"]    = min(wave / 7.0, 1.0) * 0.5 + min(wind / 60.0, 1.0) * 0.5
        row["congestion_momentum"] = queue * cong / 100.0

        # Physics-based features (new — must also exist in retrain_model.py)
        speed_safe = max(speed_val, 0.5)
        row["estimated_transit_time_h"] = dist / speed_safe
        row["effective_speed"]          = speed_val * max(1.0 - wave / 15.0 * 0.7, 0.3)
        row["port_pressure_index"]      = queue / max(crane * 10.0, 1.0)

        # ── 4. Map vessel_type to model categories ──────────────────��──────
        if "vessel_type" in row.columns:
            row["vessel_type"] = row["vessel_type"].map(
                lambda v: VESSEL_TYPE_MAP.get(str(v), "Container")
            )

        # ── 5. Drop leakage cols ───────────────────────────────────────────
        for c in _LEAKAGE_COLS:
            if c in row.columns:
                row = row.drop(columns=[c])

        # ── 6. Encode categoricals ─────────────────────────────────────────
        model = self._artifact["model"]
        model_name = self.model_name

        for col in _CATEGORICAL_COLS:
            if col in row.columns:
                if model_name == "CatBoost":
                    row[col] = row[col].astype(str)
                else:
                    # Use OrdinalEncoder from multi-model artifact if available
                    oe = self._artifact.get("ordinal_encoder")
                    if oe is not None:
                        try:
                            row[col] = oe.transform(row[[col]])[:, 0]
                        except Exception:
                            enc = self.cat_encoders.get(col, {})
                            row[col] = row[col].map(enc).fillna(-1).astype(int)
                    else:
                        enc = self.cat_encoders.get(col, {})
                        row[col] = row[col].map(enc).fillna(-1).astype(int)

        # ── 7. Align columns to training feature set ───────────────────────
        for col in self.feature_names:
            if col not in row.columns:
                row[col] = 0
        row = row[self.feature_names]

        # ── 8. Predict ─────────────────────────────────────────────────────
        raw_delay = float(np.clip(model.predict(row)[0], 0, 600))
        delay = round(raw_delay, 1)

        # ── 9. Compute predicted ETA ───────────────────────────────────────
        pred_eta: str | None = None
        sched_str = raw.get("scheduled_eta")
        if sched_str:
            try:
                sched_dt = pd.to_datetime(sched_str, utc=True)
                pred_eta = (sched_dt + timedelta(minutes=delay)).isoformat()
            except Exception:
                pass

        # ── 10. Confidence & bounds ────────────────────────────────────────
        mae  = self.mae
        rmse = self.metrics[self.model_name].get("RMSE", mae * 1.25)

        # Magnitude-scaled bounds: larger delays have wider absolute error.
        # Scale MAE by √(delay / reference_delay) — reference ≈ median training delay.
        _REF_DELAY = 30.0
        scale = math.sqrt(max(delay, 1.0) / _REF_DELAY)
        cong_factor = 1.0 + float(cong)          # 1.0 (calm) – 2.0 (max congestion)

        lower = round(max(0.0, delay - mae * scale * 0.8), 1)
        upper = round(delay + mae * scale * cong_factor, 1)

        # Per-prediction confidence calibrated to empirical accuracy:
        # CatBoost achieves 95.1 % of predictions within ±15 min on real data.
        # Linear penalties per unit, capped at their max contribution.
        # Congestion excluded — it did NOT worsen MAE in live evaluation.
        wave_penalty  = min(float(wave)  * 0.010, 0.07)  # 1 % per metre, max 7 % at ≥7 m
        queue_penalty = min(float(queue) * 0.003, 0.05)  # 0.3 % per vessel, max 5 % at ≥17
        confidence = round(
            max(0.75, min(0.97, 0.951 - wave_penalty - queue_penalty)),
            4,
        )

        # ── 11. SHAP per-prediction explanations ──────────────────────────
        # SHAP (TreeSHAP) is computed per row and is too slow to run for
        # bulk historical backfills (thousands of rows) — callers doing
        # bulk work pass include_shap=False and get the (still real, just
        # global rather than per-row) feature-importance fallback instead.
        shap_factors = self._get_shap_factors(row) if include_shap else [
            {"feature": d["feature"], "contribution_minutes": None, "direction": "unknown"}
            for d in self.get_feature_importance(top_n=5)
        ]

        # ── 12. Model staleness warning ────────────────────────────────────
        staleness: str | None = None
        age = self.model_age_days
        if age > 180:
            staleness = f"Model is {age} days old — consider retraining with recent data."
        elif age > 90:
            staleness = f"Model is {age} days old — retraining recommended soon."

        return {
            "predicted_delay_minutes": delay,
            "predicted_eta":           pred_eta,
            "confidence_score":        confidence,
            "lower_bound_minutes":     lower,
            "upper_bound_minutes":     upper,
            "model_used":              model_name,
            "top_factors":             shap_factors,
            "model_age_days":          age,
            "staleness_warning":       staleness,
        }


# ── Module-level singleton ─────────────────────────────────────────���──────────
try:
    eta_predictor = ETAPredictor()
except Exception as _e:
    import warnings
    warnings.warn(f"ETA model could not be loaded: {_e}")
    eta_predictor = None  # type: ignore
