"""Deletion vs. processing concurrency (GPT5.6 #9).

The pipeline checks ``deleted_at`` when it loads a source, then makes slow external
calls, then writes derivations much later. A deletion in that window only suppresses
the rows that existed when it ran, so a derivation written afterwards would stay
``active`` and resurrect the removed content.

These tests exercise the end-of-pipeline reconcile (``suppress_new_derivations_if_deleted``)
deterministically: both orderings must converge on "all derivations suppressed".
"""
from __future__ import annotations

import hashlib
import uuid

import pytest
from sqlalchemy import select

from app.domain.archive.models import RawArchiveItem
from app.domain.archive.service import (
    cascade_delete_archive_item,
    suppress_new_derivations_if_deleted,
)
from app.domain.derived_memory.models import Fact

pytestmark = pytest.mark.asyncio


async def _make_item(session, content: str) -> RawArchiveItem:
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
    session.add(item)
    await session.commit()
    return item


def _active_fact(archive_id: uuid.UUID, text: str) -> Fact:
    return Fact(
        id=uuid.uuid4(),
        raw_archive_id=archive_id,
        fact_text=text,
        source_span=text,
        confidence_tier="high",
        derivation_method="llm_extraction",
        derivation_model="test-model",
    )


async def _active_fact_count(session, archive_id: uuid.UUID) -> int:
    rows = (
        await session.execute(
            select(Fact).where(
                Fact.raw_archive_id == archive_id,
                Fact.source_status == "active",
            )
        )
    ).scalars().all()
    return len(rows)


async def test_reconcile_suppresses_derivations_written_after_delete(db_session, tmp_path):
    """A derivation written AFTER a delete is suppressed by the reconcile."""
    item = await _make_item(db_session, "race-after-delete")

    # Delete first (no derivations exist yet to suppress).
    await cascade_delete_archive_item(db_session, item.id, backup_dir=str(tmp_path))

    # A mid-flight worker writes a derivation AFTER the delete committed.
    late = _active_fact(item.id, "late derivation")
    db_session.add(late)
    await db_session.commit()
    assert await _active_fact_count(db_session, item.id) == 1  # resurrection risk

    reconciled = await suppress_new_derivations_if_deleted(db_session, item.id)
    assert reconciled is True
    assert await _active_fact_count(db_session, item.id) == 0


async def test_reconcile_is_noop_when_source_not_deleted(db_session, tmp_path):
    """When the source is still live, the reconcile leaves active derivations alone."""
    item = await _make_item(db_session, "still-live")
    db_session.add(_active_fact(item.id, "legit derivation"))
    await db_session.commit()

    reconciled = await suppress_new_derivations_if_deleted(db_session, item.id)
    assert reconciled is False
    assert await _active_fact_count(db_session, item.id) == 1


async def test_delete_after_derivations_suppresses_them(db_session, tmp_path):
    """The reverse ordering: derivations written BEFORE the delete are suppressed by it."""
    item = await _make_item(db_session, "delete-after-derive")
    db_session.add(_active_fact(item.id, "early derivation"))
    await db_session.commit()
    assert await _active_fact_count(db_session, item.id) == 1

    await cascade_delete_archive_item(db_session, item.id, backup_dir=str(tmp_path))
    assert await _active_fact_count(db_session, item.id) == 0

    # And a post-delete reconcile is a harmless confirmation.
    reconciled = await suppress_new_derivations_if_deleted(db_session, item.id)
    assert reconciled is True
    assert await _active_fact_count(db_session, item.id) == 0
