"""
Automation Script 4: GDPR-Compliant Log & Token Cleanup
Purges expired audit logs, blacklisted/expired JWT tokens from Redis,
expired API keys, and rotates local log files. Enforces SRS Privacy 9.3.

Usage:
    python scripts/log_cleaner.py                          # run all cleanup tasks
    python scripts/log_cleaner.py --task audit             # only purge audit logs
    python scripts/log_cleaner.py --task redis             # only flush expired tokens
    python scripts/log_cleaner.py --task api-keys          # only expire old API keys
    python scripts/log_cleaner.py --task log-files         # only rotate log files
    python scripts/log_cleaner.py --retention-months 6     # custom retention window
    python scripts/log_cleaner.py --schedule 24h           # run daily
    python scripts/log_cleaner.py --dry-run                # show what would be deleted
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.redis_client import get_redis
from app.models.iam import APIKey, AuditTrail
from app.services.gdpr_service import purge_old_audit_logs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/log_cleaner.log", mode="a"),
    ],
)
logger = logging.getLogger("log_cleaner")

REPORT_PATH = Path("logs/cleanup_report.json")
LOG_DIR = Path("logs")
MAX_LOG_SIZE_MB = 50
MAX_LOG_AGE_DAYS = 90


# ── Task 1: Audit log retention ────────────────────────────────────────────────

async def clean_audit_logs(db: AsyncSession, retention_months: int, dry_run: bool) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_months * 30)
    if dry_run:
        result = await db.execute(
            select(AuditTrail).where(AuditTrail.occurred_at < cutoff)
        )
        count = len(result.scalars().all())
        logger.info("[DRY RUN] Would delete %d audit records older than %s", count, cutoff.date())
        return {"task": "audit_logs", "would_delete": count, "cutoff": cutoff.isoformat()}

    deleted = await purge_old_audit_logs(db, retention_months=retention_months)
    logger.info("Deleted %d expired audit log records (cutoff: %s)", deleted, cutoff.date())
    return {"task": "audit_logs", "deleted": deleted, "cutoff": cutoff.isoformat()}


# ── Task 2: Redis token blacklist cleanup ──────────────────────────────────────

async def clean_redis_tokens(dry_run: bool) -> dict:
    """
    Redis TTLs handle auto-expiry, but this scans for any orphaned
    blacklist keys and reports the current blacklist size.
    """
    try:
        redis = await get_redis()
        blacklist_keys = await redis.keys("token_blacklist:*")
        expired_keys = []

        for key in blacklist_keys:
            ttl = await redis.ttl(key)
            if ttl <= 0:
                expired_keys.append(key)

        if dry_run:
            logger.info("[DRY RUN] Would remove %d expired Redis blacklist keys", len(expired_keys))
            return {"task": "redis_tokens", "would_remove": len(expired_keys), "total_keys": len(blacklist_keys)}

        if expired_keys:
            await redis.delete(*expired_keys)

        logger.info(
            "Redis cleanup: removed %d expired keys, %d active blacklist entries remain",
            len(expired_keys), len(blacklist_keys) - len(expired_keys),
        )
        return {
            "task": "redis_tokens",
            "removed": len(expired_keys),
            "active": len(blacklist_keys) - len(expired_keys),
        }
    except Exception as exc:
        logger.error("Redis cleanup failed: %s", exc)
        return {"task": "redis_tokens", "error": str(exc)}


# ── Task 3: Expired API key deactivation ──────────────────────────────────────

async def clean_expired_api_keys(db: AsyncSession, dry_run: bool) -> dict:
    now = datetime.now(timezone.utc)

    if dry_run:
        result = await db.execute(
            select(APIKey).where(
                APIKey.is_active == True,
                APIKey.expires_at != None,
                APIKey.expires_at < now,
            )
        )
        keys = result.scalars().all()
        logger.info("[DRY RUN] Would deactivate %d expired API keys", len(keys))
        return {"task": "api_keys", "would_deactivate": len(keys)}

    result = await db.execute(
        update(APIKey)
        .where(
            APIKey.is_active == True,
            APIKey.expires_at != None,
            APIKey.expires_at < now,
        )
        .values(is_active=False)
    )
    await db.commit()
    count = result.rowcount
    logger.info("Deactivated %d expired API keys", count)
    return {"task": "api_keys", "deactivated": count}


# ── Task 4: Local log file rotation ───────────────────────────────────────────

def clean_log_files(dry_run: bool) -> dict:
    if not LOG_DIR.exists():
        return {"task": "log_files", "skipped": "logs/ directory not found"}

    cutoff = datetime.now().timestamp() - (MAX_LOG_AGE_DAYS * 86400)
    removed = []
    rotated = []

    for log_file in LOG_DIR.glob("*.log*"):
        stat = log_file.stat()

        # Remove old archived logs
        if log_file.suffix in (".gz", ".1", ".2", ".3") and stat.st_mtime < cutoff:
            if not dry_run:
                log_file.unlink()
            removed.append(log_file.name)
            logger.info("  %s old log archive: %s", "[DRY RUN] Would remove" if dry_run else "Removed", log_file.name)
            continue

        # Rotate oversized active logs
        size_mb = stat.st_size / (1024 * 1024)
        if log_file.suffix == ".log" and size_mb > MAX_LOG_SIZE_MB:
            archive = log_file.with_suffix(".log.1")
            if not dry_run:
                log_file.rename(archive)
                log_file.touch()
            rotated.append({"file": log_file.name, "size_mb": round(size_mb, 1)})
            logger.info("  %s oversized log (%.1f MB): %s", "[DRY RUN] Would rotate" if dry_run else "Rotated", size_mb, log_file.name)

    return {"task": "log_files", "removed": removed, "rotated": rotated}


# ── Orchestrator ───────────────────────────────────────────────────────────────

def _parse_interval(value: str) -> int:
    value = value.strip().lower()
    if value.endswith("h"):
        return int(value[:-1]) * 3600
    if value.endswith("m"):
        return int(value[:-1]) * 60
    return int(value)


def _save_report(results: list[dict]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    history: list[dict] = []
    if REPORT_PATH.exists():
        try:
            history = json.loads(REPORT_PATH.read_text())
        except json.JSONDecodeError:
            history = []
    history.insert(0, {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "tasks": results,
    })
    history = history[:30]
    REPORT_PATH.write_text(json.dumps(history, indent=2))


TASK_CHOICES = ["all", "audit", "redis", "api-keys", "log-files"]


async def run_cleanup(db: AsyncSession, task: str, retention_months: int, dry_run: bool) -> list[dict]:
    results = []
    run_all = task == "all"

    if run_all or task == "audit":
        results.append(await clean_audit_logs(db, retention_months, dry_run))

    if run_all or task == "redis":
        results.append(await clean_redis_tokens(dry_run))

    if run_all or task == "api-keys":
        results.append(await clean_expired_api_keys(db, dry_run))

    if run_all or task == "log-files":
        results.append(clean_log_files(dry_run))

    return results


async def main(args: argparse.Namespace) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    if args.schedule:
        interval = _parse_interval(args.schedule)
        logger.info("Cleanup scheduler started — running every %d seconds", interval)
        while True:
            logger.info("=== Cleanup run at %s ===", datetime.now(timezone.utc).isoformat())
            async with async_session() as db:
                results = await run_cleanup(db, args.task, args.retention_months, args.dry_run)
            _save_report(results)
            logger.info("Next cleanup in %d seconds", interval)
            await asyncio.sleep(interval)
    else:
        logger.info("=== Cleanup run at %s ===", datetime.now(timezone.utc).isoformat())
        async with async_session() as db:
            results = await run_cleanup(db, args.task, args.retention_months, args.dry_run)
        _save_report(results)
        logger.info("=== Cleanup complete ===")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PortFlow AI — GDPR Log & Token Cleanup")
    parser.add_argument("--task", choices=TASK_CHOICES, default="all", help="Which cleanup to run (default: all)")
    parser.add_argument("--retention-months", type=int, default=settings.LOG_RETENTION_MONTHS,
                        help=f"Audit log retention window in months (default: {settings.LOG_RETENTION_MONTHS})")
    parser.add_argument("--schedule", metavar="INTERVAL", help="Run on interval: 24h, 60m, 86400")
    parser.add_argument("--dry-run", action="store_true", help="Preview deletions without modifying data")
    asyncio.run(main(parser.parse_args()))
