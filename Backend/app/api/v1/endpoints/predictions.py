from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.prediction import Prediction
from app.schemas.prediction import PredictionCreate, PredictionUpdate, PredictionResponse

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("/", response_model=list[PredictionResponse])
async def list_predictions(
    skip: int = 0,
    limit: int = 100,
    vessel_id: int | None = None,
    visit_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Prediction)
    if vessel_id is not None:
        query = query.where(Prediction.vessel_id == vessel_id)
    if visit_id is not None:
        query = query.where(Prediction.visit_id == visit_id)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
async def create_prediction(payload: PredictionCreate, db: AsyncSession = Depends(get_db)):
    prediction = Prediction(**payload.model_dump())
    db.add(prediction)
    await db.flush()
    await db.refresh(prediction)
    return prediction


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(prediction_id: int, db: AsyncSession = Depends(get_db)):
    prediction = await db.get(Prediction, prediction_id)
    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return prediction


@router.patch("/{prediction_id}", response_model=PredictionResponse)
async def update_prediction(
    prediction_id: int, payload: PredictionUpdate, db: AsyncSession = Depends(get_db)
):
    prediction = await db.get(Prediction, prediction_id)
    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prediction, field, value)
    await db.flush()
    await db.refresh(prediction)
    return prediction
