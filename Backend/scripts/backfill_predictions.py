#!/usr/bin/env python3
"""
Prediction Backfill (Phase 4.4/4.5) — populates the `predictions` table.
================================================================================
Root-cause finding (Phase 4.5, Task 3): the first backfill pass fed the model
only ~8 of its ~38 trained features (vessel specs + scheduled_eta), leaving
weather, queue, congestion, distance, speed, etc. at the model's internal
zero/None defaults. That is *not* dataset drift — it is an incomplete
feature vector, which is why confidence was flat at 95.1% (the confidence
formula's only inputs, wave_height_m and berth_queue_length, were always 0)
and MAE/R² looked catastrophic (47 min / -4.08) versus the model's real
training metrics (6.5 min / 0.82).

The fix: Digital Twin generator output (data_digital_twin/vessel_visits.csv)
already recorded the FULL real feature set for every visit — the exact same
38 columns the model was trained on (weather, queue, crane ratio, congestion
index, traffic density, distance, speed, heading, etc.) — it just never made
it into Postgres during import (Phase 4.2 only persisted the columns the
`visits` table schema has). This script reads that CSV directly and joins it
1:1 to the DB by row position, which Phase 4.2's importer preserves exactly
(`visits.id` == CSV `visit_id`, `vessels.id` == int(vessel_ref_id) — verified
empirically before writing this script). Every feature fed to the model is
therefore the genuine value the Digital Twin generated for that visit, not a
default or a fabrication.

  - Historical (Completed) visits: actual_value = the CSV's own
    `actual_delay_minutes` — the real ground truth the generator recorded,
    not a value re-derived or invented here.
  - In-progress visits: actual_value stays NULL (truthfully unknown).

SHAP per-row explanations are skipped for speed (include_shap=False) on this
bulk path; live single predictions made through the API keep full SHAP.

Run inside the container:
    docker exec portflow_api python scripts/backfill_predictions.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg
import pandas as pd

sys.path.insert(0, "/app")

from app.ml.eta_predictor import eta_predictor  # noqa: E402

DB_URL = "postgresql://portflow:portflow@db:5432/portflow"
DT_DIR = Path(__file__).resolve().parents[1] / "data_digital_twin"


def _row_to_model_input(r) -> dict:
    """The exact real feature vector the generator recorded for this visit."""
    return {
        "vessel_type":               r.vessel_type,
        "loa_m":                     float(r.loa_m),
        "draft_m":                   float(r.draft_m),
        "gross_tonnage":             float(r.gross_tonnage),
        "engine_power_kw":           float(r.engine_power_kw),
        "vessel_age_years":          float(r.vessel_age_years),
        "latitude":                  float(r.latitude)  if pd.notna(r.latitude)  else None,
        "longitude":                 float(r.longitude) if pd.notna(r.longitude) else None,
        "speed_knots":               float(r.speed_knots),
        "heading":                   float(r.heading),
        "distance_to_port_nm":       float(r.distance_to_port_nm),
        "timestamp":                 r.timestamp,
        "scheduled_eta":             r.scheduled_eta,
        "port_id":                   r.port_id,
        "traffic_density":           r.traffic_density,
        "berth_max_length":          float(r.berth_max_length) if pd.notna(r.berth_max_length) else None,
        "berth_queue_length":        int(r.berth_queue_length)  if pd.notna(r.berth_queue_length) else 0,
        "crane_availability_ratio":  float(r.crane_availability_ratio),
        "port_congestion_index":     float(r.port_congestion_index),
        "port_avg_delay_last_24h":   float(r.port_avg_delay_last_24h),
        "estimated_service_time_hours": float(r.estimated_service_time_hours),
        "wave_height_m":             float(r.wave_height_m),
        "wind_speed_knots":          float(r.wind_speed_knots),
        "visibility_km":             float(r.visibility_km),
        "precipitation_mm":          float(r.precipitation_mm),
        "temperature_c":             float(r.temperature_c),
        "berth_available_from":      r.berth_available_from,
    }


async def main():
    if eta_predictor is None:
        raise SystemExit("ETA model not loaded — cannot backfill predictions.")

    df = pd.read_csv(DT_DIR / "vessel_visits.csv", dtype={"mmsi": str})
    print(f"Loaded {len(df)} visits from the Digital Twin generator output "
          f"with their full original 38-feature snapshot.")

    conn = await asyncpg.connect(DB_URL)
    try:
        await conn.execute("DELETE FROM predictions")
        print("Cleared any previous (incomplete-feature) backfill.")

        n_hist, n_active, n_skipped = 0, 0, 0
        batch = []
        for r in df.itertuples():
            vessel_db_id = int(r.vessel_id.replace("VSL-", ""))
            visit_db_id = int(r.visit_id)
            is_historical = r.visit_status == "Completed"

            try:
                model_input = _row_to_model_input(r)
                result = eta_predictor.predict(model_input, include_shap=False)
            except Exception as exc:
                n_skipped += 1
                continue

            actual_value = None
            error_mae = None
            actual_dt = None
            if is_historical and pd.notna(r.actual_delay_minutes):
                actual_value = float(r.actual_delay_minutes)  # real ground truth from the generator
                error_mae = round(abs(result["predicted_delay_minutes"] - actual_value), 2)
                if isinstance(r.actual_arrival_time, str) and r.actual_arrival_time:
                    try:
                        actual_dt = datetime.fromisoformat(r.actual_arrival_time)
                    except Exception:
                        actual_dt = None
                n_hist += 1
            else:
                n_active += 1

            pred_dt = None
            if result["predicted_eta"]:
                try:
                    pred_dt = datetime.fromisoformat(result["predicted_eta"])
                except Exception:
                    pred_dt = None

            try:
                sched_dt = datetime.fromisoformat(r.scheduled_eta)
                created_at = sched_dt - timedelta(hours=2)
            except Exception:
                created_at = datetime.now(timezone.utc)

            batch.append((
                vessel_db_id, visit_db_id, "ETA", "COMPLETED",
                result["model_used"], "2.0.0-catboost",
                result["predicted_delay_minutes"], pred_dt, result["confidence_score"],
                result["lower_bound_minutes"], result["upper_bound_minutes"],
                actual_value, actual_dt, error_mae,
                created_at,
            ))

        await conn.executemany(
            """
            INSERT INTO predictions
                (vessel_id, visit_id, prediction_type, status,
                 model_name, model_version,
                 predicted_value, predicted_datetime, confidence_score,
                 lower_bound, upper_bound,
                 actual_value, actual_datetime, error_mae,
                 created_at, updated_at)
            VALUES ($1,$2,$3::predictiontype,$4::predictionstatus,
                    $5,$6,
                    $7,$8,$9,
                    $10,$11,
                    $12,$13,$14,
                    $15,$15)
            """,
            batch,
        )
        print(f"  ✓ {n_hist:,} historical predictions (real actual_value from the generator's own "
              f"actual_delay_minutes + real error_mae)")
        print(f"  ✓ {n_active} in-progress predictions (actual_value left NULL — not yet known)")
        if n_skipped:
            print(f"  ⚠ {n_skipped} visits skipped (model input could not be built)")
        print("✓ Backfill complete — full real feature vectors used for every row.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
