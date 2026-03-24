"""Tests for deletion cascade service.

PRIV-01: Cascade suppresses derived data immediately.
PRIV-02: Canonical memory retains source_removed marker + required_review status.

Uses pytest.importorskip so the file is skipped if the service doesn't exist yet.
Run: cd backend && uv run python3 -m pytest tests/domain/test_deletion_cascade.py -v
"""
from __future__ import annotations

import hashlib
import uuid

import pytest
pytest.importorskip("app.domain.archive.service")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.service import cascade_delete_archive_item, ArchiveItemNotFoundError
from app.domain.archive.models import RawArchiveItem
from app.domain.derived_memory.models import Summary, Fact, Embedding, FtsEntry
from app.domain.canonical_memory.models import CanonicalMemoryItem
from app.domain.audit.models import AuditEvent


def _make_archive(content: str = "Test content") -> RawArchiveItem:
    return RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )


@pytest.mark.asyncio
async def test_priv01_cascade_sets_deleted_at(db_session_phase4: AsyncSession):
    """PRIV-01: cascade sets deleted_at on raw_archive."""
    item = _make_archive()
    db_session_phase4.add(item)
    await db_session_phase4.flush()

    await cascade_delete_archive_item(db_session_phase4, item.id)

    # Service commits internally — use populate_existing to force ORM re-fetch from DB
    result = await db_session_phase4.execute(
        select(RawArchiveItem)
        .where(RawArchiveItem.id == item.id)
        .execution_options(populate_existing=True)
    )
    fetched = result.scalar_one()
    assert fetched.deleted_at is not None


@pytest.mark.asyncio
async def test_priv01_cascade_suppresses_summaries(db_session_phase4: AsyncSession):
    """PRIV-01: cascade marks summaries as source_removed."""
    item = _make_archive()
    db_session_phase4.add(item)
    await db_session_phase4.flush()

    summary = Summary(
        raw_archive_id=item.id,
        summary_text="A test summary.",
        model_used="gpt-4o-mini",
        derivation_method="llm_summarization",
    )
    db_session_phase4.add(summary)
    await db_session_phase4.flush()

    await cascade_delete_archive_item(db_session_phase4, item.id)

    result = await db_session_phase4.execute(
        select(Summary)
        .where(Summary.id == summary.id)
        .execution_options(populate_existing=True)
    )
    fetched = result.scalar_one()
    assert fetched.source_status == "source_removed"


@pytest.mark.asyncio
async def test_priv01_cascade_suppresses_facts(db_session_phase4: AsyncSession):
    """PRIV-01: cascade marks facts as source_removed."""
    item = _make_archive()
    db_session_phase4.add(item)
    await db_session_phase4.flush()

    fact = Fact(
        raw_archive_id=item.id,
        fact_text="Some fact.",
        source_span="Some fact.",
        confidence_tier="high",
        derivation_method="rule_based",
        derivation_model="local_rules_v1",
    )
    db_session_phase4.add(fact)
    await db_session_phase4.flush()

    await cascade_delete_archive_item(db_session_phase4, item.id)

    result = await db_session_phase4.execute(
        select(Fact)
        .where(Fact.id == fact.id)
        .execution_options(populate_existing=True)
    )
    fetched = result.scalar_one()
    assert fetched.source_status == "source_removed"


@pytest.mark.asyncio
async def test_priv01_cascade_suppresses_fts_entries(db_session_phase4: AsyncSession):
    """PRIV-01: cascade marks fts_entries as source_removed."""
    item = _make_archive()
    db_session_phase4.add(item)
    await db_session_phase4.flush()

    fts = FtsEntry(
        raw_archive_id=item.id,
        text_content="searchable text",
    )
    db_session_phase4.add(fts)
    await db_session_phase4.flush()

    await cascade_delete_archive_item(db_session_phase4, item.id)

    result = await db_session_phase4.execute(
        select(FtsEntry)
        .where(FtsEntry.id == fts.id)
        .execution_options(populate_existing=True)
    )
    fetched = result.scalar_one()
    assert fetched.source_status == "source_removed"


@pytest.mark.asyncio
async def test_priv02_canonical_marked_source_removed_not_deleted(db_session_phase4: AsyncSession):
    """PRIV-02: canonical memory from deleted source gets source_removed + required_review, NOT deleted."""
    item = _make_archive()
    db_session_phase4.add(item)
    await db_session_phase4.flush()

    canonical = CanonicalMemoryItem(
        raw_archive_id=item.id,
        content="Canonical fact about user.",
        status="active",
        promoted_from="fact",
        promoted_by="user_ui",
    )
    db_session_phase4.add(canonical)
    await db_session_phase4.flush()
    canonical_id = canonical.id

    await cascade_delete_archive_item(db_session_phase4, item.id)

    # Must still exist
    result = await db_session_phase4.execute(
        select(CanonicalMemoryItem)
        .where(CanonicalMemoryItem.id == canonical_id)
        .execution_options(populate_existing=True)
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None, "Canonical memory must NOT be deleted"
    assert fetched.source_status == "source_removed"
    assert fetched.status == "required_review"


@pytest.mark.asyncio
async def test_priv01_cascade_writes_audit_event(db_session_phase4: AsyncSession):
    """PRIV-01: cascade writes archive_delete audit event."""
    item = _make_archive()
    db_session_phase4.add(item)
    await db_session_phase4.flush()

    await cascade_delete_archive_item(db_session_phase4, item.id)

    result = await db_session_phase4.execute(
        select(AuditEvent).where(
            AuditEvent.event_type == "archive_delete",
            AuditEvent.raw_archive_id == item.id,
        )
    )
    event = result.scalar_one_or_none()
    assert event is not None
    assert event.actor == "user_ui"


@pytest.mark.asyncio
async def test_priv01_cascade_not_found_raises(db_session_phase4: AsyncSession):
    """PRIV-01: cascade raises ArchiveItemNotFoundError for non-existent item."""
    fake_id = uuid.uuid4()
    with pytest.raises(ArchiveItemNotFoundError):
        await cascade_delete_archive_item(db_session_phase4, fake_id)


@pytest.mark.asyncio
async def test_priv01_cascade_idempotent(db_session_phase4: AsyncSession):
    """PRIV-01: cascade on already-deleted item raises ArchiveItemNotFoundError (idempotent guard)."""
    item = _make_archive()
    db_session_phase4.add(item)
    await db_session_phase4.flush()

    await cascade_delete_archive_item(db_session_phase4, item.id)

    # Second call should raise
    with pytest.raises(ArchiveItemNotFoundError):
        await cascade_delete_archive_item(db_session_phase4, item.id)
