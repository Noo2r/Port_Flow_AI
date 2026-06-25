"""
Export endpoints — download vessel, visit, analytics, and monthly reports
as CSV or PDF files.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response

from app.core.dependencies import CurrentUser, DbSession

router = APIRouter(tags=["Data Export"])


@router.get(
    "/export/vessels.csv",
    summary="Export full vessel registry as CSV",
    response_class=Response,
)
async def export_vessels_csv(
    _user: CurrentUser,
    db: DbSession,
) -> Response:
    from app.services.export_service import export_vessels_csv as _export
    data = await _export(db)
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=vessels.csv"},
    )


@router.get(
    "/export/vessels.pdf",
    summary="Export vessel registry as a formatted PDF",
    response_class=Response,
)
async def export_vessels_pdf(
    _user: CurrentUser,
    db: DbSession,
) -> Response:
    try:
        from app.services.export_service import export_vessels_pdf as _export
        data = await _export(db)
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(exc))
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=vessel_registry.pdf"},
    )


@router.get(
    "/export/visits.csv",
    summary="Export vessel visits as CSV",
    response_class=Response,
)
async def export_visits_csv(
    _user: CurrentUser,
    db: DbSession,
    visit_status: str | None = Query(default=None, description="Filter by status (e.g. completed)"),
) -> Response:
    from app.services.export_service import export_visits_csv as _export
    data = await _export(db, status_filter=visit_status)
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=visits.csv"},
    )


@router.get(
    "/export/analytics.csv",
    summary="Export current KPI metrics snapshot as CSV",
    response_class=Response,
)
async def export_analytics_csv(
    _user: CurrentUser,
    db: DbSession,
) -> Response:
    from app.services.export_service import export_analytics_csv as _export
    data = await _export(db)
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics_kpis.csv"},
    )


@router.get(
    "/export/report/{year}/{month}.pdf",
    summary="Export a monthly operations report as PDF",
    response_class=Response,
)
async def export_monthly_report(
    year: int,
    month: int,
    _user: CurrentUser,
    db: DbSession,
) -> Response:
    if not (1 <= month <= 12):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Month must be 1–12")
    if year < 2000 or year > 2100:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid year")

    try:
        from app.services.export_service import export_monthly_report_pdf as _export
        data = await _export(db, year=year, month=month)
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(exc))

    filename = f"portflow_report_{year}_{month:02d}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
