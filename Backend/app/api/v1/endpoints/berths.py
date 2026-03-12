from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.berth import Berth
from app.schemas.berth import BerthCreate, BerthUpdate, BerthResponse

router = APIRouter(prefix="/berths", tags=["Berths"])


@router.get("/", response_model=list[BerthResponse])
async def list_berths(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Berth).offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=BerthResponse, status_code=status.HTTP_201_CREATED)
async def create_berth(payload: BerthCreate, db: AsyncSession = Depends(get_db)):
    berth = Berth(**payload.model_dump())
    db.add(berth)
    await db.flush()
    await db.refresh(berth)
    return berth


@router.get("/{berth_id}", response_model=BerthResponse)
async def get_berth(berth_id: int, db: AsyncSession = Depends(get_db)):
    berth = await db.get(Berth, berth_id)
    if not berth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Berth not found")
    return berth


@router.patch("/{berth_id}", response_model=BerthResponse)
async def update_berth(berth_id: int, payload: BerthUpdate, db: AsyncSession = Depends(get_db)):
    berth = await db.get(Berth, berth_id)
    if not berth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Berth not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(berth, field, value)
    await db.flush()
    await db.refresh(berth)
    return berth


@router.delete("/{berth_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_berth(berth_id: int, db: AsyncSession = Depends(get_db)):
    berth = await db.get(Berth, berth_id)
    if not berth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Berth not found")
    await db.delete(berth)
