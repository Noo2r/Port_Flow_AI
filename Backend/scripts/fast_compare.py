import math, pickle, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd
from catboost import CatBoostRegressor, Pool
from lightgbm import LGBMRegressor
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import OrdinalEncoder

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, "/app")
CSV_PATH  = "/tmp/port_flow_dataset.csv"
MODEL_OUT = Path("/app/app/ml/models/eta_best_model.pkl")
TARGET    = "actual_delay_minutes"
LEAKAGE   = ["actual_delay_minutes","actual_arrival_time","berth_waiting_time",
             "berth_conflict_flag","congestion_level_future","queue_length_future",
             "assigned_berth","berth_id","vessel_id","mmsi",
             "timestamp","scheduled_eta","berth_available_from"]
DT_COLS   = ["timestamp","scheduled_eta","berth_available_from"]
CAT_COLS  = ["vessel_type","port_id","traffic_density"]

def build(df):
    df = df.copy()
    for c in DT_COLS:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    if "timestamp" in df.columns and "scheduled_eta" in df.columns:
        df["hours_to_eta"] = ((df["scheduled_eta"]-df["timestamp"]).dt.total_seconds()/3600).clip(0)
    else:
        df["hours_to_eta"] = 0.0
    if "berth_available_from" in df.columns and "scheduled_eta" in df.columns:
        df["berth_lead_time_h"] = ((df["berth_available_from"]-df["scheduled_eta"]).dt.total_seconds()/3600).clip(-48,48)
    else:
        df["berth_lead_time_h"] = 0.0
    s = pd.Series(0, index=df.index)
    for col in ["hour","month"]:
        if col in df.columns:
            p = 24 if col=="hour" else 12
            df[f"{col}_sin"] = np.sin(2*np.pi*df[col]/p)
            df[f"{col}_cos"] = np.cos(2*np.pi*df[col]/p)
    df["wave_x_congestion"]  = df["wave_height_m"].fillna(0)*df["port_congestion_index"].fillna(0)
    df["queue_x_congestion"] = df["berth_queue_length"].fillna(0)*df["port_congestion_index"].fillna(0)
    df["age_x_distance"]     = df["vessel_age_years"].fillna(10)*df["distance_to_port_nm"].fillna(0)
    df["delay_x_congestion"] = df.get("eta_prediction_minutes", s).fillna(0)*df["port_congestion_index"].fillna(0)
    df["queue_load_factor"]  = df["berth_queue_length"].fillna(0)*df.get("estimated_service_time_hours",pd.Series(12,index=df.index)).fillna(12)/24.0
    df["weather_severity"]   = (df["wave_height_m"].fillna(0)/7.0).clip(0,1)*0.5+(df.get("wind_speed_knots",s).fillna(0)/60.0).clip(0,1)*0.5
    df["congestion_momentum"]= df["berth_queue_length"].fillna(0)*df["port_congestion_index"].fillna(0)/100.0
    df = df.drop(columns=[c for c in LEAKAGE if c in df.columns])
    for c in CAT_COLS:
        if c in df.columns:
            df[c] = df[c].astype(str)
    return df

def w15(yt,yp): return float(np.mean(np.abs(yt-yp)<=15)*100)
def w30(yt,yp): return float(np.mean(np.abs(yt-yp)<=30)*100)
def ev(name,yt,yp):
    mae  = mean_absolute_error(yt,yp)
    rmse = math.sqrt(mean_squared_error(yt,yp))
    r2   = r2_score(yt,yp)
    print(f"  {name:<12} MAE={mae:.2f} RMSE={rmse:.2f} R2={r2:.4f} w15={w15(yt,yp):.1f}%", flush=True)
    return {"MAE":round(mae,2),"RMSE":round(rmse,2),"R2":round(r2,4),
            "within_15_pct":round(w15(yt,yp),1),"within_30_pct":round(w30(yt,yp),1),
            "bias":round(float(np.mean(yp-yt)),2)}

print("Loading data...", flush=True)
raw = pd.read_csv(CSV_PATH)
y   = raw[TARGET].values.astype(float)
X   = build(raw)
fn  = list(X.columns)
ci  = [i for i,f in enumerate(fn) if f in CAT_COLS]
dq  = pd.qcut(y, q=4, labels=False, duplicates="drop")
Xt,Xv,yt,yv = train_test_split(X, y, test_size=0.20, random_state=42, stratify=dq)
enc = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
Xte = Xt.copy(); Xve = Xv.copy()
Xte[CAT_COLS] = enc.fit_transform(Xt[CAT_COLS])
Xve[CAT_COLS] = enc.transform(Xv[CAT_COLS])
Xte = Xte.astype(float); Xve = Xve.astype(float)
cat_encoders = {c:{v:i for i,v in enumerate(sorted(Xt[c].unique()))} for c in CAT_COLS if c in Xt.columns}
tp = Pool(Xt, yt, cat_features=ci, feature_names=fn)
vp = Pool(Xv, yv, cat_features=ci, feature_names=fn)
all_models = {}; all_metrics = {}

print("[1/3] CatBoost (2000 iter, early-stop 100)...", flush=True)
cb = CatBoostRegressor(
    iterations=2000, depth=8, min_data_in_leaf=10,
    learning_rate=0.04, l2_leaf_reg=3.0, subsample=0.85, colsample_bylevel=0.80,
    loss_function="MAE", eval_metric="MAE",
    early_stopping_rounds=100, random_seed=42, verbose=200,
    task_type="CPU", thread_count=2,
)
cb.fit(tp, eval_set=vp, plot=False)
all_models["CatBoost"]  = cb
all_metrics["CatBoost"] = ev("CatBoost", yv, cb.predict(vp))

print("[2/3] XGBoost (1000 iter, hist, early-stop 50)...", flush=True)
xgb = XGBRegressor(
    n_estimators=1000, max_depth=7, learning_rate=0.05,
    subsample=0.85, colsample_bytree=0.80, min_child_weight=10,
    reg_alpha=0.1, reg_lambda=3.0, objective="reg:absoluteerror",
    early_stopping_rounds=50, random_state=42, n_jobs=2,
    tree_method="hist", verbosity=0,
)
xgb.fit(Xte, yt, eval_set=[(Xve, yv)], verbose=False)
all_models["XGBoost"]  = xgb
all_metrics["XGBoost"] = ev("XGBoost", yv, xgb.predict(Xve))

print("[3/3] LightGBM (1000 iter, early-stop 50)...", flush=True)
lgbm = LGBMRegressor(
    n_estimators=1000, num_leaves=63, max_depth=7,
    learning_rate=0.05, subsample=0.85, colsample_bytree=0.80,
    min_child_samples=10, reg_alpha=0.1, reg_lambda=3.0,
    objective="mae", random_state=42, n_jobs=2, verbose=-1,
)
lgbm.fit(Xte, yt, eval_set=[(Xve, yv)], callbacks=[])
all_models["LightGBM"]  = lgbm
all_metrics["LightGBM"] = ev("LightGBM", yv, lgbm.predict(Xve))

best = min(all_metrics, key=lambda n: all_metrics[n]["MAE"])
print(f"\nBEST: {best}", flush=True)
print(f"  Model     MAE    R2      w15", flush=True)
for n,m in sorted(all_metrics.items(), key=lambda x: x[1]["MAE"]):
    mark = " <-- BEST" if n==best else ""
    print(f"  {n:<12} {m['MAE']:.2f}  {m['R2']:.4f}  {m['within_15_pct']:.1f}%{mark}", flush=True)

fi_raw = cb.get_feature_importance()
fi_tot = sum(fi_raw)
fi = [{"feature":f,"importance_pct":round(v/fi_tot*100,2)}
      for f,v in sorted(zip(fn,fi_raw),key=lambda x:-x[1])][:20]
MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
with open(MODEL_OUT,"wb") as fh:
    pickle.dump({
        "model": all_models[best], "model_name": best,
        "all_models": all_models, "all_metrics": all_metrics,
        "metrics": {best: all_metrics[best]},
        "feature_names": fn, "cat_encoders": cat_encoders,
        "cat_indices": ci, "ordinal_encoder": enc,
        "feature_importance": fi,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "training_rows": len(Xt), "test_rows": len(Xv),
    }, fh, protocol=5)
print("Saved OK", flush=True)
