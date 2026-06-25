"""
Stage 3 — Congestion Forecast Model Training
=============================================
Trains CatBoost, XGBoost, and LightGBM for two targets:
  • congestion_level_future  (float 0-1, regression)
  • queue_length_future      (integer 0-20, regression, rounded at inference)

Selects the best model per target by MAE on a 20% holdout.
Saves a single artifact: /app/app/ml/models/congestion_model.pkl

Run inside the container:
    docker exec portflow_api python scripts/train_congestion.py
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
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBRegressor

sys.path.insert(0, "/app")

MODEL_OUT = Path("/app/app/ml/models/congestion_model.pkl")

TARGET_CONG  = "congestion_level_future"
TARGET_QUEUE = "queue_length_future"

DATETIME_COLS    = ["timestamp", "scheduled_eta", "berth_available_from"]
CATEGORICAL_COLS = ["vessel_type", "port_id", "traffic_density"]

LEAKAGE_COLS = [
    "congestion_level_future", "queue_length_future",
    "actual_arrival_time", "berth_waiting_time", "berth_conflict_flag",
    "vessel_id", "mmsi", "berth_id", "assigned_berth",
    "timestamp", "scheduled_eta", "berth_available_from",
]


# ── 1. Dataset discovery ───────────────────────────────────────────────────────

def _find_dataset() -> Path:
    for p in [
        Path("/tmp/port_flow_dataset.csv"),
        Path("/app/app/ml/port_flow_dataset.csv"),
        Path("/app/port_flow_dataset.csv"),
        Path("/app/berth_optimizer/port_flow_dataset.csv"),
        Path("/app/data/raw/port_flow_dataset.csv"),
    ]:
        if p.exists():
            return p
    raise FileNotFoundError("Dataset not found. Copy via: docker cp port_flow_dataset.csv portflow_api:/tmp/")


# ── 2. Feature engineering ─────────────────────────────────────────────────────

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in DATETIME_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")

    if "timestamp" in df.columns and "scheduled_eta" in df.columns:
        df["hours_to_eta"] = (
            (df["scheduled_eta"] - df["timestamp"]).dt.total_seconds() / 3600
        ).clip(0, 240)
    else:
        df["hours_to_eta"] = 0.0

    if "berth_available_from" in df.columns and "scheduled_eta" in df.columns:
        df["berth_lead_time_h"] = (
            (df["berth_available_from"] - df["scheduled_eta"]).dt.total_seconds() / 3600
        ).clip(-48, 48)
    else:
        df["berth_lead_time_h"] = 0.0

    for col, period in [("hour", 24), ("month", 12)]:
        if col in df.columns:
            df[f"{col}_sin"] = np.sin(2 * np.pi * df[col] / period)
            df[f"{col}_cos"] = np.cos(2 * np.pi * df[col] / period)

    def _s(name, default=0.0):
        return df.get(name, pd.Series(default, index=df.index)).fillna(default)

    cong  = _s("port_congestion_index")
    wave  = _s("wave_height_m")
    queue = _s("berth_queue_length", 0)
    age   = _s("vessel_age_years", 10)
    dist  = _s("distance_to_port_nm")
    delay = _s("actual_delay_minutes")
    svc   = _s("estimated_service_time_hours", 12)
    wind  = _s("wind_speed_knots")

    df["wave_x_congestion"]   = wave * cong
    df["queue_x_congestion"]  = queue * cong
    df["age_x_distance"]      = age * dist
    df["delay_x_congestion"]  = delay * cong
    df["queue_load_factor"]   = queue * svc / 24.0
    df["weather_severity"]    = (wave / 7.0).clip(0, 1) * 0.5 + (wind / 60.0).clip(0, 1) * 0.5
    df["congestion_momentum"] = delay * queue / 100.0

    drop = [c for c in LEAKAGE_COLS if c in df.columns]
    df = df.drop(columns=drop)

    return df


# ── 3. Encode categoricals for XGB/LGBM ───────────────────────────────────────

def encode_for_sklearn(X_tr: pd.DataFrame, X_te: pd.DataFrame):
    """Label-encode categorical columns; returns encoded copies + fitted encoders."""
    X_tr_enc = X_tr.copy()
    X_te_enc = X_te.copy()
    encoders = {}
    for col in CATEGORICAL_COLS:
        if col not in X_tr.columns:
            continue
        le = LabelEncoder()
        X_tr_enc[col] = le.fit_transform(X_tr[col].astype(str))
        X_te_enc[col] = le.transform(
            X_te[col].astype(str).map(
                lambda v, le=le: v if v in le.classes_ else le.classes_[0]
            )
        )
        encoders[col] = le
    return X_tr_enc, X_te_enc, encoders


# ── 4. Model factories ─────────────────────────────────────────────────────────

def _make_catboost(cat_idx, seed=42):
    return CatBoostRegressor(
        iterations=800, learning_rate=0.04, depth=8,
        min_data_in_leaf=8, l2_leaf_reg=3.0, subsample=0.85,
        loss_function="MAE", eval_metric="MAE",
        early_stopping_rounds=80,
        random_seed=seed, verbose=0,
    )

def _make_xgb(seed=42):
    return XGBRegressor(
        n_estimators=800, learning_rate=0.04, max_depth=7,
        subsample=0.85, colsample_bytree=0.80, reg_lambda=2.0,
        objective="reg:absoluteerror",
        early_stopping_rounds=80,
        random_state=seed, verbosity=0,
    )

def _make_lgbm(seed=42):
    return LGBMRegressor(
        n_estimators=800, learning_rate=0.04, num_leaves=63,
        subsample=0.85, colsample_bytree=0.80, reg_lambda=2.0,
        objective="mae",
        random_state=seed, verbose=-1,
    )


# ── 5. Train one target, compare 3 models ─────────────────────────────────────

def train_target(X_tr, X_te, y_tr, y_te, feature_names, cat_idx, label):
    X_tr_enc, X_te_enc, _ = encode_for_sklearn(X_tr, X_te)

    cat_pool_tr = Pool(X_tr, y_tr, cat_features=cat_idx, feature_names=feature_names)
    cat_pool_te = Pool(X_te, y_te, cat_features=cat_idx, feature_names=feature_names)

    candidates = {}

    # CatBoost — native categoricals
    cb = _make_catboost(cat_idx)
    cb.fit(cat_pool_tr, eval_set=cat_pool_te)
    candidates["CatBoost"] = cb

    # XGBoost — needs encoded X
    xgb = _make_xgb()
    xgb.fit(
        X_tr_enc.values, y_tr,
        eval_set=[(X_te_enc.values, y_te)],
        verbose=False,
    )
    candidates["XGBoost"] = xgb

    # LightGBM — encoded X, categorical_feature by index
    lgbm = _make_lgbm()
    lgbm.fit(
        X_tr_enc, y_tr,
        eval_set=[(X_te_enc, y_te)],
        categorical_feature=cat_idx,
    )
    candidates["LightGBM"] = lgbm

    print(f"\n  {label}:")
    print(f"  {'Model':<12}  {'MAE':>8}  {'RMSE':>8}  {'R²':>8}")
    print(f"  {'-'*44}")

    best_mae, best_name, best_model = float("inf"), None, None
    preds = {}

    for name, model in candidates.items():
        if name == "CatBoost":
            p = model.predict(Pool(X_te, cat_features=cat_idx, feature_names=feature_names))
        elif name == "XGBoost":
            p = model.predict(X_te_enc.values)
        else:
            p = model.predict(X_te_enc)
        preds[name] = p
        mae  = mean_absolute_error(y_te, p)
        rmse = math.sqrt(mean_squared_error(y_te, p))
        r2   = r2_score(y_te, p)
        print(f"  {name:<12}  {mae:>8.4f}  {rmse:>8.4f}  {r2:>8.4f}")
        if mae < best_mae:
            best_mae, best_name, best_model = mae, name, model

    print(f"  → Winner: {best_name}  MAE={best_mae:.4f}")

    p = preds[best_name]
    metrics = {
        "MAE":  round(float(mean_absolute_error(y_te, p)), 4),
        "RMSE": round(float(math.sqrt(mean_squared_error(y_te, p))), 4),
        "R2":   round(float(r2_score(y_te, p)), 4),
    }
    return best_model, best_name, metrics, X_tr_enc, X_te_enc


# ── 6. Feature importance ──────────────────────────────────────────────────────

def get_importance(model, name, feature_names, cat_idx):
    try:
        if name == "CatBoost":
            imp = model.get_feature_importance()
        else:
            imp = model.feature_importances_
        total = max(sum(imp), 1e-9)
        pairs = sorted(zip(feature_names, imp), key=lambda x: x[1], reverse=True)
        return [{"feature": f, "importance_pct": round(v / total * 100, 2)} for f, v in pairs[:15]]
    except Exception:
        return []


# ── 7. Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  PortFlow AI — Stage 3: Congestion Forecast Training")
    print("=" * 65)

    csv_path = _find_dataset()
    print(f"\n[1/5] Dataset: {csv_path}")
    raw = pd.read_csv(csv_path)
    print(f"      {len(raw):,} rows × {raw.shape[1]} columns")

    y_cong  = raw[TARGET_CONG].values.astype(float)
    y_queue = raw[TARGET_QUEUE].values.astype(float)

    print("\n[2/5] Feature engineering…")
    X = build_features(raw)
    feature_names = list(X.columns)
    cat_idx = [i for i, f in enumerate(feature_names) if f in CATEGORICAL_COLS]
    print(f"      {len(feature_names)} features | {len(cat_idx)} categorical indices: {cat_idx}")

    # Ensure categoricals are strings
    for col in CATEGORICAL_COLS:
        if col in X.columns:
            X[col] = X[col].astype(str)

    print("\n[3/5] Train/test split (80 / 20)…")
    cong_q = pd.qcut(y_cong, q=4, labels=False, duplicates="drop")
    X_tr, X_te, yc_tr, yc_te, yq_tr, yq_te = train_test_split(
        X, y_cong, y_queue, test_size=0.20, random_state=42, stratify=cong_q
    )
    print(f"      Train: {len(X_tr):,}  Test: {len(X_te):,}")

    print("\n[4/5] Training CatBoost / XGBoost / LightGBM…")
    print("─" * 50)
    cong_model,  cong_name,  cong_metrics,  X_tr_enc, X_te_enc = train_target(
        X_tr, X_te, yc_tr, yc_te, feature_names, cat_idx, "congestion_level_future"
    )
    queue_model, queue_name, queue_metrics, _, _ = train_target(
        X_tr, X_te, yq_tr, yq_te, feature_names, cat_idx, "queue_length_future"
    )

    cong_fi  = get_importance(cong_model,  cong_name,  feature_names, cat_idx)
    queue_fi = get_importance(queue_model, queue_name, feature_names, cat_idx)

    print("\n[5/5] Saving artifact…")
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)

    cat_encoders: dict[str, dict] = {}
    for col in CATEGORICAL_COLS:
        if col in X_tr_enc.columns:
            cat_encoders[col] = {str(v): int(i) for i, v in enumerate(sorted(X_tr[col].unique()))}

    artifact = {
        "congestion_model":      cong_model,
        "queue_model":           queue_model,
        "congestion_model_name": cong_name,
        "queue_model_name":      queue_name,
        "feature_names":         feature_names,
        "cat_encoders":          cat_encoders,
        "cat_indices":           cat_idx,
        "metrics": {
            "congestion": cong_metrics,
            "queue":      queue_metrics,
        },
        "feature_importance": {
            "congestion": cong_fi,
            "queue":      queue_fi,
        },
        "saved_at":      datetime.now(timezone.utc).isoformat(),
        "training_rows": len(X_tr),
        "test_rows":     len(X_te),
    }

    with open(MODEL_OUT, "wb") as fh:
        pickle.dump(artifact, fh, protocol=5)

    kb = MODEL_OUT.stat().st_size / 1024
    print(f"      Saved → {MODEL_OUT}  ({kb:.0f} KB)")

    print("\n" + "=" * 65)
    print(f"  CONGESTION  MAE={cong_metrics['MAE']:.4f}  R²={cong_metrics['R2']:.4f}  [{cong_name}]")
    print(f"  QUEUE       MAE={queue_metrics['MAE']:.2f} vessels  R²={queue_metrics['R2']:.4f}  [{queue_name}]")
    print("=" * 65)


if __name__ == "__main__":
    main()
