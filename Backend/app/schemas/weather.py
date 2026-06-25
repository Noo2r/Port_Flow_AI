from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WeatherDataCreate(BaseModel):
    port_id: int | None = None
    wind_speed: float | None = None
    wind_direction: float | None = None
    visibility: float | None = None
    wave_height: float | None = None
    temperature: float | None = None
    tide_height: float | None = None
    current_speed: float | None = None
    source: str | None = "manual"


class WeatherDataResponse(WeatherDataCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recorded_at: datetime
