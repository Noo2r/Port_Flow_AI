"""
Data Utilities
==============
Loads port_flow_dataset.csv and converts rows into
VesselRequest + BerthSlot objects for the optimization engine.

Path resolution:  the CSV is expected at the same level as the
berth_optimizer/ package folder (i.e. the project root).
It can also be passed explicitly to load_dataset().
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from berth_optimizer.engine.optimizer import BerthSlot, VesselRequest

# ── Path resolution ──────────────────────────────────────────────────────────
# __file__ = .../berth_optimizer/utils/data_loader.py
# parents[0] = .../berth_optimizer/utils/
# parents[1] = .../berth_optimizer/          ← package root
# parents[2] = project root  (where the CSV usually lives)
#
# We check both locations and use whichever exists.

def _find_dataset() -> Path:
    """Return the path to port_flow_dataset.csv, checking two locations."""
    pkg_root     = Path(__file__).parents[1]          # berth_optimizer/
    project_root = Path(__file__).parents[2]           # models/  (one above)
    for candidate in [pkg_root / "port_flow_dataset.csv",
                      project_root / "port_flow_dataset.csv"]:
        if candidate.exists():
            return candidate
    # default – will raise FileNotFoundError when actually read
    return project_root / "port_flow_dataset.csv"

DATA_PATH = _find_dataset()


# ─── Dataset Loader ───────────────────────────────────────────────────────────

def load_dataset(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """Load the shared maritime dataset and parse datetime columns."""
    df = pd.read_csv(path)
    for col in ["timestamp", "scheduled_eta", "berth_available_from", "actual_arrival_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def extract_vessel_requests(
    df: pd.DataFrame,
    eta_outputs: Optional[list[dict]] = None,
    n: int = 20,
) -> list[VesselRequest]:
    """
    Convert dataset rows into VesselRequest objects.

    Parameters
    ----------
    df          : The full port_flow_dataset DataFrame.
    eta_outputs : Optional ETA model output dicts to merge.
                  Each dict needs: vessel_id, predicted_eta, predicted_delay_minutes.
    n           : Number of vessels to extract (random sample).
    """
    sample = df.sample(n=min(n, len(df)), random_state=42).copy()

    eta_lookup: dict[str, dict] = {}
    if eta_outputs:
        for rec in eta_outputs:
            vid = rec.get("vessel_id", "")
            if vid:
                eta_lookup[vid] = rec

    requests: list[VesselRequest] = []
    for _, row in sample.iterrows():
        vid = str(row.get("vessel_id", f"V_{_}"))

        if vid in eta_lookup:
            predicted_eta   = eta_lookup[vid]["predicted_eta"]
            predicted_delay = float(eta_lookup[vid]["predicted_delay_minutes"])
        else:
            sched = row.get("scheduled_eta", datetime.utcnow())
            if pd.notna(sched):
                predicted_eta = (
                    pd.to_datetime(sched)
                    + timedelta(minutes=float(row.get("actual_delay_minutes", 0)))
                ).isoformat()
            else:
                predicted_eta = (datetime.utcnow() + timedelta(hours=2)).isoformat()
            predicted_delay = float(row.get("actual_delay_minutes", 0))

        est_svc = float(row.get("estimated_service_time_hours", 6.0))
        min_svc = float(row["min_service_hours"]) if "min_service_hours" in row.index and pd.notna(row["min_service_hours"]) else est_svc
        max_svc = float(row["max_service_hours"]) if "max_service_hours" in row.index and pd.notna(row["max_service_hours"]) else est_svc

        vr = VesselRequest(
            vessel_id=vid,
            predicted_eta=predicted_eta,
            predicted_delay_minutes=predicted_delay,
            vessel_type=str(row.get("vessel_type", "Container")),
            loa_m=float(row.get("loa_m", 200.0)),
            draft_m=float(row.get("draft_m", 10.0)),
            gross_tonnage=float(row.get("gross_tonnage", 50000.0)),
            vessel_age_years=float(row.get("vessel_age_years", 10.0)),
            speed_knots=float(row.get("speed_knots", 14.0)),
            distance_to_port_nm=float(row.get("distance_to_port_nm", 100.0)),
            port_congestion_index=float(row.get("port_congestion_index", 0.5)),
            traffic_density=str(row.get("traffic_density", "Medium")),
            port_avg_delay_last_24h=float(row.get("port_avg_delay_last_24h", 20.0)),
            timestamp=str(row.get("timestamp", datetime.utcnow().isoformat())),
            hour=int(row.get("hour", 12)),
            day_of_week=int(row.get("day_of_week", 0)),
            is_weekend=bool(row.get("is_weekend", False)),
            is_night=bool(row.get("is_night", False)),
            estimated_service_time_hours=est_svc,
            min_service_hours=min_svc,
            max_service_hours=max_svc,
        )
        requests.append(vr)

    return requests


def extract_berth_slots(df: pd.DataFrame) -> list[BerthSlot]:
    """
    Extract unique berth configurations from the dataset.
    Returns one BerthSlot per unique berth_id.
    Reads berth_max_draft if present; defaults to 15.0 m.
    """
    berth_cols = [
        "berth_id", "berth_max_length", "berth_queue_length",
        "berth_available_from", "crane_availability_ratio",
    ]
    berths_df = df[berth_cols].drop_duplicates(subset=["berth_id"]).copy()

    if "berth_max_draft" in df.columns:
        draft_map = df.drop_duplicates(subset=["berth_id"]).set_index("berth_id")["berth_max_draft"]
    else:
        draft_map = None

    now = datetime.utcnow()
    berths: list[BerthSlot] = []
    for _, row in berths_df.iterrows():
        avail = pd.to_datetime(row["berth_available_from"], errors="coerce")
        if pd.isna(avail):
            avail = now + timedelta(hours=float(np.random.uniform(0, 4)))

        max_draft = 15.0
        if draft_map is not None and row["berth_id"] in draft_map.index:
            max_draft = float(draft_map[row["berth_id"]])

        berths.append(BerthSlot(
            berth_id=str(row["berth_id"]),
            berth_max_length=float(row["berth_max_length"]),
            berth_queue_length=int(row["berth_queue_length"]),
            berth_available_from=avail.isoformat(),
            crane_availability_ratio=float(row["crane_availability_ratio"]),
            berth_max_draft=max_draft,
        ))

    return berths


# ─── JSON ↔ Object Converters ─────────────────────────────────────────────────

def vessel_request_from_json(payload: dict) -> VesselRequest:
    """Convert an API JSON payload into a VesselRequest dataclass."""
    est_svc = float(payload.get("estimated_service_time_hours", 6.0))
    return VesselRequest(
        vessel_id=payload.get("vessel_id", "UNKNOWN"),
        predicted_eta=payload.get("predicted_eta", datetime.utcnow().isoformat()),
        predicted_delay_minutes=float(payload.get("predicted_delay_minutes", 0.0)),
        vessel_type=payload.get("vessel_type", "Container"),
        loa_m=float(payload.get("loa_m", 200.0)),
        draft_m=float(payload.get("draft_m", 10.0)),
        gross_tonnage=float(payload.get("gross_tonnage", 50000.0)),
        vessel_age_years=float(payload.get("vessel_age_years", 10.0)),
        speed_knots=float(payload.get("speed_knots", 14.0)),
        distance_to_port_nm=float(payload.get("distance_to_port_nm", 100.0)),
        port_id=str(payload.get("port_id", "")),
        port_congestion_index=float(payload.get("port_congestion_index", 0.5)),
        traffic_density=payload.get("traffic_density", "Medium"),
        port_avg_delay_last_24h=float(payload.get("port_avg_delay_last_24h", 20.0)),
        timestamp=payload.get("timestamp", datetime.utcnow().isoformat()),
        hour=int(payload.get("hour", 12)),
        day_of_week=int(payload.get("day_of_week", 0)),
        is_weekend=bool(payload.get("is_weekend", False)),
        is_night=bool(payload.get("is_night", False)),
        estimated_service_time_hours=est_svc,
        min_service_hours=payload.get("min_service_hours", est_svc),
        max_service_hours=payload.get("max_service_hours", est_svc),
        priority=int(payload.get("priority", 0)),
        wave_height_m=float(payload.get("wave_height_m", 1.5)),
    )


def berth_slot_from_json(payload: dict) -> BerthSlot:
    """Convert an API JSON payload into a BerthSlot dataclass."""
    return BerthSlot(
        berth_id=payload["berth_id"],
        berth_max_length=float(payload.get("berth_max_length", 300.0)),
        berth_queue_length=int(payload.get("berth_queue_length", 0)),
        berth_available_from=payload.get(
            "berth_available_from", datetime.utcnow().isoformat()
        ),
        crane_availability_ratio=float(payload.get("crane_availability_ratio", 0.8)),
        berth_max_draft=float(payload.get("berth_max_draft", 15.0)),
    )
