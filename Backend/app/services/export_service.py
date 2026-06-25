"""
Export service — generate CSV and PDF reports from DB query results.
All functions are async and return bytes ready to stream as HTTP responses.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── CSV helpers ───────────────────────────────────────────────────────────────

def _to_csv_bytes(headers: list[str], rows: list[list[Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")  # BOM for Excel compat


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


# ── Vessel CSV export ─────────────────────────────────────────────────────────

async def export_vessels_csv(db: AsyncSession) -> bytes:
    from app.models.vessel import Vessel

    result = await db.execute(select(Vessel).order_by(Vessel.id))
    vessels = result.scalars().all()

    headers = [
        "id", "imo_number", "mmsi", "name", "vessel_type", "flag",
        "length_overall", "beam", "max_draft", "gross_tonnage", "deadweight_tonnage",
        "status", "owner", "operator", "manager", "year_built", "is_active",
        "created_at", "updated_at",
    ]
    rows = [
        [
            _fmt(v.id), _fmt(v.imo_number), _fmt(v.mmsi), _fmt(v.name),
            _fmt(v.vessel_type), _fmt(v.flag),
            _fmt(v.length_overall), _fmt(v.beam), _fmt(v.max_draft),
            _fmt(v.gross_tonnage), _fmt(v.deadweight_tonnage),
            _fmt(v.status), _fmt(v.owner), _fmt(v.operator),
            _fmt(v.manager), _fmt(v.year_built), _fmt(v.is_active),
            _fmt(v.created_at), _fmt(v.updated_at),
        ]
        for v in vessels
    ]
    return _to_csv_bytes(headers, rows)


# ── Visit CSV export ──────────────────────────────────────────────────────────

async def export_visits_csv(db: AsyncSession, status_filter: str | None = None) -> bytes:
    from app.models.vessel import Vessel
    from app.models.visit import Visit

    stmt = (
        select(Visit, Vessel.name.label("vessel_name"), Vessel.imo_number)
        .join(Vessel, Visit.vessel_id == Vessel.id)
        .order_by(Visit.id)
    )
    if status_filter:
        stmt = stmt.where(Visit.status == status_filter)

    result = await db.execute(stmt)
    rows_raw = result.all()

    headers = [
        "visit_id", "vessel_name", "imo_number", "berth_id", "port_id",
        "status", "clearance_status",
        "eta", "etb", "etd", "ata", "atb", "atd",
        "cargo_type", "cargo_quantity", "cargo_unit",
        "waiting_time_hours", "berth_time_hours", "turnaround_hours",
        "efficiency_rating", "voyage_number", "agent", "notes",
    ]
    rows = [
        [
            _fmt(v.id), vessel_name, imo,
            _fmt(v.berth_id), _fmt(v.port_id),
            _fmt(v.status), _fmt(v.clearance_status),
            _fmt(v.eta), _fmt(v.etb), _fmt(v.etd),
            _fmt(v.ata), _fmt(v.atb), _fmt(v.atd),
            _fmt(v.cargo_type), _fmt(v.cargo_quantity), _fmt(v.cargo_unit),
            _fmt(v.waiting_time_hours), _fmt(v.berth_time_hours), _fmt(v.turnaround_hours),
            _fmt(v.efficiency_rating), _fmt(v.voyage_number), _fmt(v.agent), _fmt(v.notes),
        ]
        for v, vessel_name, imo in rows_raw
    ]
    return _to_csv_bytes(headers, rows)


# ── Analytics / KPI CSV export ────────────────────────────────────────────────

async def export_analytics_csv(db: AsyncSession) -> bytes:
    from app.services.analytics_service import get_dashboard_metrics

    metrics = await get_dashboard_metrics(db)
    headers = ["metric", "value"]
    rows = [
        ["total_visits", metrics.total_visits],
        ["active_visits", metrics.active_visits],
        ["completed_visits", metrics.completed_visits],
        ["scheduled_visits", metrics.scheduled_visits],
        ["avg_turnaround_minutes", metrics.avg_turnaround_minutes or "N/A"],
        ["avg_waiting_minutes", metrics.avg_waiting_minutes or "N/A"],
        ["berth_utilization_percent", metrics.berth_utilization_percent],
        ["total_berths", metrics.total_berths],
        ["occupied_berths", metrics.occupied_berths],
        ["total_vessels", metrics.total_vessels],
        ["total_ports", metrics.total_ports],
        ["total_predictions", metrics.total_predictions],
    ]
    return _to_csv_bytes(headers, rows)


# ── PDF report ────────────────────────────────────────────────────────────────

async def export_monthly_report_pdf(db: AsyncSession, year: int, month: int) -> bytes:
    """
    Generate a PDF monthly port operations report using ReportLab.
    Returns raw PDF bytes.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        raise RuntimeError("reportlab is required for PDF export. Add it to requirements.txt.")

    from app.models.berth import Berth
    from app.models.vessel import Vessel
    from app.models.visit import Visit, VisitStatus
    from sqlalchemy import extract, func

    # ── Query data ──────────────────────────────────────────────────────────
    visit_stmt = (
        select(Visit)
        .where(
            extract("year", Visit.created_at) == year,
            extract("month", Visit.created_at) == month,
        )
        .order_by(Visit.created_at)
    )
    visits = (await db.execute(visit_stmt)).scalars().all()

    total_visits = len(visits)
    completed = sum(1 for v in visits if v.status == VisitStatus.COMPLETED)
    avg_turnaround = (
        sum(v.turnaround_hours for v in visits if v.turnaround_hours) / completed
        if completed > 0 else 0
    )

    total_vessels = (await db.execute(select(func.count()).select_from(Vessel))).scalar_one()
    total_berths = (await db.execute(select(func.count()).select_from(Berth))).scalar_one()

    # ── Build PDF ───────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = styles["Title"]
    story.append(Paragraph("PortFlow AI — Monthly Operations Report", title_style))
    story.append(Paragraph(
        f"Period: {datetime(year, month, 1).strftime('%B %Y')} | "
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.5*cm))

    # KPI summary table
    story.append(Paragraph("Key Performance Indicators", styles["Heading2"]))
    kpi_data = [
        ["Metric", "Value"],
        ["Total Vessel Visits", str(total_visits)],
        ["Completed Visits", str(completed)],
        ["Avg Turnaround Time", f"{avg_turnaround:.1f} hours" if avg_turnaround else "N/A"],
        ["Total Vessels in Registry", str(total_vessels)],
        ["Total Berths", str(total_berths)],
    ]
    kpi_table = Table(kpi_data, colWidths=[8*cm, 6*cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a56db")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.5*cm))

    # Visit detail table
    if visits:
        story.append(Paragraph("Visit Summary", styles["Heading2"]))
        visit_data = [["Visit ID", "Vessel ID", "Status", "ETA", "Turnaround (h)"]]
        for v in visits[:50]:  # Cap at 50 for PDF readability
            visit_data.append([
                str(v.id),
                str(v.vessel_id),
                str(v.status.value if hasattr(v.status, "value") else v.status),
                v.eta.strftime("%Y-%m-%d %H:%M") if v.eta else "N/A",
                f"{v.turnaround_hours:.1f}" if v.turnaround_hours else "N/A",
            ])
        visit_table = Table(visit_data, colWidths=[2*cm, 2.5*cm, 4*cm, 5*cm, 3.5*cm])
        visit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a56db")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(visit_table)

    # Footer
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        "This report was auto-generated by PortFlow AI. All times are UTC.",
        styles["Italic"],
    ))

    doc.build(story)
    return buf.getvalue()


async def export_vessels_pdf(db: AsyncSession) -> bytes:
    """Export vessel registry as a formatted PDF."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        raise RuntimeError("reportlab is required for PDF export.")

    from app.models.vessel import Vessel

    vessels = (await db.execute(select(Vessel).order_by(Vessel.name))).scalars().all()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("PortFlow AI — Vessel Registry", styles["Title"]))
    story.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Total: {len(vessels)} vessels",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.5*cm))

    data = [["IMO", "Name", "Type", "Flag", "LOA (m)", "Draft (m)", "GRT", "DWT", "Owner", "Status"]]
    for v in vessels:
        data.append([
            v.imo_number, v.name,
            v.vessel_type.value if hasattr(v.vessel_type, "value") else str(v.vessel_type),
            v.flag or "", _fmt(v.length_overall), _fmt(v.max_draft),
            _fmt(v.gross_tonnage), _fmt(v.deadweight_tonnage),
            v.owner or "", v.status.value if hasattr(v.status, "value") else str(v.status),
        ])

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a56db")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    doc.build(story)
    return buf.getvalue()
