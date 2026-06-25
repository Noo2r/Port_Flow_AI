"""
Congestion Forecast API — Stage 3
===================================
POST /api/v1/congestion/predict         → single-input congestion + queue forecast
GET  /api/v1/congestion/model-info      → artifact metadata
GET  /api/v1/congestion/port-overview   → forecast for each known port (from DB state)
GET  /api/v1/congestion/evaluation      → model evaluation summary
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.ml.congestion_predictor import congestion_predictor
from app.services.congestion_service import get_port_congestion_forecasts

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class CongestionInput(BaseModel):
    # Port & vessel identity — values match training dataset
    port_id:        str   = Field("PORT_A", description="Port identifier: PORT_A–PORT_H")
    vessel_type:    str   = Field("Container")
    traffic_density:str   = Field("Medium", description="Low / Medium / High")

    # Vessel specs (dataset ranges)
    loa_m:          float = Field(230.0, ge=65,   le=399)
    draft_m:        float = Field(11.0,  ge=4,    le=22)
    gross_tonnage:  float = Field(58000, ge=2000, le=161000)
    vessel_age_years: float = Field(8.0, ge=0,   le=35)
    distance_to_port_nm: float = Field(80.0, ge=0.5, le=788)

    # Weather (dataset ranges)
    wave_height_m:    float = Field(0.9,  ge=0,    le=7.4)
    wind_speed_knots: float = Field(10.0, ge=0.1,  le=60)
    visibility_km:    float = Field(15.0, ge=3.5,  le=27.7)
    precipitation_mm: float = Field(0.5,  ge=0,    le=12.8)
    temperature_c:    float = Field(20.0, ge=-5,   le=42)

    # Port state (dataset ranges)
    port_congestion_index: float = Field(0.42, ge=0,    le=1)
    berth_queue_length:    int   = Field(4,    ge=0,    le=13)
    crane_availability_ratio: float = Field(0.77, ge=0.52, le=1)
    port_avg_delay_last_24h:  float = Field(25.0, ge=-15, le=67.2)
    estimated_service_time_hours: float = Field(20.0, ge=4, le=36)

    # Optional stage-1/2 pipeline inputs
    actual_delay_minutes:     Optional[float] = Field(None)
    eta_prediction_minutes:   Optional[float] = Field(None)
    hour:   Optional[int]   = Field(None, ge=0, le=23)
    month:  Optional[int]   = Field(None, ge=1, le=12)

    @field_validator("vessel_type")
    @classmethod
    def validate_vessel_type(cls, v: str) -> str:
        from app.ml.congestion_predictor import VESSEL_TYPE_MAP
        if v in VESSEL_TYPE_MAP:
            return v
        return "Container"

    @field_validator("traffic_density")
    @classmethod
    def validate_traffic(cls, v: str) -> str:
        return v.capitalize() if v.lower() in ("low","medium","high") else "Medium"


class CongestionResult(BaseModel):
    congestion_level:  float
    congestion_pct:    float
    congestion_label:  str
    congestion_color:  str
    queue_length:      int
    risk_score:        float
    risk_pct:          float
    confidence:        float
    top_factors:       list[dict[str, Any]]
    congestion_model:  str
    queue_model:       str
    port_id:           str
    timestamp:         str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _check_model():
    if congestion_predictor is None:
        raise HTTPException(503, detail="Congestion model not loaded. Run training first.")


# ── 1. Single prediction ───────────────────────────────────────────────────────

@router.post("/predict", response_model=CongestionResult, tags=["Congestion Forecast"])
async def predict_congestion(payload: CongestionInput):
    """
    Forecast congestion level (0–1) and queue length for the given port + conditions.
    Optionally accepts Stage 1 ETA delay and Stage 2 berth data.
    """
    _check_model()
    raw = payload.model_dump()
    result = congestion_predictor.predict(raw)
    result["port_id"]   = payload.port_id
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return result


# ── 2. Model info ──────────────────────────────────────────────────────────────

@router.get("/model-info", tags=["Congestion Forecast"])
async def get_model_info():
    """Return Stage 3 artifact metadata, metrics, and feature importance."""
    _check_model()
    return congestion_predictor.model_info()


# ── 3. Port overview — forecast for all 8 ports ───────────────────────────────

@router.get("/port-overview", tags=["Congestion Forecast"])
async def get_port_overview(db: AsyncSession = Depends(get_db)):
    """
    Returns a congestion forecast for every registered port. All scoring
    logic lives in app.services.congestion_service — the AI Assistant's
    congestion tool calls the same function, so the two never disagree.
    """
    _check_model()
    port_forecasts = await get_port_congestion_forecasts(db)
    return {
        "ports":     port_forecasts,
        "count":     len(port_forecasts),
        "generated": datetime.now(timezone.utc).isoformat(),
    }


# ── 4. Evaluation summary ──────────────────────────────────────────────────────

@router.get("/evaluation", tags=["Congestion Forecast"])
async def get_evaluation():
    """
    Return held-out evaluation metrics and interpretation for the Stage 3 model.
    """
    _check_model()
    info = congestion_predictor.model_info()
    m = info["metrics"]

    return {
        "models": {
            "congestion": {
                "name":      info["congestion_model_name"],
                "target":    "congestion_level_future (float 0–1)",
                "MAE":       m["congestion"]["MAE"],
                "RMSE":      m["congestion"]["RMSE"],
                "R2":        m["congestion"]["R2"],
                "R2_pct":    round(m["congestion"]["R2"] * 100, 1),
                "MAE_pct":   round(m["congestion"]["MAE"] * 100, 1),
                "grade":     "Excellent" if m["congestion"]["R2"] >= 0.90 else "Good",
                "note":      f"Predicts port congestion to within ±{round(m['congestion']['MAE']*100,1)}% on held-out data",
            },
            "queue": {
                "name":      info["queue_model_name"],
                "target":    "queue_length_future (integer 0–20)",
                "MAE":       m["queue"]["MAE"],
                "RMSE":      m["queue"]["RMSE"],
                "R2":        m["queue"]["R2"],
                "R2_pct":    round(m["queue"]["R2"] * 100, 1),
                "grade":     "Good" if m["queue"]["R2"] >= 0.50 else "Moderate",
                "note":      f"Predicts queue length to within ±{round(m['queue']['MAE'],1)} vessels",
            },
        },
        "training_rows": info["training_rows"],
        "features":      info["features"],
        "saved_at":      info["saved_at"],
        "pipeline":      "Stage 1 (ETA) → Stage 2 (Berth Optimizer) → Stage 3 (Congestion Forecast)",
    }
