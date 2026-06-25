"""
Congestion Forecaster — Stage 3 Engine
=======================================
Wraps the trained Stage 3 model artifact (LightGBM for congestion level,
CatBoost for queue length).

This is the standalone-package home for the prediction logic, mirroring
how Stage 2's berth-optimization engine lives in berth_optimizer/engine/.
Backend/app/ml/congestion_predictor.py re-exports everything from here so
existing imports (app.api.v1.endpoints.congestion, chat.py) keep working
unchanged — this refactor moves structure only, not behavior. The trained
model artifact itself stays at its original path
(Backend/app/ml/models/congestion_model.pkl); it was not moved or retrained.

Usage
-----
    from congestion_forecaster.engine.predictor import congestion_predictor
    result = congestion_predictor.predict(input_dict)

Singleton is loaded once at module import (thread-safe for async).
"""

from __future__ import annotations

import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Backend/congestion_forecaster/engine/predictor.py -> parents[2] = Backend/
_MODEL_PATH = Path(__file__).resolve().parents[2] / "app" / "ml" / "models" / "congestion_model.pkl"

_DATETIME_COLS    = ["timestamp", "scheduled_eta", "berth_available_from"]
_CATEGORICAL_COLS = ["vessel_type", "port_id", "traffic_density"]

_LEAKAGE_COLS = [
    "congestion_level_future", "queue_length_future",
    "actual_arrival_time", "berth_waiting_time", "berth_conflict_flag",
    "vessel_id", "mmsi", "berth_id", "assigned_berth",
    "timestamp", "scheduled_eta", "berth_available_from",
]

VESSEL_TYPE_MAP = {
    "container":     "Container",    "Container":     "Container",
    "bulk_carrier":  "Bulk Carrier", "Bulk Carrier":  "Bulk Carrier",
    "tanker":        "Tanker",       "Tanker":        "Tanker",
    "ro_ro":         "RoRo",         "RoRo":          "RoRo",
    "general_cargo": "General Cargo","General Cargo": "General Cargo",
    "car_carrier":   "Car Carrier",  "Car Carrier":   "Car Carrier",
    "cruise":        "Cruise",       "Cruise":        "Cruise",
    "feeder":        "Feeder",       "Feeder":        "Feeder",
    "lng_carrier":   "LNG Carrier",  "LNG Carrier":   "LNG Carrier",
    "vlcc":          "VLCC",         "VLCC":          "VLCC",
    "other":         "General Cargo",
}

TRAFFIC_MAP = {"low": "Low", "medium": "Medium", "high": "High",
               "Low": "Low", "Medium": "Medium", "High": "High"}


def _congestion_label(level: float) -> str:
    if level < 0.30:  return "Low"
    if level < 0.55:  return "Medium"
    if level < 0.75:  return "High"
    return "Critical"


def _congestion_color(label: str) -> str:
    return {"Low": "#22c55e", "Medium": "#f59e0b", "High": "#f97316", "Critical": "#ef4444"}[label]


class CongestionPredictor:
    def __init__(self, model_path: Path = _MODEL_PATH):
        self._path = model_path
        self._artifact: dict | None = None
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"Congestion model not found at {self._path}")
        with open(self._path, "rb") as fh:
            self._artifact = pickle.load(fh)

    @property
    def feature_names(self) -> list[str]:
        return self._artifact["feature_names"]

    @property
    def cat_encoders(self) -> dict[str, dict]:
        return self._artifact["cat_encoders"]

    @property
    def cat_indices(self) -> list[int]:
        return self._artifact["cat_indices"]

    @property
    def metrics(self) -> dict:
        return self._artifact["metrics"]

    @property
    def congestion_model_name(self) -> str:
        return self._artifact["congestion_model_name"]

    @property
    def queue_model_name(self) -> str:
        return self._artifact["queue_model_name"]

    @property
    def saved_at(self) -> str:
        return self._artifact.get("saved_at", "")

    @property
    def training_rows(self) -> int:
        return self._artifact.get("training_rows", 0)

    def get_feature_importance(self, target: str = "congestion") -> list[dict]:
        return self._artifact.get("feature_importance", {}).get(target, [])

    # ── Feature engineering (mirrors training pipeline) ────────────────────────

    def _build_features(self, raw: dict) -> pd.DataFrame:
        row = pd.DataFrame([raw.copy()])

        for col in _DATETIME_COLS:
            if col in row.columns:
                row[col] = pd.to_datetime(row[col], utc=True, errors="coerce")

        if "timestamp" in row.columns and "scheduled_eta" in row.columns:
            row["hours_to_eta"] = (
                (row["scheduled_eta"] - row["timestamp"]).dt.total_seconds() / 3600
            ).clip(0, 240).fillna(0)
        else:
            row["hours_to_eta"] = float(raw.get("hours_to_eta", 0))

        if "berth_available_from" in row.columns and "scheduled_eta" in row.columns:
            row["berth_lead_time_h"] = (
                (row["berth_available_from"] - row["scheduled_eta"]).dt.total_seconds() / 3600
            ).clip(-48, 48).fillna(0)
        else:
            row["berth_lead_time_h"] = float(raw.get("berth_lead_time_h", 0))

        # Cyclic encoding (auto-derive from scheduled_eta if not provided)
        now_hour  = raw.get("hour")
        now_month = raw.get("month")
        if now_hour is None:
            now_hour = datetime.now(timezone.utc).hour
        if now_month is None:
            now_month = datetime.now(timezone.utc).month

        row["hour"]  = int(now_hour)
        row["month"] = int(now_month)
        row["hour_sin"]  = float(np.sin(2 * np.pi * int(now_hour)  / 24))
        row["hour_cos"]  = float(np.cos(2 * np.pi * int(now_hour)  / 24))
        row["month_sin"] = float(np.sin(2 * np.pi * int(now_month) / 12))
        row["month_cos"] = float(np.cos(2 * np.pi * int(now_month) / 12))

        def _f(name, default=0.0):
            v = raw.get(name, default)
            return float(v) if v is not None else float(default)

        cong  = _f("port_congestion_index")
        wave  = _f("wave_height_m")
        queue = _f("berth_queue_length", 0)
        age   = _f("vessel_age_years", 10)
        dist  = _f("distance_to_port_nm")
        delay = _f("actual_delay_minutes") or _f("eta_prediction_minutes")
        svc   = _f("estimated_service_time_hours", 12)
        wind  = _f("wind_speed_knots")

        row["wave_x_congestion"]   = wave * cong
        row["queue_x_congestion"]  = queue * cong
        row["age_x_distance"]      = age * dist
        row["delay_x_congestion"]  = delay * cong
        row["queue_load_factor"]   = queue * svc / 24.0
        row["weather_severity"]    = min(wave / 7.0, 1.0) * 0.5 + min(wind / 60.0, 1.0) * 0.5
        row["congestion_momentum"] = delay * queue / 100.0

        # Normalize categorical strings
        if "vessel_type" in row.columns:
            row["vessel_type"] = row["vessel_type"].map(
                lambda v: VESSEL_TYPE_MAP.get(str(v), "Container")
            )
        if "traffic_density" in row.columns:
            row["traffic_density"] = row["traffic_density"].map(
                lambda v: TRAFFIC_MAP.get(str(v), "Medium")
            )
        if "port_id" in row.columns:
            row["port_id"] = row["port_id"].astype(str)

        # Drop leakage
        for c in _LEAKAGE_COLS:
            if c in row.columns:
                row = row.drop(columns=[c])

        return row

    def _encode_for_sklearn(self, row: pd.DataFrame) -> pd.DataFrame:
        row = row.copy()
        for col in _CATEGORICAL_COLS:
            if col not in row.columns:
                continue
            enc = self.cat_encoders.get(col, {})
            val = str(row[col].iloc[0])
            code = enc.get(val, 0)
            row[col] = int(code)
        # Cast all columns to numeric — LightGBM/XGBoost reject object dtype
        for col in row.columns:
            if col not in _CATEGORICAL_COLS:
                row[col] = pd.to_numeric(row[col], errors="coerce").fillna(0.0)
        return row

    def _align(self, row: pd.DataFrame) -> pd.DataFrame:
        for col in self.feature_names:
            if col not in row.columns:
                row[col] = 0
        result = row[self.feature_names]
        # Ensure no object columns remain
        for col in result.columns:
            if result[col].dtype == object:
                result = result.copy()
                result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0.0)
        return result

    def _predict_single(self, model, model_name: str, row: pd.DataFrame) -> float:
        if model_name == "CatBoost":
            from catboost import Pool
            pool = Pool(row, cat_features=self.cat_indices, feature_names=self.feature_names)
            return float(model.predict(pool)[0])
        elif model_name == "XGBoost":
            enc = self._encode_for_sklearn(row)
            return float(model.predict(self._align(enc).values)[0])
        else:  # LightGBM
            enc = self._encode_for_sklearn(row)
            return float(model.predict(self._align(enc))[0])

    # ── Core prediction ────────────────────────────────────────────────────────

    def predict(self, raw: dict[str, Any]) -> dict[str, Any]:
        row = self._build_features(raw)

        # Align to training columns
        row_cat  = self._align(row.copy())        # for CatBoost (strings OK)
        row_enc  = self._align(self._encode_for_sklearn(row.copy()))  # for sklearn

        cong_raw  = self._predict_single(
            self._artifact["congestion_model"],
            self.congestion_model_name,
            row_cat,
        )
        queue_raw = self._predict_single(
            self._artifact["queue_model"],
            self.queue_model_name,
            row_cat,
        )

        cong_level  = round(float(np.clip(cong_raw,  0.0, 1.0)), 4)
        queue_count = max(0, round(float(np.clip(queue_raw, 0, 20))))

        label = _congestion_label(cong_level)
        color = _congestion_color(label)

        # Risk score: weighted combo of congestion + queue pressure
        queue_pressure = float(queue_count) / 20.0
        risk_score = round(float(np.clip(cong_level * 0.70 + queue_pressure * 0.30, 0, 1)), 4)

        # Certainty: how far the prediction lands from the nearest decision boundary.
        # Clear predictions (well inside a zone) score high; borderline ones score low.
        # Boundaries: Low<0.30, Medium<0.55, High<0.75, Critical>=0.75
        _boundaries = [0.30, 0.55, 0.75]
        dist_to_boundary = min(abs(cong_level - b) for b in _boundaries)
        # 0.125 = half the width of the smallest zone (Medium: 0.55-0.30=0.25)
        boundary_certainty = min(dist_to_boundary / 0.125, 1.0)
        # Blend with model R² so a great model anchors the floor
        cong_r2 = self.metrics["congestion"]["R2"]
        confidence = round(float(np.clip(boundary_certainty * 0.55 + cong_r2 * 0.45, 0.0, 1.0)), 4)

        top_factors = self.get_feature_importance("congestion")[:5]

        return {
            "congestion_level":   cong_level,
            "congestion_pct":     round(cong_level * 100, 1),
            "congestion_label":   label,
            "congestion_color":   color,
            "queue_length":       queue_count,
            "risk_score":         risk_score,
            "risk_pct":           round(risk_score * 100, 1),
            "confidence":         confidence,
            "top_factors":        top_factors,
            "congestion_model":   self.congestion_model_name,
            "queue_model":        self.queue_model_name,
        }

    def model_info(self) -> dict:
        return {
            "congestion_model_name": self.congestion_model_name,
            "queue_model_name":      self.queue_model_name,
            "features":              len(self.feature_names),
            "training_rows":         self.training_rows,
            "saved_at":              self.saved_at,
            "metrics": {
                "congestion": {
                    **self.metrics["congestion"],
                    "interpretation": "MAE in congestion index units (0–1). MAE=0.038 means predictions off by ±3.8%"
                },
                "queue": {
                    **self.metrics["queue"],
                    "interpretation": "MAE in vessel count. MAE=1.69 means predictions off by ±1.7 vessels"
                },
            },
            "feature_importance": {
                "congestion": self.get_feature_importance("congestion"),
                "queue":      self.get_feature_importance("queue"),
            },
        }


try:
    congestion_predictor = CongestionPredictor()
except Exception as _e:
    import warnings
    warnings.warn(f"Congestion model could not be loaded: {_e}")
    congestion_predictor = None  # type: ignore
