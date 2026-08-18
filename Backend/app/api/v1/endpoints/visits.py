from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.core.lifecycle import InvalidTransitionError, validate_visit_transition
from app.database import get_db
from app.models.berth import Berth, BerthStatus
from app.models.visit import Visit, VisitStatus
from app.schemas.visit import VisitCreate, VisitUpdate, VisitResponse

router = APIRouter(prefix="/visits", tags=["Visits"])

_TERMINAL_STATUSES = {VisitStatus.COMPLETED, VisitStatus.CANCELLED}


def _compute_metrics(visit: Visit) -> None:
    """Derive waiting/berth/turnaround hours from actual timestamps when available,
    or sum the component fields if only those exist."""
    if visit.ata and visit.atb:
        wh = (visit.atb - visit.ata).total_seconds() / 3600
        visit.waiting_time_hours = wh if wh >= 0 else None
    if visit.atb and visit.atd:
        bh = (visit.atd - visit.atb).total_seconds() / 3600
        visit.berth_time_hours = bh if bh >= 0 else None
    if visit.ata and visit.atd:
        th = (visit.atd - visit.ata).total_seconds() / 3600
        visit.turnaround_hours = th if th >= 0 else None
    elif visit.waiting_time_hours is not None and visit.berth_time_hours is not None:
        visit.turnaround_hours = visit.waiting_time_hours + visit.berth_time_hours
    elif visit.berth_time_hours is not None and visit.turnaround_hours is None:
        visit.turnaround_hours = visit.berth_time_hours


async def _sync_berth(berth_id: int | None, new_status: BerthStatus, db: AsyncSession) -> None:
    """Load a berth by id and update its status — no-op if berth_id is None or not found."""
    if berth_id is None:
        return
    berth = await db.get(Berth, berth_id)
    if berth:
        berth.status = new_status


@router.get("/", response_model=list[VisitResponse])
async def list_visits(
    skip: int = 0,
    limit: int = 100,
    vessel_id: int | None = None,
    berth_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Visit)
    if vessel_id is not None:
        query = query.where(Visit.vessel_id == vessel_id)
    if berth_id is not None:
        query = query.where(Visit.berth_id == berth_id)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=VisitResponse, status_code=status.HTTP_201_CREATED)
async def create_visit(payload: VisitCreate, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    visit = Visit(**payload.model_dump())
    db.add(visit)
    await _sync_berth(payload.berth_id, BerthStatus.OCCUPIED, db)
    await db.commit()
    await db.refresh(visit)
    return visit


@router.get("/{visit_id}", response_model=VisitResponse)
async def get_visit(visit_id: int, db: AsyncSession = Depends(get_db)):
    visit = await db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    return visit


@router.patch("/{visit_id}", response_model=VisitResponse)
async def update_visit(visit_id: int, payload: VisitUpdate, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    visit = await db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    old_berth_id = visit.berth_id
    old_status   = visit.status

    payload_data = payload.model_dump(exclude_unset=True)
    if "status" in payload_data and payload_data["status"] != old_status:
        try:
            validate_visit_transition(old_status, payload_data["status"])
        except InvalidTransitionError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    for field, value in payload_data.items():
        setattr(visit, field, value)

    _compute_metrics(visit)

    new_berth_id  = visit.berth_id
    visit_ending  = visit.status in _TERMINAL_STATUSES

    if old_berth_id != new_berth_id:
        # Berth assignment changed: release the old one, occupy the new one (unless visit is ending)
        await _sync_berth(old_berth_id, BerthStatus.AVAILABLE, db)
        if not visit_ending:
            await _sync_berth(new_berth_id, BerthStatus.OCCUPIED, db)
    elif old_berth_id and visit_ending and old_status not in _TERMINAL_STATUSES:
        # Same berth, but visit just transitioned to a terminal state → release it
        await _sync_berth(old_berth_id, BerthStatus.AVAILABLE, db)

    await db.commit()
    await db.refresh(visit)
    return visit


@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_visit(visit_id: int, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    visit = await db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    await _sync_berth(visit.berth_id, BerthStatus.AVAILABLE, db)
    await db.delete(visit)
    await db.commit()
