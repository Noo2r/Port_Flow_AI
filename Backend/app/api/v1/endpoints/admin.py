"""
System Administration endpoints — backup management, log retention, system health.
All endpoints require Admin role.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DbSession
from app.models.iam import UserRole
from app.services.backup_service import cleanup_old_backups, list_backups, run_backup
from app.services.gdpr_service import purge_old_audit_logs

router = APIRouter(prefix="/admin", tags=["System Administration"])


def _require_admin(user: CurrentUser) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")


@router.post(
    "/backup",
    summary="Trigger a manual database backup",
    description=(
        "Executes `pg_dump` to create a compressed backup of the PostgreSQL database.\n\n"
        "Optionally uploads to S3 if `S3_BACKUP_BUCKET` is configured.\n\n"
        "Requires **Admin** role."
    ),
)
async def trigger_backup(
    current_user: CurrentUser,
    upload_to_s3: bool = False,
) -> dict:
    _require_admin(current_user)
    result = await run_backup(upload_to_s3=upload_to_s3)
    if result.get("status") == "failed":
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, result.get("error", "Backup failed"))
    return result


@router.get(
    "/backup/list",
    summary="List all local database backups",
)
async def list_backup_files(current_user: CurrentUser) -> list[dict]:
    _require_admin(current_user)
    return list_backups()


@router.delete(
    "/backup/cleanup",
    summary="Delete backups older than N days",
)
async def cleanup_backups(current_user: CurrentUser, keep_days: int = 30) -> dict:
    _require_admin(current_user)
    deleted = await cleanup_old_backups(keep_days=keep_days)
    return {"deleted_files": deleted, "keep_days": keep_days}


@router.post(
    "/maintenance/purge-logs",
    summary="Manually trigger audit log retention sweep",
)
async def purge_logs(
    current_user: CurrentUser,
    db: DbSession,
    retention_months: int = 12,
) -> dict:
    _require_admin(current_user)
    deleted = await purge_old_audit_logs(db, retention_months=retention_months)
    return {
        "deleted_audit_records": deleted,
        "retention_months": retention_months,
    }


@router.get(
    "/system/info",
    summary="System information and configuration",
)
async def system_info(current_user: CurrentUser) -> dict:
    _require_admin(current_user)
    from app.config import settings
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "debug_mode": settings.DEBUG,
        "database_host": settings.DATABASE_URL.split("@")[-1].split("/")[0] if "@" in settings.DATABASE_URL else "hidden",
        "redis_configured": bool(settings.REDIS_URL),
        "smtp_configured": bool(settings.SMTP_HOST),
        "s3_backup_configured": bool(settings.S3_BACKUP_BUCKET),
        "frontend_url": settings.FRONTEND_URL,
    }
