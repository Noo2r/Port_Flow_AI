"""
Bulk import service — parse CSV/Excel files and upsert records into the DB.
Supports:  vessels, vessel_visits, cargo_manifests, containers
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return ((self.created + self.updated) / self.total * 100) if self.total else 0.0


def _parse_csv_bytes(data: bytes) -> list[dict[str, str]]:
    text = data.decode("utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def _parse_excel_bytes(data: bytes) -> list[dict[str, str]]:
    """Parse .xlsx bytes into a list of row dicts."""
    try:
        import openpyxl  # type: ignore[import]
    except ImportError:
        raise RuntimeError("openpyxl is required for Excel import. Add it to requirements.txt.")
    wb = openpyxl.load_workbook(filename=io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
    return [
        {headers[i]: (str(cell).strip() if cell is not None else "") for i, cell in enumerate(row)}
        for row in rows[1:]
    ]


def _rows_from_bytes(data: bytes, filename: str) -> list[dict[str, str]]:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext in ("xls", "xlsx"):
        return _parse_excel_bytes(data)
    return _parse_csv_bytes(data)


def _parse_dt(value: str | None) -> datetime | None:
    if not value or value.strip() in ("", "None", "null"):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_float(value: str | None) -> float | None:
    try:
        return float(value) if value and value.strip() else None
    except (ValueError, TypeError):
        return None


def _parse_int(value: str | None) -> int | None:
    try:
        return int(value) if value and value.strip() else None
    except (ValueError, TypeError):
        return None


# ── Vessel import ─────────────────────────────────────────────────────────────
"""
Expected CSV columns (case-insensitive):
  imo_number, name, vessel_type, flag, mmsi,
  length_overall, beam, max_draft, gross_tonnage, deadweight_tonnage,
  owner, operator, manager, year_built
"""

async def import_vessels(
    data: bytes,
    filename: str,
    db: AsyncSession,
) -> ImportResult:
    from app.models.vessel import Vessel, VesselType

    result = ImportResult()
    rows = _rows_from_bytes(data, filename)
    result.total = len(rows)

    valid_types = {t.value for t in VesselType}

    for i, row in enumerate(rows, start=2):
        imo = row.get("imo_number", "").strip()
        if not imo:
            result.errors.append({"row": i, "error": "Missing imo_number"})
            result.skipped += 1
            continue

        vtype_raw = row.get("vessel_type", "other").strip().lower()
        vtype = vtype_raw if vtype_raw in valid_types else "other"

        existing = (
            await db.execute(select(Vessel).where(Vessel.imo_number == imo))
        ).scalar_one_or_none()

        try:
            if existing:
                existing.name = row.get("name", existing.name).strip() or existing.name
                existing.flag = row.get("flag", "").strip() or existing.flag
                existing.mmsi = row.get("mmsi", "").strip() or existing.mmsi
                existing.length_overall = _parse_float(row.get("length_overall")) or existing.length_overall
                existing.beam = _parse_float(row.get("beam")) or existing.beam
                existing.max_draft = _parse_float(row.get("max_draft")) or existing.max_draft
                existing.gross_tonnage = _parse_float(row.get("gross_tonnage")) or existing.gross_tonnage
                existing.deadweight_tonnage = _parse_float(row.get("deadweight_tonnage")) or existing.deadweight_tonnage
                existing.owner = row.get("owner", "").strip() or existing.owner
                existing.operator = row.get("operator", "").strip() or existing.operator
                existing.manager = row.get("manager", "").strip() or existing.manager
                existing.year_built = _parse_int(row.get("year_built")) or existing.year_built
                result.updated += 1
            else:
                name = row.get("name", "").strip()
                if not name:
                    result.errors.append({"row": i, "error": "Missing name"})
                    result.skipped += 1
                    continue
                vessel = Vessel(
                    imo_number=imo,
                    name=name,
                    vessel_type=vtype,
                    flag=row.get("flag", "").strip() or None,
                    mmsi=row.get("mmsi", "").strip() or None,
                    length_overall=_parse_float(row.get("length_overall")),
                    beam=_parse_float(row.get("beam")),
                    max_draft=_parse_float(row.get("max_draft")),
                    gross_tonnage=_parse_float(row.get("gross_tonnage")),
                    deadweight_tonnage=_parse_float(row.get("deadweight_tonnage")),
                    owner=row.get("owner", "").strip() or None,
                    operator=row.get("operator", "").strip() or None,
                    manager=row.get("manager", "").strip() or None,
                    year_built=_parse_int(row.get("year_built")),
                )
                db.add(vessel)
                result.created += 1
        except Exception as exc:
            result.errors.append({"row": i, "error": str(exc)})
            result.skipped += 1

    await db.commit()
    logger.info("Vessel import complete: %s", result)
    return result


# ── Visit import ──────────────────────────────────────────────────────────────
"""
Expected CSV columns:
  vessel_imo, eta, etb, etd, status, cargo_type, cargo_quantity,
  cargo_unit, voyage_number, agent, notes
"""

async def import_visits(
    data: bytes,
    filename: str,
    db: AsyncSession,
) -> ImportResult:
    from app.models.vessel import Vessel
    from app.models.visit import CargoType, Visit, VisitStatus

    result = ImportResult()
    rows = _rows_from_bytes(data, filename)
    result.total = len(rows)

    valid_statuses = {s.value for s in VisitStatus}
    valid_cargo = {c.value for c in CargoType}

    for i, row in enumerate(rows, start=2):
        imo = row.get("vessel_imo", "").strip()
        if not imo:
            result.errors.append({"row": i, "error": "Missing vessel_imo"})
            result.skipped += 1
            continue

        vessel = (
            await db.execute(select(Vessel).where(Vessel.imo_number == imo))
        ).scalar_one_or_none()
        if not vessel:
            result.errors.append({"row": i, "error": f"Vessel IMO {imo} not found"})
            result.skipped += 1
            continue

        status_raw = row.get("status", "scheduled").strip().lower()
        status = status_raw if status_raw in valid_statuses else "scheduled"
        cargo_raw = row.get("cargo_type", "").strip().lower()
        cargo_type = cargo_raw if cargo_raw in valid_cargo else None

        try:
            visit = Visit(
                vessel_id=vessel.id,
                eta=_parse_dt(row.get("eta")),
                etb=_parse_dt(row.get("etb")),
                etd=_parse_dt(row.get("etd")),
                status=status,
                cargo_type=cargo_type,
                cargo_quantity=_parse_float(row.get("cargo_quantity")),
                cargo_unit=row.get("cargo_unit", "").strip() or None,
                voyage_number=row.get("voyage_number", "").strip() or None,
                agent=row.get("agent", "").strip() or None,
                notes=row.get("notes", "").strip() or None,
            )
            db.add(visit)
            result.created += 1
        except Exception as exc:
            result.errors.append({"row": i, "error": str(exc)})
            result.skipped += 1

    await db.commit()
    logger.info("Visit import complete: %s", result)
    return result


# ── Cargo manifest import ─────────────────────────────────────────────────────
"""
Expected CSV columns:
  visit_id, manifest_number, total_weight_mt, total_volume_m3, total_teu,
  discharge_port, load_port, shipper, consignee, notes,
  [container rows]: container_number, iso_type, size_ft, weight_kg, is_hazmat
"""

async def import_cargo_manifest(
    data: bytes,
    filename: str,
    visit_id: int,
    db: AsyncSession,
) -> ImportResult:
    from app.models.operations import CargoManifest, Container, ContainerStatus

    result = ImportResult()
    rows = _rows_from_bytes(data, filename)
    result.total = len(rows)

    if not rows:
        return result

    # First row = manifest header
    header = rows[0]
    manifest_number = header.get("manifest_number", f"MAN-{visit_id}-AUTO").strip()

    existing = (
        await db.execute(
            select(CargoManifest).where(CargoManifest.manifest_number == manifest_number)
        )
    ).scalar_one_or_none()

    if existing:
        manifest = existing
        result.updated += 1
    else:
        manifest = CargoManifest(
            visit_id=visit_id,
            manifest_number=manifest_number,
            total_weight_mt=_parse_float(header.get("total_weight_mt")),
            total_volume_m3=_parse_float(header.get("total_volume_m3")),
            total_teu=_parse_int(header.get("total_teu")),
            discharge_port=header.get("discharge_port", "").strip() or None,
            load_port=header.get("load_port", "").strip() or None,
            shipper=header.get("shipper", "").strip() or None,
            consignee=header.get("consignee", "").strip() or None,
            notes=header.get("notes", "").strip() or None,
        )
        db.add(manifest)
        await db.flush()
        result.created += 1

    # Remaining rows = containers
    for i, row in enumerate(rows[1:], start=3):
        cn = row.get("container_number", "").strip()
        if not cn:
            continue
        try:
            container = Container(
                manifest_id=manifest.id,
                container_number=cn,
                iso_type=row.get("iso_type", "").strip() or None,
                size_ft=_parse_int(row.get("size_ft")),
                weight_kg=_parse_float(row.get("weight_kg")),
                is_hazmat=row.get("is_hazmat", "false").strip().lower() in ("true", "1", "yes"),
                is_reefer=row.get("is_reefer", "false").strip().lower() in ("true", "1", "yes"),
                temperature_set=_parse_float(row.get("temperature_set")),
                seal_number=row.get("seal_number", "").strip() or None,
                status=ContainerStatus.EXPECTED,
            )
            db.add(container)
            result.created += 1
        except Exception as exc:
            result.errors.append({"row": i, "error": str(exc)})
            result.skipped += 1

    await db.commit()
    return result
