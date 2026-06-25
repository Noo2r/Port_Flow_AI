"""
FastAPI Backend — Congestion Forecasting System
================================================
Stage 3 of the Smart Port AI Pipeline, standalone runner.

Run from inside congestion_forecaster/ folder:
    uvicorn api.main:app --reload --port 8001

Then open:  http://127.0.0.1:8001/docs

This mirrors berth_optimizer/api/main.py's structure (Stage 2). It is
read-only / stateless — congestion forecasting has no allocation registry
to persist, so there is no DB-backed state here, unlike the berth engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Support both run-from-inside and run-from-parent
_pkg = Path(__file__).parents[1]   # congestion_forecaster/
_prj = Path(__file__).parents[2]   # Backend/
for p in [str(_pkg), str(_prj)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from congestion_forecaster.engine.predictor import congestion_predictor

app = FastAPI(
    title="Congestion Forecaster — Stage 3",
    description="Standalone congestion-level and queue-length forecasting API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CongestionRequest(BaseModel):
    port_id: str = Field(..., examples=["PORT_A"])
    vessel_type: str = Field("Container", examples=["Container"])
    port_congestion_index: float = Field(0.5, ge=0.0, le=1.0)
    wave_height_m: float = Field(1.0, ge=0.0)
    wind_speed_knots: float = Field(10.0, ge=0.0)
    berth_queue_length: int = Field(2, ge=0)
    vessel_age_years: float = Field(8.0, ge=0.0)
    distance_to_port_nm: float = Field(50.0, ge=0.0)
    estimated_service_time_hours: float = Field(12.0, ge=0.0)
    traffic_density: str = Field("Medium")
    actual_delay_minutes: float | None = None
    timestamp: str | None = None
    scheduled_eta: str | None = None
    berth_available_from: str | None = None


@app.get("/health")
def health():
    return {
        "status": "healthy" if congestion_predictor is not None else "degraded",
        "model_loaded": congestion_predictor is not None,
    }


@app.get("/model-info")
def model_info():
    if congestion_predictor is None:
        raise HTTPException(status_code=503, detail="Congestion model not loaded")
    return congestion_predictor.model_info()


@app.post("/predict")
def predict(payload: CongestionRequest):
    if congestion_predictor is None:
        raise HTTPException(status_code=503, detail="Congestion model not loaded")
    return congestion_predictor.predict(payload.model_dump(exclude_none=True))
