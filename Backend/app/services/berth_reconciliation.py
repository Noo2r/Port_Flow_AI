"""
Berth occupancy reconciliation.

Invariant: a berth must never be OCCUPIED if no active (non-terminal) visit
references it. This can drift from seed/restore data (a backup captured
mid-session can freeze a berth as OCCUPIED after its visit already
completed) or, in principle, from any future write path that updates a
visit's berth without going through the release helpers in eta.py/visits.py.

This module re-derives berth occupancy from the visits table and corrects
any berth that violates the invariant. It is safe to run repeatedly —
it never marks a berth OCCUPIED, only ever corrects false OCCUPIED states.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.berth import Berth, BerthStatus
from app.models.visit import Visit, VisitStatus

_TERMINAL_VISIT_STATUSES = (VisitStatus.COMPLETED, VisitStatus.CANCELLED)


async def reconcile_berth_occupancy(db: AsyncSession) -> dict:
    """
    Find every berth marked OCCUPIED with zero active visits referencing it,
    and release it back to AVAILABLE. Returns a summary for logging.
    """
    occupied_res = await db.execute(select(Berth).where(Berth.status == BerthStatus.OCCUPIED))
    occupied_berths = occupied_res.scalars().all()

    if not occupied_berths:
        return {"checked": 0, "released": 0, "released_berth_codes": []}

    active_res = await db.execute(
        select(Visit.berth_id)
        .where(
            Visit.berth_id.in_([b.id for b in occupied_berths]),
            Visit.status.notin_(_TERMINAL_VISIT_STATUSES),
        )
        .distinct()
    )
    berth_ids_with_active_visit = {row[0] for row in active_res.all()}

    released_codes: list[str] = []
    for berth in occupied_berths:
        if berth.id not in berth_ids_with_active_visit:
            berth.status = BerthStatus.AVAILABLE
            released_codes.append(berth.code)

    if released_codes:
        await db.commit()

    return {
        "checked": len(occupied_berths),
        "released": len(released_codes),
        "released_berth_codes": released_codes,
    }
