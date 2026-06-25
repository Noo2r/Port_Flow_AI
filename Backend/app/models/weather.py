from datetime import datetime

from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WeatherData(Base):
    __tablename__ = "weather_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    port_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ports.id"), nullable=True, index=True)

    # Recorded at
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Conditions
    wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)        # knots
    wind_direction: Mapped[float | None] = mapped_column(Float, nullable=True)    # degrees 0-360
    visibility: Mapped[float | None] = mapped_column(Float, nullable=True)        # nautical miles
    wave_height: Mapped[float | None] = mapped_column(Float, nullable=True)       # meters
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)       # Celsius
    tide_height: Mapped[float | None] = mapped_column(Float, nullable=True)       # meters above chart datum
    current_speed: Mapped[float | None] = mapped_column(Float, nullable=True)     # knots

    # Source
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)         # e.g. "sensor", "forecast"

    # Relationships
    port: Mapped["Port"] = relationship("Port")  # noqa: F821

    def __repr__(self) -> str:
        return f"<WeatherData port_id={self.port_id} at={self.recorded_at}>"
