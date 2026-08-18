from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.core.lifecycle import InvalidTransitionError, validate_vessel_transition
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
async def create_vessel(payload: VesselCreate, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    vessel = Vessel(**payload.model_dump())
    db.add(vessel)
    await db.commit()
    await db.refresh(vessel)
    return vessel


@router.get("/{vessel_id}", response_model=VesselResponse)
async def get_vessel(vessel_id: int, db: AsyncSession = Depends(get_db)):
    vessel = await db.get(Vessel, vessel_id)
    if not vessel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vessel not found")
    return vessel


@router.patch("/{vessel_id}", response_model=VesselResponse)
async def update_vessel(vessel_id: int, payload: VesselUpdate, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    vessel = await db.get(Vessel, vessel_id)
    if not vessel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vessel not found")

    payload_data = payload.model_dump(exclude_unset=True)
    if "status" in payload_data and payload_data["status"] != vessel.status:
        try:
            validate_vessel_transition(vessel.status, payload_data["status"])
        except InvalidTransitionError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    for field, value in payload_data.items():
        setattr(vessel, field, value)
    await db.commit()
    await db.refresh(vessel)
    return vessel


@router.delete("/{vessel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vessel(vessel_id: int, _user: CurrentUser, db: AsyncSession = Depends(get_db)):
    vessel = await db.get(Vessel, vessel_id)
    if not vessel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vessel not found")
    db.delete(vessel)
    await db.commit()
