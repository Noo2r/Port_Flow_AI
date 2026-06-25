from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PortBase(BaseModel):
    code: str
    name: str
    country: str | None = None
    city: str | None = None
    timezone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    un_locode: str | None = None
    max_vessel_loa: float | None = None
    max_vessel_draft: float | None = None
    notes: str | None = None
    is_active: bool = True


class PortCreate(PortBase):
    pass


class PortUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    city: str | None = None
    timezone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    un_locode: str | None = None
    max_vessel_loa: float | None = None
    max_vessel_draft: float | None = None
    notes: str | None = None
    is_active: bool | None = None


class PortResponse(PortBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
