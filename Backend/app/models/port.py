from datetime import datetime

from sqlalchemy import ForeignKey, String, Float, Integer, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Port(Base):
    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Geographic
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Operational info
    un_locode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    max_vessel_loa: Mapped[float | None] = mapped_column(Float, nullable=True)   # meters
    max_vessel_draft: Mapped[float | None] = mapped_column(Float, nullable=True) # meters
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    berths: Mapped[list["Berth"]] = relationship("Berth", back_populates="port")  # noqa: F821
    terminals: Mapped[list["Terminal"]] = relationship("Terminal", back_populates="port")
    voyages_origin: Mapped[list["Voyage"]] = relationship(  # noqa: F821
        "Voyage", foreign_keys="Voyage.origin_port_id", back_populates="origin_port"
    )
    voyages_destination: Mapped[list["Voyage"]] = relationship(  # noqa: F821
        "Voyage", foreign_keys="Voyage.destination_port_id", back_populates="destination_port"
    )

    def __repr__(self) -> str:
        return f"<Port {self.code} - {self.name}>"


class Terminal(Base):
    __tablename__ = "terminals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    port_id: Mapped[int] = mapped_column(ForeignKey("ports.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    terminal_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    port: Mapped["Port"] = relationship("Port", back_populates="terminals")

    def __repr__(self) -> str:
        return f"<Terminal {self.code} @ port_id={self.port_id}>"
