import enum
from datetime import datetime

from sqlalchemy import String, Float, Integer, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VoyageStatus(str, enum.Enum):
    PLANNED = "planned"
    UNDERWAY = "underway"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DIVERTED = "diverted"


class Voyage(Base):
    __tablename__ = "voyages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    voyage_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    vessel_id: Mapped[int] = mapped_column(Integer, ForeignKey("vessels.id"), nullable=False, index=True)

    # Ports
    origin_port_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ports.id"), nullable=True)
    destination_port_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ports.id"), nullable=True)

    # Scheduling
    planned_departure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_departure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    status: Mapped[VoyageStatus] = mapped_column(
        Enum(VoyageStatus), default=VoyageStatus.PLANNED, nullable=False
    )

    # Operational data
    distance_nm: Mapped[float | None] = mapped_column(Float, nullable=True)       # nautical miles
    average_speed: Mapped[float | None] = mapped_column(Float, nullable=True)     # knots
    fuel_consumed_mt: Mapped[float | None] = mapped_column(Float, nullable=True)  # metric tons
    co2_emissions_mt: Mapped[float | None] = mapped_column(Float, nullable=True)  # metric tons

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    vessel: Mapped["Vessel"] = relationship("Vessel", back_populates="voyages")  # noqa: F821
    origin_port: Mapped["Port"] = relationship(  # noqa: F821
        "Port", foreign_keys=[origin_port_id], back_populates="voyages_origin"
    )
    destination_port: Mapped["Port"] = relationship(  # noqa: F821
        "Port", foreign_keys=[destination_port_id], back_populates="voyages_destination"
    )
    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="voyage")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Voyage {self.voyage_number} vessel_id={self.vessel_id} status={self.status}>"
