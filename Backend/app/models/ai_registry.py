import enum
from datetime import datetime, date

from sqlalchemy import String, Float, Integer, Boolean, Date, DateTime, Enum, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ModelApprovalStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


class DeploymentEnvironment(str, enum.Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class AIModelRegistry(Base):
    """Registry of all AI/ML models used in the PortFlow system."""
    __tablename__ = "ai_model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Input/output format specs
    input_format: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_format: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Training info
    training_data_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    training_data_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    training_samples: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Performance metrics
    accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae_score: Mapped[float | None] = mapped_column(Float, nullable=True)    # mean absolute error
    rmse_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Deployment
    approval_status: Mapped[ModelApprovalStatus] = mapped_column(
        Enum(ModelApprovalStatus), default=ModelApprovalStatus.DRAFT, nullable=False
    )
    deployment_env: Mapped[DeploymentEnvironment] = mapped_column(
        Enum(DeploymentEnvironment), default=DeploymentEnvironment.DEVELOPMENT, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    predictions: Mapped[list["Prediction"]] = relationship(  # noqa: F821
        "Prediction", back_populates="model_registry"
    )

    def __repr__(self) -> str:
        return f"<AIModelRegistry {self.model_name} v{self.model_version} env={self.deployment_env}>"
