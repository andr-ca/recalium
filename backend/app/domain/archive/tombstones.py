"""Deletion tombstone ledger (GPT5.6 #2; deletion-and-tombstones.md).

Deletions are made durable in two places so removed content cannot silently
reappear after a restore, reindex, or import:

1. A ``tombstones`` table inside the database (queryable, shown in the UI, and
   included in backups).
2. An **append-only NDJSON ledger file that lives outside the database dump**.
   Restoring a backup that was taken *before* a deletion would otherwise bring the
   removed content back; because this ledger is not part of ``pg_dump``, it
   survives the restore and is *reapplied* afterwards to re-suppress the content.

The reapply step matches restored rows by ``content_hash`` and re-runs the same
crypto-erase + suppression the original deletion performed, so the secret never
becomes retrievable again regardless of which backup was restored.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Written over erased plaintext columns. Crypto-erase style: the original content
# bytes are gone, but the row structure remains for audit/provenance continuity.
REDACTION_MARKER = "[redacted:deleted]"

# Append-only ledger file, stored in the backup directory but never included in a
# pg_dump, so it outlives the restore of an older (pre-deletion) backup.
TOMBSTONE_LEDGER_FILENAME = "tombstones.ndjson"

# Canonical default backup directory (host-mounted in the container). Defined here
# so both the archive (deletion) and backup (restore) services can share it without
# an import cycle.
DEFAULT_BACKUP_DIR = "/backups"


def ledger_path(backup_dir: str) -> Path:
    return Path(backup_dir) / TOMBSTONE_LEDGER_FILENAME


def append_tombstone_ledger(record: dict, backup_dir: str) -> bool:
    """Append one tombstone record to the external append-only ledger.

    Best-effort: returns True on success, False (with an error log) on failure so a
    deletion is never blocked by a ledger-write problem. The in-database tombstone
    is the primary record; this file is the cross-restore safety net.
    """
    try:
        path = ledger_path(backup_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, sort_keys=True, default=str) + "\n"
        # O_APPEND makes concurrent small writes atomic; 0600 keeps the ledger private.
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        return True
    except OSError as exc:
        logger.error(
            "Failed to append deletion tombstone to external ledger %s: %s. "
            "Restoring a pre-deletion backup may resurrect this content until the "
            "ledger is writable.",
            backup_dir,
            exc,
        )
        return False


def read_tombstone_ledger(backup_dir: str) -> list[dict]:
    """Read all tombstone records from the external ledger (empty list if absent)."""
    path = ledger_path(backup_dir)
    if not path.exists():
        return []
    records: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError:
            logger.warning("Skipping malformed tombstone ledger line: %r", raw[:120])
    return records
