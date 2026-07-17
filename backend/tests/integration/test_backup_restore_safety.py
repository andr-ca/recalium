"""End-to-end deletion / backup / restore safety (GPT5.6 #2, closure gate).

Proves the release gate: ingest a unique secret, delete it (crypto-erase +
tombstone), back up, prove the bytes are absent, restore both a pre- and a
post-deletion backup, reapply the tombstone, and prove the secret never becomes
retrievable again — plus path-traversal rejection and corrupted-archive rollback.

Uses real pg_dump/pg_restore. Guarded to only ever run against a ``*_test``
database so it can never wipe a developer's real data.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.archive.models import RawArchiveItem
from app.domain.archive.service import cascade_delete_archive_item
from app.domain.backup.service import _get_db_params, create_backup, restore_backup

pytestmark = pytest.mark.asyncio

SECRET = "SECRET-DELME-4b21-never-resurrect"

_HAS_PG_TOOLS = bool(shutil.which("pg_dump") and shutil.which("pg_restore"))


def _requires_test_db_and_tools():
    if not _HAS_PG_TOOLS:
        pytest.skip("pg_dump/pg_restore not available")
    dbname = _get_db_params()["dbname"]
    if not dbname.endswith("_test"):
        pytest.skip(
            f"refusing destructive backup/restore test against non-test DB {dbname!r}"
        )


def _db_url() -> str:
    return os.environ["DATABASE_URL"]


async def _count_secret() -> int:
    """Count rows anywhere in raw_archive still containing the secret (fresh conn)."""
    engine = create_async_engine(_db_url())
    try:
        async with async_sessionmaker(engine)() as s:
            row = await s.execute(
                text(
                    "SELECT count(*) FROM raw_archive WHERE raw_content LIKE :pat"
                ),
                {"pat": f"%{SECRET}%"},
            )
            return int(row.scalar_one())
    finally:
        await engine.dispose()


async def _seed_secret(backup_dir: str) -> uuid.UUID:
    content = f"User: my secret is {SECRET}\nAssistant: stored."
    item_id = uuid.uuid4()
    engine = create_async_engine(_db_url())
    try:
        async with async_sessionmaker(engine)() as s:
            s.add(
                RawArchiveItem(
                    id=item_id,
                    source_type="test",
                    raw_content=content,
                    content_hash=hashlib.sha256(content.encode()).hexdigest(),
                )
            )
            await s.commit()
    finally:
        await engine.dispose()
    return item_id


async def _delete(item_id: uuid.UUID, backup_dir: str) -> None:
    engine = create_async_engine(_db_url())
    try:
        async with async_sessionmaker(engine)() as s:
            await cascade_delete_archive_item(s, item_id, backup_dir=backup_dir)
    finally:
        await engine.dispose()


async def test_restore_rejects_path_traversal(tmp_path):
    """A filename escaping the backup directory is rejected before any DB action."""
    with pytest.raises(ValueError, match="outside"):
        await restore_backup("../../etc/passwd", backup_dir=str(tmp_path))
    with pytest.raises(ValueError, match="outside"):
        await restore_backup("/etc/passwd", backup_dir=str(tmp_path))


async def test_restore_rejects_corrupted_archive(tmp_path):
    """A corrupted (non-archive) file is rejected up front, leaving the DB untouched."""
    _requires_test_db_and_tools()
    corrupt = tmp_path / "corrupt.dump"
    corrupt.write_bytes(os.urandom(2048))
    with pytest.raises(RuntimeError, match="invalid or corrupted"):
        await restore_backup("corrupt.dump", backup_dir=str(tmp_path))


async def test_full_delete_backup_restore_lifecycle(tmp_path):
    """Full closure gate: secret is unrecoverable across pre/post-deletion restores."""
    _requires_test_db_and_tools()
    backup_dir = str(tmp_path)

    # 1. Ingest a unique secret.
    item_id = await _seed_secret(backup_dir)
    assert await _count_secret() == 1

    # 2. Pre-deletion backup B1 (still contains the secret).
    b1 = (await create_backup(backup_dir=backup_dir))["filename"]

    # 3. Delete → crypto-erase + tombstone (DB + external ledger).
    await _delete(item_id, backup_dir)
    assert await _count_secret() == 0, "secret bytes must be gone after deletion"

    # 4. Post-deletion backup B2 (must NOT contain the secret).
    b2 = (await create_backup(backup_dir=backup_dir))["filename"]
    b2_bytes = (tmp_path / b2).read_bytes()
    assert SECRET.encode() not in b2_bytes, "post-deletion backup leaked the secret"

    # 5. Restore the post-deletion backup — secret stays absent.
    res2 = await restore_backup(b2, backup_dir=backup_dir)
    assert res2["status"] == "success"
    assert await _count_secret() == 0

    # 6. Restore the PRE-deletion backup — the raw secret returns momentarily, but
    #    the tombstone reapply re-erases it so it never becomes retrievable.
    res1 = await restore_backup(b1, backup_dir=backup_dir)
    assert res1["status"] == "success"
    assert res1["tombstones_reapplied"] >= 1
    assert await _count_secret() == 0, "pre-deletion restore must reapply the tombstone"


async def test_corrupted_restore_leaves_data_intact(tmp_path):
    """Rollback safety: a rejected restore never damages the live database."""
    _requires_test_db_and_tools()
    backup_dir = str(tmp_path)

    # Seed a (non-secret) marker row and back it up.
    marker = f"keep-me-{uuid.uuid4().hex}"
    engine = create_async_engine(_db_url())
    try:
        async with async_sessionmaker(engine)() as s:
            s.add(
                RawArchiveItem(
                    id=uuid.uuid4(),
                    source_type="test",
                    raw_content=marker,
                    content_hash=hashlib.sha256(marker.encode()).hexdigest(),
                )
            )
            await s.commit()
    finally:
        await engine.dispose()

    # A corrupted archive must be rejected without touching the live row.
    corrupt = tmp_path / "broken.dump"
    corrupt.write_bytes(b"not a real pg_dump archive")
    with pytest.raises(RuntimeError):
        await restore_backup("broken.dump", backup_dir=backup_dir)

    engine = create_async_engine(_db_url())
    try:
        async with async_sessionmaker(engine)() as s:
            row = await s.execute(
                text("SELECT count(*) FROM raw_archive WHERE raw_content = :m"),
                {"m": marker},
            )
            assert int(row.scalar_one()) == 1, "live data must survive a rejected restore"
    finally:
        await engine.dispose()
