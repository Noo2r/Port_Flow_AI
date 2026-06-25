import enum
from datetime import datetime

from sqlalchemy import String, Float, Integer, Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VesselType(str, enum.Enum):
    CONTAINER = "container"
    BULK_CARRIER = "bulk_carrier"
    TANKER = "tanker"
    RO_RO = "ro_ro"
    GENERAL_CARGO = "general_cargo"
    OTHER = "other"


class VesselStatus(str, enum.Enum):
    AT_SEA = "at_sea"
    APPROACHING = "approaching"
    ANCHORED = "anchored"
    BERTHED = "berthed"
    DEPARTED = "departed"


class Vessel(Base):
    __tablename__ = "vessels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    imo_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    mmsi: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    vessel_type: Mapped[VesselType] = mapped_column(Enum(VesselType), nullable=False)
    flag: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Physical dimensions
    length_overall: Mapped[float | None] = mapped_column(Float, nullable=True)   # meters
    beam: Mapped[float | None] = mapped_column(Float, nullable=True)              # meters
    max_draft: Mapped[float | None] = mapped_column(Float, nullable=True)         # meters
    gross_tonnage: Mapped[float | None] = mapped_column(Float, nullable=True)
    deadweight_tonnage: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Current state
    status: Mapped[VesselStatus] = mapped_column(
        Enum(VesselStatus), default=VesselStatus.AT_SEA, nullable=False
    )
    current_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_speed: Mapped[float | None] = mapped_column(Float, nullable=True)     # knots
    current_heading: Mapped[float | None] = mapped_column(Float, nullable=True)   # degrees

    # Port association
    current_port_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ports.id"), nullable=True)

    # Ownership / commercial
    owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(200), nullable=True)
    manager: Mapped[str | None] = mapped_column(String(200), nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Research categorisation (AAST)
    research_category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Insurance
    pni_club: Mapped[str | None] = mapped_column(String(200), nullable=True)   # P&I Club
    hull_insurer: Mapped[str | None] = mapped_column(String(200), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    current_port: Mapped["Port"] = relationship("Port")  # noqa: F821
    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="vessel")  # noqa: F821
    voyages: Mapped[list["Voyage"]] = relationship("Voyage", back_populates="vessel")  # noqa: F821
    predictions: Mapped[list["Prediction"]] = relationship("Prediction", back_populates="vessel")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Vessel {self.imo_number} - {self.name}>"
