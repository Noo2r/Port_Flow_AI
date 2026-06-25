"""
Port Operations Endpoints  — DB-first, fully joined
====================================================
All data comes from the real PostgreSQL tables.  No in-memory state.

Routes (registered under /api/v1/port-ops):
    GET  /health                → engine + DB health
    GET  /berth-status          → berth occupancy + port info (DB)
    GET  /port-kpis             → aggregate performance metrics (DB)
    GET  /allocations           → visits with vessel + berth + port names (DB)
    DELETE /allocations/expired → no-op kept for API compatibility
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.berth import Berth, BerthStatus
from app.models.port import Port
from app.models.vessel import Vessel
from app.models.visit import ACTIVE_VISIT_STATUSES, TERMINAL_VISIT_STATUSES, Visit, VisitStatus
from app.services import berth_service

router = APIRouter()

# Canonical definition lives in app.models.visit.ACTIVE_VISIT_STATUSES —
# shared with analytics.py, chat.py, and analytics_service.py. SCHEDULED
# visits are future bookings, not yet underway, so they are excluded here
# too (previously this endpoint counted them as "active", which caused
# Port Operations to disagree with the Dashboard).
ACTIVE_STATUSES = ACTIVE_VISIT_STATUSES
ALL_DONE_STATUSES = TERMINAL_VISIT_STATUSES


# ── /health ───────────────────────────────────────────────────────────────────

@router.get("/health")
async def berth_engine_health(db: AsyncSession = Depends(get_db)):
    try:
        res = await db.execute(
            select(func.count()).select_from(Visit).where(Visit.status.in_(ACTIVE_STATUSES))
        )
        db_active = res.scalar() or 0
        return {
            "status": "healthy",
            "berths_loaded": len(berth_service.get_berth_registry()),
            "active_allocations": db_active,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Berth engine unavailable: {exc}")


# ── /berth-status ─────────────────────────────────────────────────────────────

@router.get("/berth-status")
async def get_berth_status(db: AsyncSession = Depends(get_db)):
    """
    Return current occupancy for every berth, grouped by real port data.
    Includes port_id and port_name so the frontend can group without regex hacks.
    """
    try:
        # All berths joined with their port
        rows = (await db.execute(
            select(Berth, Port)
            .outerjoin(Port, Berth.port_id == Port.id)
            .order_by(Berth.code)
        )).all()

        # Are there any live active visits?
        has_live = bool((await db.execute(
            select(func.count()).select_from(Visit).where(Visit.status.in_(ACTIVE_STATUSES))
        )).scalar())

        # Historical visit frequency per berth (used when no live visits)
        berth_visit_counts: dict[int, int] = {}
        berth_last_ata: dict[int, datetime | None] = {}
        if not has_live:
            hist_rows = await db.execute(
                select(Visit.berth_id, func.count().label("n"), func.max(Visit.ata).label("last_ata"))
                .where(
                    Visit.status == VisitStatus.COMPLETED,
                    Visit.berth_id.isnot(None),
                    Visit.id.in_(
                        select(Visit.id)
                        .where(Visit.status == VisitStatus.COMPLETED)
                        .order_by(desc(Visit.ata))
                        .limit(500)
                        .scalar_subquery()
                    ),
                )
                .group_by(Visit.berth_id)
            )
            for r in hist_rows.mappings():
                berth_visit_counts[r["berth_id"]] = int(r["n"])
                berth_last_ata[r["berth_id"]] = r["last_ata"]

        max_visits = max(berth_visit_counts.values(), default=1)

        berth_list = []
        for b, port in rows:
            is_live_occ = has_live and b.status == BerthStatus.OCCUPIED
            visit_n = berth_visit_counts.get(b.id, 0)
            if has_live:
                util  = 1.0 if is_live_occ else 0.0
                queue = 1   if is_live_occ else 0
            else:
                util  = round(visit_n / max_visits, 3) if max_visits else 0.0
                queue = max(0, visit_n // 5)

            last_used = berth_last_ata.get(b.id)
            berth_list.append({
                "berth_id":                 b.code,
                "berth_name":               b.name,
                "port_id":                  port.code if port else None,
                "port_name":                port.name if port else b.name,
                "berth_type":               b.berth_type.value if b.berth_type else None,
                "berth_max_length":         b.max_length,
                "berth_max_draft":          b.max_draft,
                "crane_availability_ratio": 1.0 if b.has_crane else 0.0,
                "status":                   b.status.value,
                "utilization":              util,
                "berth_utilization":        util,
                "berth_queue_length":       queue,
                "current_queue":            queue,
                "available_from":           last_used.isoformat() if last_used else None,
            })

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data_mode": "live" if has_live else "historical",
            "berths":    berth_list,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ── /port-kpis ────────────────────────────────────────────────────────────────

@router.get("/port-kpis")
async def get_port_kpis(db: AsyncSession = Depends(get_db)):
    try:
        active_count = int((await db.execute(
            select(func.count()).select_from(Visit).where(Visit.status.in_(ACTIVE_STATUSES))
        )).scalar() or 0)

        total_count = int((await db.execute(select(func.count()).select_from(Visit))).scalar() or 0)

        completed_count = int((await db.execute(
            select(func.count()).select_from(Visit).where(Visit.status == VisitStatus.COMPLETED)
        )).scalar() or 0)

        if active_count > 0:
            kpi_filter = Visit.status.in_(ACTIVE_STATUSES)
            kpi_label  = "live"
        else:
            recent_ids_q = (
                select(Visit.id)
                .where(Visit.status == VisitStatus.COMPLETED)
                .order_by(desc(Visit.ata))
                .limit(500)
                .scalar_subquery()
            )
            kpi_filter = Visit.id.in_(recent_ids_q)
            kpi_label  = "recent"

        # Digital Twin imports honestly leave waiting_time_hours NULL for
        # visits that haven't finished waiting yet (Task 5) — falling back to
        # the static column alone would show "0 wait" for vessels that have
        # actually been anchored/queueing for hours. Compute a real value:
        # finalized wait if known, else (atb - arrival) if already berthed,
        # else the live elapsed time since arrival/ETA if still queueing.
        ref_arrival = func.coalesce(Visit.ata, Visit.eta)
        wait_hours_expr = case(
            (Visit.waiting_time_hours.isnot(None), Visit.waiting_time_hours),
            (
                Visit.atb.isnot(None) & ref_arrival.isnot(None),
                func.extract("epoch", Visit.atb - ref_arrival) / 3600.0,
            ),
            (
                ref_arrival.isnot(None),
                func.extract("epoch", func.now() - ref_arrival) / 3600.0,
            ),
            else_=0.0,
        )

        avg_wait_h = float((await db.execute(
            select(func.avg(wait_hours_expr)).where(
                kpi_filter,
                wait_hours_expr <= 24,
            )
        )).scalar() or 0)

        conflicts = int((await db.execute(
            select(func.count()).select_from(Visit).where(
                kpi_filter, wait_hours_expr > 1.5, wait_hours_expr <= 24,
            )
        )).scalar() or 0)

        congested = int((await db.execute(
            select(func.count()).select_from(Visit).where(
                kpi_filter, wait_hours_expr > 1.0, wait_hours_expr <= 24,
            )
        )).scalar() or 0)

        kpi_denom = int((await db.execute(
            select(func.count()).select_from(Visit).where(kpi_filter)
        )).scalar() or 1)

        total_berths = int((await db.execute(select(func.count()).select_from(Berth))).scalar() or 1)
        occupied_now = int((await db.execute(
            select(func.count()).select_from(Berth).where(Berth.status == BerthStatus.OCCUPIED)
        )).scalar() or 0)

        if active_count == 0:
            avg_svc_h = float((await db.execute(
                select(func.avg(Visit.berth_time_hours)).where(
                    kpi_filter, Visit.berth_time_hours.isnot(None)
                )
            )).scalar() or 12.0)
            util_fraction = round(min(0.99, avg_svc_h / 24.0), 3)
        else:
            util_fraction = round(occupied_now / total_berths, 3)

        return {
            "total_allocations":        total_count,
            "completed_visits":         completed_count,
            "active_vessels":           active_count,
            "avg_waiting_time_minutes": round(avg_wait_h * 60, 1),
            "avg_berth_utilization":    util_fraction,
            "conflict_rate":            round(conflicts / kpi_denom, 3),
            "conflict_count":           conflicts,
            "congestion_rate":          round(congested / kpi_denom, 3),
            "congestion_count":         congested,
            "kpi_mode":                 kpi_label,
            "timestamp":                datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ── /allocations ──────────────────────────────────────────────────────────────

def _build_alloc_query(where_clause, order_clause, limit=None):
    q = (
        select(Visit, Vessel, Berth, Port)
        .outerjoin(Vessel, Visit.vessel_id == Vessel.id)
        .outerjoin(Berth,  Visit.berth_id  == Berth.id)
        .outerjoin(Port,   Berth.port_id   == Port.id)
        .where(where_clause)
        .order_by(order_clause)
    )
    return q.limit(limit) if limit else q


@router.get("/allocations")
async def get_active_allocations(db: AsyncSession = Depends(get_db)):
    """
    Return visit records enriched with vessel name, berth name, and port name.
    Prefers active visits; falls back to 100 most-recent completed visits.
    """
    try:
        rows = (await db.execute(
            _build_alloc_query(Visit.status.in_(ACTIVE_STATUSES), Visit.eta)
        )).all()

        if not rows:
            rows = (await db.execute(
                _build_alloc_query(Visit.status == VisitStatus.COMPLETED, desc(Visit.ata), limit=100)
            )).all()

        now = datetime.utcnow()
        allocations = []
        for v, vessel, berth, port in rows:
            ref_time_for_wait = v.ata or v.eta
            if v.waiting_time_hours is not None:
                # Known/finalized wait (set for completed visits, or any visit
                # the importer/engine already computed a real duration for).
                raw_wait_h = float(v.waiting_time_hours)
            elif v.atb and ref_time_for_wait:
                # Already berthed — the wait is over; its real duration is
                # the gap between arrival and berthing, not "0".
                raw_wait_h = max((v.atb.replace(tzinfo=None) - ref_time_for_wait.replace(tzinfo=None)).total_seconds() / 3600.0, 0.0)
            elif v.status != VisitStatus.COMPLETED and ref_time_for_wait:
                # Still queueing (never berthed yet) — the Digital Twin import
                # honestly leaves waiting_time_hours NULL here (Task 5), so
                # compute the real elapsed wait live instead of showing 0,
                # which would misleadingly read as "no wait" for a vessel
                # that has actually been anchored/queueing for hours.
                elapsed = (now - ref_time_for_wait.replace(tzinfo=None)).total_seconds() / 3600.0
                raw_wait_h = max(elapsed, 0.0)
            else:
                raw_wait_h = 0.0
            wait_h = min(raw_wait_h, 24.0)
            wait_m = round(wait_h * 60)

            ref_time = v.ata or v.eta
            if v.etb:
                berthing_start = v.etb
            elif ref_time and wait_h:
                berthing_start = ref_time + timedelta(hours=wait_h)
            else:
                berthing_start = ref_time

            berth_h = float(v.berth_time_hours or 0)
            if v.etd:
                departure = v.etd
            elif berthing_start and berth_h:
                departure = berthing_start + timedelta(hours=berth_h)
            else:
                departure = None

            # Resolve port from berth's port first, then visit's port_id
            port_code = port.code if port else None
            port_name = port.name if port else None
            if not port_code and v.port_id:
                fallback_port = await db.get(Port, v.port_id)
                if fallback_port:
                    port_code = fallback_port.code
                    port_name = fallback_port.name

            allocations.append({
                "visit_id":             v.id,
                "vessel_id":            vessel.name if vessel else f"Vessel #{v.vessel_id}",
                "vessel_name":          vessel.name if vessel else None,
                "vessel_db_id":         v.vessel_id,
                "assigned_berth":       berth.code if berth else None,
                "berth_name":           berth.name if berth else None,
                "port_id":              port_code,
                "port_name":            port_name,
                "status":               v.status.value,
                "eta":                  v.eta.isoformat()             if v.eta             else None,
                "berthing_start_time":  berthing_start.isoformat()    if berthing_start    else None,
                "departure_time":       departure.isoformat()         if departure         else None,
                "waiting_time_minutes": wait_m,
                "berth_utilization":    1.0 if berth else 0.0,
                "conflict_flag":        wait_m > 90,
                "congestion_flag":      wait_m > 60,
                "notes":                v.notes,
            })

        return {"count": len(allocations), "allocations": allocations}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ── /allocations/expired ──────────────────────────────────────────────────────

@router.delete("/allocations/expired")
def clear_expired_allocations(cutoff_hours: int = Query(48, ge=1, le=720)):
    """No-op kept for API compatibility — data lives in DB, not in memory."""
    return {"cleared": 0, "message": "allocations are DB-persisted, no in-memory state to clear"}
