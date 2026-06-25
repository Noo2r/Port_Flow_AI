"""
Database backup service.
Runs pg_dump to create compressed PostgreSQL backups.
Supports local file storage and optional S3 upload.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_BACKUP_DIR = Path("/tmp/portflow_backups")


def _parse_pg_url(url: str) -> dict:
    """Parse postgresql+asyncpg://user:pass@host:port/db into components."""
    # Strip driver prefix
    clean = url.replace("postgresql+asyncpg://", "postgresql://")
    from urllib.parse import urlparse
    parsed = urlparse(clean)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "portflow",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/"),
    }


async def run_backup(upload_to_s3: bool = False) -> dict:
    """
    Execute pg_dump, save to local file, optionally upload to S3.
    Returns a result dict with file path, size, and status.
    """
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"portflow_backup_{timestamp}.sql.gz"
    filepath = _BACKUP_DIR / filename

    pg = _parse_pg_url(settings.DATABASE_URL)

    env = os.environ.copy()
    env["PGPASSWORD"] = pg["password"]

    cmd = [
        "pg_dump",
        "-h", pg["host"],
        "-p", pg["port"],
        "-U", pg["user"],
        "-d", pg["dbname"],
        "--no-password",
        "--format=plain",
        "--compress=9",
        "--file", str(filepath),
    ]

    logger.info("Starting database backup → %s", filepath)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            error = stderr.decode()
            logger.error("pg_dump failed: %s", error)
            return {
                "status": "failed",
                "error": error,
                "timestamp": timestamp,
            }

        size_bytes = filepath.stat().st_size
        logger.info("Backup complete: %s (%.1f MB)", filename, size_bytes / 1024 / 1024)

        result = {
            "status": "success",
            "filename": filename,
            "filepath": str(filepath),
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / 1024 / 1024, 2),
            "timestamp": timestamp,
            "s3_uploaded": False,
        }

        if upload_to_s3 and settings.S3_BACKUP_BUCKET:
            result["s3_uploaded"] = await _upload_to_s3(filepath, filename)

        return result

    except asyncio.TimeoutError:
        logger.error("pg_dump timed out after 300 seconds")
        return {"status": "failed", "error": "timeout", "timestamp": timestamp}
    except FileNotFoundError:
        logger.warning("pg_dump not found — backup skipped (pg_dump not installed)")
        return {"status": "skipped", "error": "pg_dump not installed", "timestamp": timestamp}


async def _upload_to_s3(filepath: Path, filename: str) -> bool:
    """Upload backup file to S3. Requires boto3 and S3_BACKUP_BUCKET setting."""
    try:
        import boto3  # type: ignore[import]
        from botocore.exceptions import ClientError  # type: ignore[import]

        s3 = boto3.client("s3")
        s3_key = f"backups/{filename}"
        s3.upload_file(str(filepath), settings.S3_BACKUP_BUCKET, s3_key)
        logger.info("Backup uploaded to s3://%s/%s", settings.S3_BACKUP_BUCKET, s3_key)
        return True
    except ImportError:
        logger.warning("boto3 not installed — S3 upload skipped")
        return False
    except Exception as exc:
        logger.error("S3 upload failed: %s", exc)
        return False


def list_backups() -> list[dict]:
    """List all local backup files with metadata."""
    if not _BACKUP_DIR.exists():
        return []
    backups = []
    for f in sorted(_BACKUP_DIR.glob("portflow_backup_*.sql.gz"), reverse=True):
        stat = f.stat()
        backups.append({
            "filename": f.name,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return backups


async def cleanup_old_backups(keep_days: int = 30) -> int:
    """Delete backup files older than keep_days. Returns count of deleted files."""
    if not _BACKUP_DIR.exists():
        return 0
    cutoff = datetime.now(timezone.utc).timestamp() - (keep_days * 86400)
    deleted = 0
    for f in _BACKUP_DIR.glob("portflow_backup_*.sql.gz"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            deleted += 1
            logger.info("Deleted old backup: %s", f.name)
    return deleted
