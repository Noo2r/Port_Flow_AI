from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.voyage import VoyageStatus


class VoyageBase(BaseModel):
    voyage_number: str
    vessel_id: int
    origin_port_id: int | None = None
    destination_port_id: int | None = None
    planned_departure: datetime | None = None
    actual_departure: datetime | None = None
    planned_arrival: datetime | None = None
    actual_arrival: datetime | None = None
    status: VoyageStatus = VoyageStatus.PLANNED
    distance_nm: float | None = None
    average_speed: float | None = None
    fuel_consumed_mt: float | None = None
    co2_emissions_mt: float | None = None
    notes: str | None = None


class VoyageCreate(VoyageBase):
    pass


class VoyageUpdate(BaseModel):
    status: VoyageStatus | None = None
    actual_departure: datetime | None = None
    actual_arrival: datetime | None = None
    distance_nm: float | None = None
    average_speed: float | None = None
    fuel_consumed_mt: float | None = None
    co2_emissions_mt: float | None = None
    notes: str | None = None


class VoyageResponse(VoyageBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
