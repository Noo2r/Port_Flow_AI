"""
Automation Script 1: Scheduled Database Backup
Runs pg_dump backups on a configurable interval, rotates old backups,
and optionally uploads to S3. Run standalone or via cron/Task Scheduler.

Usage:
    python scripts/auto_backup.py                  # run once
    python scripts/auto_backup.py --schedule 6h    # run every 6 hours
    python scripts/auto_backup.py --keep-days 14   # keep 14 days of backups
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow imports from the app package
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.backup_service import cleanup_old_backups, list_backups, run_backup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/auto_backup.log", mode="a"),
    ],
)
logger = logging.getLogger("auto_backup")

BACKUP_REPORT_PATH = Path("logs/backup_report.json")


def _parse_interval(value: str) -> int:
    """Convert '6h', '30m', '3600' → seconds."""
    value = value.strip().lower()
    if value.endswith("h"):
        return int(value[:-1]) * 3600
    if value.endswith("m"):
        return int(value[:-1]) * 60
    return int(value)


def _write_report(result: dict) -> None:
    BACKUP_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    history: list[dict] = []
    if BACKUP_REPORT_PATH.exists():
        try:
            history = json.loads(BACKUP_REPORT_PATH.read_text())
        except json.JSONDecodeError:
            history = []
    history.insert(0, result)
    history = history[:50]  # keep last 50 entries
    BACKUP_REPORT_PATH.write_text(json.dumps(history, indent=2))


async def _run_once(keep_days: int, upload_s3: bool) -> dict:
    logger.info("=== Starting backup run ===")
    result = await run_backup(upload_to_s3=upload_s3)
    result["run_at"] = datetime.now(timezone.utc).isoformat()

    if result["status"] == "success":
        logger.info("Backup succeeded: %s (%.2f MB)", result["filename"], result["size_mb"])
    else:
        logger.error("Backup failed: %s", result.get("error"))

    deleted = await cleanup_old_backups(keep_days=keep_days)
    if deleted:
        logger.info("Rotated %d old backup(s) older than %d days", deleted, keep_days)

    backups = list_backups()
    logger.info("Current backup count: %d", len(backups))
    for b in backups[:5]:
        logger.info("  %s  %.2f MB  %s", b["filename"], b["size_mb"], b["created_at"])

    _write_report(result)
    return result


async def main(args: argparse.Namespace) -> None:
    if args.schedule:
        interval = _parse_interval(args.schedule)
        logger.info("Scheduler started — running every %d seconds", interval)
        while True:
            await _run_once(keep_days=args.keep_days, upload_s3=args.s3)
            logger.info("Next run in %d seconds", interval)
            await asyncio.sleep(interval)
    else:
        result = await _run_once(keep_days=args.keep_days, upload_s3=args.s3)
        sys.exit(0 if result["status"] in ("success", "skipped") else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PortFlow AI — Database Backup Automation")
    parser.add_argument("--schedule", metavar="INTERVAL", help="Run on interval: 6h, 30m, 3600")
    parser.add_argument("--keep-days", type=int, default=30, help="Days of backups to retain (default: 30)")
    parser.add_argument("--s3", action="store_true", help="Upload backup to S3 after creation")
    asyncio.run(main(parser.parse_args()))
