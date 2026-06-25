import enum
from datetime import datetime

from sqlalchemy import String, Float, Integer, Boolean, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnomalyType(str, enum.Enum):
    DELAY = "delay"
    EXCESSIVE_WAITING = "excessive_waiting"
    UNUSUAL_SPEED = "unusual_speed"
    CARGO_DISCREPANCY = "cargo_discrepancy"
    BERTH_CONFLICT = "berth_conflict"
    EMISSION_SPIKE = "emission_spike"
    EQUIPMENT_FAILURE = "equipment_failure"
    OTHER = "other"


class AnomalySeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vessel_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("vessels.id"), nullable=True, index=True)
    visit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("visits.id"), nullable=True, index=True)

    anomaly_type: Mapped[AnomalyType] = mapped_column(Enum(AnomalyType), nullable=False)
    severity: Mapped[AnomalySeverity] = mapped_column(
        Enum(AnomalySeverity), default=AnomalySeverity.MEDIUM, nullable=False
    )
    status: Mapped[AnomalyStatus] = mapped_column(
        Enum(AnomalyStatus), default=AnomalyStatus.OPEN, nullable=False
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)
    detected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    deviation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_automated: Mapped[bool] = mapped_column(Boolean, default=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vessel: Mapped["Vessel"] = relationship("Vessel")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Anomaly type={self.anomaly_type} severity={self.severity} status={self.status}>"
