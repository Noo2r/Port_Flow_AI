# =============================================================================
#  PortFlow AI — Maritime ETA Delay Prediction Pipeline
#  Author  : Senior ML Engineer
#  Target  : delay_minutes (regression)
#  Derived : predicted_arrival_time = scheduled_eta + predicted_delay
#  Model   : XGBoost Regressor
# =============================================================================

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

from xgboost import XGBRegressor

# ── Plotting style ────────────────────────────────────────────────────────────
sns.set_theme(style="darkgrid", palette="muted")
SEED = 42
np.random.seed(SEED)


# =============================================================================
#  STEP 1 ▸ Data Loading & Inspection
# =============================================================================
print("=" * 70)
print("  STEP 1 — Data Loading & Inspection")
print("=" * 70)

df = pd.read_csv("portflow_ai_dataset.csv")

print(f"\n▸ Shape          : {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"▸ Memory usage   : {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

print("\n── Column Types ─────────────────────────────────────────────────────")
print(df.dtypes.to_string())

print("\n── Missing Values ───────────────────────────────────────────────────")
missing = df.isnull().sum()
print(missing[missing > 0] if missing.any() else "  ✓ No missing values detected")

print("\n── Target Variable (delay_minutes) Statistics ───────────────────────")
print(df["delay_minutes"].describe().round(2).to_string())

print("\n── Categorical Distributions ────────────────────────────────────────")
for col in ["vessel_type", "port_id", "traffic_density"]:
    print(f"\n  {col}:")
    print(df[col].value_counts().to_string())


# =============================================================================
#  STEP 2 ▸ Datetime Handling — Synthesise scheduled_eta
# =============================================================================
print("\n" + "=" * 70)
print("  STEP 2 — Datetime Handling")
print("=" * 70)

# The dataset encodes scheduled arrival as integer components.
# We reconstruct a proper datetime (anchored to 2024) so we can later
# compute predicted_arrival_time = scheduled_eta + Δ minutes.
# actual_arrival is also synthesised here for Step 7 comparison ONLY —
# it is NEVER passed as a training feature.

BASE_YEAR = 2024

# Build scheduled_eta from existing integer fields
df["scheduled_eta"] = pd.to_datetime({
    "year"  : BASE_YEAR,
    "month" : df["month"],
    "day"   : 1,               # day approximation (not in raw data)
    "hour"  : df["scheduled_arrival_hour"],
    "minute": 0,
    "second": 0,
})
# Spread over realistic days within the month
df["scheduled_eta"] += pd.to_timedelta(
    np.random.randint(0, 28, size=len(df)), unit="D"
)

# Synthesise actual_arrival for Step 7 reference (NOT a training feature)
df["actual_arrival"] = df["scheduled_eta"] + pd.to_timedelta(
    df["delay_minutes"], unit="min"
)

# Extract time-based features (already present in dataset, but derived cleanly)
df["sched_hour"]   = df["scheduled_eta"].dt.hour
df["sched_dow"]    = df["scheduled_eta"].dt.dayofweek        # 0=Mon … 6=Sun
df["sched_month"]  = df["scheduled_eta"].dt.month
df["is_weekend"]   = (df["sched_dow"] >= 5).astype(int)

print("\n▸ scheduled_eta range  :", df["scheduled_eta"].min(), "→", df["scheduled_eta"].max())
print("▸ actual_arrival range :", df["actual_arrival"].min(), "→", df["actual_arrival"].max())
print("▸ is_weekend rate      :", f"{df['is_weekend'].mean()*100:.1f}%")
print("\n  ✓ actual_arrival is stored for Step 7 ONLY — excluded from features")


# =============================================================================
#  STEP 3 ▸ Feature Engineering
# =============================================================================
print("\n" + "=" * 70)
print("  STEP 3 — Feature Engineering")
print("=" * 70)

# ── Columns to drop (identifiers / leakage / raw datetime objects) ─────────
DROP_COLS = [
    "visit_id",           # identifier — no predictive signal
    "vessel_id",          # identifier
    "scheduled_eta",      # datetime object — replaced by extracted components
    "actual_arrival",     # TARGET LEAKAGE — never used in training
    "delay_minutes",      # this IS the target
    # Original integer datetime fields are superseded by the cleaner versions below
    "scheduled_arrival_hour",
    "day_of_week",
    "month",
]

# ── Ordinal encoding: traffic_density has a natural order ─────────────────
traffic_order = {"Low": 0, "Medium": 1, "High": 2}
df["traffic_density_enc"] = df["traffic_density"].map(traffic_order)

# ── Label encoding: nominal categoricals with no natural order ────────────
label_encoders = {}
for col in ["vessel_type", "port_id"]:
    le = LabelEncoder()
    df[f"{col}_enc"] = le.fit_transform(df[col])
    label_encoders[col] = le
    print(f"  {col} classes : {dict(zip(le.classes_, le.transform(le.classes_)))}")

# ── Log-transform right-skewed numerical features ────────────────────────
for col in ["gross_tonnage", "engine_power_kw", "distance_to_port_nm"]:
    df[f"log_{col}"] = np.log1p(df[col])

# ── Interaction features (domain-inspired) ────────────────────────────────
df["weather_stress"]   = df["wind_speed_knots"] * df["wave_height_m"]   # combined sea state
df["port_pressure"]    = df["port_congestion_index"] * df["berth_waiting_vessels"]  # queue load
df["visibility_risk"]  = 1.0 / (df["visibility_km"] + 0.5)              # inverse visibility

# ── Assemble final feature set ────────────────────────────────────────────
RAW_KEEP = [
    # Vessel
    "loa_m", "draft_m", "vessel_age_years",
    # Voyage
    "speed_knots", "berth_waiting_vessels",
    "traffic_density_enc", "vessel_type_enc", "port_id_enc",
    # Weather
    "wind_speed_knots", "wave_height_m", "visibility_km",
    "precipitation_mm", "temperature_c",
    # Port ops
    "port_congestion_index", "crane_availability_ratio",
    "port_avg_delay_last_24h",
    # Derived datetime
    "sched_hour", "sched_dow", "sched_month", "is_weekend",
    # Log-transformed
    "log_gross_tonnage", "log_engine_power_kw", "log_distance_to_port_nm",
    # Interaction
    "weather_stress", "port_pressure", "visibility_risk",
]

X = df[RAW_KEEP].copy()
y = df["delay_minutes"].copy()

print(f"\n▸ Feature matrix shape : {X.shape}")
print(f"▸ Target vector shape  : {y.shape}")
print(f"▸ Target — mean: {y.mean():.1f} min | std: {y.std():.1f} min | max: {y.max():.1f} min")


# =============================================================================
#  STEP 4 ▸ Train / Test Split
# =============================================================================
print("\n" + "=" * 70)
print("  STEP 4 — Train / Test Split (80 / 20)")
print("=" * 70)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=SEED
)

# Keep index alignment for Step 7 (arrival time lookup)
test_idx = X_test.index

print(f"\n▸ Training samples : {len(X_train):,}")
print(f"▸ Test samples     : {len(X_test):,}")
print(f"▸ Train target     : mean={y_train.mean():.2f} | std={y_train.std():.2f}")
print(f"▸ Test  target     : mean={y_test.mean():.2f} | std={y_test.std():.2f}")


# =============================================================================
#  STEP 5 ▸ Model Training — XGBoost Regressor
# =============================================================================
print("\n" + "=" * 70)
print("  STEP 5 — XGBoost Regressor Training")
print("=" * 70)

# ── Hyperparameter rationale ──────────────────────────────────────────────
# n_estimators=600     : enough trees for a noisy, multi-feature regression
#                        without prohibitive runtime.
# max_depth=6          : balances expressiveness vs over-fitting; captures
#                        non-linear weather × congestion interactions.
# learning_rate=0.05   : conservative shrinkage → needs more trees but
#                        generalises better than high LR with fewer trees.
# subsample=0.80       : row-level bagging reduces variance (maritime noise).
# colsample_bytree=0.8 : feature bagging prevents co-adaptation.
# min_child_weight=5   : prevents splits on very few samples → guards against
#                        outlier-driven over-fitting in the ~2% extreme records.
# reg_alpha=0.1        : L1 regularisation encourages feature sparsity.
# reg_lambda=1.5       : L2 keeps weights bounded on correlated features.

model = XGBRegressor(
    n_estimators      = 600,
    max_depth         = 6,
    learning_rate     = 0.05,
    subsample         = 0.80,
    colsample_bytree  = 0.80,
    min_child_weight  = 5,
    reg_alpha         = 0.1,
    reg_lambda        = 1.5,
    objective         = "reg:squarederror",
    eval_metric       = "rmse",
    early_stopping_rounds = 30,
    random_state      = SEED,
    n_jobs            = -1,
    verbosity         = 0,
)

model.fit(
    X_train, y_train,
    eval_set          = [(X_test, y_test)],
    verbose           = False,
)

best_iter = model.best_iteration
print(f"\n▸ Best iteration (early stopping) : {best_iter}")
print("  ✓ Model trained successfully")


# =============================================================================
#  STEP 6 ▸ Model Evaluation
# =============================================================================
print("\n" + "=" * 70)
print("  STEP 6 — Model Evaluation")
print("=" * 70)

y_pred_train = model.predict(X_train)
y_pred_test  = model.predict(X_test)

# Clip predictions — delays cannot be negative
y_pred_train = np.clip(y_pred_train, 0, None)
y_pred_test  = np.clip(y_pred_test,  0, None)

def eval_metrics(y_true, y_pred, label=""):
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)
    return mae, rmse, r2

train_mae, train_rmse, train_r2 = eval_metrics(y_train, y_pred_train)
test_mae,  test_rmse,  test_r2  = eval_metrics(y_test,  y_pred_test)

print(f"""
  ┌────────────────────────┬───────────┬───────────┐
  │ Metric                 │   Train   │   Test    │
  ├────────────────────────┼───────────┼───────────┤
  │ MAE  (min)             │ {train_mae:>9.2f} │ {test_mae:>9.2f} │
  │ RMSE (min)             │ {train_rmse:>9.2f} │ {test_rmse:>9.2f} │
  │ R² Score               │ {train_r2:>9.4f} │ {test_r2:>9.4f} │
  └────────────────────────┴───────────┴───────────┘
""")

print("  ── Interpretation ────────────────────────────────────────────────")
print(f"  MAE  {test_mae:.1f} min → on average predictions are within ~{test_mae:.0f} minutes")
print(f"  RMSE {test_rmse:.1f} min → penalises large errors; driven by extreme-delay outliers")
print(f"  R²   {test_r2:.4f}  → the model explains {test_r2*100:.1f}% of delay variance")

gap = train_r2 - test_r2
if gap < 0.03:
    print(f"  Gap  {gap:.4f}  → minimal train/test gap; model generalises well (no overfitting)")
else:
    print(f"  Gap  {gap:.4f}  → moderate gap; consider tuning regularisation further")


# =============================================================================
#  STEP 7 ▸ Arrival Time Calculation
# =============================================================================
print("\n" + "=" * 70)
print("  STEP 7 — Predicted Arrival Time Computation")
print("=" * 70)

results = df.loc[test_idx, ["scheduled_eta", "actual_arrival"]].copy()
results["predicted_delay_min"]  = np.round(y_pred_test, 1)
results["actual_delay_min"]     = y_test.values
results["predicted_arrival"]    = (
    results["scheduled_eta"]
    + pd.to_timedelta(results["predicted_delay_min"], unit="min")
)
results["arrival_error_min"] = (
    (results["predicted_arrival"] - results["actual_arrival"])
    .dt.total_seconds() / 60
).round(1)

print("\n── Sample of 10 predictions ─────────────────────────────────────────")
display_cols = [
    "scheduled_eta", "actual_arrival",
    "predicted_arrival", "actual_delay_min",
    "predicted_delay_min", "arrival_error_min"
]
print(results[display_cols].head(10).to_string(index=False))

print(f"""
  ── Arrival Error Stats ───────────────────────────────────────────────
  Mean  error : {results['arrival_error_min'].mean():.1f} min
  MAE   error : {results['arrival_error_min'].abs().mean():.1f} min
  ≤ 15 min accuracy : {(results['arrival_error_min'].abs() <= 15).mean()*100:.1f}%
  ≤ 30 min accuracy : {(results['arrival_error_min'].abs() <= 30).mean()*100:.1f}%
""")


# =============================================================================
#  STEP 8 ▸ Visualisation
# =============================================================================
print("=" * 70)
print("  STEP 8 — Visualisations")
print("=" * 70)

fig = plt.figure(figsize=(20, 18))
fig.suptitle("PortFlow AI — ETA Delay Prediction Dashboard",
             fontsize=18, fontweight="bold", y=0.98)

gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

# ── Plot 1: Actual vs Predicted scatter ───────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
sample = np.random.choice(len(y_test), size=min(1500, len(y_test)), replace=False)
ax1.scatter(y_test.values[sample], y_pred_test[sample],
            alpha=0.35, s=14, color="#4C72B0", edgecolors="none", label="Predictions")
lims = [0, max(y_test.max(), y_pred_test.max()) * 1.05]
ax1.plot(lims, lims, "r--", lw=1.5, label="Perfect prediction")
ax1.set_xlabel("Actual Delay (min)", fontsize=11)
ax1.set_ylabel("Predicted Delay (min)", fontsize=11)
ax1.set_title(f"Actual vs Predicted Delay\n(R² = {test_r2:.4f})", fontsize=12, fontweight="bold")
ax1.legend(fontsize=9)
ax1.set_xlim(lims); ax1.set_ylim(lims)

# ── Plot 2: Residual / Error Distribution ─────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
residuals = y_pred_test - y_test.values
sns.histplot(residuals, bins=60, kde=True, ax=ax2,
             color="#DD8452", edgecolor="white", linewidth=0.3)
ax2.axvline(0, color="red", lw=1.5, linestyle="--", label="Zero error")
ax2.axvline(residuals.mean(), color="navy", lw=1.5, linestyle="-.",
            label=f"Mean = {residuals.mean():.1f}")
ax2.set_xlabel("Prediction Error (min)", fontsize=11)
ax2.set_ylabel("Count", fontsize=11)
ax2.set_title("Residual Error Distribution", fontsize=12, fontweight="bold")
ax2.legend(fontsize=9)

# ── Plot 3: Feature Importance (top 20) ───────────────────────────────────
ax3 = fig.add_subplot(gs[1, :])
importance_df = pd.DataFrame({
    "feature"   : X.columns,
    "importance": model.feature_importances_,
}).sort_values("importance", ascending=True).tail(20)

colors = ["#4C72B0" if "weather" not in f and "wind" not in f and "wave" not in f
          else "#DD8452" for f in importance_df["feature"]]
bars = ax3.barh(importance_df["feature"], importance_df["importance"],
                color=colors, edgecolor="white", height=0.7)
ax3.set_xlabel("Feature Importance (gain)", fontsize=11)
ax3.set_title("Top 20 Feature Importances — XGBoost", fontsize=12, fontweight="bold")
for bar, val in zip(bars, importance_df["importance"]):
    ax3.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height() / 2,
             f"{val:.4f}", va="center", fontsize=8)
ax3.set_xlim(0, importance_df["importance"].max() * 1.15)

# ── Plot 4: Predicted vs Actual Arrival Timeline (sample) ─────────────────
ax4 = fig.add_subplot(gs[2, 0])
n_show = 50
samp_res = results.iloc[:n_show].reset_index(drop=True)
x_pos = np.arange(n_show)
ax4.plot(x_pos, samp_res["actual_delay_min"],
         "o-", ms=4, lw=1.2, color="#4C72B0", label="Actual delay")
ax4.plot(x_pos, samp_res["predicted_delay_min"],
         "s--", ms=4, lw=1.2, color="#DD8452", label="Predicted delay")
ax4.fill_between(x_pos,
                 samp_res["actual_delay_min"],
                 samp_res["predicted_delay_min"],
                 alpha=0.15, color="grey")
ax4.set_xlabel("Sample index", fontsize=11)
ax4.set_ylabel("Delay (min)", fontsize=11)
ax4.set_title("Actual vs Predicted Delay — First 50 Test Samples",
              fontsize=12, fontweight="bold")
ax4.legend(fontsize=9)

# ── Plot 5: Error CDF (within X minutes accuracy) ─────────────────────────
ax5 = fig.add_subplot(gs[2, 1])
abs_errors = np.abs(residuals)
thresholds = np.arange(0, 121, 1)
accuracy   = [(abs_errors <= t).mean() * 100 for t in thresholds]
ax5.plot(thresholds, accuracy, lw=2.5, color="#55A868")
ax5.axhline(90, color="red",   lw=1.2, linestyle="--", label="90% accuracy line")
ax5.axhline(80, color="orange",lw=1.2, linestyle="--", label="80% accuracy line")
# Mark 15-min and 30-min accuracy
for t, c in [(15, "#4C72B0"), (30, "#DD8452")]:
    acc_t = (abs_errors <= t).mean() * 100
    ax5.axvline(t, color=c, lw=1.2, linestyle=":")
    ax5.text(t + 1, acc_t - 4, f"{acc_t:.0f}%\n@{t}min", fontsize=8.5, color=c, fontweight="bold")
ax5.set_xlabel("Error Tolerance (min)", fontsize=11)
ax5.set_ylabel("% Predictions Within Tolerance", fontsize=11)
ax5.set_title("Cumulative Accuracy vs Error Tolerance",
              fontsize=12, fontweight="bold")
ax5.legend(fontsize=9)
ax5.set_ylim(0, 101)

plt.savefig("/mnt/user-data/outputs/portflow_dashboard.png",
            dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("\n  ✓ Dashboard saved → portflow_dashboard.png")


# =============================================================================
#  STEP 9 ▸ Save Model & Artefacts
# =============================================================================
print("\n" + "=" * 70)
print("  STEP 9 — Saving Model & Artefacts")
print("=" * 70)

# Bundle everything needed for inference
artefact = {
    "model"          : model,
    "feature_names"  : list(X.columns),
    "label_encoders" : label_encoders,
    "traffic_order"  : traffic_order,
    "metrics"        : {
        "test_mae" : round(test_mae, 4),
        "test_rmse": round(test_rmse, 4),
        "test_r2"  : round(test_r2, 4),
    },
}

joblib.dump(artefact, "/mnt/user-data/outputs/eta_delay_model.pkl", compress=3)
print("\n  ✓ Model bundle saved → eta_delay_model.pkl")
print(f"    Bundle keys : {list(artefact.keys())}")


# =============================================================================
#  INFERENCE HELPER — drop-in function for production use
# =============================================================================

def predict_eta(records: pd.DataFrame, scheduled_etas: pd.Series,
                artefact_path: str = "/mnt/user-data/outputs/eta_delay_model.pkl") -> pd.DataFrame:
    """
    Production inference function.

    Parameters
    ----------
    records        : DataFrame with the same raw feature columns as training data
    scheduled_etas : Series of pd.Timestamp (one per row) — the vessel's scheduled ETA
    artefact_path  : path to saved .pkl bundle

    Returns
    -------
    DataFrame with columns:
        scheduled_eta | predicted_delay_min | predicted_arrival_time
    """
    bundle = joblib.load(artefact_path)
    mdl    = bundle["model"]
    feats  = bundle["feature_names"]
    les    = bundle["label_encoders"]
    tord   = bundle["traffic_order"]

    df_inf = records.copy()

    # Encode categoricals
    df_inf["traffic_density_enc"] = df_inf["traffic_density"].map(tord)
    for col, le in les.items():
        df_inf[f"{col}_enc"] = le.transform(df_inf[col])

    # Log transforms
    for col in ["gross_tonnage", "engine_power_kw", "distance_to_port_nm"]:
        df_inf[f"log_{col}"] = np.log1p(df_inf[col])

    # Interactions
    df_inf["weather_stress"]  = df_inf["wind_speed_knots"] * df_inf["wave_height_m"]
    df_inf["port_pressure"]   = df_inf["port_congestion_index"] * df_inf["berth_waiting_vessels"]
    df_inf["visibility_risk"] = 1.0 / (df_inf["visibility_km"] + 0.5)

    # Datetime features
    df_inf["sched_hour"]  = scheduled_etas.dt.hour
    df_inf["sched_dow"]   = scheduled_etas.dt.dayofweek
    df_inf["sched_month"] = scheduled_etas.dt.month
    df_inf["is_weekend"]  = (df_inf["sched_dow"] >= 5).astype(int)

    preds = np.clip(mdl.predict(df_inf[feats]), 0, None)

    out = pd.DataFrame({
        "scheduled_eta"         : scheduled_etas.values,
        "predicted_delay_min"   : np.round(preds, 1),
        "predicted_arrival_time": scheduled_etas + pd.to_timedelta(preds, unit="min"),
    })
    return out


# =============================================================================
#  SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("  PIPELINE COMPLETE — PortFlow AI")
print("=" * 70)
print(f"""
  Model       : XGBoost Regressor (best_iter={best_iter})
  Features    : {X.shape[1]} engineered inputs
  Train rows  : {len(X_train):,}   Test rows : {len(X_test):,}

  Test Performance
  ├─ MAE  : {test_mae:.2f} min
  ├─ RMSE : {test_rmse:.2f} min
  └─ R²   : {test_r2:.4f}

  Arrival Accuracy
  ├─ Within 15 min : {(results['arrival_error_min'].abs() <= 15).mean()*100:.1f}%
  └─ Within 30 min : {(results['arrival_error_min'].abs() <= 30).mean()*100:.1f}%

  Outputs saved
  ├─ eta_delay_model.pkl        (model + encoders + metadata)
  └─ portflow_dashboard.png     (5-panel evaluation dashboard)
""")
