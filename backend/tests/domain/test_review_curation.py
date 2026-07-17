"""Conflict-queue curation domain effects (GPT5.6 #10).

Detected conflicts must surface in the review queue, and resolving/dismissing must
have a real effect on the involved facts (keep vs. suppress), not just flip a status.
"""
from __future__ import annotations

import hashlib
import uuid

import pytest

from app.domain.archive.models import RawArchiveItem
from app.domain.conflict_detection import detect_and_group_duplicates
from app.domain.derived_memory.models import ConflictGroup, Embedding, Fact
from app.domain.review_queue.service import (
    InvalidResolutionActionError,
    dismiss_review_item,
    list_pending_review_items,
    materialize_review_item,
    resolve_review_item,
)

pytestmark = pytest.mark.asyncio

_EMBED_MODEL = "all-MiniLM-L6-v2"


async def _archive(session, token: str) -> RawArchiveItem:
    content = f"conflict source {token} {uuid.uuid4()}"
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
    session.add(item)
    await session.flush()
    return item


async def _group_with_facts(session, confidences: list[str]):
    group = ConflictGroup(id=uuid.uuid4(), group_type="duplicate")
    session.add(group)
    await session.flush()
    facts = []
    for i, conf in enumerate(confidences):
        arch = await _archive(session, f"g{i}")
        fact = Fact(
            id=uuid.uuid4(),
            raw_archive_id=arch.id,
            fact_text=f"duplicate fact {i}",
            source_span="span",
            confidence_tier=conf,
            derivation_method="llm_extraction",
            derivation_model="test-model",
            conflict_group_id=group.id,
        )
        session.add(fact)
        facts.append(fact)
    await session.flush()
    item = await materialize_review_item(session, group.id, "duplicate")
    await session.commit()
    return group, facts, item


async def test_detection_materializes_review_item(db_session):
    """A detected duplicate must produce a pending review item (was never queued)."""
    vec = [0.1] * 384
    archives = []
    emb_ids = {}
    for i in range(2):
        arch = await _archive(db_session, f"dup{i}")
        db_session.add(
            Fact(
                id=uuid.uuid4(),
                raw_archive_id=arch.id,
                fact_text=f"fact {i}",
                source_span="span",
                confidence_tier="high",
                derivation_method="llm_extraction",
                derivation_model="test-model",
            )
        )
        emb = Embedding(
            id=uuid.uuid4(), raw_archive_id=arch.id, embedding=vec, embedding_model=_EMBED_MODEL
        )
        db_session.add(emb)
        await db_session.flush()
        archives.append(arch.id)
        emb_ids[arch.id] = emb.id
    await db_session.commit()

    detection = await detect_and_group_duplicates(
        db_session, raw_archive_id=archives[0], embedding_id=emb_ids[archives[0]], embedding=vec
    )
    assert detection is not None

    pending = await list_pending_review_items(db_session)
    assert any(p.conflict_group_id == detection.group.id for p in pending)


async def test_resolve_suppress_keeps_best_and_suppresses_rest(db_session):
    """action='suppress' keeps the highest-confidence fact and removes the duplicates."""
    _group, facts, item = await _group_with_facts(db_session, ["low", "high"])

    await resolve_review_item(
        db_session, item.id, resolution_note="dupes", resolved_by="u", action="suppress"
    )
    await db_session.commit()

    for f in facts:
        await db_session.refresh(f)
    active = [f for f in facts if f.source_status == "active"]
    removed = [f for f in facts if f.source_status == "source_removed"]
    assert len(active) == 1 and active[0].confidence_tier == "high"
    assert len(removed) == 1
    assert active[0].conflict_group_id is None


async def test_dismiss_keeps_all_and_clears_conflict_flag(db_session):
    """Dismiss means 'not real duplicates': facts stay active, no longer grouped."""
    _group, facts, item = await _group_with_facts(db_session, ["high", "medium"])

    await dismiss_review_item(db_session, item.id)
    await db_session.commit()

    for f in facts:
        await db_session.refresh(f)
    assert all(f.source_status == "active" for f in facts)
    assert all(f.conflict_group_id is None for f in facts)


async def test_resolve_rejects_unknown_action(db_session):
    _group, _facts, item = await _group_with_facts(db_session, ["high"])
    with pytest.raises(InvalidResolutionActionError):
        await resolve_review_item(
            db_session, item.id, resolution_note="", resolved_by="u", action="frobnicate"
        )
