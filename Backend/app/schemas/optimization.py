from datetime import datetime

from pydantic import BaseModel


class BerthAssignment(BaseModel):
    visit_id: int
    vessel_id: int
    vessel_name: str
    vessel_imo: str
    assigned_berth_id: int
    assigned_berth_code: str
    predicted_eta: datetime | None
    estimated_waiting_minutes: float


class OptimizationResult(BaseModel):
    assignments_made: int
    assignments: list[BerthAssignment]
    unassigned_visits: list[int]
    message: str
