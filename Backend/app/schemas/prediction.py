from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.prediction import PredictionType, PredictionStatus


class PredictionBase(BaseModel):
    vessel_id: int
    visit_id: int | None = None
    prediction_type: PredictionType
    model_name: str | None = None
    model_version: str | None = None


class PredictionCreate(PredictionBase):
    input_features: dict | None = None


class PredictionUpdate(BaseModel):
    status: PredictionStatus | None = None
    predicted_value: float | None = None
    predicted_datetime: datetime | None = None
    confidence_score: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    actual_value: float | None = None
    actual_datetime: datetime | None = None
    error_mae: float | None = None


class PredictionResponse(PredictionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: PredictionStatus
    predicted_value: float | None = None
    predicted_datetime: datetime | None = None
    confidence_score: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    input_features: dict | None = None
    actual_value: float | None = None
    actual_datetime: datetime | None = None
    error_mae: float | None = None
    created_at: datetime
    updated_at: datetime
