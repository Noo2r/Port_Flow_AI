import enum
from datetime import datetime, date

from sqlalchemy import String, Integer, Boolean, Date, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ResearchStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class DataAccessLevel(str, enum.Enum):
    AGGREGATED = "aggregated"
    ANONYMIZED = "anonymized"
    FULL = "full"


class AASTResearchProject(Base):
    """Academic and Scientific & Technology research projects with port data access."""
    __tablename__ = "aast_research_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    institution: Mapped[str] = mapped_column(String(200), nullable=False)
    principal_investigator: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ResearchStatus] = mapped_column(
        Enum(ResearchStatus), default=ResearchStatus.PROPOSED, nullable=False
    )
    data_access_level: Mapped[DataAccessLevel] = mapped_column(
        Enum(DataAccessLevel), default=DataAccessLevel.AGGREGATED, nullable=False
    )

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ethics_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    ethics_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    data_access_records: Mapped[list["ResearchDataAccess"]] = relationship(
        "ResearchDataAccess", back_populates="project"
    )
    findings: Mapped[list["ResearchFinding"]] = relationship("ResearchFinding", back_populates="project")

    def __repr__(self) -> str:
        return f"<AASTResearchProject {self.project_code} status={self.status}>"


class ResearchDataAccess(Base):
    __tablename__ = "research_data_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("aast_research_projects.id"), nullable=False, index=True
    )
    dataset: Mapped[str] = mapped_column(String(100), nullable=False)
    access_level: Mapped[DataAccessLevel] = mapped_column(Enum(DataAccessLevel), nullable=False)
    records_accessed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    purpose: Mapped[str | None] = mapped_column(String(500), nullable=True)

    project: Mapped["AASTResearchProject"] = relationship(
        "AASTResearchProject", back_populates="data_access_records"
    )

    def __repr__(self) -> str:
        return f"<ResearchDataAccess project_id={self.project_id} dataset={self.dataset}>"


class ResearchFinding(Base):
    __tablename__ = "research_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("aast_research_projects.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    publication_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["AASTResearchProject"] = relationship("AASTResearchProject", back_populates="findings")

    def __repr__(self) -> str:
        return f"<ResearchFinding project_id={self.project_id} title={self.title[:40]}>"
