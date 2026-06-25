from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.intelligence import AISService, ConflictDetector, WeatherCorrelationEngine
from app.database import get_db
from app.schemas.operations import (
    AISUpdateRequest,
    AISUpdateResponse,
    ConflictResponse,
    WeatherImpactResponse,
)

router = APIRouter()


@router.post("/visits/{visit_id}/ais", response_model=AISUpdateResponse)
async def update_ais_position(
    visit_id: int,
    payload: AISUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await AISService.update_position(
            visit_id=visit_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            speed_knots=payload.speed_knots,
            heading_degrees=payload.heading_degrees,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/visits/{visit_id}/weather-impact", response_model=WeatherImpactResponse)
async def get_weather_impact(visit_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await WeatherCorrelationEngine.calculate_delay(visit_id=visit_id, db=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/berths/{berth_id}/conflicts", response_model=ConflictResponse)
async def get_berth_conflicts(berth_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await ConflictDetector.detect_conflicts(berth_id=berth_id, db=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
