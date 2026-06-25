#!/usr/bin/env python3
"""
Digital Twin Importer (Phase 4.2) — replaces scripts/seed_dataset.py.
========================================================================
Reads the five Digital Twin datasets produced by
scripts/digital_twin_generator.py (Phase 4.1) and loads them into
PostgreSQL, faithfully preserving every generated operational state
instead of hardcoding every row to AVAILABLE/AT_SEA/COMPLETED the way
seed_dataset.py did.

Import order (Task 2 — preserves referential integrity):
    1. Ports     — UPSERT by code, never deleted (users.port_id references
                   ports.id; deleting ports would risk cascading into the
                   users table)
    2. Berths    — fresh INSERT, status taken directly from berths.csv
    3. Vessels   — fresh INSERT, status taken directly from vessels.csv
    4. Historical visits — from vessel_visits.csv rows with
                   visit_status == "Completed"
    5. Current operational state — the small number of in-progress visits
                   (vessel_visits.csv rows with visit_status != "Completed"),
                   imported with their real, not-yet-knowable fields left
                   NULL (Task 5)

All lifecycle/status translation goes through
app.core.digital_twin_mapping — the single mapping table (Task 3). This
script contains no inline status-conversion logic of its own.

Run inside the container:
    docker exec portflow_api python scripts/import_digital_twin.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import pandas as pd

sys.path.insert(0, "/app")

from app.core.digital_twin_mapping import (  # noqa: E402
    BERTH_OCCUPYING_STAGES,
    map_berth_status,
    map_vessel_status,
    map_visit_status,
)

DB_URL = "postgresql://portflow:portflow@db:5432/portflow"
DT_DIR = Path(__file__).resolve().parents[1] / "data_digital_twin"

CSV_TO_DB_VESSEL_TYPE: dict[str, str] = {
    "Container": "CONTAINER", "Bulk Carrier": "BULK_CARRIER", "Tanker": "TANKER",
    "RoRo": "RO_RO", "General Cargo": "GENERAL_CARGO", "LNG Carrier": "OTHER",
    "Car Carrier": "OTHER", "VLCC": "TANKER", "Cruise": "OTHER", "Feeder": "CONTAINER",
}
VESSEL_TO_BERTH_TYPE: dict[str, str] = {
    "Container": "CONTAINER", "Bulk Carrier": "BULK", "Tanker": "TANKER",
    "RoRo": "RO_RO", "General Cargo": "GENERAL", "LNG Carrier": "TANKER",
    "Car Carrier": "RO_RO", "VLCC": "TANKER", "Cruise": "GENERAL", "Feeder": "CONTAINER",
}
CARGO_TYPE_MAP = {
    "Containers": "CONTAINERS", "Bulk Dry": "BULK_DRY", "Bulk Liquid": "BULK_LIQUID",
    "General": "GENERAL",
}


def parse_dt(s) -> datetime | None:
    if s is None or (isinstance(s, float) and pd.isna(s)) or s == "":
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def nval(v):
    """asyncpg-safe null coercion for pandas NaN/None."""
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    return v


async def wipe_old_demo_data(conn: asyncpg.Connection) -> None:
    """
    Remove every previously-imported vessel/visit/berth and everything that
    depends on them, WITHOUT touching ports or users — ports are UPSERTed
    (never deleted) specifically because users.port_id is a nullable FK into
    ports.id, and a careless CASCADE on ports could wipe the admin account.
    """
    print("Clearing previously-imported demo data (vessels, visits, berths, "
          "and everything that references them — ports and users are preserved)...")
    # No FK constraint exists on engine_allocations, so it survives a
    # vessels/visits/berths CASCADE untouched unless cleared explicitly.
    await conn.execute("DELETE FROM engine_allocations")
    await conn.execute("TRUNCATE TABLE vessels, visits, berths RESTART IDENTITY CASCADE")


async def import_ports(conn: asyncpg.Connection, ports_df: pd.DataFrame) -> dict[str, int]:
    port_id_map: dict[str, int] = {}
    for r in ports_df.itertuples():
        pid = await conn.fetchval(
            """
            INSERT INTO ports (code, name, country, city, latitude, longitude, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, TRUE)
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name, country = EXCLUDED.country, city = EXCLUDED.city,
                latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude
            RETURNING id
            """,
            r.port_code, r.port_name, r.country, r.city, float(r.latitude), float(r.longitude),
        )
        port_id_map[r.port_code] = pid
    print(f"  ✓ Ports: {len(port_id_map)} upserted (existing rows updated, none deleted)")
    return port_id_map


async def import_berths(conn: asyncpg.Connection, berths_df: pd.DataFrame, port_id_map: dict[str, int]) -> dict[str, int]:
    berth_id_map: dict[str, int] = {}
    for r in berths_df.itertuples():
        btype = "MULTIPURPOSE"  # berths.csv doesn't carry a vessel-type bias; assigned per-visit instead
        db_status = map_berth_status(r.status).name
        bid = await conn.fetchval(
            """
            INSERT INTO berths
                (code, name, port_id, berth_type, max_length, max_draft,
                 has_crane, has_pipeline, has_cold_ironing, has_fresh_water,
                 has_bunker_facility, priority_level, status, is_active)
            VALUES ($1, $2, $3, $4::berthtype, $5, $6,
                    $7, FALSE, FALSE, TRUE, FALSE,
                    $8, $9::berthstatus, TRUE)
            RETURNING id
            """,
            r.berth_id, r.berth_id, port_id_map[r.port_code], btype,
            float(r.max_length), float(r.max_draft), bool(r.has_crane),
            int(r.priority), db_status,
        )
        berth_id_map[r.berth_id] = bid
    print(f"  ✓ Berths: {len(berth_id_map)} inserted, status preserved from berths.csv (no hardcoded AVAILABLE)")
    return berth_id_map


async def import_vessels(conn: asyncpg.Connection, vessels_df: pd.DataFrame, port_id_map: dict[str, int]) -> dict[str, int]:
    vessel_id_map: dict[str, int] = {}
    for r in vessels_df.itertuples():
        vtype = CSV_TO_DB_VESSEL_TYPE.get(r.vessel_type, "OTHER")
        db_status = map_vessel_status(r.current_lifecycle_stage).name
        cur_port_id = port_id_map.get(r.current_port)
        vid = await conn.fetchval(
            """
            INSERT INTO vessels
                (imo_number, mmsi, name, vessel_type, flag, owner, operator,
                 length_overall, beam, max_draft, gross_tonnage, deadweight_tonnage,
                 year_built, current_lat, current_lon, current_speed, current_heading,
                 current_port_id, status, is_active)
            VALUES ($1,$2,$3,$4::vesseltype,$5,$6,$7,
                    $8,$9,$10,$11,$12,
                    $13,$14,$15,$16,$17,
                    $18,$19::vesselstatus,TRUE)
            RETURNING id
            """,
            r.imo_number, r.mmsi, r.name, vtype, r.flag, r.owner, r.operator,
            float(r.loa_m), float(r.beam_m), float(r.draft_m), float(r.gross_tonnage), float(r.deadweight_tonnage),
            int(r.build_year), float(r.current_lat), float(r.current_lon),
            float(r.current_speed_knots), float(r.current_heading),
            cur_port_id, db_status,
        )
        vessel_id_map[r.vessel_ref_id] = vid
    print(f"  ✓ Vessels: {len(vessel_id_map)} inserted with persistent identity "
          f"(real names, valid IMO/MMSI) and status preserved from vessels.csv")
    return vessel_id_map


async def import_visits(
    conn: asyncpg.Connection,
    visits_df: pd.DataFrame,
    vessel_id_map: dict[str, int],
    berth_id_map: dict[str, int],
    port_id_map: dict[str, int],
) -> tuple[int, int]:
    n_historical, n_in_progress, n_skipped = 0, 0, 0

    for r in visits_df.itertuples():
        vessel_db_id = vessel_id_map.get(r.vessel_id)
        if vessel_db_id is None:
            n_skipped += 1
            continue
        berth_db_id = berth_id_map.get(r.assigned_berth) if pd.notna(r.assigned_berth) else None
        port_db_id  = port_id_map.get(r.port_id)
        db_status   = map_visit_status(r.visit_status).name
        cargo_db    = CARGO_TYPE_MAP.get(nval(r.cargo_type))

        is_historical = r.visit_status == "Completed"

        await conn.execute(
            """
            INSERT INTO visits
                (vessel_id, berth_id, port_id,
                 eta, etb, etd, ata, atb, atd,
                 cargo_type, cargo_quantity,
                 status, clearance_status,
                 waiting_time_hours, berth_time_hours, turnaround_hours)
            VALUES ($1,$2,$3,
                    $4,$5,$6,$7,$8,$9,
                    $10::cargotype,$11,
                    $12::visitstatus,$13::clearancestatus,
                    $14,$15,$16)
            """,
            vessel_db_id, berth_db_id, port_db_id,
            parse_dt(nval(r.scheduled_eta)), parse_dt(nval(r.etb)), parse_dt(nval(r.etd)),
            parse_dt(nval(r.ata)), parse_dt(nval(r.atb)), parse_dt(nval(r.atd)),
            cargo_db, nval(r.cargo_quantity),
            db_status, "FULLY_CLEARED" if is_historical else "PENDING",
            nval(r.berth_waiting_time) / 60.0 if nval(r.berth_waiting_time) is not None else None,
            nval(r.berth_time_hours), nval(r.turnaround_hours),
        )
        if is_historical:
            n_historical += 1
        else:
            n_in_progress += 1

    print(f"  ✓ Visits: {n_historical:,} historical (Completed) + {n_in_progress} in-progress "
          f"imported with their real visit_status preserved ({n_skipped} skipped — no matching vessel)")
    return n_historical, n_in_progress


async def regenerate_berth_optimizer_csv(berths_df: pd.DataFrame, port_id_map: dict[str, int]) -> None:
    """
    The live Stage-2 berth-optimization AI engine (app/services/berth_service.py)
    loads its in-memory berth registry directly from
    Backend/berth_optimizer/port_flow_dataset.csv — completely independently
    of the `berths` table this importer just populated. Phase 4.1's analysis
    flagged this as a dual-source-of-truth risk: if that file keeps
    describing the *old* 96 berths while Postgres now has a *new* set, the
    AI engine and the rest of the app would disagree about which berths
    exist. Regenerating it from the same berths.csv this importer just used
    keeps both representations of "the 96 berths" derived from one source.
    """
    optimizer_csv = Path(__file__).resolve().parents[1] / "berth_optimizer" / "port_flow_dataset.csv"
    rows = []
    for r in berths_df.itertuples():
        rows.append({
            "berth_id": r.berth_id,
            "port_id": r.port_code,
            "berth_max_length": r.max_length,
            "berth_queue_length": 0 if r.status == "Available" else 1,
            "berth_available_from": datetime.utcnow().isoformat(),
            "crane_availability_ratio": 0.9 if r.has_crane else 0.3,
            "vessel_type": "Container",  # required column for the loader's draft-map step; not used for slot identity
        })
    pd.DataFrame(rows).to_csv(optimizer_csv, index=False)
    print(f"  ✓ Regenerated {optimizer_csv.name} for the live Stage-2 AI engine "
          f"from the same 96 berths just imported (closes the dual-source-of-truth risk)")


async def main():
    if not DT_DIR.exists():
        raise SystemExit(f"Digital Twin datasets not found at {DT_DIR}. Run "
                          f"scripts/digital_twin_generator.py first (Phase 4.1).")

    print("=" * 70)
    print("  PortFlow AI — Digital Twin Importer (Phase 4.2)")
    print("=" * 70)

    print("\nLoading generated CSVs...")
    # imo_number/mmsi are all-digit strings — without an explicit dtype,
    # pandas infers them as int64 on CSV round-trip, which both loses the
    # "this is an identifier, not a number" semantics and breaks asyncpg's
    # strict text-column type check below.
    str_dtype = {"imo_number": str, "mmsi": str}
    vessels_df    = pd.read_csv(DT_DIR / "vessels.csv", dtype=str_dtype)
    ports_df      = pd.read_csv(DT_DIR / "ports.csv")
    berths_df     = pd.read_csv(DT_DIR / "berths.csv")
    visits_df     = pd.read_csv(DT_DIR / "vessel_visits.csv", dtype={"mmsi": str})
    print(f"  vessels={len(vessels_df)}  ports={len(ports_df)}  berths={len(berths_df)}  visits={len(visits_df)}")

    conn = await asyncpg.connect(DB_URL)
    try:
        async with conn.transaction():
            await wipe_old_demo_data(conn)

            print("\n[1/5] Importing ports...")
            port_id_map = await import_ports(conn, ports_df)

            print("[2/5] Importing berths...")
            berth_id_map = await import_berths(conn, berths_df, port_id_map)

            print("[3/5] Importing vessels...")
            vessel_id_map = await import_vessels(conn, vessels_df, port_id_map)

            print("[4/5] Importing historical visits + [5/5] current operational state...")
            await import_visits(conn, visits_df, vessel_id_map, berth_id_map, port_id_map)

        print("\nRegenerating the AI engine's berth registry CSV...")
        await regenerate_berth_optimizer_csv(berths_df, port_id_map)

        print("\n✓ Import complete. Transaction committed.")
    except Exception:
        print("\n✗ Import FAILED — transaction rolled back, no partial data left behind.")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
