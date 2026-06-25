"""
FastAPI Backend — Berth Optimization System
============================================
Run from inside berth_optimizer/ folder:
    uvicorn api.main:app --reload --port 8000

Then open:  http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

# Support both run-from-inside and run-from-parent
_pkg = Path(__file__).parents[1]          # berth_optimizer/
_prj = Path(__file__).parents[2]          # models/
for p in [str(_pkg), str(_prj)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select

from berth_optimizer.engine.optimizer import AllocationResult, BerthOptimizationEngine
from berth_optimizer.utils.data_loader import (
    load_dataset, extract_berth_slots,
    vessel_request_from_json, berth_slot_from_json, _find_dataset,
)

# app.* is reachable because _prj (Backend/) is on sys.path (set above)
try:
    from app.database import AsyncSessionLocal
    from app.models.engine_allocation import EngineAllocation
    _DB_AVAILABLE = True
except Exception:  # DB deps not installed or env not configured
    _DB_AVAILABLE = False

engine = BerthOptimizationEngine()
berth_registry: list = []


# ── DB persistence helpers ────────────────────────────────────────────────────

async def _load_active_allocations() -> list[AllocationResult]:
    """Return all engine_allocations rows whose departure_time is in the future."""
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(EngineAllocation).where(EngineAllocation.departure_time > now)
            )
        ).scalars().all()
    return [
        AllocationResult(
            request_id=r.request_id,
            vessel_id=r.vessel_id,
            assigned_berth=r.assigned_berth,
            berthing_start_time=r.berthing_start_time.isoformat(),
            waiting_time_minutes=r.waiting_time_minutes,
            departure_time=r.departure_time.isoformat(),
            berth_utilization=r.berth_utilization,
            allocation_score=r.allocation_score,
            service_duration_hours=r.service_duration_hours,
            congestion_flag=r.congestion_flag,
            conflict_flag=r.conflict_flag,
            alert_messages=r.alert_messages or [],
            allocated_at=r.allocated_at.isoformat(),
        )
        for r in rows
    ]


async def _save_allocation(result: AllocationResult) -> None:
    """Insert a new AllocationResult row (skip if request_id already exists)."""
    async with AsyncSessionLocal() as session:
        exists = (
            await session.execute(
                select(EngineAllocation.id).where(
                    EngineAllocation.request_id == result.request_id
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            session.add(
                EngineAllocation(
                    request_id=result.request_id,
                    vessel_id=result.vessel_id,
                    assigned_berth=result.assigned_berth,
                    berthing_start_time=datetime.fromisoformat(result.berthing_start_time),
                    waiting_time_minutes=result.waiting_time_minutes,
                    departure_time=datetime.fromisoformat(result.departure_time),
                    berth_utilization=result.berth_utilization,
                    allocation_score=result.allocation_score,
                    service_duration_hours=result.service_duration_hours,
                    congestion_flag=result.congestion_flag,
                    conflict_flag=result.conflict_flag,
                    alert_messages=result.alert_messages,
                    allocated_at=datetime.fromisoformat(result.allocated_at),
                )
            )
            await session.commit()


# ── Application lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global berth_registry
    try:
        csv_path = _find_dataset()
        df = load_dataset(csv_path)
        berth_registry = extract_berth_slots(df)
        print(f"[startup] Loaded {len(berth_registry)} berths from {csv_path.name}")
    except Exception as e:
        print(f"[startup] Warning: dataset not loaded ({e}). Place port_flow_dataset.csv in berth_optimizer/")
        berth_registry = []

    if _DB_AVAILABLE:
        try:
            saved = await _load_active_allocations()
            engine._active_allocations.extend(saved)
            print(f"[startup] Restored {len(saved)} active allocation(s) from database")
        except Exception as exc:
            print(f"[startup] Warning: could not restore allocations from DB ({exc})")

    yield


app = FastAPI(
    title="Smart Port - Berth Optimization API",
    description="Stage 2 of the Smart Port AI pipeline. Open /docs for interactive testing.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


class BerthSlotInput(BaseModel):
    berth_id: str
    berth_max_length: float = Field(300.0, ge=50.0)
    berth_queue_length: int = Field(0, ge=0)
    berth_available_from: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    crane_availability_ratio: float = Field(0.8, ge=0.0, le=1.0)
    berth_max_draft: float = Field(15.0, ge=1.0)


class AllocationRequest(BaseModel):
    predicted_eta: str
    predicted_delay_minutes: float = Field(0.0, ge=0.0)
    vessel_id: str
    vessel_type: str = "Container"
    loa_m: float = Field(200.0, ge=10.0)
    draft_m: float = Field(10.0, ge=1.0)
    gross_tonnage: float = Field(50000.0, ge=100.0)
    vessel_age_years: float = Field(10.0, ge=0.0)
    speed_knots: float = Field(14.0, ge=0.0)
    distance_to_port_nm: float = Field(100.0, ge=0.0)
    port_congestion_index: float = Field(0.5, ge=0.0, le=1.0)
    traffic_density: str = "Medium"
    port_avg_delay_last_24h: float = 20.0
    estimated_service_time_hours: float = Field(6.0, ge=0.5)
    min_service_hours: Optional[float] = None
    max_service_hours: Optional[float] = None
    timestamp: Optional[str] = None
    hour: int = Field(12, ge=0, le=23)
    day_of_week: int = Field(0, ge=0, le=6)
    is_weekend: bool = False
    is_night: bool = False
    berths: Optional[list[BerthSlotInput]] = None

    class Config:
        json_schema_extra = {"example": {
            "vessel_id": "MSC-AURORA-001",
            "predicted_eta": "2025-07-15T14:30:00",
            "predicted_delay_minutes": 35.0,
            "vessel_type": "Container",
            "loa_m": 210.0, "draft_m": 12.5,
            "gross_tonnage": 75000.0, "vessel_age_years": 8.0,
            "speed_knots": 15.0, "distance_to_port_nm": 85.0,
            "port_congestion_index": 0.62, "traffic_density": "High",
            "port_avg_delay_last_24h": 28.5,
            "estimated_service_time_hours": 8.0,
            "hour": 14, "day_of_week": 1, "is_weekend": False, "is_night": False,
        }}


class AllocationResponse(BaseModel):
    assigned_berth: str
    berthing_start_time: str
    waiting_time_minutes: float
    departure_time: str
    berth_utilization: float
    conflict_flag: bool
    congestion_flag: bool
    alert_messages: list[str]
    request_id: str


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "berths_loaded": len(berth_registry),
        "active_allocations": len(engine.get_active_allocations()),
    }


@app.post("/allocate-berth", response_model=AllocationResponse)
async def allocate_berth(request: AllocationRequest):
    payload = request.model_dump(exclude={"berths"})
    if not payload.get("timestamp"):
        payload["timestamp"] = datetime.utcnow().isoformat()
    vessel = vessel_request_from_json(payload)
    berths = ([berth_slot_from_json(b.model_dump()) for b in request.berths]
              if request.berths else berth_registry)
    if not berths:
        raise HTTPException(
            status_code=422,
            detail="No berths available. Place port_flow_dataset.csv inside berth_optimizer/ and restart."
        )
    result = engine.allocate(vessel, berths)
    if _DB_AVAILABLE:
        try:
            await _save_allocation(result)
        except Exception as exc:
            print(f"[warn] Failed to persist allocation {result.request_id}: {exc}")
    return result.to_api_response()


@app.get("/berth-status")
def get_berth_status():
    if not berth_registry:
        return {"berths": [], "message": "Dataset not loaded — no berths registered."}
    return {"timestamp": datetime.utcnow().isoformat(),
            "berths": engine.get_berth_status(berth_registry)}


@app.get("/port-kpis")
def get_port_kpis():
    kpis = engine.get_port_kpis()
    kpis["timestamp"] = datetime.utcnow().isoformat()
    return kpis


@app.get("/allocations")
def get_allocations():
    allocations = engine.get_active_allocations()
    return {"count": len(allocations), "allocations": [a.to_dict() for a in allocations]}


@app.delete("/allocations/expired")
def clear_expired(cutoff_hours: int = 48):
    removed = engine.clear_expired_allocations(cutoff_hours)
    return {"removed": removed, "remaining": len(engine.get_active_allocations())}
