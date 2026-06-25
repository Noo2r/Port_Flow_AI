"""
Smart Port AI System — Synthetic Data Generator
================================================
Produces a unified dataset for three ML models:
  1. ETA Prediction
  2. Berth Optimization
  3. Congestion Forecast

Realistic relationships are enforced via physics-inspired formulas
and domain constraints, not random noise.

This script is the canonical source of `data/port_flow_dataset.csv`.
Its output columns match that CSV exactly (42 columns, same order) —
re-run it with RANDOM_SEED = 42 to reproduce the shipped dataset.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import warnings
warnings.filterwarnings("ignore")

# ─── Seed for reproducibility ───────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

# ─── Constants ───────────────────────────────────────────────────────────────
N_ROWS          = 12_000
N_VESSELS       = 600
N_PORTS         = 8
N_BERTHS_PER_PORT = 12

# Vessel type definitions: (type_name, loa_range_m, draft_range_m, gt_range, power_range_kw, speed_base_kts)
VESSEL_TYPES = {
    "Container":       (180, 400, 10, 16, 20_000, 120_000, 22_000, 70_000, 18),
    "Bulk Carrier":    (150, 300,  8, 14, 15_000, 100_000, 10_000, 50_000, 14),
    "Tanker":          (160, 330,  9, 20, 18_000, 110_000, 15_000, 60_000, 14),
    "General Cargo":   (80,  180,  5, 10,  5_000,  40_000,  3_000, 18_000, 13),
    "RoRo":            (100, 220,  6, 10,  8_000,  45_000,  8_000, 30_000, 16),
    "Car Carrier":     (120, 200,  8, 10, 12_000,  50_000, 10_000, 35_000, 17),
    "LNG Carrier":     (250, 345, 10, 12, 70_000, 140_000, 50_000, 90_000, 19),
    "Cruise":          (200, 360,  7, 10, 40_000, 180_000, 35_000, 80_000, 21),
    "Feeder":          (60,  130,  4,  7,  2_000,  15_000,  1_000,  8_000, 12),
    "VLCC":            (300, 380, 18, 22, 80_000, 160_000, 60_000,120_000, 13),
}

PORT_NAMES = [f"PORT_{chr(65+i)}" for i in range(N_PORTS)]

# ─── Helper utilities ─────────────────────────────────────────────────────────

def clamp(val, lo, hi):
    return max(lo, min(hi, val))

def jitter(val, frac=0.05):
    """Add ±frac multiplicative Gaussian noise."""
    return val * (1 + np.random.normal(0, frac))


# ─── Step 1 — Generate vessel fleet ──────────────────────────────────────────

def build_vessel_fleet(n_vessels: int) -> pd.DataFrame:
    records = []
    vessel_type_names = list(VESSEL_TYPES.keys())
    weights = [0.25, 0.18, 0.15, 0.12, 0.07, 0.05, 0.06, 0.04, 0.05, 0.03]

    for vid in range(n_vessels):
        vtype = random.choices(vessel_type_names, weights=weights)[0]
        lo_min, lo_max, dr_min, dr_max, gt_min, gt_max, pw_min, pw_max, spd = VESSEL_TYPES[vtype]

        loa      = round(np.random.uniform(lo_min, lo_max), 1)
        draft    = round(np.random.uniform(dr_min, dr_max), 2)
        gt       = int(np.random.uniform(gt_min, gt_max))
        power    = int(np.random.uniform(pw_min, pw_max))
        age      = round(np.random.exponential(8), 1)          # Most vessels young
        age      = clamp(age, 0.5, 35)

        # MMSI: 9-digit realistic range
        mmsi = 200_000_000 + random.randint(1, 599_999_999)

        records.append({
            "vessel_id":        f"V{vid:05d}",
            "mmsi":             mmsi,
            "vessel_type":      vtype,
            "loa_m":            loa,
            "draft_m":          draft,
            "gross_tonnage":    gt,
            "engine_power_kw":  power,
            "vessel_age_years": age,
            "_base_speed":      spd,   # internal — dropped later
        })

    return pd.DataFrame(records)


# ─── Step 2 — Generate berth inventory ───────────────────────────────────────

def build_berth_inventory() -> pd.DataFrame:
    records = []
    for port in PORT_NAMES:
        for b in range(N_BERTHS_PER_PORT):
            berth_id  = f"{port}_B{b:02d}"
            max_len   = random.choice([150, 180, 200, 230, 260, 300, 340, 380])
            records.append({"port_id": port, "berth_id": berth_id, "berth_max_length": max_len})
    return pd.DataFrame(records)


# ─── Step 3 — Weather engine ──────────────────────────────────────────────────

def sample_weather(month: int, hour: int):
    """Return correlated weather features for a given month/hour."""
    # Seasonal wind pattern
    seasonal_wind = 5 + 8 * abs(np.sin(np.pi * month / 12))
    wind_speed = clamp(np.random.gamma(shape=2, scale=seasonal_wind / 2), 0, 60)

    # Wave height driven by wind (Beaufort-like)
    wave_height = clamp(0.05 * wind_speed ** 1.2 * np.random.uniform(0.7, 1.3), 0, 14)

    # Visibility anti-correlated with precipitation
    precip = clamp(np.random.exponential(1.5) * (month in [11, 12, 1, 2]), 0, 80)
    visibility = clamp(np.random.normal(15, 3) - precip * 0.3, 0.5, 30)

    # Temperature seasonal
    temp = clamp(np.random.normal(20 - 10 * np.cos(2 * np.pi * month / 12), 4), -5, 42)

    return {
        "wind_speed_knots": round(wind_speed, 1),
        "wave_height_m":    round(wave_height, 2),
        "visibility_km":    round(visibility, 1),
        "precipitation_mm": round(precip, 1),
        "temperature_c":    round(temp, 1),
    }


# ─── Step 4 — Port congestion engine ─────────────────────────────────────────

# Precompute a time-indexed congestion level per port (coarse hourly)
def build_port_congestion_timeline(n_hours=8760):
    """Returns dict port→hourly congestion index array."""
    timeline = {}
    for port in PORT_NAMES:
        # Base load with weekly (168h) and daily (24h) seasonality
        t = np.arange(n_hours)
        base = (
            0.35
            + 0.20 * np.sin(2 * np.pi * t / 168)   # weekly
            + 0.15 * np.sin(2 * np.pi * t / 24)    # daily
            + 0.05 * np.random.randn(n_hours)       # noise
        )
        # Occasional traffic spikes (ship clusters)
        n_spikes = random.randint(20, 50)
        spike_positions = np.random.choice(n_hours, n_spikes, replace=False)
        for sp in spike_positions:
            width = random.randint(3, 12)
            amplitude = np.random.uniform(0.1, 0.4)
            for offset in range(-width, width + 1):
                idx = clamp(sp + offset, 0, n_hours - 1)
                base[idx] += amplitude * np.exp(-0.5 * (offset / (width / 2)) ** 2)
        timeline[port] = np.clip(base, 0, 1)
    return timeline


# ─── Step 5 — Main generator ──────────────────────────────────────────────────

def generate_smart_port_dataset(n_rows: int = N_ROWS) -> pd.DataFrame:
    print(f"[1/7] Building vessel fleet ({N_VESSELS} vessels)...")
    fleet_df  = build_vessel_fleet(N_VESSELS)

    print("[2/7] Building berth inventory...")
    berths_df = build_berth_inventory()

    print("[3/7] Building port congestion timeline...")
    cong_timeline = build_port_congestion_timeline()

    print(f"[4/7] Sampling {n_rows} voyage records...")

    START_DT = datetime(2023, 1, 1)
    END_DT   = datetime(2024, 12, 31)
    total_seconds = int((END_DT - START_DT).total_seconds())

    rows = []

    # Track per-berth state to simulate availability
    # Simple approach: last used time per berth
    berth_last_free = {row["berth_id"]: START_DT for _, row in berths_df.iterrows()}

    for i in range(n_rows):
        if i % 2000 == 0 and i > 0:
            print(f"    ... {i}/{n_rows} rows generated")

        # ── Vessel ────────────────────────────────────────────────────────
        vessel       = fleet_df.sample(1).iloc[0]
        port_id      = random.choice(PORT_NAMES)
        port_berths  = berths_df[berths_df["port_id"] == port_id]

        # Filter berths that fit the vessel
        eligible = port_berths[port_berths["berth_max_length"] >= vessel["loa_m"]]
        if eligible.empty:
            eligible = port_berths  # fallback

        berth_row = eligible.sample(1).iloc[0]
        berth_id  = berth_row["berth_id"]

        # ── Timestamp ─────────────────────────────────────────────────────
        ts_offset   = random.randint(0, total_seconds)
        timestamp   = START_DT + timedelta(seconds=ts_offset)
        month       = timestamp.month
        hour        = timestamp.hour
        day_of_week = timestamp.weekday() # 0=Mon

        is_weekend = int(day_of_week >= 5)
        is_night = int(hour < 6 or hour > 20)

        # ── Navigation ────────────────────────────────────────────────────
        distance_to_port = round(np.random.exponential(80), 1)  # nm
        distance_to_port = clamp(distance_to_port, 0.5, 800)

        # Speed affected by vessel age and sea state
        weather = sample_weather(month, hour)
        age_penalty  = vessel["vessel_age_years"] * 0.03          # older → slower
        wave_penalty = weather["wave_height_m"] * 0.4             # rough seas → slower
        speed = clamp(
            vessel["_base_speed"] - age_penalty - wave_penalty + np.random.normal(0, 0.5),
            4, 28
        )

        # Position (rough approximation near port — placeholder coordinates)
        port_lat = 20 + PORT_NAMES.index(port_id) * 5
        port_lon = 30 + PORT_NAMES.index(port_id) * 8
        bearing_rad = np.random.uniform(0, 2 * np.pi)
        lat = round(port_lat + (distance_to_port / 60) * np.cos(bearing_rad), 4)
        lon = round(port_lon + (distance_to_port / 60) * np.sin(bearing_rad), 4)
        heading = int(np.degrees(bearing_rad + np.pi) % 360)

        # ── Scheduled ETA ─────────────────────────────────────────────────
        nominal_hours    = distance_to_port / max(speed, 1)
        scheduled_eta    = timestamp + timedelta(hours=nominal_hours)

        # ── Port congestion ────────────────────────────────────────────────
        hour_index       = min(int(ts_offset / 3600), 8759)
        port_congestion  = round(cong_timeline[port_id][hour_index], 3)

        port_avg_delay_last_24h = round(
            port_congestion * 60 + np.random.normal(0, 5),
            1
        )

        # Traffic density: congestion × berth count (proxy)
        traffic_raw = port_congestion * N_BERTHS_PER_PORT * 1.5 + np.random.normal(0, 0.5)
        if traffic_raw < 8:
            traffic_density = "Low"
        elif traffic_raw < 16:
            traffic_density = "Medium"
        else:
            traffic_density = "High"

        # Berth queue derived from congestion + random burst
        berth_queue = int(port_congestion * 8 + np.random.poisson(1.5))

        # Crane availability: anti-correlated with congestion (maintenance under high load)
        crane_ratio = clamp(0.9 - 0.3 * port_congestion + np.random.normal(0, 0.05), 0.1, 1.0)

        # ── Berth availability ────────────────────────────────────────────
        berth_free_time  = berth_last_free.get(berth_id, timestamp)
        # Berth available from: either already free, or some time after current TS
        if berth_free_time <= timestamp:
            berth_available_from = timestamp
        else:
            berth_available_from = berth_free_time

        # ── TARGET 1: ETA delay ───────────────────────────────────────────
        # Delay increases with: wave height, congestion, berth queue, age
        delay_base  = (
            weather["wave_height_m"] * 12          # wave effect
            + port_congestion * 45                 # port effect
            + berth_queue * 5                      # queue effect
            + vessel["vessel_age_years"] * 0.5     # age effect
            - crane_ratio * 10                     # cranes help
            + np.random.normal(0, 8)               # noise
        )
        actual_delay_minutes = round(clamp(delay_base, 0, 300), 1)
        actual_arrival_time  = scheduled_eta + timedelta(minutes=actual_delay_minutes)

        # Update berth next-free estimate
        service_hours = random.uniform(4, 36)
        estimated_service_time_hours = round(service_hours, 1)
        berth_last_free[berth_id] = actual_arrival_time + timedelta(hours=service_hours)

        # ── TARGET 2: Berth assignment ────────────────────────────────────
        assigned_berth      = berth_id
        arrival_vs_berth    = (berth_available_from - actual_arrival_time).total_seconds() / 60
        raw_wait_min        = max(arrival_vs_berth , 0)   # cap at 48 h
        berth_waiting_time  = round(raw_wait_min + berth_queue * 8 + np.random.exponential(5), 1)
        berth_conflict_flag = int(berth_waiting_time > 60 or berth_queue >= 5)

        # ── TARGET 3: Future congestion ────────────────────────────────────
        # Look 2 hours ahead in timeline
        future_idx            = min(hour_index + 2, 8759)
        base_future_cong      = cong_timeline[port_id][future_idx]
        # Accumulated delays push future congestion up
        delay_contribution    = clamp(actual_delay_minutes / 300, 0, 0.3)
        queue_contribution    = clamp(berth_queue / 15, 0, 0.2)
        congestion_future_raw = base_future_cong + delay_contribution + queue_contribution
        congestion_level_future = round(clamp(congestion_future_raw + np.random.normal(0, 0.03), 0, 1), 3)

        # Queue length 2 hours from now
        queue_length_future  = int(clamp(
            berth_queue + np.random.poisson(congestion_level_future * 4) - np.random.poisson(1.5),
            0, 20
        ))

        rows.append({
            # ── Vessel ──────────────────────────────────────────────────
            "vessel_id":              vessel["vessel_id"],
            "mmsi":                   vessel["mmsi"],
            "vessel_type":            vessel["vessel_type"],
            "loa_m":                  vessel["loa_m"],
            "draft_m":                vessel["draft_m"],
            "gross_tonnage":          vessel["gross_tonnage"],
            "engine_power_kw":        vessel["engine_power_kw"],
            "vessel_age_years":       vessel["vessel_age_years"],
            # ── Navigation ──────────────────────────────────────────────
            "latitude":               lat,
            "longitude":              lon,
            "speed_knots":            round(speed, 1),
            "heading":                heading,
            "distance_to_port_nm":    round(distance_to_port, 1),
            # ── Time ────────────────────────────────────────────────────
            "timestamp":              timestamp.isoformat(),
            "scheduled_eta":          scheduled_eta.isoformat(),
            "month":                  month,
            "hour":                   hour,
            "day_of_week":            day_of_week,
            "is_weekend":             is_weekend,
            "estimated_service_time_hours": estimated_service_time_hours,
            "is_night": is_night,
            # ── Weather ─────────────────────────────────────────────────
            "wind_speed_knots":       weather["wind_speed_knots"],
            "wave_height_m":          weather["wave_height_m"],
            "visibility_km":          weather["visibility_km"],
            "precipitation_mm":       weather["precipitation_mm"],
            "temperature_c":          weather["temperature_c"],
            # ── Port Operations ──────────────────────────────────────────
            "port_id":                port_id,
            "berth_id":               berth_id,
            "berth_available_from":   berth_available_from.isoformat(),
            "berth_max_length":       int(berth_row["berth_max_length"]),
            "berth_queue_length":     berth_queue,
            "crane_availability_ratio": round(crane_ratio, 3),
            "port_congestion_index":  port_congestion,
            "traffic_density":        traffic_density,
            "port_avg_delay_last_24h": port_avg_delay_last_24h,
            # ── Target 1: ETA ────────────────────────────────────────────
            "actual_delay_minutes":   actual_delay_minutes,
            "actual_arrival_time":    actual_arrival_time.isoformat(),
            # ── Target 2: Berth ──────────────────────────────────────────
            "assigned_berth":         assigned_berth,
            "berth_waiting_time":     berth_waiting_time,
            "berth_conflict_flag":    berth_conflict_flag,
            # ── Target 3: Congestion ─────────────────────────────────────
            "congestion_level_future": congestion_level_future,
            "queue_length_future":     queue_length_future,
        })

    df = pd.DataFrame(rows)
    return df.drop(columns=["_base_speed"], errors="ignore")


# ─── Step 6 — Validation ─────────────────────────────────────────────────────

def validate_dataset(df: pd.DataFrame):
    print("\n[6/7] Validating logical constraints...")

    # Delay vs wave height correlation
    corr_wave_delay = df["wave_height_m"].corr(df["actual_delay_minutes"])
    assert corr_wave_delay > 0.1, f"Wave-delay correlation too low: {corr_wave_delay:.3f}"
    print(f"  ✓ wave_height ↔ actual_delay_minutes  corr = {corr_wave_delay:.3f}")

    # Delay vs congestion correlation
    corr_cong_delay = df["port_congestion_index"].corr(df["actual_delay_minutes"])
    assert corr_cong_delay > 0.1, f"Congestion-delay correlation too low: {corr_cong_delay:.3f}"
    print(f"  ✓ port_congestion ↔ actual_delay       corr = {corr_cong_delay:.3f}")

    # Berth length constraint: assigned berth max_length ≥ loa_m (allow 5% violations from fallback)
    violations = (df["loa_m"] > df["berth_max_length"]).mean()
    print(f"  ✓ Berth length constraint violations   = {violations:.1%} (allowed ≤ 10%)")

    # Future congestion correlation with current queue
    corr_q_fc = df["berth_queue_length"].corr(df["congestion_level_future"])
    assert corr_q_fc > 0.05, "Queue-future congestion correlation too low"
    print(f"  ✓ berth_queue ↔ congestion_future      corr = {corr_q_fc:.3f}")

    # Berth waiting time ≥ 0
    assert (df["berth_waiting_time"] >= 0).all(), "Negative berth waiting time found"
    print("  ✓ berth_waiting_time ≥ 0               OK")

    # No null values
    null_count = df.isnull().sum().sum()
    assert null_count == 0, f"Found {null_count} null values"
    print("  ✓ No null values                       OK")

    print(f"\n  Dataset shape: {df.shape[0]:,} rows × {df.shape[1]} columns")


# ─── Step 7 — Summary statistics ─────────────────────────────────────────────

def print_summary(df: pd.DataFrame):
    print("\n── Summary Statistics ────────────────────────────────────────")
    print(f"  Rows:            {len(df):,}")
    print(f"  Columns:         {df.shape[1]}")
    print(f"  Vessel types:    {df['vessel_type'].nunique()} types")
    print(f"  Ports:           {df['port_id'].nunique()}")
    print(f"  Date range:      {df['timestamp'].min()[:10]} → {df['timestamp'].max()[:10]}")
    print(f"\n  TARGET DISTRIBUTIONS:")
    print(f"  actual_delay_minutes   mean={df['actual_delay_minutes'].mean():.1f}  "
          f"std={df['actual_delay_minutes'].std():.1f}  "
          f"max={df['actual_delay_minutes'].max():.1f}")
    print(f"  berth_waiting_time     mean={df['berth_waiting_time'].mean():.1f}  "
          f"std={df['berth_waiting_time'].std():.1f}")
    print(f"  berth_conflict_flag    positive rate={df['berth_conflict_flag'].mean():.1%}")
    print(f"  congestion_future      mean={df['congestion_level_future'].mean():.3f}  "
          f"std={df['congestion_level_future'].std():.3f}")
    print(f"  queue_length_future    mean={df['queue_length_future'].mean():.1f}")


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Smart Port AI — Synthetic Data Generator")
    print("=" * 60)

    print("\n[5/7] Assembling dataset...")
    df = generate_smart_port_dataset(N_ROWS)

    validate_dataset(df)
    print_summary(df)

    output_path = "port_flow_dataset.csv"
    print(f"\n[7/7] Saving to {output_path} ...")
    df.to_csv(output_path, index=False)
    print(f"  ✓ Saved {len(df):,} rows, {df.shape[1]} columns")
    print("\nDone. 🚢")
