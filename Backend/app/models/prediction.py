import enum
from datetime import datetime

from sqlalchemy import String, Float, Integer, DateTime, Enum, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PredictionType(str, enum.Enum):
    ETA = "eta"                          # Estimated Time of Arrival
    ETB = "etb"                          # Estimated Time of Berthing
    BERTH_CONGESTION = "berth_congestion"
    WAITING_TIME = "waiting_time"
    BERTH_ASSIGNMENT = "berth_assignment"


class PredictionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vessel_id: Mapped[int] = mapped_column(Integer, ForeignKey("vessels.id"), nullable=False, index=True)
    visit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("visits.id"), nullable=True, index=True)

    prediction_type: Mapped[PredictionType] = mapped_column(Enum(PredictionType), nullable=False)
    status: Mapped[PredictionStatus] = mapped_column(
        Enum(PredictionStatus), default=PredictionStatus.PENDING, nullable=False
    )

    # Model info
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Prediction result
    predicted_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)   # 0.0 - 1.0
    lower_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_bound: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Input features snapshot (for auditability)
    input_features: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Actuals for model evaluation
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_mae: Mapped[float | None] = mapped_column(Float, nullable=True)  # Mean Absolute Error (hours)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    vessel: Mapped["Vessel"] = relationship("Vessel", back_populates="predictions")  # noqa: F821
    visit: Mapped["Visit"] = relationship("Visit", back_populates="predictions")      # noqa: F821

    def __repr__(self) -> str:
        return f"<Prediction type={self.prediction_type} vessel_id={self.vessel_id} confidence={self.confidence_score}>"
