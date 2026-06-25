"""
Notification dispatch service.
Resolves the delivery channel (email, in-app) and dispatches notifications.
Supports both immediate and scheduled delivery.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import Notification, NotificationChannel, NotificationStatus, NotificationTemplate
from app.services.email_service import send_notification_email

logger = logging.getLogger(__name__)


async def dispatch_notification(notification_id: int, db: AsyncSession) -> bool:
    """
    Deliver a pending notification and update its status.
    Returns True on success, False on failure.
    """
    notif = await db.get(Notification, notification_id)
    if not notif:
        logger.warning("Notification %d not found", notification_id)
        return False

    if notif.status not in (NotificationStatus.PENDING,):
        logger.debug("Notification %d already processed: %s", notification_id, notif.status)
        return True

    success = False
    try:
        if notif.channel == NotificationChannel.EMAIL:
            success = await send_notification_email(
                to=notif.recipient,
                subject=notif.subject or "PortFlow AI Notification",
                body=notif.body,
            )
        elif notif.channel == NotificationChannel.IN_APP:
            # In-app notifications are stored as "sent" once the record exists
            success = True
        elif notif.channel == NotificationChannel.WEBHOOK:
            success = await _dispatch_webhook(notif.recipient, notif.body)
        else:
            logger.warning("Unsupported channel: %s", notif.channel)
            success = False

        notif.status = NotificationStatus.SENT if success else NotificationStatus.FAILED
        notif.sent_at = datetime.now(timezone.utc) if success else None

    except Exception as exc:
        logger.error("Failed to dispatch notification %d: %s", notification_id, exc)
        notif.status = NotificationStatus.FAILED
        notif.error_message = str(exc)[:500]

    await db.commit()
    return success


async def _dispatch_webhook(url: str, body: str) -> bool:
    """POST notification body to a webhook URL."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                content=body,
                headers={"Content-Type": "application/json"},
            )
            return response.is_success
    except Exception as exc:
        logger.error("Webhook dispatch failed: %s", exc)
        return False


async def create_and_dispatch(
    recipient: str,
    channel: NotificationChannel,
    body: str,
    subject: str | None = None,
    reference_type: str | None = None,
    reference_id: int | None = None,
    template_id: int | None = None,
    db: AsyncSession = None,
) -> Notification:
    """
    Create a Notification record and immediately dispatch it.
    """
    notif = Notification(
        template_id=template_id,
        recipient=recipient,
        channel=channel,
        subject=subject,
        body=body,
        status=NotificationStatus.PENDING,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(notif)
    await db.flush()

    await dispatch_notification(notif.id, db)
    await db.refresh(notif)
    return notif


async def send_berth_assignment_notification(
    visit_id: int,
    vessel_name: str,
    berth_name: str,
    etb: datetime | None,
    recipient_email: str,
    db: AsyncSession,
) -> None:
    """Send an email notification when a berth is assigned to a vessel."""
    body = (
        f"Berth Assignment Confirmation\n\n"
        f"Vessel: {vessel_name}\n"
        f"Berth: {berth_name}\n"
        f"ETB: {etb.strftime('%Y-%m-%d %H:%M UTC') if etb else 'TBD'}\n"
        f"Visit ID: {visit_id}\n\n"
        f"Please ensure all pre-arrival formalities are completed."
    )
    await create_and_dispatch(
        recipient=recipient_email,
        channel=NotificationChannel.EMAIL,
        subject=f"PortFlow AI — Berth Assigned: {vessel_name}",
        body=body,
        reference_type="visit",
        reference_id=visit_id,
        db=db,
    )


async def flush_pending_notifications(db: AsyncSession) -> dict[str, int]:
    """
    Background job: deliver all pending notifications that are due.
    Called by the background scheduler.
    """
    now = datetime.now(timezone.utc)
    pending = (
        await db.execute(
            select(Notification).where(
                Notification.status == NotificationStatus.PENDING,
                (Notification.scheduled_at.is_(None)) | (Notification.scheduled_at <= now),
            ).limit(100)
        )
    ).scalars().all()

    sent = failed = 0
    for notif in pending:
        result = await dispatch_notification(notif.id, db)
        if result:
            sent += 1
        else:
            failed += 1

    if pending:
        logger.info("Notification flush: %d sent, %d failed", sent, failed)
    return {"sent": sent, "failed": failed}
