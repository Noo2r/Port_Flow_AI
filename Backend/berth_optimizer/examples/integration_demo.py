"""
Integration Demo
================
End-to-end Smart Port pipeline:
    ETA Model Output → Berth Optimization Engine → Allocation Result

Run from the project root (models/ folder):
    python berth_optimizer/examples/integration_demo.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Make package importable from any working directory
sys.path.insert(0, str(Path(__file__).parents[2]))

from berth_optimizer.engine.optimizer import BerthOptimizationEngine, BerthSlot, VesselRequest
from berth_optimizer.utils.data_loader import (
    load_dataset, extract_berth_slots, extract_vessel_requests,
    vessel_request_from_json, berth_slot_from_json, _find_dataset,
)

EXAMPLE_REQUEST = {
    "vessel_id": "MSC-AURORA-001",
    "predicted_eta": "2025-07-15T14:30:00",
    "predicted_delay_minutes": 35.0,
    "vessel_type": "Container",
    "loa_m": 210.0,
    "draft_m": 12.5,
    "gross_tonnage": 75000.0,
    "vessel_age_years": 8.0,
    "speed_knots": 15.0,
    "distance_to_port_nm": 85.0,
    "port_congestion_index": 0.62,
    "traffic_density": "High",
    "port_avg_delay_last_24h": 28.5,
    "estimated_service_time_hours": 8.0,
    "timestamp": "2025-07-15T10:00:00",
    "hour": 14,
    "day_of_week": 1,
    "is_weekend": False,
    "is_night": False,
}

EXAMPLE_BERTHS = [
    {"berth_id": "BERTH-A1", "berth_max_length": 280.0, "berth_queue_length": 1,
     "berth_available_from": "2025-07-15T13:00:00", "crane_availability_ratio": 0.90},
    {"berth_id": "BERTH-B2", "berth_max_length": 220.0, "berth_queue_length": 3,
     "berth_available_from": "2025-07-15T12:00:00", "crane_availability_ratio": 0.70},
    {"berth_id": "BERTH-C3", "berth_max_length": 180.0, "berth_queue_length": 0,
     "berth_available_from": "2025-07-15T14:00:00", "crane_availability_ratio": 0.95},
    {"berth_id": "BERTH-D4", "berth_max_length": 320.0, "berth_queue_length": 2,
     "berth_available_from": "2025-07-15T16:00:00", "crane_availability_ratio": 0.85},
]


def run_demo():
    print("\n" + "=" * 65)
    print("  Smart Port — Berth Optimization Demo")
    print("  Pipeline Stage 2: ETA Outputs → Berth Allocation")
    print("=" * 65)

    vessel = vessel_request_from_json(EXAMPLE_REQUEST)
    berths = [berth_slot_from_json(b) for b in EXAMPLE_BERTHS]

    print("\n[Berth Candidates]")
    for b in berths:
        print(f"  {b.berth_id:<12} max_len={b.berth_max_length}m  "
              f"queue={b.berth_queue_length}  cranes={b.crane_availability_ratio:.0%}  "
              f"avail={b.berth_available_from[:16]}")

    engine = BerthOptimizationEngine()
    result = engine.allocate(vessel, berths)

    print("\n[Allocation Result]")
    api_resp = result.to_api_response()
    for k, v in api_resp.items():
        print(f"  {k:<30} = {v}")

    print("\n[Example API JSON Request]")
    print(json.dumps(EXAMPLE_REQUEST, indent=2))

    print("\n[Example API JSON Response]")
    print(json.dumps(api_resp, indent=2))

    print("\n[Port KPIs]")
    for k, v in engine.get_port_kpis().items():
        print(f"  {k:<35} = {v}")

    # Batch demo with dataset
    print("\n[Batch Allocation Demo — using dataset]")
    try:
        csv_path = _find_dataset()
        df = load_dataset(csv_path)
        berths_data  = extract_berth_slots(df)
        vessels_data = extract_vessel_requests(df, n=10)
        batch_engine = BerthOptimizationEngine()
        wait_times   = []
        for v in vessels_data:
            r = batch_engine.allocate(v, berths_data)
            wait_times.append(r.waiting_time_minutes)
        bk = batch_engine.get_port_kpis()
        print(f"  Vessels processed    : {len(vessels_data)}")
        print(f"  Avg waiting time     : {sum(wait_times)/len(wait_times):.1f} min")
        print(f"  Max waiting time     : {max(wait_times):.1f} min")
        print(f"  Berth utilization    : {bk['avg_berth_utilization']:.1%}")
        print(f"  Conflicts detected   : {bk['conflict_count']}")
    except Exception as e:
        print(f"  (dataset not available — skipping batch demo: {e})")

    print("\n✓ Demo complete.\n")
    return result


if __name__ == "__main__":
    run_demo()
