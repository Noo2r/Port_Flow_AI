"""
Smart Port — Enterprise Berth Operations Center (v2)
=====================================================
Enhanced dashboard extending the original with:
  - Berth Assignment Board (interactive scheduling grid)
  - Utilization donut widget
  - AI Operational Insights panel
  - Scheduling Conflicts panel
  - Operational Status Legend
  All existing functionality preserved exactly.

Run from inside berth_optimizer/:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
import random
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parents[2]))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from berth_optimizer.engine.optimizer import BerthOptimizationEngine, BerthSlot, VesselRequest
from berth_optimizer.utils.data_loader import (
    load_dataset, extract_berth_slots, extract_vessel_requests, _find_dataset
)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Smart Port Operations Center",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── Base ── */
body, .stApp { background:#0a0e1a; }

/* ── Original alert boxes ── */
.alert-box   { background:#2d1a1a; border-left:4px solid #ff4b4b; padding:10px 14px;
               border-radius:4px; margin:6px 0; font-size:0.9rem; }
.warning-box { background:#2d2a1a; border-left:4px solid #ffa500; padding:10px 14px;
               border-radius:4px; margin:6px 0; font-size:0.9rem; }
div[data-testid="metric-container"] { border:1px solid #1e2535; border-radius:10px;
               padding:10px; background:#0d1221; }

/* ── Section divider ── */
.section-header {
    font-size:1.1rem; font-weight:700; color:#7eb8f7; letter-spacing:.08em;
    text-transform:uppercase; padding:6px 0 4px 0;
    border-bottom:1px solid #1e2d4a; margin-bottom:12px; margin-top:24px;
}

/* ── Board grid cells ── */
.board-wrap { overflow-x:auto; border-radius:10px; background:#0d1221;
              border:1px solid #1e2535; padding:12px; }
.board-table { border-collapse:collapse; min-width:900px; width:100%; }
.board-table th { background:#111827; color:#7eb8f7; font-size:.72rem;
                  font-weight:600; text-align:center; padding:6px 4px;
                  border:1px solid #1e2535; letter-spacing:.05em; }
.board-table td { border:1px solid #1a2235; padding:3px; min-width:58px;
                  text-align:center; vertical-align:middle; }
.cell-berth  { background:#111827; color:#94a3b8; font-size:.72rem;
               font-weight:700; text-align:left !important; padding:6px 8px !important;
               white-space:nowrap; min-width:90px; }
.cell-avail  { background:#0d2818; color:#22c55e; font-size:.65rem;
               border-radius:4px; padding:4px 2px; }
.cell-occ    { background:#0d1e3d; color:#60a5fa; font-size:.65rem;
               border-radius:4px; padding:4px 2px; cursor:pointer; }
.cell-maint  { background:#2d2200; color:#facc15; font-size:.65rem;
               border-radius:4px; padding:4px 2px; }
.cell-conf   { background:#3d0d0d; color:#f87171; font-size:.65rem;
               border-radius:4px; padding:4px 2px; }

/* ── Legend pills ── */
.legend-wrap { display:flex; gap:16px; flex-wrap:wrap; margin:10px 0; }
.legend-pill { display:flex; align-items:center; gap:6px; font-size:.78rem; color:#94a3b8; }
.legend-dot  { width:12px; height:12px; border-radius:3px; display:inline-block; }

/* ── Insight cards ── */
.insight-card { border-radius:10px; padding:14px 16px; margin:8px 0;
                border-left:4px solid; }
.insight-critical { background:#1f0a0a; border-color:#ef4444; }
.insight-warning  { background:#1f1600; border-color:#f59e0b; }
.insight-info     { background:#0a1628; border-color:#3b82f6; }
.insight-success  { background:#061a10; border-color:#10b981; }
.insight-title    { font-weight:700; font-size:.85rem; margin-bottom:4px; }
.insight-body     { font-size:.78rem; color:#94a3b8; }
.insight-badge    { display:inline-block; font-size:.65rem; font-weight:700;
                    padding:2px 8px; border-radius:20px; margin-bottom:6px; }
.badge-critical { background:#7f1d1d; color:#fca5a5; }
.badge-warning  { background:#78350f; color:#fcd34d; }
.badge-info     { background:#1e3a5f; color:#93c5fd; }
.badge-success  { background:#064e3b; color:#6ee7b7; }

/* ── Conflict cards ── */
.conflict-card { background:#150a0a; border:1px solid #3d1515; border-radius:10px;
                 padding:14px; margin:8px 0; }
.conflict-card h5 { margin:0 0 6px 0; color:#f87171; font-size:.85rem; }
.conflict-meta  { font-size:.75rem; color:#94a3b8; }
.sev-high   { color:#ef4444; font-weight:700; }
.sev-medium { color:#f59e0b; font-weight:700; }
.sev-low    { color:#60a5fa; font-weight:700; }

/* ── Status bar ── */
.status-bar { display:flex; align-items:center; gap:20px; background:#0d1221;
              border:1px solid #1e2535; border-radius:8px; padding:10px 18px;
              font-size:.78rem; color:#94a3b8; margin-bottom:12px; }
.status-dot { width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:5px; }
.dot-green  { background:#22c55e; box-shadow:0 0 6px #22c55e88; }
.dot-blue   { background:#3b82f6; box-shadow:0 0 6px #3b82f688; }
.dot-yellow { background:#facc15; box-shadow:0 0 6px #facc1588; }
.dot-red    { background:#ef4444; box-shadow:0 0 6px #ef444488; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data
def get_dataset():
    try:
        return load_dataset(_find_dataset())
    except Exception:
        return None


def run_scenario_allocations(vessels, berths):
    eng = BerthOptimizationEngine()
    rows = []
    for vessel in vessels:
        result = eng.allocate(vessel, berths)
        rows.append({
            "vessel_id":      result.vessel_id,
            "predicted_eta":  vessel.predicted_eta,
            "assigned_berth": result.assigned_berth,
            "berthing_start": result.berthing_start_time,
            "waiting_min":    result.waiting_time_minutes,
            "departure":      result.departure_time,
            "utilization":    result.berth_utilization,
            "score":          result.allocation_score,
            "conflict":       result.conflict_flag,
            "congestion":     result.congestion_flag,
            "service_h":      result.service_duration_hours,
        })
    return pd.DataFrame(rows), eng


def build_board_data(alloc_df, scenario_berths, view_hours=24):
    """
    Build a dict:  berth_id → list of (start_h, end_h, vessel_id, status)
    where hours are relative to the earliest start in alloc_df.
    """
    if alloc_df.empty:
        return {}, datetime.utcnow()

    starts = pd.to_datetime(alloc_df["berthing_start"])
    base   = starts.min().floor("h")

    board = {}
    for _, row in alloc_df.iterrows():
        bid   = row["assigned_berth"]
        s     = (pd.to_datetime(row["berthing_start"]) - base).total_seconds() / 3600
        e     = (pd.to_datetime(row["departure"])       - base).total_seconds() / 3600
        s, e  = max(0, s), min(view_hours, e)
        if e <= s:
            continue
        status = "conflict" if row["conflict"] else ("congestion" if row["congestion"] else "occupied")
        board.setdefault(bid, []).append((s, e, row["vessel_id"], status))

    return board, base


def generate_ai_insights(alloc_df, kpis, congestion_idx, crane_ratio, queue_len):
    """Generate operational insights from allocation outputs."""
    insights = []

    avg_wait = kpis.get("avg_waiting_time_minutes", 0)
    conflicts = kpis.get("conflict_count", 0)
    utilization = kpis.get("avg_berth_utilization", 0)

    if conflicts > 0:
        insights.append({
            "severity": "critical",
            "title": f"🚨 {conflicts} Berth Conflict(s) Detected",
            "body": "Overlapping allocations found. Consider redistributing vessels to alternate berths or adjusting departure windows.",
            "improvement": f"Resolving conflicts could reduce delays by ~{conflicts * 12}–{conflicts * 20} min",
        })

    if congestion_idx >= 0.75:
        insights.append({
            "severity": "critical",
            "title": "⚠ Port Congestion Critical Threshold Exceeded",
            "body": f"Congestion index at {congestion_idx:.0%}. High traffic density increases waiting times and docking risk.",
            "improvement": "Staggering arrivals by 30–45 min could reduce congestion by ~15–20%",
        })
    elif congestion_idx >= 0.5:
        insights.append({
            "severity": "warning",
            "title": "⚡ Moderate Congestion — Monitor Closely",
            "body": f"Congestion index at {congestion_idx:.0%}. Approaching operational threshold.",
            "improvement": "Pre-emptive berth reallocation recommended before peak window",
        })

    if avg_wait > 90:
        insights.append({
            "severity": "warning",
            "title": f"⏱ High Average Waiting Time: {avg_wait:.0f} min",
            "body": "Vessel waiting times exceed the 90-min operational target. Queue pressure is building.",
            "improvement": "Opening additional berths or increasing crane ratio could cut wait by ~25%",
        })

    if crane_ratio < 0.5:
        insights.append({
            "severity": "warning",
            "title": f"🏗 Low Crane Availability: {crane_ratio:.0%}",
            "body": "Reduced crane capacity is extending service durations and blocking berth turnover.",
            "improvement": "Restoring crane capacity to >75% could improve throughput by ~30%",
        })

    if utilization > 0.85:
        insights.append({
            "severity": "warning",
            "title": f"📊 Berth Utilization Exceeds Optimal Range: {utilization:.1%}",
            "body": "Optimal utilization is 75–85%. Exceeding this reduces buffer for delays.",
            "improvement": "Divert low-priority vessels to anchorage to restore buffer capacity",
        })
    elif utilization < 0.4:
        insights.append({
            "severity": "info",
            "title": f"💡 Underutilized Capacity: {utilization:.1%}",
            "body": "Several berths are idle. Opportunity to accept additional vessel bookings.",
            "improvement": "Proactive outreach to shipping lines could increase revenue by ~18%",
        })
    else:
        insights.append({
            "severity": "success",
            "title": f"✅ Berth Utilization in Optimal Range: {utilization:.1%}",
            "body": "Port is operating efficiently within the 40–85% optimal window.",
            "improvement": "Maintain current scheduling cadence — system performing well",
        })

    if queue_len >= 4:
        insights.append({
            "severity": "warning",
            "title": f"🚢 Queue Pressure: {queue_len} Vessels Queued",
            "body": "Long queues at berths may trigger cascading delays across the terminal.",
            "improvement": "Deploy anchorage holding protocol for vessels with ETA >2h",
        })

    return insights[:5]


def build_conflict_cards(alloc_df):
    """Extract conflict records from allocation output."""
    cards = []
    for _, row in alloc_df.iterrows():
        if row["conflict"]:
            start = pd.to_datetime(row["berthing_start"]).strftime("%H:%M")
            end   = pd.to_datetime(row["departure"]).strftime("%H:%M")
            cards.append({
                "berth": row["assigned_berth"],
                "vessel": row["vessel_id"],
                "issue": "Overlapping allocation — schedule conflict detected",
                "time": f"{start} → {end}",
                "severity": "high",
                "wait": f"{row['waiting_min']:.0f} min delay",
            })
        elif row["congestion"]:
            start = pd.to_datetime(row["berthing_start"]).strftime("%H:%M")
            cards.append({
                "berth": row["assigned_berth"],
                "vessel": row["vessel_id"],
                "issue": "Congestion-induced delay at berth approach",
                "time": start,
                "severity": "medium",
                "wait": f"{row['waiting_min']:.0f} min wait",
            })
    return cards


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

st.sidebar.markdown("""
<div style='text-align:center; padding:8px 0 4px 0;'>
  <span style='font-size:2rem;'>⚓</span><br>
  <span style='font-size:1rem; font-weight:700; color:#7eb8f7; letter-spacing:.1em;'>SMART PORT</span><br>
  <span style='font-size:.7rem; color:#64748b; letter-spacing:.15em;'>OPERATIONS CENTER</span>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.markdown("**⚙ Scenario Controls**")

congestion_override  = st.sidebar.slider("Port Congestion Index",       0.0, 1.0, 0.5, 0.05)
queue_override       = st.sidebar.slider("Berth Queue Length",           0,   8,   2,   1)
berth_avail_offset_h = st.sidebar.slider("Berth Avail. Offset (hours)", -4,  8,   0,   1)
crane_ratio_override = st.sidebar.slider("Crane Availability Ratio",    0.1, 1.0, 0.8, 0.05)
n_vessels            = st.sidebar.slider("Vessels to Simulate",          5,  30,  12,   1)

st.sidebar.markdown("---")
st.sidebar.markdown("**📅 Board View**")
board_view = st.sidebar.radio("Timeline window", ["Day (24h)", "12-Hour", "6-Hour"], horizontal=False)
view_hours = {"Day (24h)": 24, "12-Hour": 12, "6-Hour": 6}[board_view]

st.sidebar.markdown("---")
run_btn = st.sidebar.button("▶ Run Allocation Scenario", type="primary", use_container_width=True)

# ── Sidebar legend ────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("**🗺 Status Legend**")
st.sidebar.markdown("""
<div style='font-size:.78rem; line-height:2;'>
  <span style='color:#22c55e;'>█</span> Available &nbsp;
  <span style='color:#3b82f6;'>█</span> Occupied<br>
  <span style='color:#facc15;'>█</span> Maintenance &nbsp;
  <span style='color:#ef4444;'>█</span> Conflict
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA & RUN ENGINE
# ══════════════════════════════════════════════════════════════════════════════

df = get_dataset()
if df is None:
    st.error("❌ Could not load **port_flow_dataset.csv**. Place it inside `berth_optimizer/` and restart.")
    st.stop()

raw_berths = extract_berth_slots(df)

scenario_berths = []
for b in raw_berths:
    avail_dt = pd.to_datetime(b.berth_available_from) + timedelta(hours=berth_avail_offset_h)
    scenario_berths.append(BerthSlot(
        berth_id=b.berth_id,
        berth_max_length=b.berth_max_length,
        berth_queue_length=min(queue_override, 5),
        berth_available_from=avail_dt.isoformat(),
        crane_availability_ratio=crane_ratio_override,
        berth_max_draft=b.berth_max_draft,
    ))

raw_vessels = extract_vessel_requests(df, n=n_vessels)
for v in raw_vessels:
    v.port_congestion_index = congestion_override

if run_btn or "alloc_df" not in st.session_state:
    alloc_df, snap_engine = run_scenario_allocations(raw_vessels, scenario_berths)
    st.session_state["alloc_df"]    = alloc_df
    st.session_state["kpis"]        = snap_engine.get_port_kpis()
    st.session_state["berth_status"] = snap_engine.get_berth_status(scenario_berths)

alloc_df     = st.session_state["alloc_df"]
kpis         = st.session_state["kpis"]
berth_status = st.session_state.get("berth_status", [])


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div style='display:flex; align-items:center; justify-content:space-between;
            padding:16px 0 8px 0; border-bottom:1px solid #1e2535; margin-bottom:16px;'>
  <div>
    <div style='font-size:1.5rem; font-weight:800; color:#f1f5f9; letter-spacing:.02em;'>
      ⚓ Smart Port — Operations Center
    </div>
    <div style='font-size:.78rem; color:#64748b; margin-top:2px;'>
      Stage 2 AI Pipeline &nbsp;•&nbsp; Berth Optimization Engine v2 &nbsp;•&nbsp;
      {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
    </div>
  </div>
  <div style='text-align:right; font-size:.75rem; color:#64748b;'>
    Congestion <b style='color:{"#ef4444" if congestion_override>=0.75 else "#f59e0b" if congestion_override>=0.5 else "#22c55e"};'>{congestion_override:.0%}</b>
    &nbsp;|&nbsp; Queue <b style='color:#7eb8f7;'>{queue_override}</b>
    &nbsp;|&nbsp; Cranes <b style='color:#a78bfa;'>{crane_ratio_override:.0%}</b>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ① ORIGINAL: OPERATIONAL KPIs
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-header">📊 Operational KPIs</div>', unsafe_allow_html=True)
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Active Vessels",        kpis["active_vessels"])
k2.metric("Total Allocations",     kpis["total_allocations"])
k3.metric("Avg Waiting Time",      f"{kpis['avg_waiting_time_minutes']:.1f} min",
          delta=f"{kpis['avg_waiting_time_minutes']-30:.1f} vs baseline", delta_color="inverse")
k4.metric("Avg Berth Utilization", f"{kpis['avg_berth_utilization']:.1%}")
k5.metric("Congestion Level",      f"{congestion_override:.0%}",
          delta="HIGH" if congestion_override >= 0.75 else "LOW",
          delta_color="inverse" if congestion_override >= 0.75 else "normal")
k6.metric("Conflicts",             kpis["conflict_count"], delta_color="inverse")


# ══════════════════════════════════════════════════════════════════════════════
# ② ORIGINAL: ACTIVE ALERTS
# ══════════════════════════════════════════════════════════════════════════════

alerts_all = []
for _, row in alloc_df.iterrows():
    if row["conflict"]:
        alerts_all.append(("conflict",   f"Berth conflict — Vessel {row['vessel_id']} at {row['assigned_berth']}"))
    if row["congestion"]:
        alerts_all.append(("congestion", f"High congestion — Vessel {row['vessel_id']}"))

if alerts_all:
    st.markdown('<div class="section-header">🚨 Active Alerts</div>', unsafe_allow_html=True)
    for atype, msg in alerts_all[:6]:
        css  = "alert-box" if atype == "conflict" else "warning-box"
        icon = "🚨"         if atype == "conflict" else "⚠"
        st.markdown(f'<div class="{css}">{icon} {msg}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ③ ORIGINAL: LIVE VESSEL QUEUE TABLE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-header">🚢 Live Vessel Queue</div>', unsafe_allow_html=True)
disp = alloc_df.rename(columns={
    "vessel_id":"Vessel ID","predicted_eta":"Predicted ETA",
    "assigned_berth":"Assigned Berth","waiting_min":"Wait (min)",
    "berthing_start":"Berthing Start","departure":"Departure",
    "utilization":"Berth Util.","score":"Score",
    "conflict":"Conflict?","congestion":"Congestion?",
})

def style_row(row):
    if row["Conflict?"]:   return ["background-color:#3d1a1a"]*len(row)
    if row["Congestion?"]: return ["background-color:#3d2e00"]*len(row)
    return [""]*len(row)

styled = disp[[
    "Vessel ID","Predicted ETA","Assigned Berth",
    "Wait (min)","Berthing Start","Departure",
    "Berth Util.","Score","Conflict?","Congestion?"
]].style.apply(style_row, axis=1).format({
    "Wait (min)":"{:.1f}","Berth Util.":"{:.1%}","Score":"{:.3f}"
})
st.dataframe(styled, use_container_width=True, height=280)


# ══════════════════════════════════════════════════════════════════════════════
# ④ ORIGINAL: GANTT TIMELINE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-header">📅 Berth Occupancy Timeline (Gantt)</div>', unsafe_allow_html=True)
gantt = alloc_df.copy()
gantt["Start"]  = pd.to_datetime(gantt["berthing_start"])
gantt["Finish"] = pd.to_datetime(gantt["departure"])
gantt["Status"] = gantt.apply(
    lambda r: "Conflict" if r["conflict"] else ("Congestion" if r["congestion"] else "Normal"), axis=1
)
fig_gantt = px.timeline(
    gantt, x_start="Start", x_end="Finish", y="assigned_berth",
    color="Status", hover_name="vessel_id",
    hover_data={"waiting_min":True,"score":True,"Status":False},
    color_discrete_map={"Conflict":"#ef4444","Congestion":"#f59e0b","Normal":"#3b82f6"},
    title="Berth Allocation Timeline",
)
fig_gantt.update_layout(
    plot_bgcolor="#0d1221", paper_bgcolor="#0d1221",
    font_color="#e2e8f0", height=380,
    xaxis_title="Time", yaxis_title="Berth ID",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
fig_gantt.update_xaxes(gridcolor="#1e2535")
fig_gantt.update_yaxes(gridcolor="#1e2535")
st.plotly_chart(fig_gantt, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ⑤ ORIGINAL: UTILIZATION + WAITING TIME + SCORE CHARTS
# ══════════════════════════════════════════════════════════════════════════════

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 🏗️ Berth Utilization")
    util_df = (alloc_df.groupby("assigned_berth")["utilization"]
               .mean().reset_index().sort_values("utilization", ascending=False))
    fig_util = px.bar(util_df, x="assigned_berth", y="utilization", color="utilization",
                      color_continuous_scale="Blues", title="Average Berth Utilization")
    fig_util.update_layout(plot_bgcolor="#0d1221", paper_bgcolor="#0d1221",
                           font_color="#e2e8f0", coloraxis_showscale=False, height=300)
    fig_util.update_yaxes(tickformat=".0%", gridcolor="#1e2535")
    fig_util.update_xaxes(gridcolor="#1e2535")
    st.plotly_chart(fig_util, use_container_width=True)

with col2:
    st.markdown("#### ⏱ Waiting Time Distribution")
    fig_wait = px.histogram(alloc_df, x="waiting_min", nbins=15,
                            color_discrete_sequence=["#6366f1"],
                            title="Vessel Waiting Times",
                            labels={"waiting_min":"Waiting Time (min)"})
    fig_wait.add_vline(x=alloc_df["waiting_min"].mean(), line_dash="dash",
                       line_color="#f59e0b",
                       annotation_text=f"Avg: {alloc_df['waiting_min'].mean():.1f} min")
    fig_wait.update_layout(plot_bgcolor="#0d1221", paper_bgcolor="#0d1221",
                           font_color="#e2e8f0", height=300)
    fig_wait.update_yaxes(gridcolor="#1e2535")
    fig_wait.update_xaxes(gridcolor="#1e2535")
    st.plotly_chart(fig_wait, use_container_width=True)

st.markdown("#### 🎯 Allocation Score by Berth")
fig_score = px.box(alloc_df, x="assigned_berth", y="score", color="assigned_berth",
                   title="Allocation Score Distribution per Berth",
                   labels={"score":"Score","assigned_berth":"Berth"})
fig_score.update_layout(showlegend=False, plot_bgcolor="#0d1221",
                         paper_bgcolor="#0d1221", font_color="#e2e8f0", height=300)
fig_score.update_yaxes(gridcolor="#1e2535")
fig_score.update_xaxes(gridcolor="#1e2535")
st.plotly_chart(fig_score, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ══ NEW SECTIONS BELOW ════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style='margin:32px 0 8px 0; padding:10px 18px; background:linear-gradient(90deg,#0d1e3d,#0a0e1a);
            border-left:4px solid #3b82f6; border-radius:6px; font-size:.85rem;
            color:#7eb8f7; letter-spacing:.1em; font-weight:700;'>
  ── ADVANCED OPERATIONS CENTER ──
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# NEW ①: BERTH ASSIGNMENT BOARD
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-header">🗓 Berth Assignment Board</div>', unsafe_allow_html=True)

# Status bar
n_occ   = alloc_df[~alloc_df["conflict"] & ~alloc_df["congestion"]].shape[0]
n_conf  = alloc_df["conflict"].sum()
n_cong  = alloc_df["congestion"].sum()
n_total = len(scenario_berths)

st.markdown(f"""
<div class='status-bar'>
  <span><span class='status-dot dot-green'></span>Available berths: <b>{max(0, n_total - len(alloc_df["assigned_berth"].unique()))}</b></span>
  <span><span class='status-dot dot-blue'></span>Occupied: <b>{n_occ}</b></span>
  <span><span class='status-dot dot-red'></span>Conflicts: <b>{n_conf}</b></span>
  <span><span class='status-dot dot-yellow'></span>Congested: <b>{n_cong}</b></span>
  <span style='margin-left:auto; color:#475569;'>View: <b style='color:#7eb8f7;'>{board_view}</b></span>
</div>
""", unsafe_allow_html=True)

# ── Build Gantt-style board as a Plotly figure ──────────────────────────────
board_data, base_time = build_board_data(alloc_df, scenario_berths, view_hours)

unique_berths = sorted(alloc_df["assigned_berth"].unique())
# Add maintenance slots for berths with no vessels (simulate realistic port)
all_berth_ids = sorted({b.berth_id for b in scenario_berths})
maint_berths  = [b for b in all_berth_ids if b not in board_data][:3]

board_rows = []
# Allocated berths
for bid in unique_berths:
    slots = board_data.get(bid, [])
    for s, e, vid, status in slots:
        color = {"conflict":"#ef4444","congestion":"#f59e0b","occupied":"#3b82f6"}.get(status,"#3b82f6")
        board_rows.append({
            "Berth": bid,
            "Start": base_time + timedelta(hours=s),
            "End":   base_time + timedelta(hours=e),
            "Vessel": vid,
            "Status": status.capitalize(),
            "Color": color,
        })

# Maintenance rows for idle berths
for bid in maint_berths:
    maint_start = base_time + timedelta(hours=random.uniform(1, view_hours * 0.3))
    maint_end   = maint_start + timedelta(hours=random.uniform(2, 5))
    board_rows.append({
        "Berth": bid,
        "Start": maint_start,
        "End":   min(maint_end, base_time + timedelta(hours=view_hours)),
        "Vessel": "MAINTENANCE",
        "Status": "Maintenance",
        "Color": "#facc15",
    })

if board_rows:
    board_df = pd.DataFrame(board_rows)
    fig_board = px.timeline(
        board_df,
        x_start="Start", x_end="End",
        y="Berth", color="Status",
        hover_name="Vessel",
        hover_data={"Start": True, "End": True, "Status": True, "Color": False},
        color_discrete_map={
            "Occupied":    "#3b82f6",
            "Conflict":    "#ef4444",
            "Congestion":  "#f59e0b",
            "Maintenance": "#facc15",
        },
        title=f"Berth Assignment Board — {board_view}",
    )

    # Add available (empty) background bands
    for bid in all_berth_ids:
        fig_board.add_shape(
            type="rect",
            x0=base_time, x1=base_time + timedelta(hours=view_hours),
            y0=bid, y1=bid,
            line=dict(color="#1e2535", width=0.5),
            fillcolor="#0d2818",
            opacity=0.15,
            layer="below",
        )

    fig_board.update_layout(
        plot_bgcolor="#0d1221", paper_bgcolor="#0d1221",
        font_color="#e2e8f0", height=420,
        xaxis_title="Time Window",
        yaxis_title="Berth / Terminal",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            bgcolor="#0d1221", bordercolor="#1e2535",
        ),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    fig_board.update_xaxes(gridcolor="#1e2535", showgrid=True, dtick=3600000)
    fig_board.update_yaxes(gridcolor="#1e2535", showgrid=True)
    st.plotly_chart(fig_board, use_container_width=True)
else:
    st.info("No allocation data available for the board. Run the scenario first.")

# ── Legend ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class='legend-wrap'>
  <div class='legend-pill'><span class='legend-dot' style='background:#22c55e;'></span> Available</div>
  <div class='legend-pill'><span class='legend-dot' style='background:#3b82f6;'></span> Occupied</div>
  <div class='legend-pill'><span class='legend-dot' style='background:#facc15;'></span> Maintenance</div>
  <div class='legend-pill'><span class='legend-dot' style='background:#ef4444;'></span> Conflict</div>
  <div class='legend-pill'><span class='legend-dot' style='background:#f59e0b;'></span> Congestion</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# NEW ②: UTILIZATION DONUT  +  AI INSIGHTS  (side by side)
# ══════════════════════════════════════════════════════════════════════════════

col_left, col_right = st.columns([1, 2])

# ── Utilization Donut ────────────────────────────────────────────────────────
with col_left:
    st.markdown('<div class="section-header">📊 Terminal Utilization</div>', unsafe_allow_html=True)

    util_val  = kpis.get("avg_berth_utilization", 0)
    conf_pct  = kpis["conflict_count"] / max(kpis["total_allocations"], 1)
    maint_pct = 0.05 + crane_ratio_override * 0.05   # simulated maintenance proportion
    avail_pct = max(0, 1.0 - util_val - conf_pct - maint_pct)

    donut_labels  = ["Occupied", "Available", "Maintenance", "Conflict"]
    donut_values  = [util_val, avail_pct, maint_pct, conf_pct]
    donut_colors  = ["#3b82f6", "#22c55e", "#facc15", "#ef4444"]

    fig_donut = go.Figure(go.Pie(
        labels=donut_labels,
        values=donut_values,
        hole=0.65,
        marker=dict(colors=donut_colors, line=dict(color="#0d1221", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="%{label}: %{percent}<extra></extra>",
    ))
    fig_donut.add_annotation(
        text=f"<b>{util_val:.0%}</b><br><span style='font-size:10px'>Utilization</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=18, color="#e2e8f0"),
    )
    fig_donut.update_layout(
        showlegend=True,
        legend=dict(orientation="v", x=1.0, y=0.5, font=dict(color="#94a3b8", size=11)),
        paper_bgcolor="#0d1221", plot_bgcolor="#0d1221",
        margin=dict(l=0, r=80, t=20, b=0),
        height=280,
    )
    st.plotly_chart(fig_donut, use_container_width=True)

    # Insight text
    if util_val > 0.85:
        st.markdown('<div class="warning-box">⚠ Utilization exceeds optimal range (75–85%)</div>', unsafe_allow_html=True)
    elif util_val < 0.4:
        st.markdown('<div style="background:#061a10;border-left:4px solid #10b981;padding:10px 14px;border-radius:4px;font-size:.85rem;">💡 Below optimal range — capacity available</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:#061a10;border-left:4px solid #10b981;padding:10px 14px;border-radius:4px;font-size:.85rem;">✅ Operating in optimal range: 75–85%</div>', unsafe_allow_html=True)


# ── AI Insights Panel ────────────────────────────────────────────────────────
with col_right:
    st.markdown('<div class="section-header">🤖 AI Operational Insights</div>', unsafe_allow_html=True)

    insights = generate_ai_insights(
        alloc_df, kpis, congestion_override, crane_ratio_override, queue_override
    )

    for ins in insights:
        sev   = ins["severity"]
        cls   = f"insight-{sev}"
        badge = f"badge-{sev}"
        label = {"critical":"CRITICAL","warning":"WARNING","info":"INFO","success":"OPTIMAL"}.get(sev, sev.upper())

        st.markdown(f"""
        <div class='insight-card {cls}'>
          <span class='insight-badge {badge}'>{label}</span>
          <div class='insight-title'>{ins['title']}</div>
          <div class='insight-body'>{ins['body']}</div>
          <div style='margin-top:6px; font-size:.75rem; color:#64748b;'>
            💡 <em>{ins['improvement']}</em>
          </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# NEW ③: SCHEDULING CONFLICTS PANEL
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-header">⚠ Scheduling Conflicts & Delays</div>', unsafe_allow_html=True)

conflict_cards = build_conflict_cards(alloc_df)

if not conflict_cards:
    st.markdown("""
    <div style='background:#061a10; border:1px solid #10b981; border-radius:10px;
                padding:18px; text-align:center; color:#6ee7b7; font-size:.9rem;'>
      ✅ No scheduling conflicts detected — all berths operating nominally
    </div>
    """, unsafe_allow_html=True)
else:
    cc1, cc2 = st.columns(2)
    for i, card in enumerate(conflict_cards):
        col = cc1 if i % 2 == 0 else cc2
        sev_cls = {"high": "sev-high", "medium": "sev-medium", "low": "sev-low"}.get(card["severity"], "sev-low")
        sev_lbl = card["severity"].upper()
        with col:
            st.markdown(f"""
            <div class='conflict-card'>
              <h5>🔴 {card['berth']} — {card['vessel']}</h5>
              <div class='conflict-meta'>
                <b>Issue:</b> {card['issue']}<br>
                <b>Time:</b> {card['time']} &nbsp;|&nbsp;
                <b>Impact:</b> {card['wait']}<br>
                <b>Severity:</b> <span class='{sev_cls}'>{sev_lbl}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# NEW ④: BERTH PERFORMANCE HEATMAP
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-header">🌡 Berth Performance Heatmap</div>', unsafe_allow_html=True)

if not alloc_df.empty:
    heat_df = alloc_df.copy()
    heat_df["hour_bucket"] = pd.to_datetime(heat_df["berthing_start"]).dt.floor("3H").dt.strftime("%H:%M")
    heat_pivot = heat_df.groupby(["assigned_berth", "hour_bucket"])["waiting_min"].mean().reset_index()
    heat_matrix = heat_pivot.pivot(index="assigned_berth", columns="hour_bucket", values="waiting_min").fillna(0)

    fig_heat = go.Figure(go.Heatmap(
        z=heat_matrix.values,
        x=heat_matrix.columns.tolist(),
        y=heat_matrix.index.tolist(),
        colorscale=[[0,"#0d2818"],[0.4,"#1e3a5f"],[0.7,"#78350f"],[1.0,"#7f1d1d"]],
        hovertemplate="Berth: %{y}<br>Time: %{x}<br>Avg Wait: %{z:.1f} min<extra></extra>",
        colorbar=dict( title=dict(text="Wait (min)", font=dict(color="#94a3b8")),tickfont=dict(color="#94a3b8"),
),
    ))
    fig_heat.update_layout(
        title="Average Waiting Time by Berth & Time Slot",
        plot_bgcolor="#0d1221", paper_bgcolor="#0d1221",
        font_color="#e2e8f0", height=320,
        xaxis_title="Time Window", yaxis_title="Berth",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig_heat, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# NEW ⑤: BERTH THROUGHPUT TIMELINE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-header">📈 Throughput & Efficiency Trends</div>', unsafe_allow_html=True)

t1, t2 = st.columns(2)

with t1:
    # Service duration distribution
    fig_svc = px.violin(
        alloc_df, y="service_h", x="assigned_berth",
        color="assigned_berth", box=True, points="all",
        title="Service Duration by Berth (hours)",
        labels={"service_h": "Service Hours", "assigned_berth": "Berth"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_svc.update_layout(
        showlegend=False, plot_bgcolor="#0d1221", paper_bgcolor="#0d1221",
        font_color="#e2e8f0", height=320,
    )
    fig_svc.update_yaxes(gridcolor="#1e2535")
    fig_svc.update_xaxes(gridcolor="#1e2535")
    st.plotly_chart(fig_svc, use_container_width=True)

with t2:
    # Score vs wait scatter
    fig_scatter = px.scatter(
        alloc_df, x="waiting_min", y="score",
        color="assigned_berth", size="service_h",
        hover_name="vessel_id",
        title="Allocation Score vs Waiting Time",
        labels={"waiting_min": "Waiting Time (min)", "score": "Allocation Score"},
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig_scatter.update_layout(
        plot_bgcolor="#0d1221", paper_bgcolor="#0d1221",
        font_color="#e2e8f0", height=320,
        legend=dict(font=dict(color="#94a3b8"), bgcolor="#0d1221"),
    )
    fig_scatter.update_yaxes(gridcolor="#1e2535")
    fig_scatter.update_xaxes(gridcolor="#1e2535")
    st.plotly_chart(fig_scatter, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# NEW ⑥: BERTH STATUS SUMMARY TABLE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="section-header">🏗 Berth Status Summary</div>', unsafe_allow_html=True)

if berth_status:
    bstatus_df = pd.DataFrame(berth_status)
    # Merge with conflict info from alloc_df
    conflict_berths = set(alloc_df[alloc_df["conflict"]]["assigned_berth"].tolist())
    bstatus_df["status"] = bstatus_df["berth_id"].apply(
        lambda b: "🔴 Conflict" if b in conflict_berths else
                  ("🟡 Congested" if bstatus_df[bstatus_df["berth_id"]==b]["current_queue"].values[0] >= 3 else
                   ("🔵 Occupied" if bstatus_df[bstatus_df["berth_id"]==b]["current_queue"].values[0] > 0 else "🟢 Available"))
    )
    display_cols = {
        "berth_id": "Berth ID",
        "berth_max_length": "Max Length (m)",
        "berth_max_draft": "Max Draft (m)",
        "crane_availability_ratio": "Crane Ratio",
        "current_queue": "Queue",
        "utilization": "Utilization",
        "status": "Status",
    }
    bstatus_show = bstatus_df.rename(columns=display_cols)[[
        "Berth ID","Max Length (m)","Max Draft (m)","Crane Ratio","Queue","Utilization","Status"
    ]].copy()

    def style_status(val):
        if "Conflict" in str(val):  return "color:#ef4444; font-weight:700"
        if "Congested" in str(val): return "color:#f59e0b; font-weight:700"
        if "Occupied" in str(val):  return "color:#3b82f6; font-weight:700"
        return "color:#22c55e; font-weight:700"

    st.dataframe(
        bstatus_show.style
        .applymap(style_status, subset=["Status"])
        .format({"Crane Ratio": "{:.0%}", "Utilization": "{:.1%}",
                 "Max Length (m)": "{:.0f}", "Max Draft (m)": "{:.1f}"}),
        use_container_width=True, height=280,
    )


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown(f"""
<div style='display:flex; justify-content:space-between; font-size:.72rem; color:#475569; padding:4px 0;'>
  <span>⚓ Smart Port AI Pipeline &nbsp;•&nbsp; Stage 2: Berth Optimization v2</span>
  <span>Next Stage → Congestion Forecast Model</span>
  <span>Last updated: {datetime.utcnow().strftime('%H:%M:%S UTC')}</span>
</div>
""", unsafe_allow_html=True)
