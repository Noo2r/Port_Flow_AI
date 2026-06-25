"""
Smart Port — Congestion Forecast Dashboard (Stage 3)
=====================================================
Interactive Streamlit dashboard for the congestion/queue-length forecaster,
mirroring berth_optimizer/dashboard/app.py's structure for Stage 2.

Run from inside congestion_forecaster/:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from congestion_forecaster.engine.predictor import congestion_predictor

st.set_page_config(page_title="Congestion Forecaster — Stage 3", page_icon="🚢", layout="wide")

st.title("🚢 Smart Port — Congestion Forecast Dashboard")
st.caption("Stage 3 of the Smart Port AI Pipeline — LightGBM (congestion level) + CatBoost (queue length)")

if congestion_predictor is None:
    st.error("Congestion model could not be loaded. Check Backend/app/ml/models/congestion_model.pkl exists.")
    st.stop()

info = congestion_predictor.model_info()

# ── Model summary ───────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Congestion Model", info["congestion_model_name"])
col2.metric("Queue Model", info["queue_model_name"])
col3.metric("Congestion MAE", f"{info['metrics']['congestion']['MAE']:.3f}")
col4.metric("Queue MAE", f"{info['metrics']['queue']['MAE']:.2f} vessels")

st.divider()

# ── Live prediction form ──────────────────────────────────────────────────────
st.subheader("Run a Forecast")

with st.form("forecast_form"):
    c1, c2, c3 = st.columns(3)
    with c1:
        port_id = st.selectbox("Port", [f"PORT_{c}" for c in "ABCDEFGH"])
        vessel_type = st.selectbox(
            "Vessel Type",
            ["Container", "Bulk Carrier", "Tanker", "RoRo", "General Cargo",
             "Car Carrier", "Cruise", "Feeder", "LNG Carrier", "VLCC"],
        )
        traffic_density = st.selectbox("Traffic Density", ["Low", "Medium", "High"])
    with c2:
        port_congestion_index = st.slider("Current Port Congestion Index", 0.0, 1.0, 0.5)
        berth_queue_length = st.slider("Current Berth Queue Length", 0, 20, 3)
        wave_height_m = st.slider("Wave Height (m)", 0.0, 10.0, 1.5)
    with c3:
        wind_speed_knots = st.slider("Wind Speed (knots)", 0.0, 60.0, 12.0)
        vessel_age_years = st.slider("Vessel Age (years)", 0.0, 35.0, 8.0)
        distance_to_port_nm = st.slider("Distance to Port (nm)", 0.0, 800.0, 80.0)

    submitted = st.form_submit_button("Forecast Congestion", type="primary")

if submitted:
    result = congestion_predictor.predict({
        "port_id": port_id,
        "vessel_type": vessel_type,
        "traffic_density": traffic_density,
        "port_congestion_index": port_congestion_index,
        "berth_queue_length": berth_queue_length,
        "wave_height_m": wave_height_m,
        "wind_speed_knots": wind_speed_knots,
        "vessel_age_years": vessel_age_years,
        "distance_to_port_nm": distance_to_port_nm,
    })

    r1, r2, r3 = st.columns(3)
    r1.metric("Congestion Level", f"{result['congestion_pct']:.1f}%", result["congestion_label"])
    r2.metric("Forecasted Queue", f"{result['queue_length']} vessels")
    r3.metric("Risk Score", f"{result['risk_pct']:.1f}%")

    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=result["congestion_pct"],
        title={"text": f"Congestion — {result['congestion_label']}"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": result["congestion_color"]},
            "steps": [
                {"range": [0, 30], "color": "#dcfce7"},
                {"range": [30, 55], "color": "#fef3c7"},
                {"range": [55, 75], "color": "#fed7aa"},
                {"range": [75, 100], "color": "#fee2e2"},
            ],
        },
    ))
    st.plotly_chart(gauge, use_container_width=True)

st.divider()

# ── Feature importance ────────────────────────────────────────────────────────
st.subheader("What Drives These Forecasts")
fi_col1, fi_col2 = st.columns(2)
with fi_col1:
    st.markdown("**Congestion Level — top features**")
    df_cong = pd.DataFrame(info["feature_importance"]["congestion"][:10])
    if not df_cong.empty:
        st.bar_chart(df_cong.set_index("feature")["importance_pct"])
with fi_col2:
    st.markdown("**Queue Length — top features**")
    df_queue = pd.DataFrame(info["feature_importance"]["queue"][:10])
    if not df_queue.empty:
        st.bar_chart(df_queue.set_index("feature")["importance_pct"])
