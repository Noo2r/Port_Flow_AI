"""
Work Order endpoints — CRUD + auto-generation trigger.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import DbSession, require_roles
from app.models.iam import UserRole
from app.models.work_orders import WorkOrder, WorkOrderStatus

_ops_dep = Depends(require_roles(UserRole.ADMIN, UserRole.PORT_MANAGER, UserRole.OPERATIONS))
from app.schemas.work_orders import WorkOrderCreate, WorkOrderResponse, WorkOrderUpdate
from app.services.work_order_service import (
    auto_create_work_orders,
    get_visit_work_orders,
    update_work_order_status,
)

router = APIRouter(tags=["Work Orders"])


@router.get(
    "/work-orders",
    response_model=list[WorkOrderResponse],
    summary="List work orders (optionally filter by visit or status)",
)
async def list_work_orders(
    db: DbSession,
    visit_id: int | None = None,
    status_filter: WorkOrderStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[WorkOrder]:
    stmt = select(WorkOrder).offset(skip).limit(limit).order_by(WorkOrder.scheduled_start)
    if visit_id:
        stmt = stmt.where(WorkOrder.visit_id == visit_id)
    if status_filter:
        stmt = stmt.where(WorkOrder.status == status_filter)
    return (await db.execute(stmt)).scalars().all()


@router.get(
    "/work-orders/{order_id}",
    response_model=WorkOrderResponse,
    summary="Get a single work order",
)
async def get_work_order(order_id: int, db: DbSession) -> WorkOrder:
    order = await db.get(WorkOrder, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Work order not found")
    return order


@router.post(
    "/work-orders",
    response_model=WorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually create a work order",
    dependencies=[_ops_dep],
)
async def create_work_order(
    payload: WorkOrderCreate,
    db: DbSession,
) -> WorkOrder:
    order = WorkOrder(**payload.model_dump())
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


@router.patch(
    "/work-orders/{order_id}",
    response_model=WorkOrderResponse,
    summary="Update a work order (status, assignment, schedule)",
    dependencies=[_ops_dep],
)
async def patch_work_order(
    order_id: int,
    payload: WorkOrderUpdate,
    db: DbSession,
) -> WorkOrder:
    order = await db.get(WorkOrder, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Work order not found")

    data = payload.model_dump(exclude_none=True)

    # If status is changing, route through the service so actual_start/actual_end
    # are stamped automatically and completion_notes are handled correctly.
    if "status" in data:
        new_status = WorkOrderStatus(data.pop("status"))
        notes = data.pop("completion_notes", None)
        order = await update_work_order_status(order_id, new_status, notes, db)

    # Apply any remaining non-status fields (assignment, schedule, etc.)
    for field, value in data.items():
        setattr(order, field, value)

    if data:  # only commit again if there were extra fields
        await db.commit()
        await db.refresh(order)

    return order


@router.post(
    "/visits/{visit_id}/work-orders/auto",
    response_model=list[WorkOrderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Auto-generate standard work orders for a visit",
    description=(
        "Triggers automatic creation of the standard set of port work orders "
        "(pilotage, mooring, customs, cargo handling, etc.) for an assigned visit. "
        "Idempotent — safe to call multiple times."
    ),
    dependencies=[_ops_dep],
)
async def auto_generate_work_orders(
    visit_id: int,
    db: DbSession,
) -> list[WorkOrder]:
    from app.models.visit import Visit

    visit = await db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Visit not found")
    if not visit.berth_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Visit must have an assigned berth before generating work orders",
        )

    orders = await auto_create_work_orders(
        visit_id=visit_id,
        vessel_id=visit.vessel_id,
        berth_id=visit.berth_id,
        etb=visit.etb,
        etd=visit.etd,
        db=db,
    )
    if not orders:
        # Already existed — return existing
        orders = await get_visit_work_orders(visit_id, db)
    return orders


@router.get(
    "/visits/{visit_id}/work-orders",
    response_model=list[WorkOrderResponse],
    summary="List all work orders for a visit",
)
async def visit_work_orders(visit_id: int, db: DbSession) -> list[WorkOrder]:
    return await get_visit_work_orders(visit_id, db)
