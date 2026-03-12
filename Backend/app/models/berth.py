import enum
from datetime import datetime

from sqlalchemy import String, Float, Integer, Boolean, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BerthStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    RESERVED = "reserved"


class BerthType(str, enum.Enum):
    CONTAINER = "container"
    BULK = "bulk"
    TANKER = "tanker"
    RO_RO = "ro_ro"
    GENERAL = "general"
    MULTIPURPOSE = "multipurpose"


class Berth(Base):
    __tablename__ = "berths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    terminal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    berth_type: Mapped[BerthType] = mapped_column(Enum(BerthType), nullable=False)

    # Physical specs
    max_length: Mapped[float] = mapped_column(Float, nullable=False)      # meters
    max_beam: Mapped[float | None] = mapped_column(Float, nullable=True)   # meters
    max_draft: Mapped[float] = mapped_column(Float, nullable=False)        # meters
    max_tonnage: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Equipment / capabilities
    has_crane: Mapped[bool] = mapped_column(Boolean, default=False)
    crane_capacity_tons: Mapped[float | None] = mapped_column(Float, nullable=True)
    has_pipeline: Mapped[bool] = mapped_column(Boolean, default=False)

    # Current state
    status: Mapped[BerthStatus] = mapped_column(
        Enum(BerthStatus), default=BerthStatus.AVAILABLE, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    visits: Mapped[list["Visit"]] = relationship("Visit", back_populates="berth")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Berth {self.code} - {self.name}>"
