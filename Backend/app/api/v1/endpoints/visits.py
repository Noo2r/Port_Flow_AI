from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.visit import Visit
from app.schemas.visit import VisitCreate, VisitUpdate, VisitResponse

router = APIRouter(prefix="/visits", tags=["Visits"])


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
async def create_visit(payload: VisitCreate, db: AsyncSession = Depends(get_db)):
    visit = Visit(**payload.model_dump())
    db.add(visit)
    await db.flush()
    await db.refresh(visit)
    return visit


@router.get("/{visit_id}", response_model=VisitResponse)
async def get_visit(visit_id: int, db: AsyncSession = Depends(get_db)):
    visit = await db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    return visit


@router.patch("/{visit_id}", response_model=VisitResponse)
async def update_visit(visit_id: int, payload: VisitUpdate, db: AsyncSession = Depends(get_db)):
    visit = await db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(visit, field, value)
    await db.flush()
    await db.refresh(visit)
    return visit


@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_visit(visit_id: int, db: AsyncSession = Depends(get_db)):
    visit = await db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    await db.delete(visit)
