import enum
from datetime import datetime

from sqlalchemy import String, Float, Integer, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmissionSource(str, enum.Enum):
    MAIN_ENGINE = "main_engine"
    AUXILIARY_ENGINE = "auxiliary_engine"
    BOILER = "boiler"
    COLD_IRONING = "cold_ironing"


class VesselEmission(Base):
    __tablename__ = "vessel_emissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vessel_id: Mapped[int] = mapped_column(Integer, ForeignKey("vessels.id"), nullable=False, index=True)
    visit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("visits.id"), nullable=True, index=True)

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source: Mapped[EmissionSource] = mapped_column(
        Enum(EmissionSource), default=EmissionSource.MAIN_ENGINE, nullable=False
    )

    co2_mt: Mapped[float | None] = mapped_column(Float, nullable=True)
    sox_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    nox_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm_kg: Mapped[float | None] = mapped_column(Float, nullable=True)           # particulate matter
    fuel_consumed_mt: Mapped[float | None] = mapped_column(Float, nullable=True)

    vessel: Mapped["Vessel"] = relationship("Vessel")  # noqa: F821

    def __repr__(self) -> str:
        return f"<VesselEmission vessel_id={self.vessel_id} co2={self.co2_mt}mt>"


class WasteCategory(str, enum.Enum):
    BILGE_WATER = "bilge_water"
    SLUDGE = "sludge"
    GARBAGE = "garbage"
    SEWAGE = "sewage"
    HAZARDOUS = "hazardous"


class WasteManagement(Base):
    __tablename__ = "waste_management"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id"), nullable=False, index=True)
    category: Mapped[WasteCategory] = mapped_column(Enum(WasteCategory), nullable=False)
    quantity_m3: Mapped[float] = mapped_column(Float, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    disposal_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contractor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    certificate_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<WasteManagement visit_id={self.visit_id} category={self.category}>"
