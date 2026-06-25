"""
Digital Twin lifecycle mapping — single source of truth (Phase 4.2, Task 3).

The Digital Twin generator (Backend/scripts/digital_twin_generator.py) uses
its own richer 8-stage vocabulary for "what is this vessel doing right now":

    At Sea -> Approaching -> Anchored -> Waiting -> Berthing -> Berthed
            -> Cargo Operations -> Departing

The database has two separate, coarser enums:
    app.models.vessel.VesselStatus  (5 values)
    app.models.visit.VisitStatus    (8 values, different vocabulary)
    app.models.berth.BerthStatus    (4 values — no "Cleaning")

Every place in the importer (and any future code) that needs to translate a
Digital Twin stage/status string into a database enum must import from this
module — never redefine the mapping inline. If the generator's vocabulary
changes, this is the only file that needs to change.
"""
from __future__ import annotations

from app.models.berth import BerthStatus
from app.models.vessel import VesselStatus
from app.models.visit import VisitStatus

# ── Digital Twin lifecycle stage -> VesselStatus ──────────────────────────────
# VesselStatus has no equivalent for "Waiting" (queueing) or the fine-grained
# berth-occupying sub-stages (Berthing / Cargo Operations / Departing) — they
# all collapse onto the closest coarser vessel-level state. The *visit*-level
# mapping below preserves the finer distinction; this one only describes
# "where is the vessel, physically, right now."
DT_STAGE_TO_VESSEL_STATUS: dict[str, VesselStatus] = {
    "At Sea":           VesselStatus.AT_SEA,
    "Approaching":      VesselStatus.APPROACHING,
    "Anchored":         VesselStatus.ANCHORED,
    "Waiting":          VesselStatus.ANCHORED,    # queueing at anchor for a berth
    "Berthing":         VesselStatus.BERTHED,      # alongside, mooring in progress
    "Berthed":          VesselStatus.BERTHED,
    "Cargo Operations": VesselStatus.BERTHED,      # still alongside
    "Departing":        VesselStatus.DEPARTED,     # casting off / has left the berth
}

# ── Digital Twin lifecycle stage -> VisitStatus ───────────────────────────────
# This mapping is intentionally near 1:1 — VisitStatus is the DB's
# fine-grained lifecycle enum and was designed for exactly this vocabulary.
DT_STAGE_TO_VISIT_STATUS: dict[str, VisitStatus] = {
    "At Sea":           VisitStatus.SCHEDULED,
    "Approaching":      VisitStatus.APPROACHING,
    "Anchored":         VisitStatus.ANCHORED,
    "Waiting":          VisitStatus.ANCHORED,      # no separate "waiting" value in VisitStatus
    "Berthing":         VisitStatus.BERTHING,
    "Berthed":          VisitStatus.IN_PORT,
    "Cargo Operations": VisitStatus.IN_PORT,
    "Departing":        VisitStatus.DEPARTING,
}

# vessel_visits.csv's own `visit_status` column for historical rows is
# already the literal string "Completed" (set directly by the generator,
# not one of the 8 lifecycle stages above) — mapped separately since it's
# not part of the live-snapshot vocabulary.
DT_VISIT_STATUS_TO_DB: dict[str, VisitStatus] = {
    "Completed": VisitStatus.COMPLETED,
    **DT_STAGE_TO_VISIT_STATUS,
}

# ── Digital Twin berth status -> BerthStatus ──────────────────────────────────
# BerthStatus has no "Cleaning" value — the closest real-world equivalent is
# Maintenance (berth temporarily out of service for a non-occupancy reason).
DT_BERTH_STATUS_TO_DB: dict[str, BerthStatus] = {
    "Available":   BerthStatus.AVAILABLE,
    "Occupied":    BerthStatus.OCCUPIED,
    "Reserved":    BerthStatus.RESERVED,
    "Maintenance": BerthStatus.MAINTENANCE,
    "Cleaning":    BerthStatus.MAINTENANCE,   # no dedicated DB value — documented collapse
}

# Berth-occupying / queueing stage sets — re-exported here (mirroring the
# generator's own BERTH_OCCUPYING_STAGES / QUEUEING_STAGES) so the importer
# never has to redefine "which stages occupy a berth" a second time.
BERTH_OCCUPYING_STAGES = {"Berthing", "Berthed", "Cargo Operations", "Departing"}
QUEUEING_STAGES = {"Anchored", "Waiting"}


def map_vessel_status(dt_stage: str) -> VesselStatus:
    try:
        return DT_STAGE_TO_VESSEL_STATUS[dt_stage]
    except KeyError:
        raise ValueError(
            f"Unknown Digital Twin lifecycle stage '{dt_stage}' — add it to "
            f"DT_STAGE_TO_VESSEL_STATUS in app/core/digital_twin_mapping.py"
        )


def map_visit_status(dt_visit_status: str) -> VisitStatus:
    try:
        return DT_VISIT_STATUS_TO_DB[dt_visit_status]
    except KeyError:
        raise ValueError(
            f"Unknown Digital Twin visit status '{dt_visit_status}' — add it to "
            f"DT_VISIT_STATUS_TO_DB in app/core/digital_twin_mapping.py"
        )


def map_berth_status(dt_berth_status: str) -> BerthStatus:
    try:
        return DT_BERTH_STATUS_TO_DB[dt_berth_status]
    except KeyError:
        raise ValueError(
            f"Unknown Digital Twin berth status '{dt_berth_status}' — add it to "
            f"DT_BERTH_STATUS_TO_DB in app/core/digital_twin_mapping.py"
        )
