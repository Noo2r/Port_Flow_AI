"""
Berth Optimization Service
==========================
Wraps the Stage-2 BerthOptimizationEngine as a module-level singleton.
Loaded once at startup; allocate() is thread-safe and side-effect-free
(save for updating the in-memory allocation registry).
"""
from __future__ import annotations

import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from berth_optimizer.engine.optimizer import BerthOptimizationEngine, VesselRequest, BerthSlot
from berth_optimizer.utils.data_loader import (
    load_dataset, extract_berth_slots, vessel_request_from_json,
)

# ── Singleton engine ──────────────────────────────────────────────────────────
_engine: BerthOptimizationEngine | None = None
_berth_registry: list[BerthSlot] = []

# Auto-cleanup: every CLEANUP_INTERVAL_ROWS processed allocations, sweep
# clear_expired_allocations() so the in-memory allocation list doesn't grow
# unbounded over a long-running session (matches the original design spec
# of "~every 200 processed rows"). A time-based backstop also runs from the
# app's 6-hour maintenance loop (app/main.py) for low-traffic sessions that
# never hit this row count.
CLEANUP_INTERVAL_ROWS = 200
_allocation_count = 0


def _init_engine() -> None:
    """Load the engine and berth registry from the CSV dataset."""
    global _engine, _berth_registry
    try:
        _engine = BerthOptimizationEngine()
        csv_path = (
            Path(__file__).parents[2]  # A-Backend/
            / "berth_optimizer"
            / "port_flow_dataset.csv"
        )
        if not csv_path.exists():
            warnings.warn(f"Berth dataset not found at {csv_path}. Berth allocations will fail.")
            return
        df = load_dataset(csv_path)
        _berth_registry = extract_berth_slots(df)
        logger.info("Loaded %d berths from dataset.", len(_berth_registry))
    except Exception as exc:
        warnings.warn(f"[berth_service] Failed to initialise: {exc}")


_init_engine()


# ── Public helpers ────────────────────────────────────────────────────────────

def get_engine() -> BerthOptimizationEngine:
    if _engine is None:
        raise RuntimeError("Berth optimization engine not loaded.")
    return _engine


def get_berth_registry() -> list[BerthSlot]:
    return _berth_registry


def allocate_berth_for_vessel(
    vessel_id: str,
    predicted_eta: str,
    predicted_delay_minutes: float,
    vessel_type: str,
    loa_m: float,
    draft_m: float,
    gross_tonnage: float,
    vessel_age_years: float,
    speed_knots: float,
    distance_to_port_nm: float,
    port_congestion_index: float,
    traffic_density: str,
    port_avg_delay_last_24h: float,
    estimated_service_time_hours: float = 6.0,
    port_id: str = "",
    timestamp: Optional[str] = None,
    hour: Optional[int] = None,
    day_of_week: Optional[int] = None,
    is_weekend: Optional[bool] = None,
    is_night: Optional[bool] = None,
    priority: int = 0,
    wave_height_m: float = 1.5,
) -> dict:
    """
    Build a VesselRequest from ETA model outputs + vessel data,
    run the berth optimizer, and return the allocation response dict.
    """
    engine = get_engine()
    berths = get_berth_registry()
    if not berths:
        raise RuntimeError(
            "No berths in registry — port_flow_dataset.csv may be missing."
        )

    # Derive time context from predicted_eta if not provided.
    # IMPORTANT: strip timezone to naive UTC — the berth optimizer compares
    # predicted_eta with berth_available_from values loaded from the CSV
    # which are always timezone-naive (pandas default). Mixing aware+naive
    # raises TypeError inside optimizer.py (which we must not modify).
    try:
        eta_dt = datetime.fromisoformat(predicted_eta.replace("Z", "+00:00"))
        # Convert to naive UTC
        if eta_dt.tzinfo is not None:
            from datetime import timezone
            eta_dt = eta_dt.astimezone(timezone.utc).replace(tzinfo=None)
        predicted_eta_naive = eta_dt.isoformat()
    except Exception:
        eta_dt = datetime.utcnow()
        predicted_eta_naive = eta_dt.isoformat()

    # Also make timestamp naive
    try:
        ts_raw = timestamp or datetime.utcnow().isoformat()
        ts_dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        if ts_dt.tzinfo is not None:
            from datetime import timezone
            ts_dt = ts_dt.astimezone(timezone.utc).replace(tzinfo=None)
        timestamp_naive = ts_dt.isoformat()
    except Exception:
        timestamp_naive = datetime.utcnow().isoformat()

    payload = {
        "vessel_id": vessel_id,
        "predicted_eta": predicted_eta_naive,
        "predicted_delay_minutes": predicted_delay_minutes,
        "vessel_type": vessel_type,
        "loa_m": loa_m,
        "draft_m": draft_m,
        "gross_tonnage": gross_tonnage,
        "vessel_age_years": vessel_age_years,
        "speed_knots": speed_knots,
        "distance_to_port_nm": distance_to_port_nm,
        "port_id": port_id,
        "port_congestion_index": port_congestion_index,
        "traffic_density": traffic_density,
        "port_avg_delay_last_24h": port_avg_delay_last_24h,
        "estimated_service_time_hours": estimated_service_time_hours,
        "timestamp": timestamp_naive,
        "hour": hour if hour is not None else eta_dt.hour,
        "day_of_week": day_of_week if day_of_week is not None else eta_dt.weekday(),
        "is_weekend": is_weekend if is_weekend is not None else (eta_dt.weekday() >= 5),
        "is_night": is_night if is_night is not None else (eta_dt.hour < 6 or eta_dt.hour > 20),
        "priority": priority,
        "wave_height_m": wave_height_m,
    }

    vessel_req = vessel_request_from_json(payload)
    result = engine.allocate(vessel_req, berths)

    global _allocation_count
    _allocation_count += 1
    if _allocation_count % CLEANUP_INTERVAL_ROWS == 0:
        removed = engine.clear_expired_allocations()
        from app.core.logging_config import logger
        logger.info(
            "berth_service | auto-cleanup at %d allocations — removed %d expired",
            _allocation_count, removed,
        )

    return result.to_api_response()


def get_berth_status() -> dict:
    engine = get_engine()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "berths": engine.get_berth_status(get_berth_registry()),
    }


def get_port_kpis() -> dict:
    engine = get_engine()
    kpis = engine.get_port_kpis()
    kpis["timestamp"] = datetime.utcnow().isoformat()
    return kpis


def get_active_allocations() -> dict:
    engine = get_engine()
    allocations = engine.get_active_allocations()
    return {
        "count": len(allocations),
        "allocations": [a.to_dict() for a in allocations],
    }


def clear_expired_allocations(cutoff_hours: int = 48) -> dict:
    engine = get_engine()
    removed = engine.clear_expired_allocations(cutoff_hours)
    return {
        "removed": removed,
        "remaining": len(engine.get_active_allocations()),
    }
