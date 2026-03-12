from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.berth import BerthType, BerthStatus


class BerthBase(BaseModel):
    code: str
    name: str
    berth_type: BerthType
    max_length: float
    max_draft: float
    terminal: str | None = None
    max_beam: float | None = None
    max_tonnage: float | None = None
    has_crane: bool = False
    crane_capacity_tons: float | None = None
    has_pipeline: bool = False


class BerthCreate(BerthBase):
    pass


class BerthUpdate(BaseModel):
    name: str | None = None
    berth_type: BerthType | None = None
    terminal: str | None = None
    max_length: float | None = None
    max_beam: float | None = None
    max_draft: float | None = None
    max_tonnage: float | None = None
    has_crane: bool | None = None
    crane_capacity_tons: float | None = None
    has_pipeline: bool | None = None
    status: BerthStatus | None = None
    is_active: bool | None = None


class BerthResponse(BerthBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: BerthStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime
