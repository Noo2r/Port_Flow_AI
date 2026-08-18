from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.database import get_db
from app.models.voyage import Voyage
from app.schemas.voyage import VoyageCreate, VoyageResponse, VoyageUpdate

router = APIRouter()


@router.get("/", response_model=list[VoyageResponse])
async def list_voyages(
    vessel_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(Voyage).offset(skip).limit(limit)
    if vessel_id is not None:
        q = q.where(Voyage.vessel_id == vessel_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/", response_model=VoyageResponse, status_code=status.HTTP_201_CREATED)
async def create_voyage(payload: VoyageCreate, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    voyage = Voyage(**payload.model_dump())
    db.add(voyage)
    await db.commit()
    await db.refresh(voyage)
    return voyage


@router.get("/{voyage_id}", response_model=VoyageResponse)
async def get_voyage(voyage_id: int, db: AsyncSession = Depends(get_db)):
    voyage = await db.get(Voyage, voyage_id)
    if voyage is None:
        raise HTTPException(status_code=404, detail="Voyage not found")
    return voyage


@router.patch("/{voyage_id}", response_model=VoyageResponse)
async def update_voyage(voyage_id: int, payload: VoyageUpdate, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    voyage = await db.get(Voyage, voyage_id)
    if voyage is None:
        raise HTTPException(status_code=404, detail="Voyage not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(voyage, field, value)
    await db.commit()
    await db.refresh(voyage)
    return voyage


@router.delete("/{voyage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voyage(voyage_id: int, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    voyage = await db.get(Voyage, voyage_id)
    if voyage is None:
        raise HTTPException(status_code=404, detail="Voyage not found")
    db.delete(voyage)
    await db.commit()
