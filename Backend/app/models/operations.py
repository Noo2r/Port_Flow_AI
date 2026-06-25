import enum
from datetime import datetime

from sqlalchemy import String, Float, Integer, Boolean, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ManifestStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    COMPLETED = "completed"


class CargoManifest(Base):
    __tablename__ = "cargo_manifests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id"), nullable=False, index=True)
    manifest_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[ManifestStatus] = mapped_column(
        Enum(ManifestStatus), default=ManifestStatus.DRAFT, nullable=False
    )

    # Totals
    total_weight_mt: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_volume_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_teu: Mapped[int | None] = mapped_column(Integer, nullable=True)         # for container ships

    discharge_port: Mapped[str | None] = mapped_column(String(100), nullable=True)
    load_port: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipper: Mapped[str | None] = mapped_column(String(150), nullable=True)
    consignee: Mapped[str | None] = mapped_column(String(150), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    visit: Mapped["Visit"] = relationship("Visit", back_populates="cargo_manifest")  # noqa: F821
    containers: Mapped[list["Container"]] = relationship("Container", back_populates="manifest")
    bulk_cargo: Mapped[list["BulkCargo"]] = relationship("BulkCargo", back_populates="manifest")

    def __repr__(self) -> str:
        return f"<CargoManifest {self.manifest_number} status={self.status}>"


class ContainerStatus(str, enum.Enum):
    EXPECTED = "expected"
    ON_BOARD = "on_board"
    DISCHARGED = "discharged"
    LOADED = "loaded"
    IN_YARD = "in_yard"
    DEPARTED = "departed"


class Container(Base):
    __tablename__ = "containers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    manifest_id: Mapped[int] = mapped_column(Integer, ForeignKey("cargo_manifests.id"), nullable=False, index=True)
    container_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    iso_type: Mapped[str | None] = mapped_column(String(10), nullable=True)       # e.g. 22G1, 42G1
    size_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)           # 20 or 40
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_hazmat: Mapped[bool] = mapped_column(Boolean, default=False)
    is_reefer: Mapped[bool] = mapped_column(Boolean, default=False)
    temperature_set: Mapped[float | None] = mapped_column(Float, nullable=True)   # Celsius for reefer
    status: Mapped[ContainerStatus] = mapped_column(
        Enum(ContainerStatus), default=ContainerStatus.EXPECTED, nullable=False
    )
    seal_number: Mapped[str | None] = mapped_column(String(30), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    manifest: Mapped["CargoManifest"] = relationship("CargoManifest", back_populates="containers")

    def __repr__(self) -> str:
        return f"<Container {self.container_number} status={self.status}>"


class BulkCargo(Base):
    __tablename__ = "bulk_cargo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    manifest_id: Mapped[int] = mapped_column(Integer, ForeignKey("cargo_manifests.id"), nullable=False, index=True)
    commodity: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_mt: Mapped[float] = mapped_column(Float, nullable=False)
    stowage_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_hazmat: Mapped[bool] = mapped_column(Boolean, default=False)
    un_number: Mapped[str | None] = mapped_column(String(10), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    manifest: Mapped["CargoManifest"] = relationship("CargoManifest", back_populates="bulk_cargo")

    def __repr__(self) -> str:
        return f"<BulkCargo {self.commodity} {self.quantity_mt}mt>"
