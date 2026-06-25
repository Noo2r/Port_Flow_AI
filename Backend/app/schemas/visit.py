from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.visit import VisitStatus, CargoType, ClearanceStatus


class VisitBase(BaseModel):
    vessel_id: int
    berth_id: int | None = None
    port_id: int | None = None
    voyage_id: int | None = None
    eta: datetime | None = None
    etb: datetime | None = None
    etd: datetime | None = None
    cargo_type: CargoType | None = None
    cargo_quantity: float | None = None
    cargo_unit: str | None = None
    voyage_number: str | None = None
    agent: str | None = None
    notes: str | None = None


class VisitCreate(VisitBase):
    pass


class VisitUpdate(BaseModel):
    berth_id: int | None = None
    port_id: int | None = None
    voyage_id: int | None = None
    eta: datetime | None = None
    etb: datetime | None = None
    etd: datetime | None = None
    ata: datetime | None = None
    atb: datetime | None = None
    atd: datetime | None = None
    cargo_type: CargoType | None = None
    cargo_quantity: float | None = None
    cargo_unit: str | None = None
    status: VisitStatus | None = None
    clearance_status: ClearanceStatus | None = None
    voyage_number: str | None = None
    agent: str | None = None
    notes: str | None = None
    waiting_time_hours: float | None = None
    berth_time_hours: float | None = None
    turnaround_hours: float | None = None
    efficiency_rating: float | None = None


class VisitResponse(VisitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: VisitStatus
    clearance_status: ClearanceStatus
    ata: datetime | None = None
    atb: datetime | None = None
    atd: datetime | None = None
    waiting_time_hours: float | None = None
    berth_time_hours: float | None = None
    turnaround_hours: float | None = None
    efficiency_rating: float | None = None
    created_at: datetime
    updated_at: datetime
