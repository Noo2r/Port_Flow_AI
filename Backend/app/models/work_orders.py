"""
Work Order model — auto-generated on berth assignment, tracks port operations tasks.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WorkOrderType(str, enum.Enum):
    MOORING = "mooring"
    UNMOORING = "unmooring"
    PILOTAGE = "pilotage"
    TUGBOAT = "tugboat"
    CARGO_HANDLING = "cargo_handling"
    CUSTOMS_INSPECTION = "customs_inspection"
    HEALTH_INSPECTION = "health_inspection"
    BUNKERING = "bunkering"
    FRESH_WATER = "fresh_water"
    WASTE_RECEPTION = "waste_reception"
    MAINTENANCE = "maintenance"
    GENERAL = "general"


class WorkOrderStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkOrderPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Associations
    visit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("visits.id"), nullable=False, index=True
    )
    berth_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("berths.id"), nullable=True, index=True
    )
    vessel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vessels.id"), nullable=False, index=True
    )
    assigned_to: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    # Details
    # values_callable ensures SQLAlchemy stores enum .value ("pilotage") not .name ("PILOTAGE")
    order_type: Mapped[WorkOrderType] = mapped_column(
        Enum(WorkOrderType, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[WorkOrderStatus] = mapped_column(
        Enum(WorkOrderStatus, values_callable=lambda x: [e.value for e in x]),
        default=WorkOrderStatus.PENDING, nullable=False
    )
    priority: Mapped[WorkOrderPriority] = mapped_column(
        Enum(WorkOrderPriority, values_callable=lambda x: [e.value for e in x]),
        default=WorkOrderPriority.NORMAL, nullable=False
    )

    # Scheduling
    scheduled_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scheduled_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    visit: Mapped["Visit"] = relationship("Visit")  # noqa: F821
    vessel: Mapped["Vessel"] = relationship("Vessel")  # noqa: F821
    berth: Mapped["Berth"] = relationship("Berth")  # noqa: F821

    def __repr__(self) -> str:
        return f"<WorkOrder {self.order_type} visit={self.visit_id} status={self.status}>"
