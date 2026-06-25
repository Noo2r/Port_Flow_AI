"""
GDPR compliance service.
Provides:
  - Data anonymization (right to erasure / right to be forgotten)
  - Personal data export (right of access / data portability)
  - Audit trail retention enforcement
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.iam import AuditTrail, User

logger = logging.getLogger(__name__)


def _anon_email(user_id: int) -> str:
    """Deterministic anonymized email — cannot be reversed."""
    return f"anonymized_{hashlib.sha256(str(user_id).encode()).hexdigest()[:12]}@deleted.local"


async def anonymize_user(user_id: int, db: AsyncSession, requested_by_id: int) -> dict:
    """
    Right to Erasure — anonymize all PII for a user.
    The User record is preserved (for FK integrity) but all PII is scrubbed.
    """
    user = await db.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    original_email = user.email

    # Scrub PII
    user.email = _anon_email(user_id)
    user.full_name = "Anonymized User"
    user.hashed_password = None
    user.is_active = False
    user.is_verified = False
    user.last_login = None

    # Scrub audit trails
    await db.execute(
        update(AuditTrail)
        .where(AuditTrail.user_id == user_id)
        .values(ip_address=None, user_agent=None, details="[GDPR ANONYMIZED]")
    )

    # Log the anonymization event itself
    audit = AuditTrail(
        user_id=requested_by_id,
        action="GDPR_ANONYMIZE",
        resource_type="User",
        resource_id=user_id,
        details=json.dumps({"original_email_hash": hashlib.sha256(original_email.encode()).hexdigest()}),
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()

    logger.info(
        "GDPR anonymization completed for user %d by user %d",
        user_id, requested_by_id,
    )
    return {
        "user_id": user_id,
        "status": "anonymized",
        "anonymized_at": datetime.now(timezone.utc).isoformat(),
        "requested_by": requested_by_id,
    }


async def export_user_data(user_id: int, db: AsyncSession) -> dict:
    """
    Right of Access / Data Portability — export all data held about a user.
    Returns a JSON-serializable dict.
    """
    user = await db.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    from app.models.iam import APIKey
    api_keys = (
        await db.execute(select(APIKey).where(APIKey.user_id == user_id))
    ).scalars().all()

    audit_trails = (
        await db.execute(
            select(AuditTrail)
            .where(AuditTrail.user_id == user_id)
            .order_by(AuditTrail.occurred_at.desc())
            .limit(1000)
        )
    ).scalars().all()

    def _dt(v) -> str | None:
        return v.isoformat() if v else None

    return {
        "export_generated_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "last_login": _dt(user.last_login),
            "created_at": _dt(user.created_at),
        },
        "api_keys": [
            {
                "id": k.id,
                "name": k.name,
                "is_active": k.is_active,
                "expires_at": _dt(k.expires_at),
                "last_used_at": _dt(k.last_used_at),
                "created_at": _dt(k.created_at),
            }
            for k in api_keys
        ],
        "audit_trail": [
            {
                "action": t.action,
                "resource_type": t.resource_type,
                "resource_id": t.resource_id,
                "ip_address": t.ip_address,
                "occurred_at": _dt(t.occurred_at),
            }
            for t in audit_trails
        ],
    }


# ── Log retention ─────────────────────────────────────────────────────────────

async def purge_old_audit_logs(
    db: AsyncSession,
    retention_months: int = 12,
) -> int:
    """
    Delete audit trail records older than `retention_months`.
    Per SRS Privacy 9.3 — 12-month log retention.
    Returns the number of records deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_months * 30)
    result = await db.execute(
        delete(AuditTrail).where(AuditTrail.occurred_at < cutoff)
    )
    await db.commit()
    deleted = result.rowcount
    logger.info(
        "Log retention sweep: deleted %d audit records older than %s",
        deleted, cutoff.date(),
    )
    return deleted
