"""
GDPR / Privacy endpoints.
  POST /privacy/users/{id}/anonymize  — right to erasure
  GET  /privacy/users/{id}/export     — right of access / data portability
  POST /privacy/audit-logs/purge      — trigger manual log retention sweep
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.dependencies import CurrentUser, DbSession
from app.models.iam import UserRole
from app.services.gdpr_service import anonymize_user, export_user_data, purge_old_audit_logs

router = APIRouter(prefix="/privacy", tags=["Privacy & GDPR"])


@router.post(
    "/users/{user_id}/anonymize",
    summary="[Admin] Right to Erasure — anonymize all user PII",
    description=(
        "Irreversibly anonymizes all personally identifiable information for the specified user.\n\n"
        "The user record is preserved for referential integrity but all PII is scrubbed.\n"
        "Requires **Admin** role. Cannot anonymize another admin."
    ),
)
async def anonymize_user_endpoint(
    user_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    if user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot anonymize yourself")

    try:
        result = await anonymize_user(user_id, db, requested_by_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))

    return result


@router.get(
    "/users/{user_id}/export",
    summary="Right of Access — export all data held about a user",
    description=(
        "Returns a full JSON export of all data held about a user.\n\n"
        "A user may access their own data. Admins may access any user's data."
    ),
)
async def export_user_data_endpoint(
    user_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> JSONResponse:
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

    try:
        data = await export_user_data(user_id, db)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))

    return JSONResponse(content=data)


@router.get(
    "/me/export",
    summary="Export your own personal data (data portability)",
)
async def export_own_data(
    current_user: CurrentUser,
    db: DbSession,
) -> JSONResponse:
    data = await export_user_data(current_user.id, db)
    return JSONResponse(content=data)


@router.post(
    "/audit-logs/purge",
    summary="[Admin] Purge audit logs older than 12 months",
    description=(
        "Deletes all audit trail records older than the configured retention period (default: 12 months).\n\n"
        "This runs automatically via the background scheduler but can be triggered manually here."
    ),
)
async def purge_audit_logs(
    current_user: CurrentUser,
    db: DbSession,
    retention_months: int = 12,
) -> dict:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    deleted = await purge_old_audit_logs(db, retention_months=retention_months)
    return {
        "deleted_records": deleted,
        "retention_months": retention_months,
        "message": f"Purged {deleted} audit log records older than {retention_months} months",
    }
