import enum
from datetime import datetime

from sqlalchemy import ForeignKey, String, Float, Integer, Boolean, DateTime, Enum, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class KPICategory(str, enum.Enum):
    EFFICIENCY = "efficiency"
    SAFETY = "safety"
    ENVIRONMENTAL = "environmental"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"


class KPIDefinition(Base):
    __tablename__ = "kpi_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[KPICategory] = mapped_column(Enum(KPICategory), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_higher_better: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    values: Mapped[list["KPIValue"]] = relationship("KPIValue", back_populates="kpi")

    def __repr__(self) -> str:
        return f"<KPIDefinition {self.code}>"


class KPIValue(Base):
    __tablename__ = "kpi_values"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    kpi_id: Mapped[int] = mapped_column(ForeignKey("kpi_definitions.id"), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    kpi: Mapped["KPIDefinition"] = relationship("KPIDefinition", back_populates="values")

    def __repr__(self) -> str:
        return f"<KPIValue kpi_id={self.kpi_id} value={self.value}>"


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), default=ReportStatus.DRAFT, nullable=False
    )
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Report {self.title} type={self.report_type} status={self.status}>"
