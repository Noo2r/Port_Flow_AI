"""
Automation Script 3: Bulk Data Seeder
Generates realistic port, vessel, berth, and visit records in the database.
Useful for load testing, demos, and staging environment setup.

Usage:
    python scripts/data_seeder.py                         # seed defaults
    python scripts/data_seeder.py --vessels 50 --visits 100
    python scripts/data_seeder.py --mode reset            # wipe demo data then re-seed
    python scripts/data_seeder.py --mode visits-only      # only add visits to existing vessels
    python scripts/data_seeder.py --dry-run               # preview without writing
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.berth import Berth, BerthStatus, BerthType
from app.models.port import Port
from app.models.vessel import Vessel, VesselStatus, VesselType
from app.models.visit import Visit, VisitStatus, CargoType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("data_seeder")

# ── Sample data pools ──────────────────────────────────────────────────────────

VESSEL_NAMES = [
    "MV Atlantic Star", "MV Pacific Horizon", "MV Mediterranean Sun",
    "MV Arabian Gulf", "MV Red Sea Express", "MV Blue Nile", "MV Delta Queen",
    "MV Suez Pioneer", "MV Alexandria Bridge", "MV Port Said Trader",
    "MV Nile Gateway", "MV Desert Wind", "MV Oasis Carrier", "MV Sahara Clipper",
    "MV Sinai Voyager", "MV Pharaoh Star", "MV Lotus Express", "MV Sphinx Carrier",
    "MV Pyramid Trader", "MV Cairo Bridge",
]

FLAGS = ["EG", "GR", "PA", "LR", "MH", "BS", "CY", "MT", "SG", "HK"]

VESSEL_TYPES = [
    VesselType.CONTAINER, VesselType.BULK_CARRIER, VesselType.TANKER,
    VesselType.GENERAL_CARGO, VesselType.RO_RO,
]

PORTS_DATA = [
    dict(code="EGALX", name="Port of Alexandria", country="EG", city="Alexandria",
         timezone="Africa/Cairo", latitude=31.2001, longitude=29.9187,
         un_locode="EGALX", max_vessel_loa=380.0, max_vessel_draft=16.5),
    dict(code="EGPSD", name="Port Said Port", country="EG", city="Port Said",
         timezone="Africa/Cairo", latitude=31.2653, longitude=32.3019,
         un_locode="EGPSD", max_vessel_loa=400.0, max_vessel_draft=17.0),
    dict(code="ADSUH", name="Port of Sokhna", country="EG", city="Ain Sokhna",
         timezone="Africa/Cairo", latitude=29.9519, longitude=32.3480,
         un_locode="EGSKH", max_vessel_loa=300.0, max_vessel_draft=14.0),
]

BERTH_TEMPLATES = [
    dict(suffix="A1", berth_type=BerthType.CONTAINER, max_length=320.0, max_draft=14.5, has_crane=True, crane_capacity_tons=100.0, priority_level=1),
    dict(suffix="A2", berth_type=BerthType.CONTAINER, max_length=300.0, max_draft=13.5, has_crane=True, crane_capacity_tons=80.0, priority_level=2),
    dict(suffix="B1", berth_type=BerthType.BULK, max_length=260.0, max_draft=12.0, has_crane=True, crane_capacity_tons=60.0, priority_level=3),
    dict(suffix="B2", berth_type=BerthType.BULK, max_length=240.0, max_draft=11.0, has_crane=False, priority_level=4),
    dict(suffix="C1", berth_type=BerthType.TANKER, max_length=280.0, max_draft=15.0, has_crane=False, priority_level=2),
    dict(suffix="D1", berth_type=BerthType.GENERAL, max_length=200.0, max_draft=10.0, has_crane=False, priority_level=5),
]


# ── Generators ─────────────────────────────────────────────────────────────────

def _make_imo() -> str:
    return f"IMO{random.randint(1000000, 9999998):07d}"


def _make_mmsi() -> str:
    return f"{random.randint(100000000, 999999999)}"


def _make_vessel(index: int) -> dict:
    vtype = random.choice(VESSEL_TYPES)
    loa = round(random.uniform(100.0, 350.0), 1)
    return dict(
        imo_number=_make_imo(),
        mmsi=_make_mmsi(),
        name=f"{random.choice(VESSEL_NAMES)} {index}",
        vessel_type=vtype,
        flag=random.choice(FLAGS),
        length_overall=loa,
        beam=round(loa * 0.13, 1),
        max_draft=round(random.uniform(6.0, 16.0), 1),
        gross_tonnage=round(random.uniform(5000.0, 120000.0), 0),
        deadweight_tonnage=round(random.uniform(8000.0, 200000.0), 0),
        status=random.choice([VesselStatus.AT_SEA, VesselStatus.ANCHORED]),
        current_speed=round(random.uniform(0.0, 18.0), 1),
        current_heading=round(random.uniform(0.0, 359.9), 1),
        owner=f"Shipping Co. {random.randint(1, 50)}",
        operator=f"Port Ops Ltd {random.randint(1, 20)}",
        year_built=random.randint(2000, 2024),
    )


_ACTIVE_STATUSES = (VisitStatus.ANCHORED, VisitStatus.BERTHING, VisitStatus.IN_PORT)

def _make_visit(vessel: Vessel, berth: Berth, port: Port, offset_days: int) -> dict:
    eta = datetime.now(timezone.utc) + timedelta(days=offset_days, hours=random.randint(-12, 12))
    etd = eta + timedelta(hours=random.randint(6, 72))
    status = random.choice([VisitStatus.SCHEDULED, VisitStatus.ANCHORED, VisitStatus.IN_PORT])
    ata = eta + timedelta(hours=random.randint(0, 3)) if status in _ACTIVE_STATUSES else None
    return dict(
        vessel_id=vessel.id,
        port_id=port.id,
        berth_id=berth.id if status == VisitStatus.IN_PORT else None,
        status=status,
        eta=eta,
        etd=etd,
        ata=ata,
        cargo_type=random.choice(list(CargoType)),
        cargo_quantity=round(random.uniform(500.0, 50000.0), 0),
        cargo_unit=random.choice(["TEU", "tons", "m³", "units"]),
    )


# ── Core seeder ────────────────────────────────────────────────────────────────

async def seed(db: AsyncSession, n_vessels: int, n_visits: int, mode: str, dry_run: bool) -> None:
    if mode == "reset":
        logger.info("Reset mode: removing existing demo data...")
        if not dry_run:
            await db.execute(delete(Visit).where(Visit.cargo_type.isnot(None)))
            await db.execute(delete(Vessel).where(Vessel.owner.like("Shipping Co.%")))
            await db.commit()
        logger.info("Demo data cleared.")

    # Ensure ports exist
    ports: list[Port] = []
    for pdata in PORTS_DATA:
        result = await db.execute(select(Port).where(Port.code == pdata["code"]).limit(1))
        port = result.scalar_one_or_none()
        if port is None:
            port = Port(**pdata, is_active=True)
            if not dry_run:
                db.add(port)
                await db.flush()
            logger.info("  + Port: %s", pdata["name"])
        ports.append(port)

    # Ensure berths exist per port
    berths: list[Berth] = []
    for port in ports:
        for tmpl in BERTH_TEMPLATES:
            code = f"{port.code}-{tmpl['suffix']}"
            result = await db.execute(select(Berth).where(Berth.code == code).limit(1))
            berth = result.scalar_one_or_none()
            if berth is None:
                bdata = {k: v for k, v in tmpl.items() if k != "suffix"}
                berth = Berth(code=code, name=f"{port.name} Berth {tmpl['suffix']}",
                              port_id=port.id, status=BerthStatus.AVAILABLE, **bdata)
                if not dry_run:
                    db.add(berth)
                    await db.flush()
                logger.info("  + Berth: %s", code)
            berths.append(berth)

    if not dry_run:
        await db.commit()

    if mode == "visits-only":
        result = await db.execute(select(Vessel).limit(n_vessels))
        vessels = list(result.scalars().all())
    else:
        # Create vessels
        vessels: list[Vessel] = []
        logger.info("Creating %d vessels...", n_vessels)
        for i in range(1, n_vessels + 1):
            vdata = _make_vessel(i)
            vessel = Vessel(**vdata)
            if not dry_run:
                db.add(vessel)
                await db.flush()
            vessels.append(vessel)
            if i % 10 == 0:
                logger.info("  %d/%d vessels created", i, n_vessels)
        if not dry_run:
            await db.commit()

    # Track which berths we've marked occupied to avoid double-marking
    occupied_berth_ids: set[int] = set()

    # Create visits
    logger.info("Creating %d visits...", n_visits)
    for i in range(n_visits):
        vessel = random.choice(vessels)
        port = random.choice(ports)
        port_berths = [b for b in berths if b.port_id == port.id]
        berth = random.choice(port_berths) if port_berths else berths[0]
        vdata = _make_visit(vessel, berth, port, offset_days=random.randint(-30, 30))
        visit = Visit(**vdata)
        if not dry_run:
            db.add(visit)
            # Sync berth status: IN_PORT visit → berth occupied
            if vdata.get("berth_id") and vdata["berth_id"] not in occupied_berth_ids:
                assigned = next((b for b in berths if b.id == vdata["berth_id"]), None)
                if assigned:
                    assigned.status = BerthStatus.OCCUPIED
                    occupied_berth_ids.add(assigned.id)
        if (i + 1) % 25 == 0:
            if not dry_run:
                await db.commit()
            logger.info("  %d/%d visits created", i + 1, n_visits)

    if not dry_run:
        await db.commit()

    label = "[DRY RUN] Would create" if dry_run else "Created"
    logger.info("=== %s: %d vessels, %d visits across %d ports ===",
                label, n_vessels if mode != "visits-only" else 0, n_visits, len(ports))


async def main(args: argparse.Namespace) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        await seed(
            db,
            n_vessels=args.vessels,
            n_visits=args.visits,
            mode=args.mode,
            dry_run=args.dry_run,
        )

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PortFlow AI — Bulk Data Seeder")
    parser.add_argument("--vessels", type=int, default=20, help="Number of vessels to create (default: 20)")
    parser.add_argument("--visits", type=int, default=50, help="Number of visits to create (default: 50)")
    parser.add_argument("--mode", choices=["seed", "reset", "visits-only"], default="seed",
                        help="seed=add data, reset=wipe demo data then re-seed, visits-only=only add visits")
    parser.add_argument("--dry-run", action="store_true", help="Preview operations without writing to DB")
    asyncio.run(main(parser.parse_args()))
