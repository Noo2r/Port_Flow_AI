"""Work Order Pydantic schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.work_orders import WorkOrderPriority, WorkOrderStatus, WorkOrderType


class WorkOrderCreate(BaseModel):
    visit_id: int
    vessel_id: int
    berth_id: int | None = None
    order_type: WorkOrderType
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    priority: WorkOrderPriority = WorkOrderPriority.NORMAL
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None


class WorkOrderUpdate(BaseModel):
    status: WorkOrderStatus | None = None
    priority: WorkOrderPriority | None = None
    assigned_to: int | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    completion_notes: str | None = None


class WorkOrderResponse(BaseModel):
    id: int
    visit_id: int
    vessel_id: int
    berth_id: int | None
    assigned_to: int | None
    order_type: WorkOrderType
    title: str
    description: str | None
    status: WorkOrderStatus
    priority: WorkOrderPriority
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    actual_start: datetime | None
    actual_end: datetime | None
    completion_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
