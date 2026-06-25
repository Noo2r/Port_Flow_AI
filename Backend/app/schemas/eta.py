from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Prediction request ────────────────────────────────────────────────────────
class PredictETAInput(BaseModel):
    """Full ML-model input for CatBoost ETA prediction."""

    # Identifiers
    vessel_id: int
    visit_id:  Optional[int] = None

    # Scheduling (ISO-8601)
    scheduled_eta:        str = Field(..., example="2024-06-15T16:00:00Z")
    timestamp:            str = Field(..., example="2024-06-15T10:30:00Z")
    berth_available_from: Optional[str] = Field(None, example="2024-06-15T14:00:00Z")

    # Navigation
    latitude:            float = Field(..., ge=-90,  le=90,  example=25.0)
    longitude:           float = Field(..., ge=-180, le=180, example=55.0)
    speed_knots:         float = Field(..., ge=0,    le=35,  example=14.5)
    heading:             int   = Field(180, ge=0,    le=359)
    distance_to_port_nm: float = Field(..., ge=0.1,  le=900, example=80.0)

    # Port / berth conditions
    port_id:                  str   = Field(..., example="PORT_A")
    traffic_density:          str   = Field(..., example="Medium")
    berth_max_length:         int   = Field(..., ge=100, le=450, example=260)
    berth_queue_length:       int   = Field(..., ge=0,   le=30,  example=3)
    crane_availability_ratio: float = Field(..., ge=0.0, le=1.0, example=0.8)
    port_congestion_index:    float = Field(..., ge=0.0, le=1.0, example=0.35)
    port_avg_delay_last_24h:  float = Field(..., ge=0,           example=25.0)

    # Weather
    wave_height_m:    float = Field(..., ge=0, le=15, example=1.5)
    wind_speed_knots: float = Field(..., ge=0, le=70, example=12.0)
    visibility_km:    float = Field(..., ge=0, le=50, example=15.0)
    precipitation_mm: float = Field(0.0, ge=0)
    temperature_c:    float = Field(22.0)

    # Vessel overrides (auto-filled from DB when vessel_id is given)
    vessel_type:                  Optional[str]   = None
    loa_m:                        Optional[float] = None
    draft_m:                      Optional[float] = None
    gross_tonnage:                Optional[int]   = None
    engine_power_kw:              Optional[int]   = Field(None, example=35_000)
    vessel_age_years:             Optional[float] = Field(None, example=8.0)
    estimated_service_time_hours: float           = Field(12.0)


# ── Prediction response ───────────────────────────────────────────────────────
class PredictETAResult(BaseModel):
    vessel_id:   int
    visit_id:    Optional[int]
    model_name:  str
    model_version: str

    predicted_delay_minutes: float
    predicted_eta:           Optional[str]
    confidence_score:        float
    lower_bound_minutes:     float
    upper_bound_minutes:     float

    top_delay_factors:  list[dict]
    model_mae_minutes:  float
    model_r2:           float
    model_age_days:     Optional[int] = None
    staleness_warning:  Optional[str] = None

    prediction_id: int
    created_at:    str


# ── Model info response ───────────────────────────────────────────────────────
class ETAModelInfo(BaseModel):
    model_name:         str
    model_version:      str
    saved_at:           str
    model_age_days:     int
    staleness_warning:  Optional[str]
    metrics:            dict
    feature_count:      int
    feature_importance: list[dict]
    status:             str
    available_models:   list[str] = []


# ── Prediction feedback ───────────────────────────────────────────────────────
class PredictionFeedback(BaseModel):
    prediction_id:        int
    actual_delay_minutes: float = Field(..., ge=0, description="True delay in minutes at arrival")
    actual_arrival_time:  Optional[str] = Field(None, description="ISO-8601 actual arrival datetime")
    notes:                Optional[str] = None


class PredictionFeedbackResult(BaseModel):
    prediction_id:     int
    predicted_minutes: float
    actual_minutes:    float
    error_minutes:     float
    message:           str
