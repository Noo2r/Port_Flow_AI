import enum
from datetime import datetime

from sqlalchemy import String, Float, Integer, Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EquipmentType(str, enum.Enum):
    CRANE = "crane"
    FORKLIFT = "forklift"
    REACH_STACKER = "reach_stacker"
    TUGBOAT = "tugboat"
    MOORING_BOAT = "mooring_boat"
    CONVEYOR = "conveyor"
    PUMP = "pump"
    OTHER = "other"


class EquipmentStatus(str, enum.Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    BREAKDOWN = "breakdown"
    RETIRED = "retired"


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    port_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ports.id"), nullable=True, index=True)
    berth_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("berths.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    equipment_type: Mapped[EquipmentType] = mapped_column(Enum(EquipmentType), nullable=False)
    capacity_tons: Mapped[float | None] = mapped_column(Float, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[EquipmentStatus] = mapped_column(
        Enum(EquipmentStatus), default=EquipmentStatus.AVAILABLE, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    allocations: Mapped[list["EquipmentAllocation"]] = relationship(
        "EquipmentAllocation", back_populates="equipment"
    )

    def __repr__(self) -> str:
        return f"<Equipment {self.code} type={self.equipment_type} status={self.status}>"


class EquipmentAllocation(Base):
    __tablename__ = "equipment_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    equipment_id: Mapped[int] = mapped_column(Integer, ForeignKey("equipment.id"), nullable=False, index=True)
    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id"), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    task: Mapped[str | None] = mapped_column(String(200), nullable=True)
    moves_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="allocations")

    def __repr__(self) -> str:
        return f"<EquipmentAllocation equipment_id={self.equipment_id} visit_id={self.visit_id}>"


class LaborShift(Base):
    __tablename__ = "labor_shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    port_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ports.id"), nullable=True)
    shift_name: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gang_size: Mapped[int] = mapped_column(Integer, default=0)
    supervisor: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    allocations: Mapped[list["LaborAllocation"]] = relationship(
        "LaborAllocation", back_populates="shift"
    )

    def __repr__(self) -> str:
        return f"<LaborShift {self.shift_name}>"


class LaborAllocation(Base):
    __tablename__ = "labor_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    shift_id: Mapped[int] = mapped_column(Integer, ForeignKey("labor_shifts.id"), nullable=False, index=True)
    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id"), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    headcount: Mapped[int] = mapped_column(Integer, default=1)
    productivity_moves_ph: Mapped[float | None] = mapped_column(Float, nullable=True)

    shift: Mapped["LaborShift"] = relationship("LaborShift", back_populates="allocations")

    def __repr__(self) -> str:
        return f"<LaborAllocation shift_id={self.shift_id} visit_id={self.visit_id}>"
