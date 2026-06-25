"""
Bulk import endpoints — CSV / Excel upload for vessels, visits, cargo manifests.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.dependencies import DbSession, require_roles
from app.models.iam import UserRole
from app.services.import_service import (
    ImportResult,
    import_cargo_manifest,
    import_vessels,
    import_visits,
)

router = APIRouter(tags=["Data Import"])

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
_ops_dep = Depends(require_roles(UserRole.ADMIN, UserRole.PORT_MANAGER, UserRole.OPERATIONS))


def _validate_upload(file: UploadFile) -> None:
    allowed_types = {
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/octet-stream",
    }
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type: {file.content_type}. Use CSV or XLSX.",
        )


@router.post(
    "/import/vessels",
    response_model=ImportResult,
    status_code=status.HTTP_200_OK,
    summary="Bulk import vessels from CSV/XLSX",
    description=(
        "Upload a CSV or Excel file to create/update vessels in bulk.\n\n"
        "**Required columns:** `imo_number`, `name`, `vessel_type`\n\n"
        "**Optional columns:** `flag`, `mmsi`, `length_overall`, `beam`, `max_draft`, "
        "`gross_tonnage`, `deadweight_tonnage`, `owner`, `operator`, `manager`, `year_built`\n\n"
        "Existing vessels (matched by IMO) are updated. New vessels are created."
    ),
    dependencies=[_ops_dep],
)
async def import_vessels_endpoint(
    db: DbSession,
    file: UploadFile = File(..., description="CSV or XLSX file"),
) -> ImportResult:
    _validate_upload(file)
    data = await file.read()
    if len(data) > _MAX_FILE_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 10 MB limit")
    return await import_vessels(data, file.filename or "upload.csv", db)


@router.post(
    "/import/visits",
    response_model=ImportResult,
    status_code=status.HTTP_200_OK,
    summary="Bulk import vessel visits from CSV/XLSX",
    description=(
        "Upload a CSV or Excel file to create visit records in bulk.\n\n"
        "**Required columns:** `vessel_imo`\n\n"
        "**Optional columns:** `eta`, `etb`, `etd`, `status`, `cargo_type`, `cargo_quantity`, "
        "`cargo_unit`, `voyage_number`, `agent`, `notes`\n\n"
        "Dates must be in `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DD` format (UTC)."
    ),
    dependencies=[_ops_dep],
)
async def import_visits_endpoint(
    db: DbSession,
    file: UploadFile = File(..., description="CSV or XLSX file"),
) -> ImportResult:
    _validate_upload(file)
    data = await file.read()
    if len(data) > _MAX_FILE_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 10 MB limit")
    return await import_visits(data, file.filename or "upload.csv", db)


@router.post(
    "/import/cargo/{visit_id}",
    response_model=ImportResult,
    status_code=status.HTTP_200_OK,
    summary="Import cargo manifest for a specific visit",
    description=(
        "Upload a CSV or Excel file containing cargo manifest data for a visit.\n\n"
        "**Row 1 (manifest header):** `manifest_number`, `total_weight_mt`, `total_volume_m3`, "
        "`total_teu`, `discharge_port`, `load_port`, `shipper`, `consignee`, `notes`\n\n"
        "**Rows 2+ (containers):** `container_number`, `iso_type`, `size_ft`, `weight_kg`, "
        "`is_hazmat`, `is_reefer`, `temperature_set`, `seal_number`"
    ),
    dependencies=[_ops_dep],
)
async def import_cargo_manifest_endpoint(
    visit_id: int,
    db: DbSession,
    file: UploadFile = File(..., description="CSV or XLSX file"),
) -> ImportResult:
    _validate_upload(file)
    data = await file.read()
    if len(data) > _MAX_FILE_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 10 MB limit")
    return await import_cargo_manifest(data, file.filename or "upload.csv", visit_id, db)


@router.get(
    "/import/template/{entity}",
    summary="Download a CSV template for bulk import",
    response_description="CSV template file",
)
async def download_template(entity: str) -> dict:
    """Return the column headers for each importable entity."""
    templates = {
        "vessels": {
            "columns": [
                "imo_number", "name", "vessel_type", "flag", "mmsi",
                "length_overall", "beam", "max_draft", "gross_tonnage",
                "deadweight_tonnage", "owner", "operator", "manager", "year_built",
            ],
            "example_row": [
                "IMO1234567", "MV Example", "container", "MT", "123456789",
                "200.5", "32.0", "12.5", "25000", "45000",
                "Owner Corp", "Operator Ltd", "Manager SA", "2010",
            ],
        },
        "visits": {
            "columns": [
                "vessel_imo", "eta", "etb", "etd", "status",
                "cargo_type", "cargo_quantity", "cargo_unit",
                "voyage_number", "agent", "notes",
            ],
            "example_row": [
                "IMO1234567", "2024-03-15 08:00:00", "2024-03-15 12:00:00",
                "2024-03-17 18:00:00", "scheduled", "containers", "1500",
                "TEU", "VOY-001", "Agent Co.", "First call",
            ],
        },
        "cargo": {
            "columns": [
                "manifest_number", "total_weight_mt", "total_volume_m3", "total_teu",
                "discharge_port", "load_port", "shipper", "consignee", "notes",
                "# --- containers below this row ---",
                "container_number", "iso_type", "size_ft", "weight_kg",
                "is_hazmat", "is_reefer", "temperature_set", "seal_number",
            ],
            "note": (
                "Row 1 = manifest header fields. "
                "Rows 2+ = individual container records (one per row)."
            ),
        },
    }
    return templates.get(entity, {})
