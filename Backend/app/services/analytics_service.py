"""Dashboard analytics service — all async queries + KPI time-period comparison."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Corrupt seed records can have waiting_time_hours up to 17 376 h and
# turnaround_hours derived from them is equally inflated.  Cap each metric
# at a realistic ceiling so averages are meaningful.
MAX_WAIT_HOURS = 24      # realistic max port wait before vessel is redirected
MAX_TURN_HOURS = 48      # realistic max berth turnaround (berth_time ≤ 36 h + wait ≤ 24 h)

from app.models.berth import Berth, BerthStatus
from app.models.port import Port
from app.models.prediction import Prediction
from app.models.vessel import Vessel
from app.models.visit import ACTIVE_VISIT_STATUSES, Visit, VisitStatus
from app.schemas.analytics import DashboardMetrics


async def get_dashboard_metrics(db: AsyncSession) -> DashboardMetrics:
    # --- Visit counts ---
    total_visits = (await db.execute(select(func.count()).select_from(Visit))).scalar_one()

    # Canonical definition: app.models.visit.ACTIVE_VISIT_STATUSES
    active_statuses = ACTIVE_VISIT_STATUSES
    active_visits = (
        await db.execute(
            select(func.count()).select_from(Visit).where(Visit.status.in_(active_statuses))
        )
    ).scalar_one()

    completed_visits = (
        await db.execute(
            select(func.count()).select_from(Visit).where(Visit.status == VisitStatus.COMPLETED)
        )
    ).scalar_one()

    scheduled_visits = (
        await db.execute(
            select(func.count()).select_from(Visit).where(Visit.status == VisitStatus.SCHEDULED)
        )
    ).scalar_one()

    # --- Performance averages ---
    avg_turnaround = (
        await db.execute(
            select(func.avg(Visit.turnaround_hours)).where(
                Visit.turnaround_hours > 0,
                Visit.turnaround_hours <= MAX_TURN_HOURS,
            )
        )
    ).scalar_one()

    # Cap at MAX_WAIT_HOURS — corrupt seed values (up to 17 376 h) must not
    # distort the metric displayed across Dashboard, Analytics, and Port Ops.
    avg_waiting = (
        await db.execute(
            select(func.avg(Visit.waiting_time_hours)).where(
                Visit.waiting_time_hours > 0,
                Visit.waiting_time_hours <= MAX_WAIT_HOURS,
            )
        )
    ).scalar_one()

    # --- Berths ---
    total_berths = (await db.execute(select(func.count()).select_from(Berth))).scalar_one()
    occupied_berths = (
        await db.execute(
            select(func.count()).select_from(Berth).where(Berth.status == BerthStatus.OCCUPIED)
        )
    ).scalar_one()
    berth_util = (occupied_berths / total_berths * 100) if total_berths > 0 else 0.0

    # --- Misc ---
    total_vessels = (await db.execute(select(func.count()).select_from(Vessel))).scalar_one()
    total_ports = (await db.execute(select(func.count()).select_from(Port))).scalar_one()
    total_predictions = (await db.execute(select(func.count()).select_from(Prediction))).scalar_one()

    # ── Integrity validation ─────────────────────────────────────────────────
    # These are assertions about data consistency — logged as warnings so the
    # API never crashes on bad data, but anomalies are visible in server logs.
    explicit_sum = scheduled_visits + active_visits + completed_visits
    if explicit_sum > total_visits:
        logger.warning(
            "INTEGRITY: visit counts overlap — scheduled=%d active=%d completed=%d "
            "sum=%d but total=%d",
            scheduled_visits, active_visits, completed_visits, explicit_sum, total_visits,
        )
    if active_visits > total_visits:
        logger.warning("INTEGRITY: active_visits=%d > total_visits=%d", active_visits, total_visits)
    if completed_visits > total_visits:
        logger.warning("INTEGRITY: completed_visits=%d > total_visits=%d", completed_visits, total_visits)
    if scheduled_visits > total_visits:
        logger.warning("INTEGRITY: scheduled_visits=%d > total_visits=%d", scheduled_visits, total_visits)
    if avg_waiting and avg_waiting < 0:
        logger.warning("INTEGRITY: avg_waiting_hours=%.2f is negative", avg_waiting)
    if berth_util < 0 or berth_util > 100:
        logger.warning("INTEGRITY: berth_utilization_percent=%.1f out of [0,100]", berth_util)

    return DashboardMetrics(
        total_visits=total_visits,
        active_visits=active_visits,
        completed_visits=completed_visits,
        scheduled_visits=scheduled_visits,
        avg_turnaround_minutes=round(avg_turnaround * 60, 1) if avg_turnaround else None,
        avg_waiting_minutes=round(avg_waiting * 60, 1) if avg_waiting else None,
        berth_utilization_percent=round(berth_util, 1),
        total_berths=total_berths,
        occupied_berths=occupied_berths,
        total_vessels=total_vessels,
        total_ports=total_ports,
        total_predictions=total_predictions,
    )


# ── KPI time-period comparison ────────────────────────────────────────────────

async def _period_metrics(year: int, month: int, db: AsyncSession) -> dict[str, Any]:
    """Compute KPI metrics for a specific calendar month."""

    def _month_filter(col):
        return (extract("year", col) == year) & (extract("month", col) == month)

    # Visit counts
    total = (
        await db.execute(
            select(func.count()).select_from(Visit).where(_month_filter(Visit.created_at))
        )
    ).scalar_one()

    completed = (
        await db.execute(
            select(func.count()).select_from(Visit).where(
                _month_filter(Visit.created_at),
                Visit.status == VisitStatus.COMPLETED,
            )
        )
    ).scalar_one()

    # Averages
    avg_turn = (
        await db.execute(
            select(func.avg(Visit.turnaround_hours)).where(
                _month_filter(Visit.created_at),
                Visit.turnaround_hours > 0,
                Visit.turnaround_hours <= MAX_TURN_HOURS,
            )
        )
    ).scalar_one()

    avg_wait = (
        await db.execute(
            select(func.avg(Visit.waiting_time_hours)).where(
                _month_filter(Visit.created_at),
                Visit.waiting_time_hours > 0,
                Visit.waiting_time_hours <= MAX_WAIT_HOURS,
            )
        )
    ).scalar_one()

    avg_eff = (
        await db.execute(
            select(func.avg(Visit.efficiency_rating)).where(
                _month_filter(Visit.created_at),
                Visit.efficiency_rating.isnot(None),
            )
        )
    ).scalar_one()

    # Predictions made this month
    predictions = (
        await db.execute(
            select(func.count()).select_from(Prediction).where(
                _month_filter(Prediction.created_at)
            )
        )
    ).scalar_one()

    return {
        "period": f"{year}-{month:02d}",
        "total_visits": total,
        "completed_visits": completed,
        "completion_rate_pct": round(completed / total * 100, 1) if total > 0 else 0.0,
        "avg_turnaround_hours": round(float(avg_turn), 2) if avg_turn else None,
        "avg_waiting_hours": round(float(avg_wait), 2) if avg_wait else None,
        "avg_efficiency_rating": round(float(avg_eff), 2) if avg_eff else None,
        "total_predictions": predictions,
    }


def _delta(current: float | None, previous: float | None) -> float | None:
    """Return % change from previous to current, or None if unavailable."""
    if current is None or previous is None or previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


async def compare_kpi_periods(
    year: int,
    month: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Compare KPIs for the given month against the previous month.
    Returns both periods' metrics plus delta % for each KPI.
    """
    # Compute previous month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    current = await _period_metrics(year, month, db)
    previous = await _period_metrics(prev_year, prev_month, db)

    return {
        "current_period": current,
        "previous_period": previous,
        "deltas": {
            "total_visits_delta_pct": _delta(current["total_visits"], previous["total_visits"]),
            "completed_visits_delta_pct": _delta(current["completed_visits"], previous["completed_visits"]),
            "completion_rate_delta_pct": _delta(current["completion_rate_pct"], previous["completion_rate_pct"]),
            "avg_turnaround_delta_pct": _delta(current["avg_turnaround_hours"], previous["avg_turnaround_hours"]),
            "avg_waiting_delta_pct": _delta(current["avg_waiting_hours"], previous["avg_waiting_hours"]),
            "avg_efficiency_delta_pct": _delta(current["avg_efficiency_rating"], previous["avg_efficiency_rating"]),
            "predictions_delta_pct": _delta(current["total_predictions"], previous["total_predictions"]),
        },
        "insights": _generate_insights(current, previous),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _generate_insights(current: dict, previous: dict) -> list[str]:
    """Generate plain-English insights from KPI deltas."""
    insights: list[str] = []

    c_turn = current.get("avg_turnaround_hours")
    p_turn = previous.get("avg_turnaround_hours")
    if c_turn and p_turn:
        if c_turn < p_turn:
            pct = round((p_turn - c_turn) / p_turn * 100, 1)
            insights.append(f"Turnaround improved by {pct}% compared to last month.")
        elif c_turn > p_turn:
            pct = round((c_turn - p_turn) / p_turn * 100, 1)
            insights.append(f"⚠️ Turnaround increased by {pct}% — investigate bottlenecks.")

    c_visits = current.get("total_visits", 0)
    p_visits = previous.get("total_visits", 0)
    if c_visits > p_visits and p_visits > 0:
        pct = round((c_visits - p_visits) / p_visits * 100, 1)
        insights.append(f"Port traffic grew by {pct}% ({c_visits} vs {p_visits} visits).")
    elif c_visits < p_visits and p_visits > 0:
        pct = round((p_visits - c_visits) / p_visits * 100, 1)
        insights.append(f"Port traffic declined by {pct}% ({c_visits} vs {p_visits} visits).")

    c_eff = current.get("avg_efficiency_rating")
    p_eff = previous.get("avg_efficiency_rating")
    if c_eff and p_eff:
        if c_eff >= p_eff:
            insights.append(f"Efficiency rating maintained/improved: {c_eff:.2f} (prev: {p_eff:.2f}).")
        else:
            insights.append(f"⚠️ Efficiency rating dropped: {c_eff:.2f} vs {p_eff:.2f} last month.")

    if not insights:
        insights.append("Insufficient data for meaningful comparison.")

    return insights
