"""Backup and restore service.

BKUP-01: Scheduled daily backups with 30-day retention.
BKUP-02: Restore within 15 minutes.
BKUP-03: Restore recovers all data including audit events and configuration.
PRIV-03: backup_predates_deletion() detects if a backup predates any deletion event.

Tool: pg_dump (custom format -Fc) and pg_restore.
Backup location: /backups/ (bind-mounted from ./backups on host).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_BACKUP_DIR = "/backups"
_RESTORE_TIMEOUT_SECONDS = 15 * 60  # 15 minutes (BKUP-02)


def _get_db_params() -> dict[str, str]:
    """Extract DB connection parameters from settings.

    Prefers individual postgres_* fields when set; falls back to parsing database_url.
    """
    settings = get_settings()

    # Use individual fields if they look non-default or meaningful
    # (They have defaults so we always use them directly)
    return {
        "host": settings.postgres_host,
        "port": str(settings.postgres_port),
        "user": settings.postgres_user,
        "password": settings.postgres_password,
        "dbname": settings.postgres_db,
    }


async def create_backup(backup_dir: str = DEFAULT_BACKUP_DIR) -> dict:
    """Run pg_dump and save a custom-format dump file.

    BKUP-01: Backup includes all data (archive, settings, audit events, telemetry).

    Returns:
        dict with keys: filename, created_at, size_bytes, backup_dir
    """
    params = _get_db_params()
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"recalium_{timestamp}.dump"
    filepath = Path(backup_dir) / filename

    env = os.environ.copy()
    env["PGPASSWORD"] = params["password"]

    proc = await asyncio.create_subprocess_exec(
        "pg_dump",
        "-Fc",
        "-h", params["host"],
        "-p", params["port"],
        "-U", params["user"],
        "-d", params["dbname"],
        "-f", str(filepath),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(
            f"pg_dump failed (exit {proc.returncode}): {stderr.decode().strip()}"
        )

    size_bytes = filepath.stat().st_size
    created_at = datetime.now(timezone.utc).isoformat()

    logger.info("Backup created: %s (%d bytes)", filename, size_bytes)
    return {
        "filename": filename,
        "created_at": created_at,
        "size_bytes": size_bytes,
        "backup_dir": backup_dir,
    }


async def list_backups(backup_dir: str = DEFAULT_BACKUP_DIR) -> list[dict]:
    """List all .dump backup files in backup_dir, newest first.

    Returns:
        list of dicts with keys: filename, created_at, size_bytes
    """
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return []

    backups = []
    for f in backup_path.glob("*.dump"):
        stat = f.stat()
        created_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        backups.append({
            "filename": f.name,
            "created_at": created_at,
            "size_bytes": stat.st_size,
        })

    # Sort newest first
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups


async def restore_backup(
    filename: str,
    backup_dir: str = DEFAULT_BACKUP_DIR,
) -> dict:
    """Restore a pg_dump custom-format file using pg_restore.

    BKUP-02: Restore completes within 15 minutes.
    BKUP-03: Recovers all data including audit events and configuration.

    Returns:
        dict with keys: filename, restored_at, status
    Raises:
        FileNotFoundError: if the backup file does not exist
        RuntimeError: if pg_restore fails or times out
    """
    filepath = Path(backup_dir) / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Backup file not found: {filepath}")

    params = _get_db_params()
    env = os.environ.copy()
    env["PGPASSWORD"] = params["password"]

    proc = await asyncio.create_subprocess_exec(
        "pg_restore",
        "--clean",
        "--if-exists",
        "-h", params["host"],
        "-p", params["port"],
        "-U", params["user"],
        "-d", params["dbname"],
        str(filepath),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=_RESTORE_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise RuntimeError(
            f"pg_restore timed out after {_RESTORE_TIMEOUT_SECONDS}s (BKUP-02 violation)"
        )

    if proc.returncode != 0:
        raise RuntimeError(
            f"pg_restore failed (exit {proc.returncode}): {stderr.decode().strip()}"
        )

    restored_at = datetime.now(timezone.utc).isoformat()
    logger.info("Restore complete from: %s", filename)
    return {
        "filename": filename,
        "restored_at": restored_at,
        "status": "success",
    }


async def delete_old_backups(
    backup_dir: str = DEFAULT_BACKUP_DIR,
    retention_days: int = 30,
) -> int:
    """Delete .dump backup files older than retention_days.

    BKUP-01: 30-day retention policy.

    Returns:
        Number of files deleted
    """
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted = 0

    for f in backup_path.glob("*.dump"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            f.unlink()
            logger.info("Deleted old backup: %s", f.name)
            deleted += 1

    return deleted


async def backup_predates_deletion(
    session: AsyncSession,
    backup_timestamp: datetime,
) -> bool:
    """Check if there are any deletion audit events AFTER the given backup timestamp.

    PRIV-03: UI flags backups that predate any deletion event, warning the user
    that restoring may re-introduce data that was intentionally deleted.

    Returns:
        True if there is at least one deletion event after backup_timestamp,
        False otherwise.
    """
    result = await session.execute(
        text(
            "SELECT 1 FROM audit_events "
            "WHERE event_type = 'archive_delete' "
            "AND occurred_at > :ts "
            "LIMIT 1"
        ),
        {"ts": backup_timestamp},
    )
    row = result.fetchone()
    return row is not None
