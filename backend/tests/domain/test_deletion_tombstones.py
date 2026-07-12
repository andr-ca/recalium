"""Deletion crypto-erase + tombstone ledger + restore reapply (GPT5.6 #2).

These are fast domain-level tests (no pg_dump). The full backup/restore E2E lives
in tests/integration/test_backup_restore_safety.py.
"""
from __future__ import annotations

import hashlib
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem, Tombstone
from app.domain.archive.service import (
    cascade_delete_archive_item,
    reapply_tombstones,
)
from app.domain.archive.tombstones import (
    REDACTION_MARKER,
    read_tombstone_ledger,
)
from app.domain.derived_memory.models import Fact, FtsEntry, Summary

SECRET = "SECRET-TOKEN-9f3a-unique-do-not-leak"


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def _seed_item_with_secret(session: AsyncSession) -> RawArchiveItem:
    content = f"User: please remember my api key {SECRET}\nAssistant: noted."
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content,
        content_hash=_hash(content),
    )
    session.add(item)
    await session.flush()
    session.add(
        Summary(
            raw_archive_id=item.id,
            summary_text=f"The user shared {SECRET}.",
            model_used="local",
            derivation_method="llm_summarization",
        )
    )
    session.add(
        Fact(
            raw_archive_id=item.id,
            fact_text=f"api key is {SECRET}",
            source_span=f"my api key {SECRET}",
            confidence_tier="high",
            derivation_method="rule_based",
            derivation_model="local_rules_v1",
        )
    )
    session.add(
        FtsEntry(raw_archive_id=item.id, text_content=f"api key {SECRET}")
    )
    await session.flush()
    return item


@pytest.mark.asyncio
async def test_deletion_erases_all_plaintext(db_session_phase4: AsyncSession, tmp_path):
    """Deletion crypto-erases raw + derived plaintext so the secret is gone."""
    item = await _seed_item_with_secret(db_session_phase4)

    await cascade_delete_archive_item(
        db_session_phase4, item.id, backup_dir=str(tmp_path)
    )

    raw = (
        await db_session_phase4.execute(
            select(RawArchiveItem)
            .where(RawArchiveItem.id == item.id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert raw.deleted_at is not None
    assert raw.raw_content == REDACTION_MARKER
    assert SECRET not in raw.raw_content

    summary = (
        await db_session_phase4.execute(
            select(Summary).where(Summary.raw_archive_id == item.id)
        )
    ).scalar_one()
    fact = (
        await db_session_phase4.execute(
            select(Fact).where(Fact.raw_archive_id == item.id)
        )
    ).scalar_one()
    fts = (
        await db_session_phase4.execute(
            select(FtsEntry).where(FtsEntry.raw_archive_id == item.id)
        )
    ).scalar_one()
    assert SECRET not in summary.summary_text
    assert SECRET not in fact.fact_text
    assert SECRET not in fact.source_span
    assert SECRET not in fts.text_content
    assert summary.source_status == "source_removed"
    assert fact.source_status == "source_removed"


@pytest.mark.asyncio
async def test_deletion_writes_db_tombstone_and_ledger(
    db_session_phase4: AsyncSession, tmp_path
):
    """Deletion records a DB tombstone and an external append-only ledger entry."""
    item = await _seed_item_with_secret(db_session_phase4)
    content_hash = item.content_hash

    await cascade_delete_archive_item(
        db_session_phase4, item.id, backup_dir=str(tmp_path)
    )

    tomb = (
        await db_session_phase4.execute(
            select(Tombstone).where(Tombstone.source_id == item.id)
        )
    ).scalar_one()
    assert tomb.content_hash == content_hash
    assert tomb.removal_type == "delete"

    ledger = read_tombstone_ledger(str(tmp_path))
    assert len(ledger) == 1
    assert ledger[0]["content_hash"] == content_hash
    assert ledger[0]["source_id"] == str(item.id)
    # The ledger stores only the one-way hash, never the plaintext.
    assert SECRET not in (tmp_path / "tombstones.ndjson").read_text()


@pytest.mark.asyncio
async def test_reapply_reerases_restored_predeletion_copy(
    db_session_phase4: AsyncSession, tmp_path
):
    """A restored pre-deletion copy (same content_hash) is re-suppressed by reapply."""
    # 1. Delete an item — writes a ledger entry.
    original = await _seed_item_with_secret(db_session_phase4)
    content_hash = original.content_hash
    await cascade_delete_archive_item(
        db_session_phase4, original.id, backup_dir=str(tmp_path)
    )

    # 2. Simulate restoring a pre-deletion backup: a fresh ACTIVE row reappears with
    #    the original content_hash and full plaintext, and no tombstone of its own.
    restored_content = f"User: please remember my api key {SECRET}\nAssistant: noted."
    restored = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=restored_content,
        content_hash=content_hash,
    )
    db_session_phase4.add(restored)
    await db_session_phase4.commit()

    # 3. Reapply tombstones from the ledger.
    summary = await reapply_tombstones(db_session_phase4, backup_dir=str(tmp_path))
    assert summary["reapplied"] == 1

    fetched = (
        await db_session_phase4.execute(
            select(RawArchiveItem)
            .where(RawArchiveItem.id == restored.id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert fetched.deleted_at is not None
    assert fetched.raw_content == REDACTION_MARKER
    assert SECRET not in fetched.raw_content


@pytest.mark.asyncio
async def test_reapply_is_idempotent(db_session_phase4: AsyncSession, tmp_path):
    """Reapplying with no un-suppressed matching rows is a no-op."""
    item = await _seed_item_with_secret(db_session_phase4)
    await cascade_delete_archive_item(
        db_session_phase4, item.id, backup_dir=str(tmp_path)
    )

    # The deleted row is already suppressed, so a reapply changes nothing.
    summary = await reapply_tombstones(db_session_phase4, backup_dir=str(tmp_path))
    assert summary["reapplied"] == 0
