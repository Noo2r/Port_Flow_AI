"""
Berth Operations Schemas
========================
Pydantic models for the Stage-2 berth optimizer API and
the unified ETA + Berth combined response.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel

from app.schemas.eta import PredictETAResult


# ── Berth allocation response ─────────────────────────────────────────────────
class BerthAllocationResult(BaseModel):
    assigned_berth:      str
    berthing_start_time: str
    waiting_time_minutes: float
    departure_time:      str
    berth_utilization:   float
    conflict_flag:       bool
    congestion_flag:     bool
    alert_messages:      list[str]
    request_id:          str


# ── Combined ETA + Berth response ─────────────────────────────────────────────
class ETAAndBerthResult(BaseModel):
    """
    Unified response returned by POST /api/v1/ai/predict/eta-and-berth.
    Contains the full Stage-1 ETA prediction plus Stage-2 berth allocation.
    """
    # Stage 1 — ETA model
    eta: PredictETAResult

    # Stage 2 — Berth optimizer
    berth: Optional[BerthAllocationResult] = None
    berth_error: Optional[str] = None   # populated if Stage 2 failed
