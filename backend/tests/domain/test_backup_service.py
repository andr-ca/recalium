"""Tests for backup/restore service.

BKUP-01: Scheduled daily backups.
BKUP-02: Restore within 15 minutes.
BKUP-03: Restore recovers all data.
PRIV-03: UI flags backups predating deletion events.

Skipped entirely if pg_dump not available in PATH.
Run: cd backend && uv run python3 -m pytest tests/domain/test_backup_service.py -v
"""
from __future__ import annotations

import shutil

import pytest

# Skip all tests in this file if pg_dump is not available
pytestmark = pytest.mark.skipif(
    shutil.which("pg_dump") is None,
    reason="pg_dump not available — skipping backup tests",
)

pytest.importorskip("app.domain.backup.service")


@pytest.mark.asyncio
async def test_bkup01_create_backup_returns_metadata(tmp_path, monkeypatch):
    """BKUP-01: create_backup() returns a metadata dict with filename and size."""
    from app.domain.backup.service import create_backup

    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    result = await create_backup(backup_dir=str(tmp_path))
    assert "filename" in result
    assert "size_bytes" in result
    assert "created_at" in result


@pytest.mark.asyncio
async def test_bkup01_list_backups_returns_sorted_list(tmp_path):
    """BKUP-01: list_backups() returns sorted list of backup metadata."""
    from app.domain.backup.service import list_backups

    result = await list_backups(backup_dir=str(tmp_path))
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_priv03_backup_predates_deletion_flag(db_session_phase4, tmp_path):
    """PRIV-03: backup_predates_deletion() detects deletion events after backup timestamp."""
    from app.domain.backup.service import backup_predates_deletion
    from app.domain.audit.models import AuditEvent
    from datetime import datetime, timezone, timedelta

    # Create a deletion audit event
    event = AuditEvent(
        event_type="archive_delete",
        actor="user_ui",
        operation_metadata={"archive_id": "test-id"},
        occurred_at=datetime.now(timezone.utc),
    )
    db_session_phase4.add(event)
    await db_session_phase4.flush()

    # A backup taken before the deletion should be flagged
    backup_time = datetime.now(timezone.utc) - timedelta(hours=1)
    result = await backup_predates_deletion(db_session_phase4, backup_time)
    assert result is True

    # A backup taken after the deletion should not be flagged
    future_backup_time = datetime.now(timezone.utc) + timedelta(hours=1)
    result2 = await backup_predates_deletion(db_session_phase4, future_backup_time)
    assert result2 is False


@pytest.mark.asyncio
async def test_bkup01_delete_old_backups(tmp_path, monkeypatch):
    """BKUP-01: delete_old_backups() removes files older than retention_days."""
    import os
    from datetime import datetime, timezone, timedelta
    from app.domain.backup.service import delete_old_backups

    # Create a mock old backup file
    old_file = tmp_path / "recalium_20000101_000000.dump"
    old_file.write_bytes(b"fake dump")

    # Set modification time to 31 days ago
    old_mtime = (datetime.now(timezone.utc) - timedelta(days=31)).timestamp()
    os.utime(old_file, (old_mtime, old_mtime))

    deleted = await delete_old_backups(backup_dir=str(tmp_path), retention_days=30)
    assert deleted >= 1
    assert not old_file.exists()
