"""Greedy berth assignment optimizer."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import logger
from app.models.berth import Berth, BerthStatus
from app.models.vessel import Vessel
from app.models.visit import Visit, VisitStatus
from app.schemas.optimization import BerthAssignment, OptimizationResult


async def optimize_berth_assignments(db: AsyncSession) -> OptimizationResult:
    # 1. Fetch unassigned scheduled visits sorted by ETA
    result = await db.execute(
        select(Visit)
        .where(Visit.status == VisitStatus.SCHEDULED)
        .where(Visit.berth_id.is_(None))
        .order_by(Visit.eta.asc().nulls_last())
    )
    unassigned = result.scalars().all()

    # 2. Fetch available berths sorted by priority (lowest number = highest priority)
    berth_result = await db.execute(
        select(Berth)
        .where(Berth.status == BerthStatus.AVAILABLE)
        .where(Berth.is_active.is_(True))
        .order_by(Berth.priority_level.asc())
    )
    available_berths = list(berth_result.scalars().all())

    assignments: list[BerthAssignment] = []
    unassigned_ids: list[int] = []

    now = datetime.now(timezone.utc)

    for visit in unassigned:
        vessel = await db.get(Vessel, visit.vessel_id)
        assigned = False

        for berth in available_berths:
            if await _berth_is_free(berth, visit, db):
                # Assign
                visit.berth_id = berth.id
                berth.status = BerthStatus.RESERVED
                available_berths.remove(berth)

                predicted_eta = visit.eta
                waiting_minutes = 0.0
                if predicted_eta and predicted_eta > now:
                    waiting_minutes = (predicted_eta - now).total_seconds() / 60

                assignments.append(BerthAssignment(
                    visit_id=visit.id,
                    vessel_id=visit.vessel_id,
                    vessel_name=vessel.name if vessel else "Unknown",
                    vessel_imo=vessel.imo_number if vessel else "Unknown",
                    assigned_berth_id=berth.id,
                    assigned_berth_code=berth.code,
                    predicted_eta=predicted_eta,
                    estimated_waiting_minutes=round(waiting_minutes, 1),
                ))
                assigned = True
                logger.info(
                    "OPTIMIZER | assigned visit_id=%d vessel=%s → berth=%s",
                    visit.id,
                    vessel.imo_number if vessel else "?",
                    berth.code,
                )
                break

        if not assigned:
            unassigned_ids.append(visit.id)

    await db.flush()

    return OptimizationResult(
        assignments_made=len(assignments),
        assignments=assignments,
        unassigned_visits=unassigned_ids,
        message=(
            f"Assigned {len(assignments)} visit(s). "
            f"{len(unassigned_ids)} visit(s) could not be assigned (no suitable berth available)."
        ),
    )


async def _berth_is_free(berth: Berth, candidate: Visit, db: AsyncSession) -> bool:
    """Check that the berth has no active visits that overlap with the candidate's window."""
    if not (candidate.etb and candidate.etd):
        return True  # no window defined — assign optimistically

    result = await db.execute(
        select(Visit)
        .where(Visit.berth_id == berth.id)
        .where(Visit.status.in_([VisitStatus.SCHEDULED, VisitStatus.APPROACHING, VisitStatus.IN_PORT]))
        .where(Visit.etb < candidate.etd)
        .where(Visit.etd > candidate.etb)
    )
    overlaps = result.scalars().all()
    return len(overlaps) == 0
