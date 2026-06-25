"""
Work Order service — auto-generates standard work orders when a vessel is berthed.
Also handles manual creation, status updates, and queries.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_orders import WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType

logger = logging.getLogger(__name__)

# Standard work orders auto-created on any berth assignment
_STANDARD_ORDERS: list[dict] = [
    {
        "order_type": WorkOrderType.PILOTAGE,
        "title": "Vessel Pilotage — Inbound",
        "description": "Pilot boarding and vessel guidance to berth.",
        "priority": WorkOrderPriority.URGENT,
        "offset_hours": -2,       # 2 hours before ETB
        "duration_hours": 2,
    },
    {
        "order_type": WorkOrderType.MOORING,
        "title": "Vessel Mooring",
        "description": "Secure vessel to berth using mooring lines.",
        "priority": WorkOrderPriority.HIGH,
        "offset_hours": 0,        # at ETB
        "duration_hours": 1,
    },
    {
        "order_type": WorkOrderType.TUGBOAT,
        "title": "Tugboat Assistance — Berthing",
        "description": "Tugboat standby and assistance for berthing manoeuvre.",
        "priority": WorkOrderPriority.HIGH,
        "offset_hours": -1,
        "duration_hours": 2,
    },
    {
        "order_type": WorkOrderType.CUSTOMS_INSPECTION,
        "title": "Customs Clearance Inspection",
        "description": "Customs authority boarding and document verification.",
        "priority": WorkOrderPriority.NORMAL,
        "offset_hours": 1,        # 1 hour after berthing
        "duration_hours": 2,
    },
    {
        "order_type": WorkOrderType.HEALTH_INSPECTION,
        "title": "Health & Sanitation Inspection",
        "description": "Port health authority inspection of vessel and crew.",
        "priority": WorkOrderPriority.NORMAL,
        "offset_hours": 1,
        "duration_hours": 1,
    },
    {
        "order_type": WorkOrderType.CARGO_HANDLING,
        "title": "Cargo Operations",
        "description": "Load/discharge cargo as per manifest.",
        "priority": WorkOrderPriority.NORMAL,
        "offset_hours": 3,        # after inspections
        "duration_hours": 12,
    },
    {
        "order_type": WorkOrderType.WASTE_RECEPTION,
        "title": "Waste Reception Service",
        "description": "Collect and dispose of vessel waste in compliance with MARPOL.",
        "priority": WorkOrderPriority.NORMAL,
        "offset_hours": 2,
        "duration_hours": 2,
    },
    {
        "order_type": WorkOrderType.UNMOORING,
        "title": "Vessel Unmooring — Outbound",
        "description": "Release mooring lines and prepare vessel for departure.",
        "priority": WorkOrderPriority.HIGH,
        "offset_hours": -1,       # 1 hour before ETD (relative to ETD)
        "duration_hours": 1,
    },
]


async def auto_create_work_orders(
    visit_id: int,
    vessel_id: int,
    berth_id: int,
    etb: datetime | None,
    etd: datetime | None,
    db: AsyncSession,
) -> list[WorkOrder]:
    """
    Auto-generate standard port work orders when a berth is assigned to a visit.
    Idempotent — skips if orders already exist for this visit.
    """
    existing = (
        await db.execute(
            select(WorkOrder).where(WorkOrder.visit_id == visit_id)
        )
    ).scalars().first()

    if existing:
        logger.debug("Work orders already exist for visit %d — skipping auto-create", visit_id)
        return []

    now = datetime.now(timezone.utc)
    base_etb = etb or now
    base_etd = etd or (base_etb + timedelta(hours=24))

    orders: list[WorkOrder] = []
    for template in _STANDARD_ORDERS:
        if template["order_type"] == WorkOrderType.UNMOORING:
            # UNMOORING is scheduled relative to ETD
            start = base_etd + timedelta(hours=template["offset_hours"])
        else:
            start = base_etb + timedelta(hours=template["offset_hours"])

        end = start + timedelta(hours=template["duration_hours"])

        order = WorkOrder(
            visit_id=visit_id,
            vessel_id=vessel_id,
            berth_id=berth_id,
            order_type=template["order_type"],
            title=template["title"],
            description=template["description"],
            priority=template["priority"],
            status=WorkOrderStatus.PENDING,
            scheduled_start=start,
            scheduled_end=end,
        )
        db.add(order)
        orders.append(order)

    await db.commit()
    logger.info("Auto-created %d work orders for visit %d (berth %d)", len(orders), visit_id, berth_id)
    return orders


async def get_visit_work_orders(visit_id: int, db: AsyncSession) -> list[WorkOrder]:
    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.visit_id == visit_id)
        .order_by(WorkOrder.scheduled_start)
    )
    return result.scalars().all()


async def update_work_order_status(
    order_id: int,
    new_status: WorkOrderStatus,
    notes: str | None,
    db: AsyncSession,
) -> WorkOrder:
    order = await db.get(WorkOrder, order_id)
    if not order:
        raise ValueError(f"WorkOrder {order_id} not found")

    order.status = new_status
    if notes:
        order.completion_notes = notes
    if new_status == WorkOrderStatus.IN_PROGRESS and not order.actual_start:
        order.actual_start = datetime.now(timezone.utc)
    elif new_status == WorkOrderStatus.COMPLETED and not order.actual_end:
        order.actual_end = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(order)
    return order
