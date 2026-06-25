from datetime import datetime

from pydantic import BaseModel, Field


class AISUpdateRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    speed_knots: float | None = Field(default=None, ge=0, le=50)
    heading_degrees: float | None = Field(default=None, ge=0, le=360)


class AISUpdateResponse(BaseModel):
    visit_id: int
    vessel_id: int
    vessel_name: str
    latitude: float
    longitude: float
    speed_knots: float | None
    heading_degrees: float | None
    updated_at: datetime


class WeatherImpactResponse(BaseModel):
    visit_id: int
    vessel_id: int
    original_eta: datetime | None
    adjusted_eta: datetime | None
    delay_hours: float
    weather_factor: float
    wind_speed: float | None
    visibility: float | None
    wave_height: float | None


class ConflictItem(BaseModel):
    visit_id: int
    vessel_name: str
    vessel_imo: str
    etb: datetime | None
    etd: datetime | None
    status: str


class ConflictResponse(BaseModel):
    berth_id: int
    berth_code: str
    conflicts_found: int
    conflicts: list[ConflictItem]
    resolution_suggestion: str | None
