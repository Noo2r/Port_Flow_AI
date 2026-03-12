from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.vessel import Vessel
from app.schemas.vessel import VesselCreate, VesselUpdate, VesselResponse

router = APIRouter(prefix="/vessels", tags=["Vessels"])


@router.get("/", response_model=list[VesselResponse])
async def list_vessels(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Vessel).offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=VesselResponse, status_code=status.HTTP_201_CREATED)
async def create_vessel(payload: VesselCreate, db: AsyncSession = Depends(get_db)):
    vessel = Vessel(**payload.model_dump())
    db.add(vessel)
    await db.flush()
    await db.refresh(vessel)
    return vessel


@router.get("/{vessel_id}", response_model=VesselResponse)
async def get_vessel(vessel_id: int, db: AsyncSession = Depends(get_db)):
    vessel = await db.get(Vessel, vessel_id)
    if not vessel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vessel not found")
    return vessel


@router.patch("/{vessel_id}", response_model=VesselResponse)
async def update_vessel(vessel_id: int, payload: VesselUpdate, db: AsyncSession = Depends(get_db)):
    vessel = await db.get(Vessel, vessel_id)
    if not vessel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vessel not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vessel, field, value)
    await db.flush()
    await db.refresh(vessel)
    return vessel


@router.delete("/{vessel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vessel(vessel_id: int, db: AsyncSession = Depends(get_db)):
    vessel = await db.get(Vessel, vessel_id)
    if not vessel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vessel not found")
    await db.delete(vessel)
