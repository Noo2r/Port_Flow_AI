import enum
from datetime import datetime

from sqlalchemy import String, Float, Integer, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VisitStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    APPROACHING = "approaching"
    ANCHORED = "anchored"
    BERTHING = "berthing"
    IN_PORT = "in_port"
    DEPARTING = "departing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CargoType(str, enum.Enum):
    CONTAINERS = "containers"
    BULK_DRY = "bulk_dry"
    BULK_LIQUID = "bulk_liquid"
    GENERAL = "general"
    RO_RO = "ro_ro"
    PASSENGER = "passenger"
    OTHER = "other"


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vessel_id: Mapped[int] = mapped_column(Integer, ForeignKey("vessels.id"), nullable=False, index=True)
    berth_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("berths.id"), nullable=True, index=True)

    # Scheduling
    eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # Estimated Time of Arrival
    etb: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # Estimated Time of Berthing
    etd: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # Estimated Time of Departure

    # Actuals
    ata: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # Actual Time of Arrival
    atb: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # Actual Time of Berthing
    atd: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)   # Actual Time of Departure

    # Cargo
    cargo_type: Mapped[CargoType | None] = mapped_column(Enum(CargoType), nullable=True)
    cargo_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)             # tonnes
    cargo_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)              # e.g. TEU, MT

    # Status
    status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus), default=VisitStatus.SCHEDULED, nullable=False
    )
    voyage_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Waiting / performance metrics
    waiting_time_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    berth_time_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    vessel: Mapped["Vessel"] = relationship("Vessel", back_populates="visits")  # noqa: F821
    berth: Mapped["Berth"] = relationship("Berth", back_populates="visits")      # noqa: F821
    predictions: Mapped[list["Prediction"]] = relationship("Prediction", back_populates="visit")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Visit vessel_id={self.vessel_id} berth_id={self.berth_id} status={self.status}>"
