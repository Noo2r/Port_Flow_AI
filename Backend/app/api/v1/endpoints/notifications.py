"""
Notification endpoints — CRUD for notifications and templates,
plus manual dispatch trigger.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession, require_roles
from app.models.iam import UserRole

_ops_dep = Depends(require_roles(UserRole.ADMIN, UserRole.PORT_MANAGER, UserRole.OPERATIONS))
from app.models.notifications import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationTemplate,
)
from app.services.notification_service import create_and_dispatch, dispatch_notification

router = APIRouter(tags=["Notifications"])


# ── Pydantic schemas (inline for simplicity) ──────────────────────────────────

class NotificationSend(BaseModel):
    recipient: str = Field(description="Email address, phone number, or webhook URL")
    channel: NotificationChannel
    subject: str | None = None
    body: str = Field(min_length=1)
    reference_type: str | None = None
    reference_id: int | None = None


class NotificationResponse(BaseModel):
    id: int
    recipient: str
    channel: NotificationChannel
    subject: str | None
    body: str
    status: NotificationStatus
    reference_type: str | None
    reference_id: int | None
    error_message: str | None
    sent_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


class TemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    event_type: str
    channel: NotificationChannel
    subject: str | None = None
    body_template: str = Field(min_length=1, description="Jinja2-style template body")
    is_active: bool = True


class TemplateResponse(BaseModel):
    id: int
    name: str
    event_type: str
    channel: NotificationChannel
    subject: str | None
    body_template: str
    is_active: bool

    model_config = {"from_attributes": True}


# ── Notifications ─────────────────────────────────────────────────────────────

@router.post(
    "/notifications/send",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a notification immediately",
    description=(
        "Create and dispatch a notification via the specified channel.\n\n"
        "Supports **email**, **in_app**, and **webhook** channels.\n"
        "SMS support requires a configured SMS gateway (future)."
    ),
    dependencies=[_ops_dep],
)
async def send_notification(
    payload: NotificationSend,
    db: DbSession,
) -> Notification:
    return await create_and_dispatch(
        recipient=payload.recipient,
        channel=payload.channel,
        subject=payload.subject,
        body=payload.body,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        db=db,
    )


@router.get(
    "/notifications",
    response_model=list[NotificationResponse],
    summary="List notifications (paginated)",
)
async def list_notifications(
    _user: CurrentUser,
    db: DbSession,
    status_filter: NotificationStatus | None = None,
    channel: NotificationChannel | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Notification]:
    stmt = (
        select(Notification)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if status_filter:
        stmt = stmt.where(Notification.status == status_filter)
    if channel:
        stmt = stmt.where(Notification.channel == channel)
    return (await db.execute(stmt)).scalars().all()


@router.get(
    "/notifications/{notification_id}",
    response_model=NotificationResponse,
    summary="Get a single notification",
)
async def get_notification(notification_id: int, _user: CurrentUser, db: DbSession) -> Notification:
    notif = await db.get(Notification, notification_id)
    if not notif:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    return notif


@router.post(
    "/notifications/{notification_id}/retry",
    response_model=NotificationResponse,
    summary="Retry a failed notification",
    dependencies=[_ops_dep],
)
async def retry_notification(
    notification_id: int,
    db: DbSession,
) -> Notification:
    notif = await db.get(Notification, notification_id)
    if not notif:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    if notif.status != NotificationStatus.FAILED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only FAILED notifications can be retried")

    notif.status = NotificationStatus.PENDING
    notif.error_message = None
    await db.commit()

    await dispatch_notification(notification_id, db)
    await db.refresh(notif)
    return notif


@router.patch(
    "/notifications/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark an in-app notification as read",
)
async def mark_read(notification_id: int, _user: CurrentUser, db: DbSession) -> None:
    notif = await db.get(Notification, notification_id)
    if not notif:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    notif.status = NotificationStatus.READ
    await db.commit()


# ── Notification Templates ────────────────────────────────────────────────────

@router.get(
    "/notification-templates",
    response_model=list[TemplateResponse],
    summary="List notification templates",
)
async def list_templates(_user: CurrentUser, db: DbSession) -> list[NotificationTemplate]:
    return (await db.execute(select(NotificationTemplate))).scalars().all()


@router.post(
    "/notification-templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a notification template",
    dependencies=[_ops_dep],
)
async def create_template(
    payload: TemplateCreate,
    db: DbSession,
) -> NotificationTemplate:
    template = NotificationTemplate(**payload.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.delete(
    "/notification-templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a notification template",
    dependencies=[_ops_dep],
)
async def deactivate_template(
    template_id: int,
    db: DbSession,
) -> None:
    template = await db.get(NotificationTemplate, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    template.is_active = False
    await db.commit()
