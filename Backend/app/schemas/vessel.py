from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.vessel import VesselType, VesselStatus


class VesselBase(BaseModel):
    imo_number: str
    name: str
    vessel_type: VesselType
    mmsi: str | None = None
    flag: str | None = None
    length_overall: float | None = None
    beam: float | None = None
    max_draft: float | None = None
    gross_tonnage: float | None = None
    deadweight_tonnage: float | None = None


class VesselCreate(VesselBase):
    pass


class VesselUpdate(BaseModel):
    name: str | None = None
    vessel_type: VesselType | None = None
    mmsi: str | None = None
    flag: str | None = None
    length_overall: float | None = None
    beam: float | None = None
    max_draft: float | None = None
    gross_tonnage: float | None = None
    deadweight_tonnage: float | None = None
    status: VesselStatus | None = None
    current_lat: float | None = None
    current_lon: float | None = None
    current_speed: float | None = None
    current_heading: float | None = None


class VesselResponse(VesselBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: VesselStatus
    current_lat: float | None = None
    current_lon: float | None = None
    current_speed: float | None = None
    current_heading: float | None = None
    created_at: datetime
    updated_at: datetime
