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


# Canonical "active visit" definition — single source of truth shared by
# analytics.py, port_ops.py, chat.py, and analytics_service.py.
# A visit is "active" once the vessel is operationally underway or in port.
# SCHEDULED visits are future bookings, not yet underway, so they are
# tracked as a separate count and excluded here.
ACTIVE_VISIT_STATUSES = [
    VisitStatus.APPROACHING,
    VisitStatus.ANCHORED,
    VisitStatus.BERTHING,
    VisitStatus.IN_PORT,
    VisitStatus.DEPARTING,
]

# Terminal states — visit lifecycle has ended.
TERMINAL_VISIT_STATUSES = [VisitStatus.COMPLETED, VisitStatus.CANCELLED]


class CargoType(str, enum.Enum):
    CONTAINERS = "containers"
    BULK_DRY = "bulk_dry"
    BULK_LIQUID = "bulk_liquid"
    GENERAL = "general"
    RO_RO = "ro_ro"
    PASSENGER = "passenger"
    OTHER = "other"


class ClearanceStatus(str, enum.Enum):
    PENDING = "pending"
    CUSTOMS_CLEARED = "customs_cleared"
    PORT_CLEARED = "port_cleared"
    HEALTH_CLEARED = "health_cleared"
    FULLY_CLEARED = "fully_cleared"
    FLAGGED = "flagged"


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vessel_id: Mapped[int] = mapped_column(Integer, ForeignKey("vessels.id"), nullable=False, index=True)
    berth_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("berths.id"), nullable=True, index=True)
    port_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ports.id"), nullable=True, index=True)
    voyage_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("voyages.id"), nullable=True, index=True)

    # Scheduling
    eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    etb: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    etd: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Actuals
    ata: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    atb: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    atd: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Cargo
    cargo_type: Mapped[CargoType | None] = mapped_column(Enum(CargoType), nullable=True)
    cargo_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    cargo_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Status
    status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus), default=VisitStatus.SCHEDULED, nullable=False
    )
    clearance_status: Mapped[ClearanceStatus] = mapped_column(
        Enum(ClearanceStatus), default=ClearanceStatus.PENDING, nullable=False
    )
    voyage_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Performance metrics
    waiting_time_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    berth_time_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnaround_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    efficiency_rating: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0-10.0

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    vessel: Mapped["Vessel"] = relationship("Vessel", back_populates="visits")  # noqa: F821
    berth: Mapped["Berth"] = relationship("Berth", back_populates="visits")      # noqa: F821
    port: Mapped["Port"] = relationship("Port")                                  # noqa: F821
    voyage: Mapped["Voyage"] = relationship("Voyage", back_populates="visits")   # noqa: F821
    predictions: Mapped[list["Prediction"]] = relationship("Prediction", back_populates="visit")  # noqa: F821
    cargo_manifest: Mapped["CargoManifest"] = relationship(  # noqa: F821
        "CargoManifest", back_populates="visit", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Visit vessel_id={self.vessel_id} berth_id={self.berth_id} status={self.status}>"
