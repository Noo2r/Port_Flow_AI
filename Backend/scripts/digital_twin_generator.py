"""
Smart Port AI System — Digital Twin Generator (Phase 4.1)
============================================================
Produces FIVE related datasets representing a living smart port, replacing
the single monolithic ML-sample table with a coherent operational snapshot:

    vessels.csv          — 600 vessels, persistent identity + current state
    ports.csv             — 8 ports, static reference data
    berths.csv             — 96 berths, current occupancy snapshot
    vessel_visits.csv       — ~12,000 historical + ~100 in-progress visits
    live_port_state.csv      — per-port "right now" operational snapshot

Design constraint (Phase 4.1 scope — see project analysis):
  This script does NOT touch the database, the importer, FastAPI, or the
  frontend. It only produces CSVs into data/digital_twin/, alongside the
  existing data/port_flow_dataset.csv (left completely untouched).

AI-model compatibility constraint:
  vessel_visits.csv keeps every raw feature column name/unit that
  app/ml/eta_predictor.py and congestion_forecaster/engine/predictor.py
  already expect (wave_height_m, port_congestion_index, berth_queue_length,
  vessel_age_years, loa_m, draft_m, gross_tonnage, traffic_density, etc.) —
  the trained .pkl models require zero changes and zero retraining.
  New columns (vessel identity, origin_port_id, visit_status, ...) are
  additive only; both predictors select features strictly by name
  (`row[self.feature_names]`), so extra columns are silently ignored.

Run:
    docker exec portflow_api python scripts/digital_twin_generator.py
"""
from __future__ import annotations

import random
import string
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ─── Seed for reproducibility ───────────────────────────────────────────────
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

# ─── Output location — new, separate from the existing dataset ──────────────
# Backend/ is the directory actually mounted into the API container
# (docker-compose.yml: "./Backend:/app"); the project-root data/ folder is
# NOT mounted, so writing there from inside the container would silently
# land nowhere the host can see. Backend/data_digital_twin/ keeps these
# completely separate from data/port_flow_dataset.csv either way.
OUT_DIR = Path(__file__).resolve().parents[1] / "data_digital_twin"

N_VESSELS         = 600
N_PORTS           = 8
N_BERTHS_PER_PORT = 12
N_HISTORICAL_VISITS_PER_VESSEL = 20   # -> ~12,000 historical rows total

def clamp(val, lo, hi):
    return max(lo, min(hi, val))


# ─────────────────────────────────────────────────────────────────────────────
# Reference data
# ─────────────────────────────────────────────────────────────────────────────

# Vessel type physical-spec ranges (same ranges as the original ML generator,
# so vessel_visits.csv's loa_m/draft_m/gross_tonnage distributions stay
# consistent with what the trained models were fit on). Added: beam ratio
# (LOA/beam is a realistic ~6.0-7.5 for most commercial vessel types) and a
# deadweight/gross-tonnage ratio, since Vessel.beam / Vessel.deadweight_tonnage
# already exist as DB columns but were never populated by the old generator.
VESSEL_TYPES = {
    # name:            (loa_min,loa_max, draft_min,draft_max, gt_min,gt_max, pw_min,pw_max, speed, beam_ratio, dwt_ratio)
    "Container":     (180, 400, 10, 16, 20_000, 120_000, 22_000, 70_000, 18, 7.2, 1.15),
    "Bulk Carrier":  (150, 300,  8, 14, 15_000, 100_000, 10_000, 50_000, 14, 6.2, 1.55),
    "Tanker":        (160, 330,  9, 20, 18_000, 110_000, 15_000, 60_000, 14, 6.0, 1.65),
    "General Cargo": (80,  180,  5, 10,  5_000,  40_000,  3_000, 18_000, 13, 6.5, 1.35),
    "RoRo":          (100, 220,  6, 10,  8_000,  45_000,  8_000, 30_000, 16, 6.8, 0.55),
    "Car Carrier":   (120, 200,  8, 10, 12_000,  50_000, 10_000, 35_000, 17, 6.6, 0.45),
    "LNG Carrier":   (250, 345, 10, 12, 70_000, 140_000, 50_000, 90_000, 19, 6.0, 0.50),
    "Cruise":        (200, 360,  7, 10, 40_000, 180_000, 35_000, 80_000, 21, 7.5, 0.30),
    "Feeder":        (60,  130,  4,  7,  2_000,  15_000,  1_000,  8_000, 12, 6.3, 1.20),
    "VLCC":          (300, 380, 18, 22, 80_000, 160_000, 60_000,120_000, 13, 5.8, 1.75),
}
VESSEL_TYPE_WEIGHTS = [0.25, 0.18, 0.15, 0.12, 0.07, 0.05, 0.06, 0.04, 0.05, 0.03]

# Real shipping-line carriers — (short prefix used in vessel names, full legal
# owner/operator name, list of flags they commonly register under)
CARRIERS = [
    ("MSC",            "Mediterranean Shipping Company",      ["Panama", "Liberia"]),
    ("Maersk",         "A.P. Moller-Maersk",                  ["Denmark", "Singapore"]),
    ("CMA CGM",        "CMA CGM Group",                        ["France", "Marshall Islands"]),
    ("COSCO Shipping", "China COSCO Shipping Corporation",      ["China", "Hong Kong"]),
    ("Ever",           "Evergreen Marine Corporation",          ["Panama", "Marshall Islands"]),
    ("ONE",            "Ocean Network Express",                 ["Japan", "Singapore"]),
    ("Hapag-Lloyd",    "Hapag-Lloyd AG",                         ["Germany", "Malta"]),
    ("Yang Ming",      "Yang Ming Marine Transport Corp",        ["Taiwan", "Panama"]),
    ("ZIM",            "ZIM Integrated Shipping Services",       ["Israel", "Marshall Islands"]),
    ("OOCL",           "Orient Overseas Container Line",          ["Hong Kong", "Bahamas"]),
    ("PIL",            "Pacific International Lines",             ["Singapore"]),
    ("NYK",            "Nippon Yusen Kaisha",                     ["Japan"]),
    ("MOL",            "Mitsui O.S.K. Lines",                     ["Japan", "Panama"]),
]

NAME_WORDS = [
    "Istanbul", "Glory", "Leo", "Horizon", "Pioneer", "Endeavor", "Triumph",
    "Voyager", "Spirit", "Star", "Phoenix", "Atlas", "Odyssey", "Legacy",
    "Vanguard", "Liberty", "Unity", "Harmony", "Discovery", "Endurance",
    "Victory", "Premier", "Navigator", "Pathfinder", "Constellation",
    "Meridian", "Zenith", "Apex", "Crown", "Eagle", "Falcon", "Pearl",
    "Jade", "Amber", "Sapphire", "Emerald", "Neptune", "Poseidon",
    "Atlantic", "Pacific", "Britannia", "Hamburg", "Felicity",
    "Jacques Saadé", "Edmonton", "Shanghai", "Rotterdam", "Singapore",
    "Busan", "Yokohama", "Santos", "Valencia", "Antwerp", "Savannah",
]

# Maritime Identification Digits (MID) — real per-flag prefixes, used so a
# vessel's MMSI prefix actually matches its flag state (a small but
# meaningful realism/validity detail).
FLAG_MID = {
    "Panama":            ["351", "352", "353", "354", "355", "356", "357"],
    "Liberia":           ["636", "637"],
    "Denmark":           ["219", "220"],
    "Singapore":         ["563", "564"],
    "France":            ["226", "227", "228"],
    "Marshall Islands":  ["538"],
    "China":             ["412", "413"],
    "Hong Kong":         ["477"],
    "Japan":             ["431", "432"],
    "Germany":           ["211", "218"],
    "Malta":             ["215", "229", "248", "256"],
    "Taiwan":            ["416"],
    "Israel":            ["428"],
    "Bahamas":           ["308", "309", "311"],
}
ALL_FLAGS = list(FLAG_MID.keys())

PORT_DEFS = [
    # code,    name,         country,  city,         lat,    lon,    region
    ("PORT_A", "Port Alpha",   "Egypt",  "Alexandria",  31.20,  29.92, "Mediterranean"),
    ("PORT_B", "Port Bravo",   "Egypt",  "Port Said",   31.26,  32.30, "Mediterranean"),
    ("PORT_C", "Port Capri",   "Italy",  "Genoa",       44.41,   8.93, "Mediterranean"),
    ("PORT_D", "Port Delta",   "Greece", "Piraeus",     37.94,  23.64, "Mediterranean"),
    ("PORT_E", "Port Echo",    "Egypt",  "Suez",        29.97,  32.55, "Red Sea"),
    ("PORT_F", "Port Foxtrot", "Saudi Arabia", "Jeddah", 21.49,  39.18, "Red Sea"),
    ("PORT_G", "Port Gulf",    "UAE",    "Jebel Ali",    25.01,  55.06, "Gulf"),
    ("PORT_H", "Port Harbor",  "Singapore", "Singapore", 1.29,  103.85, "Southeast Asia"),
]

# Per-port "base load" bias — deliberately different so congestion varies
# meaningfully across the network (Task 7 / "avoid all ports having nearly
# identical congestion levels"), rather than all ports drawing from the same
# distribution and converging to similar values by chance.
PORT_BASE_LOAD = {
    "PORT_A": 0.55,  # busy regional hub -> tends toward Medium/High
    "PORT_B": 0.30,  # quieter -> tends toward Low/Medium
    "PORT_C": 0.40,
    "PORT_D": 0.70,  # very busy -> tends toward High/Critical
    "PORT_E": 0.25,  # quiet -> tends toward Low
    "PORT_F": 0.50,
    "PORT_G": 0.60,
    "PORT_H": 0.80,  # major global hub -> tends toward Critical
}

# Vessel lifecycle stages, in this generator's own richer vocabulary (Task 7).
# These map down to the existing VesselStatus/VisitStatus DB enums in
# Phase 4.2 — that mapping is documented in the compatibility report, not
# implemented here, since Phase 4.1 does not touch the database.
LIFECYCLE_STAGES = [
    "At Sea", "Approaching", "Anchored", "Waiting",
    "Berthing", "Berthed", "Cargo Operations", "Departing",
]
# Target proportions across 600 vessels, closely matching the example
# distribution given in the brief (520/28/16/22/14 across 5 buckets) but
# split slightly finer to distinguish "occupies a berth right now" stages
# (Berthing, Berthed, Cargo Operations, Departing) from stages that don't
# (At Sea, Approaching, Anchored, Waiting) — this finer split is what makes
# berths.csv's occupied count and vessels.csv's "currently at a berth" count
# match exactly, by construction, rather than by coincidence.
LIFECYCLE_WEIGHTS = {
    "At Sea":            0.8500,
    "Approaching":       0.0400,
    "Anchored":          0.0200,
    "Waiting":           0.0100,
    "Berthing":          0.0100,
    "Berthed":           0.0350,
    "Cargo Operations":  0.0150,
    "Departing":         0.0200,
}
BERTH_OCCUPYING_STAGES = {"Berthing", "Berthed", "Cargo Operations", "Departing"}
QUEUEING_STAGES         = {"Anchored", "Waiting"}


# ─────────────────────────────────────────────────────────────────────────────
# Identity generators — IMO / MMSI with real check-digit / MID validity
# ─────────────────────────────────────────────────────────────────────────────

def generate_imo_number(rng: random.Random) -> str:
    """7-digit IMO number with a real, verifiable check digit.
    Algorithm: digit7 = sum(digit[i] * (7-i) for i in 0..5) mod 10.
    """
    digits = [rng.randint(0, 9) for _ in range(6)]
    if digits[0] == 0:
        digits[0] = rng.randint(1, 9)
    check = sum(d * (7 - i) for i, d in enumerate(digits)) % 10
    return "".join(str(d) for d in digits) + str(check)


def is_valid_imo(imo: str) -> bool:
    if not imo.isdigit() or len(imo) != 7:
        return False
    digits = [int(c) for c in imo]
    check = sum(d * (7 - i) for i, d in enumerate(digits[:6])) % 10
    return check == digits[6]


def generate_mmsi(rng: random.Random, flag: str) -> str:
    mid = rng.choice(FLAG_MID[flag])
    rest = "".join(str(rng.randint(0, 9)) for _ in range(6))
    return mid + rest


def is_valid_mmsi(mmsi: str) -> bool:
    return mmsi.isdigit() and len(mmsi) == 9 and mmsi[0] != "0"


def generate_vessel_name(rng: random.Random, used_names: set[str]) -> tuple[str, str]:
    """Returns (name, carrier_short). Guaranteed unique within this run."""
    for _ in range(50):
        carrier_short, _, _ = rng.choice(CARRIERS)
        word = rng.choice(NAME_WORDS)
        name = f"{carrier_short} {word}"
        if name not in used_names:
            used_names.add(name)
            return name, carrier_short
    # Pool exhausted (shouldn't happen at 600 vessels / ~650 combos) — append
    # a roman-numeral-style suffix rather than ever falling back to "V00001".
    carrier_short, _, _ = rng.choice(CARRIERS)
    word = rng.choice(NAME_WORDS)
    suffix = rng.randint(2, 9)
    name = f"{carrier_short} {word} {suffix}"
    used_names.add(name)
    return name, carrier_short


def carrier_owner(carrier_short: str) -> tuple[str, list[str]]:
    for short, owner, flags in CARRIERS:
        if short == carrier_short:
            return owner, flags
    return "Independent Owner", ALL_FLAGS


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Vessels (persistent identity + current lifecycle state)
# ─────────────────────────────────────────────────────────────────────────────

def generate_vessels(n: int = N_VESSELS) -> pd.DataFrame:
    rng = random.Random(RANDOM_SEED)
    used_names: set[str] = set()
    port_codes = [p[0] for p in PORT_DEFS]
    port_latlon = {p[0]: (p[4], p[5]) for p in PORT_DEFS}

    stage_pool = list(LIFECYCLE_WEIGHTS.keys())
    stage_w    = list(LIFECYCLE_WEIGHTS.values())

    rows = []
    for i in range(n):
        type_name = rng.choices(list(VESSEL_TYPES.keys()), weights=VESSEL_TYPE_WEIGHTS)[0]
        loa_min, loa_max, dr_min, dr_max, gt_min, gt_max, pw_min, pw_max, base_speed, beam_ratio, dwt_ratio = VESSEL_TYPES[type_name]

        loa   = round(rng.uniform(loa_min, loa_max), 1)
        draft = round(rng.uniform(dr_min, dr_max), 2)
        gt    = int(rng.uniform(gt_min, gt_max))
        power = int(rng.uniform(pw_min, pw_max))
        age   = clamp(round(rng.expovariate(1 / 8), 1), 0.5, 35)
        beam  = round(loa / beam_ratio * rng.uniform(0.95, 1.05), 1)
        dwt   = round(gt * dwt_ratio * rng.uniform(0.92, 1.08))

        name, carrier_short = generate_vessel_name(rng, used_names)
        owner, flag_pool = carrier_owner(carrier_short)
        flag = rng.choice(flag_pool) if flag_pool else rng.choice(ALL_FLAGS)
        imo  = generate_imo_number(rng)
        mmsi = generate_mmsi(rng, flag)

        stage = rng.choices(stage_pool, weights=stage_w)[0]
        dest_port = rng.choice(port_codes)
        cur_port  = dest_port if stage in (BERTH_OCCUPYING_STAGES | QUEUEING_STAGES | {"Approaching"}) else rng.choice(port_codes)
        plat, plon = port_latlon[cur_port]

        if stage == "At Sea":
            # Genuinely out at sea — offset well away from any single port.
            dist_deg = rng.uniform(2.0, 12.0)
            bearing  = rng.uniform(0, 2 * np.pi)
            lat = round(plat + dist_deg * np.cos(bearing), 4)
            lon = round(plon + dist_deg * np.sin(bearing), 4)
            speed = round(clamp(base_speed - age * 0.03 + rng.gauss(0, 1.0), 4, 28), 1)
            heading = rng.randint(0, 359)
        elif stage == "Approaching":
            dist_deg = rng.uniform(0.3, 1.5)
            bearing  = rng.uniform(0, 2 * np.pi)
            lat = round(plat + dist_deg * np.cos(bearing), 4)
            lon = round(plon + dist_deg * np.sin(bearing), 4)
            speed = round(clamp(base_speed * 0.6 + rng.gauss(0, 0.5), 3, 18), 1)
            heading = rng.randint(0, 359)
        elif stage in QUEUEING_STAGES:
            lat = round(plat + rng.uniform(-0.05, 0.05), 4)
            lon = round(plon + rng.uniform(-0.05, 0.05), 4)
            speed = 0.0
            heading = rng.randint(0, 359)
        else:  # berth-occupying stages — alongside, at the port's coordinates
            lat = round(plat + rng.uniform(-0.01, 0.01), 4)
            lon = round(plon + rng.uniform(-0.01, 0.01), 4)
            speed = 0.0
            heading = rng.randint(0, 359)

        rows.append({
            "vessel_id":        f"VSL-{i+1:04d}",   # internal join key only — NOT shown as the vessel's identity
            "name":             name,
            "imo_number":       imo,
            "mmsi":             mmsi,
            "flag":             flag,
            "owner":            owner,
            "operator":         owner,
            "vessel_type":      type_name,
            "loa_m":            loa,
            "beam_m":           beam,
            "draft_m":          draft,
            "gross_tonnage":    gt,
            "deadweight_tonnage": dwt,
            "engine_power_kw":  power,
            "vessel_age_years": age,
            "build_year":       max(1985, int(round(2025 - age))),
            "destination_port": dest_port,
            "current_port":     cur_port,
            "current_lifecycle_stage": stage,
            "current_lat":      lat,
            "current_lon":      lon,
            "current_speed_knots": speed,
            "current_heading":  heading,
        })

    df = pd.DataFrame(rows)
    assert df["imo_number"].apply(is_valid_imo).all(), "Generated an invalid IMO number"
    assert df["mmsi"].apply(is_valid_mmsi).all(), "Generated an invalid MMSI"
    assert df["name"].is_unique, "Duplicate vessel name generated"
    assert df["imo_number"].is_unique, "Duplicate IMO number generated"
    assert df["mmsi"].is_unique, "Duplicate MMSI generated"
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Ports
# ─────────────────────────────────────────────────────────────────────────────

def generate_ports() -> pd.DataFrame:
    rows = []
    for code, name, country, city, lat, lon, region in PORT_DEFS:
        rows.append({
            "port_code":  code,
            "port_name":  name,
            "country":    country,
            "city":       city,
            "latitude":   lat,
            "longitude":  lon,
            "num_berths": N_BERTHS_PER_PORT,
            "max_loa_m":  380.0,
            "max_draft_m": 22.0,
            "capacity_teu": int(np.random.uniform(800_000, 4_500_000)),
            "operational_region": region,
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Berths (occupancy derived FROM vessels, not independently guessed)
# ─────────────────────────────────────────────────────────────────────────────

def generate_berths(vessels_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Returns (berths_df, demotions) where `demotions` maps vessel_id -> new
    lifecycle stage for any vessel that could not be given a real berth/queue
    slot at its own port (only possible if a single port draws more
    berth-occupying or queueing vessels than it has berths — a `zip()` over
    mismatched-length lists would otherwise silently drop the overflow
    vessels with no berth at all, which is exactly the kind of orphaned
    state Task 8 forbids). The caller must apply these demotions back onto
    vessels_df before generating visits/live-state from it.
    """
    rng = random.Random(RANDOM_SEED + 1)
    port_codes = [p[0] for p in PORT_DEFS]
    demotions: dict[str, str] = {}

    berths = []
    for port in port_codes:
        for b in range(N_BERTHS_PER_PORT):
            berths.append({
                "berth_id":   f"{port}_B{b:02d}",
                "port_code":  port,
                "max_length": rng.choice([150, 180, 200, 230, 260, 300, 340, 380]),
                "max_draft":  round(rng.uniform(12, 22), 1),
                "has_crane":  rng.random() < 0.85,
                "priority":   rng.randint(1, 5),
                "status":     "Available",   # default; overwritten below where applicable
                "occupying_vessel_id": None,
            })
    berths_df = pd.DataFrame(berths)

    # Vessels currently occupying a berth (Berthing / Berthed / Cargo
    # Operations / Departing) must each get exactly one real berth at their
    # current port — this is what makes "every occupied berth corresponds to
    # a real active vessel" true by construction, not by post-hoc patching.
    occupying = vessels_df[vessels_df["current_lifecycle_stage"].isin(BERTH_OCCUPYING_STAGES)]
    for port in port_codes:
        port_vessels = list(occupying[occupying["current_port"] == port].itertuples())
        port_berth_idx = berths_df.index[berths_df["port_code"] == port].tolist()
        rng.shuffle(port_berth_idx)
        for vessel_row, berth_idx in zip(port_vessels, port_berth_idx):
            berths_df.loc[berth_idx, "status"] = "Occupied"
            berths_df.loc[berth_idx, "occupying_vessel_id"] = vessel_row.vessel_id
        # Overflow: more occupying vessels than berths at this port. Demote
        # to "Waiting" (a queueing stage) instead of leaving them assigned
        # to a berth-occupying stage with no actual berth — a real port
        # would queue them, not invent capacity.
        if len(port_vessels) > len(port_berth_idx):
            for vessel_row in port_vessels[len(port_berth_idx):]:
                demotions[vessel_row.vessel_id] = "Waiting"

    # Vessels queueing (Anchored / Waiting) get one of the *remaining* berths
    # at their port soft-"Reserved" for them — consistent with "some
    # reserved" and avoids a queueing vessel having literally nothing
    # assigned anywhere in the dataset. A port with more queueing vessels
    # than free berths simply reserves what it has — queueing vessels
    # without a reservation are still valid (genuinely waiting for nothing
    # specific yet), so no demotion is needed here.
    queueing = vessels_df[vessels_df["current_lifecycle_stage"].isin(QUEUEING_STAGES)]
    for port in port_codes:
        free_idx = berths_df.index[(berths_df["port_code"] == port) & (berths_df["status"] == "Available")].tolist()
        rng.shuffle(free_idx)
        port_queue_vessels = queueing[queueing["current_port"] == port]
        for vessel_row, berth_idx in zip(port_queue_vessels.itertuples(), free_idx):
            berths_df.loc[berth_idx, "status"] = "Reserved"
            berths_df.loc[berth_idx, "occupying_vessel_id"] = vessel_row.vessel_id  # vessel it's reserved for

    # A handful of remaining available berths go into Maintenance / Cleaning
    # — small, realistic proportions, never touching an occupied/reserved one.
    free_idx = berths_df.index[berths_df["status"] == "Available"].tolist()
    rng.shuffle(free_idx)
    n_maintenance = max(1, round(len(berths_df) * 0.04))
    n_cleaning    = max(1, round(len(berths_df) * 0.02))
    for idx in free_idx[:n_maintenance]:
        berths_df.loc[idx, "status"] = "Maintenance"
    for idx in free_idx[n_maintenance:n_maintenance + n_cleaning]:
        berths_df.loc[idx, "status"] = "Cleaning"

    return berths_df, demotions


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Weather + congestion timeline (adapted from the original generator
# so vessel_visits.csv's raw feature distributions stay consistent with what
# the trained models were fit on)
# ─────────────────────────────────────────────────────────────────────────────

def sample_weather(month: int, hour: int) -> dict:
    seasonal_wind = 5 + 8 * abs(np.sin(np.pi * month / 12))
    wind_speed = clamp(np.random.gamma(shape=2, scale=seasonal_wind / 2), 0, 60)
    wave_height = clamp(0.05 * wind_speed ** 1.2 * np.random.uniform(0.7, 1.3), 0, 14)
    precip = clamp(np.random.exponential(1.5) * (month in [11, 12, 1, 2]), 0, 80)
    visibility = clamp(np.random.normal(15, 3) - precip * 0.3, 0.5, 30)
    temp = clamp(np.random.normal(20 - 10 * np.cos(2 * np.pi * month / 12), 4), -5, 42)
    return {
        "wind_speed_knots": round(wind_speed, 1),
        "wave_height_m":    round(wave_height, 2),
        "visibility_km":    round(visibility, 1),
        "precipitation_mm": round(precip, 1),
        "temperature_c":    round(temp, 1),
    }


def build_port_congestion_timeline(n_hours: int = 8760) -> dict:
    """Per-port hourly congestion index, with a deliberate per-port base-load
    bias (PORT_BASE_LOAD) so different ports land at genuinely different
    congestion levels rather than all regressing to a similar mean."""
    timeline = {}
    for code, *_ in PORT_DEFS:
        base_load = PORT_BASE_LOAD[code]
        t = np.arange(n_hours)
        base = (
            base_load
            + 0.15 * np.sin(2 * np.pi * t / 168)
            + 0.10 * np.sin(2 * np.pi * t / 24)
            + 0.05 * np.random.randn(n_hours)
        )
        n_spikes = random.randint(15, 40)
        spike_positions = np.random.choice(n_hours, n_spikes, replace=False)
        for sp in spike_positions:
            width = random.randint(3, 12)
            amplitude = np.random.uniform(0.1, 0.35)
            for offset in range(-width, width + 1):
                idx = clamp(sp + offset, 0, n_hours - 1)
                base[idx] += amplitude * np.exp(-0.5 * (offset / (width / 2)) ** 2)
        timeline[code] = np.clip(base, 0, 1)
    return timeline


def congestion_label(level: float) -> str:
    if level < 0.30: return "Low"
    if level < 0.55: return "Medium"
    if level < 0.75: return "High"
    return "Critical"


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Visits (historical, ML-feature-complete + a handful "in progress")
# ─────────────────────────────────────────────────────────────────────────────

def generate_visits(vessels_df: pd.DataFrame, berths_df: pd.DataFrame, now: datetime) -> pd.DataFrame:
    port_codes = [p[0] for p in PORT_DEFS]
    cong_timeline = build_port_congestion_timeline()

    START_DT = now - timedelta(days=730)
    END_DT   = now - timedelta(days=1)   # historical rows stay strictly in the past
    total_seconds = int((END_DT - START_DT).total_seconds())

    berth_max_len = dict(zip(berths_df["berth_id"], berths_df["max_length"]))
    berth_port    = dict(zip(berths_df["berth_id"], berths_df["port_code"]))
    berths_by_port = {p: berths_df.loc[berths_df["port_code"] == p, "berth_id"].tolist() for p in port_codes}

    rows = []
    visit_seq = 0

    # ── Historical (completed) visits — one block per vessel, full ML feature set
    for vessel in vessels_df.itertuples():
        for _ in range(N_HISTORICAL_VISITS_PER_VESSEL):
            visit_seq += 1
            port_id = random.choice(port_codes)
            eligible = [b for b in berths_by_port[port_id] if berth_max_len[b] >= vessel.loa_m]
            berth_id = random.choice(eligible or berths_by_port[port_id])

            ts_offset = random.randint(0, total_seconds)
            timestamp = START_DT + timedelta(seconds=ts_offset)
            month, hour, dow = timestamp.month, timestamp.hour, timestamp.weekday()
            is_weekend = int(dow >= 5)
            is_night   = int(hour < 6 or hour > 20)

            distance_to_port = clamp(round(np.random.exponential(80), 1), 0.5, 800)
            weather = sample_weather(month, hour)
            speed = clamp(18 - vessel.vessel_age_years * 0.03 - weather["wave_height_m"] * 0.4 + np.random.normal(0, 0.5), 4, 28)

            nominal_hours = distance_to_port / max(speed, 1)
            scheduled_eta = timestamp + timedelta(hours=nominal_hours)

            hour_index = min(int(ts_offset / 3600), 8759)
            port_congestion = round(cong_timeline[port_id][hour_index], 3)
            port_avg_delay = round(port_congestion * 60 + np.random.normal(0, 5), 1)

            traffic_raw = port_congestion * N_BERTHS_PER_PORT * 1.5 + np.random.normal(0, 0.5)
            traffic_density = "Low" if traffic_raw < 8 else ("Medium" if traffic_raw < 16 else "High")

            berth_queue = int(port_congestion * 8 + np.random.poisson(1.5))
            crane_ratio = clamp(0.9 - 0.3 * port_congestion + np.random.normal(0, 0.05), 0.1, 1.0)

            delay_base = (
                weather["wave_height_m"] * 12
                + port_congestion * 45
                + berth_queue * 5
                + vessel.vessel_age_years * 0.5
                - crane_ratio * 10
                + np.random.normal(0, 8)
            )
            actual_delay = round(clamp(delay_base, 0, 300), 1)
            actual_arrival = scheduled_eta + timedelta(minutes=actual_delay)
            service_hours = round(random.uniform(4, 36), 1)
            departure = actual_arrival + timedelta(hours=service_hours)

            wait_min = round(max(0, np.random.exponential(20)) + berth_queue * 6, 1)
            conflict_flag = int(wait_min > 60 or berth_queue >= 5)

            future_idx = min(hour_index + 2, 8759)
            delay_contrib = clamp(actual_delay / 300, 0, 0.3)
            queue_contrib = clamp(berth_queue / 15, 0, 0.2)
            cong_future = round(clamp(cong_timeline[port_id][future_idx] + delay_contrib + queue_contrib + np.random.normal(0, 0.03), 0, 1), 3)
            queue_future = int(clamp(berth_queue + np.random.poisson(cong_future * 4) - np.random.poisson(1.5), 0, 20))

            rows.append({
                "visit_id":   visit_seq,
                "vessel_id":  vessel.vessel_id,
                "origin_port_id": random.choice([p for p in port_codes if p != port_id]),
                "port_id":    port_id,
                "assigned_berth": berth_id,
                "visit_status": "Completed",
                "vessel_type": vessel.vessel_type,
                "loa_m": vessel.loa_m, "draft_m": vessel.draft_m,
                "gross_tonnage": vessel.gross_tonnage, "engine_power_kw": vessel.engine_power_kw,
                "vessel_age_years": vessel.vessel_age_years,
                "mmsi": vessel.mmsi,
                "latitude": round(vessel.current_lat + np.random.normal(0, 0.5), 4),
                "longitude": round(vessel.current_lon + np.random.normal(0, 0.5), 4),
                "speed_knots": round(speed, 1), "heading": random.randint(0, 359),
                "distance_to_port_nm": distance_to_port,
                "timestamp": timestamp.isoformat(), "scheduled_eta": scheduled_eta.isoformat(),
                "month": month, "hour": hour, "day_of_week": dow,
                "is_weekend": is_weekend, "is_night": is_night,
                "estimated_service_time_hours": service_hours,
                "wind_speed_knots": weather["wind_speed_knots"], "wave_height_m": weather["wave_height_m"],
                "visibility_km": weather["visibility_km"], "precipitation_mm": weather["precipitation_mm"],
                "temperature_c": weather["temperature_c"],
                "berth_available_from": timestamp.isoformat(),
                "berth_max_length": berth_max_len[berth_id],
                "berth_queue_length": berth_queue, "crane_availability_ratio": round(crane_ratio, 3),
                "port_congestion_index": port_congestion, "traffic_density": traffic_density,
                "port_avg_delay_last_24h": port_avg_delay,
                "actual_delay_minutes": actual_delay, "actual_arrival_time": actual_arrival.isoformat(),
                "scheduled_arrival": scheduled_eta.isoformat(), "ata": actual_arrival.isoformat(),
                "etb": actual_arrival.isoformat(), "atb": actual_arrival.isoformat(),
                "etd": departure.isoformat(), "atd": departure.isoformat(),
                "cargo_type": random.choice(["Containers", "Bulk Dry", "Bulk Liquid", "General"]),
                "cargo_quantity": round(random.uniform(500, 80_000), 1),
                "berth_waiting_time": wait_min, "berth_time_hours": service_hours,
                "turnaround_hours": round(wait_min / 60 + service_hours, 2),
                "berth_conflict_flag": conflict_flag,
                "congestion_level_future": cong_future, "queue_length_future": queue_future,
            })

    # ── In-progress visits — exactly the vessels currently mid-voyage, with
    # only the fields that would actually be known at this point filled in
    # (no fabricated ATA/delay for a vessel that hasn't arrived yet).
    in_progress_stages = BERTH_OCCUPYING_STAGES | QUEUEING_STAGES | {"Approaching"}
    in_progress = vessels_df[vessels_df["current_lifecycle_stage"].isin(in_progress_stages)]
    for vessel in in_progress.itertuples():
        visit_seq += 1
        stage = vessel.current_lifecycle_stage
        port_id = vessel.current_port
        weather = sample_weather(now.month, now.hour)
        distance_to_port = round(np.random.exponential(40), 1) if stage == "Approaching" else 0.0
        scheduled_eta = now + timedelta(hours=random.uniform(0.5, 6)) if stage == "Approaching" else now - timedelta(hours=random.uniform(1, 20))
        has_arrived = stage != "Approaching"
        actual_arrival = (now - timedelta(hours=random.uniform(0.1, 18))) if has_arrived else None
        assigned_berth = None
        if stage in BERTH_OCCUPYING_STAGES:
            match = berths_df[(berths_df["port_code"] == port_id) & (berths_df["occupying_vessel_id"] == vessel.vessel_id)]
            assigned_berth = match["berth_id"].iloc[0] if len(match) else None
        elif stage in QUEUEING_STAGES:
            match = berths_df[(berths_df["port_code"] == port_id) & (berths_df["occupying_vessel_id"] == vessel.vessel_id) & (berths_df["status"] == "Reserved")]
            assigned_berth = match["berth_id"].iloc[0] if len(match) else None

        hour_index = min(int((now - datetime(now.year, 1, 1)).total_seconds() / 3600), 8759)
        port_congestion = round(cong_timeline[port_id][hour_index], 3)
        berth_queue = int(port_congestion * 8 + np.random.poisson(1.5))

        rows.append({
            "visit_id": visit_seq, "vessel_id": vessel.vessel_id,
            "origin_port_id": vessel.destination_port if vessel.destination_port != port_id else None,
            "port_id": port_id, "assigned_berth": assigned_berth,
            "visit_status": stage,
            "vessel_type": vessel.vessel_type, "loa_m": vessel.loa_m, "draft_m": vessel.draft_m,
            "gross_tonnage": vessel.gross_tonnage, "engine_power_kw": vessel.engine_power_kw,
            "vessel_age_years": vessel.vessel_age_years, "mmsi": vessel.mmsi,
            "latitude": vessel.current_lat, "longitude": vessel.current_lon,
            "speed_knots": vessel.current_speed_knots, "heading": vessel.current_heading,
            "distance_to_port_nm": distance_to_port,
            "timestamp": now.isoformat(), "scheduled_eta": scheduled_eta.isoformat(),
            "month": now.month, "hour": now.hour, "day_of_week": now.weekday(),
            "is_weekend": int(now.weekday() >= 5), "is_night": int(now.hour < 6 or now.hour > 20),
            "estimated_service_time_hours": round(random.uniform(4, 36), 1),
            "wind_speed_knots": weather["wind_speed_knots"], "wave_height_m": weather["wave_height_m"],
            "visibility_km": weather["visibility_km"], "precipitation_mm": weather["precipitation_mm"],
            "temperature_c": weather["temperature_c"],
            "berth_available_from": now.isoformat(),
            "berth_max_length": berth_max_len.get(assigned_berth, 250.0),
            "berth_queue_length": berth_queue, "crane_availability_ratio": round(clamp(0.9 - 0.3 * port_congestion, 0.1, 1.0), 3),
            "port_congestion_index": port_congestion,
            "traffic_density": "High" if port_congestion > 0.55 else ("Medium" if port_congestion > 0.3 else "Low"),
            "port_avg_delay_last_24h": round(port_congestion * 60, 1),
            # Not-yet-knowable ground truth — left null rather than fabricated.
            # ML training scripts must filter to visit_status == "Completed"
            # (Phase 4.2 concern; this CSV is internally honest either way).
            "actual_delay_minutes": None, "actual_arrival_time": actual_arrival.isoformat() if actual_arrival else None,
            "scheduled_arrival": scheduled_eta.isoformat(),
            "ata": actual_arrival.isoformat() if actual_arrival else None,
            "etb": None, "atb": now.isoformat() if stage in (BERTH_OCCUPYING_STAGES - {"Berthing"}) else None,
            "etd": None, "atd": None,
            "cargo_type": random.choice(["Containers", "Bulk Dry", "Bulk Liquid", "General"]) if stage in BERTH_OCCUPYING_STAGES else None,
            "cargo_quantity": round(random.uniform(500, 80_000), 1) if stage in BERTH_OCCUPYING_STAGES else None,
            "berth_waiting_time": None, "berth_time_hours": None, "turnaround_hours": None,
            "berth_conflict_flag": int(berth_queue >= 5),
            "congestion_level_future": None, "queue_length_future": None,
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Live port state ("right now" snapshot, aggregated, not historical)
# ─────────────────────────────────────────────────────────────────────────────

def generate_live_port_state(vessels_df: pd.DataFrame, berths_df: pd.DataFrame, now: datetime) -> pd.DataFrame:
    rows = []
    for code, name, *_ in PORT_DEFS:
        at_port = vessels_df[vessels_df["current_port"] == code]
        stage_counts = at_port["current_lifecycle_stage"].value_counts().to_dict()

        port_berths = berths_df[berths_df["port_code"] == code]
        occupied  = (port_berths["status"] == "Occupied").sum()
        available = (port_berths["status"] == "Available").sum()
        reserved  = (port_berths["status"] == "Reserved").sum()
        maint     = port_berths["status"].isin(["Maintenance", "Cleaning"]).sum()
        utilization = round(occupied / len(port_berths), 3)

        queue_length = stage_counts.get("Anchored", 0) + stage_counts.get("Waiting", 0)
        weather = sample_weather(now.month, now.hour)

        # Congestion driven by what's actually happening at this port right
        # now — berth utilization + queue pressure + weather severity — not
        # an independent random draw, so it can never silently disagree with
        # the berth/queue numbers in this same row (Task 8).
        weather_severity = clamp(weather["wave_height_m"] / 7.0, 0, 1) * 0.5 + clamp(weather["wind_speed_knots"] / 60.0, 0, 1) * 0.5
        base_load = PORT_BASE_LOAD[code]
        congestion_index = round(clamp(
            0.45 * utilization + 0.25 * clamp(queue_length / 12, 0, 1) + 0.15 * weather_severity + 0.15 * base_load,
            0, 1,
        ), 3)

        rows.append({
            "port_code": code, "port_name": name, "snapshot_time": now.isoformat(),
            "active_vessels":     int(at_port.shape[0]),
            "at_sea_vessels":     int(stage_counts.get("At Sea", 0)),
            "approaching_vessels": int(stage_counts.get("Approaching", 0)),
            "anchored_vessels":   int(stage_counts.get("Anchored", 0)),
            "waiting_vessels":    int(stage_counts.get("Waiting", 0)),
            "berthed_vessels":    int(stage_counts.get("Berthing", 0) + stage_counts.get("Berthed", 0) + stage_counts.get("Cargo Operations", 0)),
            "departing_vessels":  int(stage_counts.get("Departing", 0)),
            "queue_length":       int(queue_length),
            "congestion_index":   congestion_index,
            "congestion_label":   congestion_label(congestion_index),
            "wind_speed_knots":   weather["wind_speed_knots"], "wave_height_m": weather["wave_height_m"],
            "visibility_km":      weather["visibility_km"], "temperature_c": weather["temperature_c"],
            "precipitation_mm":   weather["precipitation_mm"],
            "crane_utilization":  round(clamp(0.5 + utilization * 0.4 + np.random.normal(0, 0.05), 0, 1), 3),
            "berth_utilization":  utilization,
            "occupied_berths":    int(occupied), "available_berths": int(available),
            "reserved_berths":    int(reserved), "maintenance_berths": int(maint),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Validation (Task 10)
# ─────────────────────────────────────────────────────────────────────────────

def validate(vessels_df, ports_df, berths_df, visits_df, live_state_df) -> tuple[bool, list[str]]:
    checks: list[tuple[str, bool, str]] = []

    def check(name, condition, detail=""):
        checks.append((name, bool(condition), detail))

    # Identity
    check("No duplicate vessel names", vessels_df["name"].is_unique)
    check("No duplicate IMO numbers", vessels_df["imo_number"].is_unique)
    check("No duplicate MMSI", vessels_df["mmsi"].is_unique)
    check("All IMO numbers pass check-digit validation", vessels_df["imo_number"].apply(is_valid_imo).all())
    check("All MMSI are valid 9-digit values", vessels_df["mmsi"].apply(is_valid_mmsi).all())
    check("No anonymous placeholder vessel names (e.g. V00001-style)",
          not vessels_df["name"].str.match(r"^V\d{5}$").any())

    # Referential integrity
    valid_vessel_ids = set(vessels_df["vessel_id"])
    valid_berth_ids  = set(berths_df["berth_id"])
    valid_port_codes = set(ports_df["port_code"])
    check("No orphan visits (every visit.vessel_id exists in vessels.csv)",
          visits_df["vessel_id"].isin(valid_vessel_ids).all())
    assigned = visits_df["assigned_berth"].dropna()
    check("No orphan visit->berth references",
          assigned.isin(valid_berth_ids).all() if len(assigned) else True)
    check("Every visit.port_id is a real port",
          visits_df["port_id"].isin(valid_port_codes).all())
    occ_berths = berths_df[berths_df["status"] == "Occupied"]
    check("No orphan occupied berths (every Occupied berth's vessel exists and is in a berth-occupying stage)",
          occ_berths["occupying_vessel_id"].apply(
              lambda vid: vid in valid_vessel_ids and
              vessels_df.loc[vessels_df["vessel_id"] == vid, "current_lifecycle_stage"].iloc[0] in BERTH_OCCUPYING_STAGES
          ).all() if len(occ_berths) else True)

    # Berth occupancy consistency (Task 8's central example)
    n_occupying_vessels = vessels_df["current_lifecycle_stage"].isin(BERTH_OCCUPYING_STAGES).sum()
    n_occupied_berths    = (berths_df["status"] == "Occupied").sum()
    check(f"Occupied berths ({n_occupied_berths}) exactly equals berth-occupying vessels ({n_occupying_vessels})",
          n_occupied_berths == n_occupying_vessels)
    check("Berth status counts sum to total berth count (no berth double-counted/missing)",
          berths_df["status"].value_counts().sum() == len(berths_df))
    check("Occupied berth count falls in a realistic operational range (30-75 of 96)",
          30 <= n_occupied_berths <= 75)
    check("Available berth count falls in a realistic operational range (15-40 of 96)",
          15 <= (berths_df["status"] == "Available").sum() <= 40)

    # Vessel lifecycle distribution sanity
    total = len(vessels_df)
    at_sea_pct = (vessels_df["current_lifecycle_stage"] == "At Sea").sum() / total
    check("At-Sea vessels form the large majority (70-90%), not ~100%",
          0.70 <= at_sea_pct <= 0.90, f"actual={at_sea_pct:.1%}")
    check("At least one vessel in every lifecycle stage",
          set(vessels_df["current_lifecycle_stage"].unique()) == set(LIFECYCLE_STAGES))

    # Timestamps
    completed = visits_df[visits_df["visit_status"] == "Completed"]
    check("All completed visits have both scheduled_eta and actual_arrival_time",
          completed[["scheduled_eta", "actual_arrival_time"]].notna().all().all())
    check("No completed visit's actual_arrival_time is in the future",
          (pd.to_datetime(completed["actual_arrival_time"]) <= pd.Timestamp(datetime.utcnow())).all())
    in_progress = visits_df[visits_df["visit_status"] != "Completed"]
    not_arrived = in_progress[in_progress["visit_status"] == "Approaching"]
    check("In-progress 'Approaching' visits correctly have no actual_arrival_time yet (not fabricated)",
          not_arrived["actual_arrival_time"].isna().all() if len(not_arrived) else True)

    # Congestion realism
    congestion_values = live_state_df["congestion_index"]
    check("Congestion index is within [0,1] for every port",
          congestion_values.between(0, 1).all())
    check("Congestion varies meaningfully across ports (stddev > 0.05, not all ~identical)",
          congestion_values.std() > 0.05, f"stddev={congestion_values.std():.3f}")
    check("Not every port has the same congestion label",
          live_state_df["congestion_label"].nunique() > 1)
    check("Queue length is non-negative for every port",
          (live_state_df["queue_length"] >= 0).all())

    # AI-compatibility — exact raw feature columns the trained models require
    REQUIRED_ETA_RAW_COLUMNS = {
        "vessel_type", "loa_m", "draft_m", "gross_tonnage", "engine_power_kw",
        "vessel_age_years", "latitude", "longitude", "speed_knots", "heading",
        "distance_to_port_nm", "timestamp", "scheduled_eta", "month", "hour",
        "day_of_week", "is_weekend", "is_night", "estimated_service_time_hours",
        "wind_speed_knots", "wave_height_m", "visibility_km", "precipitation_mm",
        "temperature_c", "port_id", "berth_id" if "berth_id" in visits_df.columns else "assigned_berth",
        "berth_max_length", "berth_queue_length", "crane_availability_ratio",
        "port_congestion_index", "traffic_density", "port_avg_delay_last_24h",
        "actual_delay_minutes", "berth_available_from",
    }
    missing_cols = REQUIRED_ETA_RAW_COLUMNS - set(visits_df.columns)
    check("vessel_visits.csv retains every raw feature column the trained ETA/congestion models require",
          len(missing_cols) == 0, f"missing={missing_cols}" if missing_cols else "")

    all_ok = all(c[1] for c in checks)
    return all_ok, checks


def format_report(checks: list[tuple[str, bool, str]], counts: dict) -> str:
    lines = [
        "=" * 78,
        "  PORTFLOW AI — DIGITAL TWIN GENERATOR — VALIDATION REPORT",
        "=" * 78,
        "",
        "Dataset row counts:",
    ]
    for name, n in counts.items():
        lines.append(f"  {name:<22} {n:>8,} rows")
    lines.append("")
    lines.append("Checks:")
    n_pass = 0
    for name, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        n_pass += int(ok)
        suffix = f"  ({detail})" if detail else ""
        lines.append(f"  [{mark}] {name}{suffix}")
    lines.append("")
    lines.append(f"Result: {n_pass}/{len(checks)} checks passed.")
    lines.append("=" * 78)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def main():
    now = datetime.utcnow()
    print("=" * 60)
    print("  PortFlow AI — Digital Twin Generator (Phase 4.1)")
    print("=" * 60)

    print("\n[1/6] Generating vessels (persistent identity + lifecycle state)...")
    vessels_df = generate_vessels(N_VESSELS)

    print("[2/6] Generating ports...")
    ports_df = generate_ports()

    print("[3/6] Generating berths (occupancy derived from vessel state)...")
    berths_df, demotions = generate_berths(vessels_df)
    if demotions:
        print(f"  ↳ {len(demotions)} vessel(s) demoted to 'Waiting' — their port had more "
              f"berth-occupying vessels than berths (queued instead of an invented berth).")
        for vid, new_stage in demotions.items():
            vessels_df.loc[vessels_df["vessel_id"] == vid, "current_lifecycle_stage"] = new_stage
            # Demoted vessels are no longer alongside — pull them back to anchorage
            # position/speed so current_lat/lon stays consistent with "Waiting".
            vessels_df.loc[vessels_df["vessel_id"] == vid, "current_speed_knots"] = 0.0

    print("[4/6] Generating visits (historical + in-progress)...")
    visits_df = generate_visits(vessels_df, berths_df, now)

    print("[5/6] Generating live port state snapshot...")
    live_state_df = generate_live_port_state(vessels_df, berths_df, now)

    print("[6/6] Validating internal consistency...")
    ok, checks = validate(vessels_df, ports_df, berths_df, visits_df, live_state_df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Drop the internal-only helper column before writing vessels.csv — it's
    # a join key for this generator run, not part of the public schema.
    vessels_out = vessels_df.rename(columns={"vessel_id": "vessel_ref_id"})
    vessels_out.to_csv(OUT_DIR / "vessels.csv", index=False)
    ports_df.to_csv(OUT_DIR / "ports.csv", index=False)
    berths_df.to_csv(OUT_DIR / "berths.csv", index=False)
    visits_df.to_csv(OUT_DIR / "vessel_visits.csv", index=False)
    live_state_df.to_csv(OUT_DIR / "live_port_state.csv", index=False)

    counts = {
        "vessels.csv": len(vessels_df),
        "ports.csv": len(ports_df),
        "berths.csv": len(berths_df),
        "vessel_visits.csv": len(visits_df),
        "live_port_state.csv": len(live_state_df),
    }
    report = format_report(checks, counts)
    print("\n" + report)

    (OUT_DIR / "VALIDATION_REPORT.txt").write_text(report, encoding="utf-8")

    print(f"\nFiles written to: {OUT_DIR}")
    if not ok:
        raise SystemExit("Validation FAILED — see report above.")
    print("\nDone. All validation checks passed. 🚢")


if __name__ == "__main__":
    main()
