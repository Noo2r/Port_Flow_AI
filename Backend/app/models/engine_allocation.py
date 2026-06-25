from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EngineAllocation(Base):
    """Persists BerthOptimizationEngine._active_allocations so conflict detection
    survives a server restart."""

    __tablename__ = "engine_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    vessel_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    assigned_berth: Mapped[str] = mapped_column(String(100), nullable=False)
    berthing_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    waiting_time_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    departure_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, index=True)
    berth_utilization: Mapped[float] = mapped_column(Float, nullable=False)
    allocation_score: Mapped[float] = mapped_column(Float, nullable=False)
    service_duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    congestion_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    conflict_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    alert_messages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    allocated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<EngineAllocation request_id={self.request_id} berth={self.assigned_berth}>"
