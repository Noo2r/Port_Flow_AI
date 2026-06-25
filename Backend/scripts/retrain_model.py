#!/usr/bin/env python3
"""
Retrain all ETA candidate models and save the best artifact.

Run inside the container:
    docker exec portflow_api python scripts/retrain_model.py

Trains CatBoost, XGBoost, and LightGBM on the 12,000-row dataset.
All three models + full metrics are saved; the lowest-MAE model becomes
the active default. The active model can be changed at runtime via
POST /api/v1/ai/set-active-model without retraining.
"""
from __future__ import annotations

import math
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from lightgbm import LGBMRegressor
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import OrdinalEncoder

sys.path.insert(0, "/app")

CSV_PATH   = "/tmp/port_flow_dataset.csv"
MODEL_OUT  = Path("/app/app/ml/models/eta_best_model.pkl")
TARGET_COL = "actual_delay_minutes"

LEAKAGE_COLS = [
    "actual_delay_minutes", "actual_arrival_time", "berth_waiting_time",
    "berth_conflict_flag", "congestion_level_future", "queue_length_future",
    "assigned_berth", "berth_id", "vessel_id", "mmsi",
    "timestamp", "scheduled_eta", "berth_available_from",
]
DATETIME_COLS    = ["timestamp", "scheduled_eta", "berth_available_from"]
CATEGORICAL_COLS = ["vessel_type", "port_id", "traffic_density"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in DATETIME_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")

    if "timestamp" in df.columns and "scheduled_eta" in df.columns:
        df["hours_to_eta"] = (
            (df["scheduled_eta"] - df["timestamp"]).dt.total_seconds() / 3600
        ).clip(lower=0)
    else:
        df["hours_to_eta"] = 0.0

    if "berth_available_from" in df.columns and "scheduled_eta" in df.columns:
        df["berth_lead_time_h"] = (
            (df["berth_available_from"] - df["scheduled_eta"]).dt.total_seconds() / 3600
        ).clip(-48, 48)
    else:
        df["berth_lead_time_h"] = 0.0

    for col in ["hour", "month"]:
        if col in df.columns:
            period = 24 if col == "hour" else 12
            df[f"{col}_sin"] = np.sin(2 * np.pi * df[col] / period)
            df[f"{col}_cos"] = np.cos(2 * np.pi * df[col] / period)

    df["wave_x_congestion"]  = df["wave_height_m"].fillna(0) * df["port_congestion_index"].fillna(0)
    df["queue_x_congestion"] = df["berth_queue_length"].fillna(0) * df["port_congestion_index"].fillna(0)
    df["age_x_distance"]     = df["vessel_age_years"].fillna(10) * df["distance_to_port_nm"].fillna(0)
    df["delay_x_congestion"] = df.get("eta_prediction_minutes", pd.Series(0, index=df.index)).fillna(0) * df["port_congestion_index"].fillna(0)
    df["queue_load_factor"]  = df["berth_queue_length"].fillna(0) * df.get("estimated_service_time_hours", pd.Series(12, index=df.index)).fillna(12) / 24.0
    df["weather_severity"]   = (df["wave_height_m"].fillna(0) / 7.0).clip(0, 1) * 0.5 + (df.get("wind_speed_knots", pd.Series(0, index=df.index)).fillna(0) / 60.0).clip(0, 1) * 0.5
    df["congestion_momentum"] = df["berth_queue_length"].fillna(0) * df["port_congestion_index"].fillna(0) / 100.0

    # Physics-based features — must match eta_predictor.py inference exactly
    speed_safe = df["speed_knots"].fillna(10.0).clip(lower=0.5)
    df["estimated_transit_time_h"] = df["distance_to_port_nm"].fillna(0) / speed_safe
    df["effective_speed"]          = df["speed_knots"].fillna(0) * (1.0 - (df["wave_height_m"].fillna(0) / 15.0 * 0.7).clip(0, 0.7)).clip(lower=0.3)
    df["port_pressure_index"]      = df["berth_queue_length"].fillna(0) / (df["crane_availability_ratio"].fillna(0.8) * 10.0).clip(lower=1.0)

    drop = [c for c in LEAKAGE_COLS if c in df.columns]
    df = df.drop(columns=drop)

    for col in CATEGORICAL_COLS:
        if col in df.columns:
            df[col] = df[col].astype(str)

    return df


def accuracy_within(y_true: np.ndarray, y_pred: np.ndarray, tol: float) -> float:
    return float(np.mean(np.abs(y_true - y_pred) <= tol) * 100)


def eval_metrics(name: str, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = math.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)
    w15  = accuracy_within(y_true, y_pred, 15)
    w30  = accuracy_within(y_true, y_pred, 30)
    bias = float(np.mean(y_pred - y_true))
    print(f"  {name:<14}  MAE={mae:.2f}  RMSE={rmse:.2f}  R²={r2:.4f}  "
          f"±15min={w15:.1f}%  bias={bias:+.2f}")
    return {
        "MAE":            round(mae,  2),
        "RMSE":           round(rmse, 2),
        "R2":             round(r2,   4),
        "within_15_pct":  round(w15,  1),
        "within_30_pct":  round(w30,  1),
        "bias":           round(bias, 2),
    }


def main() -> None:
    print("=" * 70)
    print("  PortFlow AI — Multi-Model ETA Comparison & Best-Model Selection")
    print("=" * 70)

    # ── 1. Load & engineer features ──────────────────────────────────────────
    print(f"\n[1/5] Loading {CSV_PATH}…")
    raw = pd.read_csv(CSV_PATH)
    print(f"      {len(raw):,} rows, {raw.shape[1]} columns")

    y = raw[TARGET_COL].values.astype(float)
    X = build_features(raw)
    feature_names = list(X.columns)
    cat_indices   = [i for i, f in enumerate(feature_names) if f in CATEGORICAL_COLS]
    print(f"      Features after engineering: {len(feature_names)}")

    # ── 2. Train/test split ──────────────────────────────────────────────────
    print("\n[2/5] Splitting 80/20 train/test (stratified by delay quartile)…")
    delay_q = pd.qcut(y, q=4, labels=False, duplicates="drop")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=delay_q
    )
    print(f"      Train: {len(X_train):,}   Test: {len(X_test):,}")

    # Ordinal-encoded versions for sklearn-compatible models
    enc = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    X_train_enc = X_train.copy()
    X_test_enc  = X_test.copy()
    X_train_enc[CATEGORICAL_COLS] = enc.fit_transform(X_train[CATEGORICAL_COLS])
    X_test_enc[CATEGORICAL_COLS]  = enc.transform(X_test[CATEGORICAL_COLS])
    X_train_enc = X_train_enc.astype(float)
    X_test_enc  = X_test_enc.astype(float)

    cat_encoders: dict[str, dict] = {}
    for col in CATEGORICAL_COLS:
        if col in X_train.columns:
            vals = X_train[col].unique()
            cat_encoders[col] = {v: i for i, v in enumerate(sorted(vals))}

    # ── 3. Train all models ───────────────────────────────────────────────────
    print("\n[3/5] Training all candidate models…")
    all_models:  dict[str, object] = {}
    all_metrics: dict[str, dict]   = {}

    # ── CatBoost ──
    print("\n  [CatBoost]")
    train_pool = Pool(X_train, y_train, cat_features=cat_indices, feature_names=feature_names)
    test_pool  = Pool(X_test,  y_test,  cat_features=cat_indices, feature_names=feature_names)
    cb = CatBoostRegressor(
        iterations=3000, depth=9, min_data_in_leaf=8,
        learning_rate=0.03, l2_leaf_reg=2.5, subsample=0.85, colsample_bylevel=0.80,
        bagging_temperature=0.5,
        loss_function="MAE", eval_metric="MAE",
        early_stopping_rounds=150, random_seed=42, verbose=500, task_type="CPU",
        thread_count=-1,
    )
    cb.fit(train_pool, eval_set=test_pool, plot=False)
    cb_pred = cb.predict(test_pool)
    all_models["CatBoost"]  = cb
    all_metrics["CatBoost"] = eval_metrics("CatBoost", y_test, cb_pred)

    # ── XGBoost ──
    print("\n  [XGBoost]")
    xgb = XGBRegressor(
        n_estimators=1000, max_depth=7, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.80, min_child_weight=10,
        reg_alpha=0.1, reg_lambda=3.0, objective="reg:absoluteerror",
        eval_metric="mae", early_stopping_rounds=50,
        random_state=42, n_jobs=-1, verbosity=1,
    )
    xgb.fit(
        X_train_enc, y_train,
        eval_set=[(X_test_enc, y_test)],
        verbose=200,
    )
    xgb_pred = xgb.predict(X_test_enc)
    all_models["XGBoost"]  = xgb
    all_metrics["XGBoost"] = eval_metrics("XGBoost", y_test, xgb_pred)

    # ── LightGBM ──
    print("\n  [LightGBM]")
    lgbm = LGBMRegressor(
        n_estimators=1000, num_leaves=63, max_depth=7,
        learning_rate=0.05, subsample=0.85, colsample_bytree=0.80,
        min_child_samples=10, reg_alpha=0.1, reg_lambda=3.0,
        objective="mae", random_state=42, n_jobs=-1, verbose=-1,
    )
    lgbm.fit(
        X_train_enc, y_train,
        eval_set=[(X_test_enc, y_test)],
        callbacks=[],
    )
    lgbm_pred = lgbm.predict(X_test_enc)
    all_models["LightGBM"]  = lgbm
    all_metrics["LightGBM"] = eval_metrics("LightGBM", y_test, lgbm_pred)

    # ── 4. Pick best by MAE ────────────────────────────────────────────────────
    print("\n[4/5] Selecting best model by MAE…")
    best_name = min(all_metrics, key=lambda n: all_metrics[n]["MAE"])
    best_model = all_models[best_name]
    print(f"\n  {'Model':<14}  {'MAE':>6}  {'R²':>7}  {'±15 min':>8}")
    print(f"  {'-'*40}")
    for name, m in sorted(all_metrics.items(), key=lambda x: x[1]["MAE"]):
        marker = " ← BEST" if name == best_name else ""
        print(f"  {name:<14}  {m['MAE']:>6.2f}  {m['R2']:>7.4f}  {m['within_15_pct']:>7.1f}%{marker}")

    # Feature importance (CatBoost)
    fi_raw = cb.get_feature_importance()
    fi_total = sum(fi_raw)
    feature_importance = sorted(
        [{"feature": f, "importance_pct": round(v / fi_total * 100, 2)}
         for f, v in zip(feature_names, fi_raw)],
        key=lambda x: x["importance_pct"], reverse=True,
    )[:20]

    # ── 5. Save artifact ───────────────────────────────────────────────────────
    print(f"\n[5/5] Saving artifact → {MODEL_OUT}")
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)

    artifact = {
        # Active model (best by MAE) — backward-compatible keys
        "model":         best_model,
        "model_name":    best_name,
        # All candidates
        "all_models":    all_models,
        "all_metrics":   all_metrics,
        # Shared metadata
        "feature_names": feature_names,
        "cat_encoders":  cat_encoders,
        "cat_indices":   cat_indices,
        "ordinal_encoder": enc,
        "feature_importance": feature_importance,
        # Legacy key — kept for backward compat
        "metrics": {best_name: all_metrics[best_name]},
        "saved_at":      datetime.now(timezone.utc).isoformat(),
        "training_rows": len(X_train),
        "test_rows":     len(X_test),
    }

    with open(MODEL_OUT, "wb") as fh:
        pickle.dump(artifact, fh, protocol=5)

    size_kb = MODEL_OUT.stat().st_size / 1024
    print(f"      Saved ({size_kb:.0f} KB)")
    print("\n  ✓ Artifact contains all 3 models. Switch active model at runtime:")
    print("    POST /api/v1/ai/set-active-model  {\"model_name\": \"LightGBM\"}")
    print("\n" + "=" * 70)
    print(f"  BEST → {best_name}  MAE {all_metrics[best_name]['MAE']:.2f} min  "
          f"R² {all_metrics[best_name]['R2']:.4f}  "
          f"±15min {all_metrics[best_name]['within_15_pct']:.1f}%")
    print("=" * 70)


if __name__ == "__main__":
    main()
