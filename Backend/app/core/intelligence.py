"""
Async intelligence layer:
  - AISService: update vessel position from AIS data
  - WeatherCorrelationEngine: adjust ETA based on latest weather
  - ConflictDetector: find overlapping berth bookings
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import logger
from app.models.berth import Berth
from app.models.vessel import Vessel
from app.models.visit import Visit, VisitStatus
from app.models.weather import WeatherData
from app.schemas.operations import (
    AISUpdateResponse,
    ConflictItem,
    ConflictResponse,
    WeatherImpactResponse,
)


class AISService:
    @staticmethod
    async def update_position(
        visit_id: int,
        latitude: float,
        longitude: float,
        speed_knots: float | None,
        heading_degrees: float | None,
        db: AsyncSession,
    ) -> AISUpdateResponse:
        visit = await db.get(Visit, visit_id)
        if visit is None:
            raise ValueError(f"Visit {visit_id} not found")

        vessel = await db.get(Vessel, visit.vessel_id)
        if vessel is None:
            raise ValueError(f"Vessel {visit.vessel_id} not found")

        vessel.current_lat = latitude
        vessel.current_lon = longitude
        if speed_knots is not None:
            vessel.current_speed = speed_knots
        if heading_degrees is not None:
            vessel.current_heading = heading_degrees

        await db.flush()
        logger.info(
            "AIS update | vessel=%s | lat=%.4f lon=%.4f speed=%s",
            vessel.imo_number, latitude, longitude, speed_knots,
        )

        return AISUpdateResponse(
            visit_id=visit_id,
            vessel_id=vessel.id,
            vessel_name=vessel.name,
            latitude=latitude,
            longitude=longitude,
            speed_knots=speed_knots,
            heading_degrees=heading_degrees,
            updated_at=datetime.now(timezone.utc),
        )


class WeatherCorrelationEngine:
    # Heuristic thresholds
    HIGH_WIND_KNOTS = 25.0
    LOW_VISIBILITY_NM = 1.0
    HIGH_WAVE_M = 3.0

    @staticmethod
    async def calculate_delay(
        visit_id: int,
        db: AsyncSession,
    ) -> WeatherImpactResponse:
        visit = await db.get(Visit, visit_id)
        if visit is None:
            raise ValueError(f"Visit {visit_id} not found")

        # Fetch latest weather for the port
        weather: WeatherData | None = None
        if visit.port_id is not None:
            result = await db.execute(
                select(WeatherData)
                .where(WeatherData.port_id == visit.port_id)
                .order_by(WeatherData.recorded_at.desc())
                .limit(1)
            )
            weather = result.scalar_one_or_none()

        delay_hours = 0.0
        weather_factor = 1.0

        if weather:
            if weather.wind_speed and weather.wind_speed > WeatherCorrelationEngine.HIGH_WIND_KNOTS:
                extra = (weather.wind_speed - WeatherCorrelationEngine.HIGH_WIND_KNOTS) * 0.1
                delay_hours += extra
                weather_factor += 0.05

            if weather.visibility and weather.visibility < WeatherCorrelationEngine.LOW_VISIBILITY_NM:
                delay_hours += 2.0
                weather_factor += 0.1

            if weather.wave_height and weather.wave_height > WeatherCorrelationEngine.HIGH_WAVE_M:
                extra = (weather.wave_height - WeatherCorrelationEngine.HIGH_WAVE_M) * 0.5
                delay_hours += extra
                weather_factor += 0.05

        original_eta = visit.eta
        adjusted_eta = None
        if original_eta and delay_hours > 0:
            adjusted_eta = original_eta + timedelta(hours=delay_hours)
            # Persist updated ETA
            visit.eta = adjusted_eta
            await db.flush()

        return WeatherImpactResponse(
            visit_id=visit_id,
            vessel_id=visit.vessel_id,
            original_eta=original_eta,
            adjusted_eta=adjusted_eta or original_eta,
            delay_hours=round(delay_hours, 2),
            weather_factor=round(weather_factor, 3),
            wind_speed=weather.wind_speed if weather else None,
            visibility=weather.visibility if weather else None,
            wave_height=weather.wave_height if weather else None,
        )


class ConflictDetector:
    @staticmethod
    async def detect_conflicts(
        berth_id: int,
        db: AsyncSession,
    ) -> ConflictResponse:
        berth = await db.get(Berth, berth_id)
        if berth is None:
            raise ValueError(f"Berth {berth_id} not found")

        active_statuses = [
            VisitStatus.SCHEDULED,
            VisitStatus.APPROACHING,
            VisitStatus.ANCHORED,
            VisitStatus.BERTHING,
            VisitStatus.IN_PORT,
        ]
        result = await db.execute(
            select(Visit)
            .where(Visit.berth_id == berth_id)
            .where(Visit.status.in_(active_statuses))
            .order_by(Visit.etb.asc().nulls_last())
        )
        visits = result.scalars().all()

        conflicts: list[ConflictItem] = []
        for i, v1 in enumerate(visits):
            for v2 in visits[i + 1:]:
                if _overlaps(v1, v2):
                    vessel = await db.get(Vessel, v1.vessel_id)
                    if not any(c.visit_id == v1.id for c in conflicts):
                        conflicts.append(ConflictItem(
                            visit_id=v1.id,
                            vessel_name=vessel.name if vessel else "Unknown",
                            vessel_imo=vessel.imo_number if vessel else "Unknown",
                            etb=v1.etb,
                            etd=v1.etd,
                            status=v1.status.value,
                        ))

        resolution = None
        if conflicts:
            resolution = (
                f"{len(conflicts)} scheduling overlap(s) detected on berth {berth.code}. "
                "Consider delaying lowest-priority visits or reassigning to alternative berths."
            )

        return ConflictResponse(
            berth_id=berth_id,
            berth_code=berth.code,
            conflicts_found=len(conflicts),
            conflicts=conflicts,
            resolution_suggestion=resolution,
        )


def _overlaps(v1: Visit, v2: Visit) -> bool:
    """Return True if two visits have overlapping berth windows."""
    if not (v1.etb and v1.etd and v2.etb and v2.etd):
        return False
    return v1.etb < v2.etd and v2.etb < v1.etd
