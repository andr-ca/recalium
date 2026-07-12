"""Conflict detection tests — CANM-06.

Tests will FAIL (RED) until app.domain.conflict_detection is created.
"""
from __future__ import annotations

import hashlib
import math
import uuid

import pytest

pytest.importorskip(
    "app.domain.conflict_detection",
    reason="conflict_detection module not yet implemented",
)

from app.domain.conflict_detection import find_duplicate_candidates, create_conflict_group  # noqa: E402



async def _make_archive_item(session):
    """Helper: insert a minimal RawArchiveItem to satisfy FK constraint on embeddings."""
    from app.domain.archive.models import RawArchiveItem
    content = "test content for conflict detection"
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
    session.add(item)
    await session.flush()
    return item


async def test_no_duplicates_when_table_empty(db_session_phase2):
    """CANM-06: No duplicate candidates found when embeddings table is empty."""
    embedding = [0.1] * 384  # 384-dim unit vector

    candidates = await find_duplicate_candidates(
        session=db_session_phase2,
        embedding=embedding,
        exclude_id=uuid.uuid4(),
    )
    assert candidates == []


async def test_duplicate_detected_by_cosine_similarity(db_session_phase2):
    """CANM-06: Near-identical embeddings (cosine distance < 0.15) are flagged as duplicates."""
    from app.domain.derived_memory.models import Embedding

    # Insert a parent archive item first (FK requirement)
    archive_item = await _make_archive_item(db_session_phase2)

    # Insert a near-identical embedding
    vec = [1.0 / math.sqrt(384)] * 384  # normalized unit vector
    emb = Embedding(
        raw_archive_id=archive_item.id,
        embedding=vec,
        embedding_model="all-MiniLM-L6-v2",
    )
    db_session_phase2.add(emb)
    await db_session_phase2.commit()

    # Query with the same vector — should find it as near-duplicate
    candidates = await find_duplicate_candidates(
        session=db_session_phase2,
        embedding=vec,
        exclude_id=uuid.uuid4(),  # different ID
    )
    assert emb.id in candidates


async def test_conflict_group_created_for_duplicates(db_session_phase2):
    """CANM-06: create_conflict_group materializes a conflict_groups row linking fact IDs."""
    import uuid
    from app.domain.derived_memory.models import ConflictGroup

    fact_ids = [uuid.uuid4(), uuid.uuid4()]
    group = await create_conflict_group(
        session=db_session_phase2,
        fact_ids=fact_ids,
        group_type="duplicate",
    )

    assert group is not None
    assert group.group_type == "duplicate"
    assert group.resolved_at is None


def _one_hot(index: int) -> list[float]:
    """A normalized 384-dim one-hot vector — orthogonal to other tests' vectors."""
    vec = [0.0] * 384
    vec[index] = 1.0
    return vec


async def _make_fact(session, archive_id, text_value: str):
    from app.domain.derived_memory.models import Fact
    fact = Fact(
        id=uuid.uuid4(),
        raw_archive_id=archive_id,
        fact_text=text_value,
        source_span=text_value,
        confidence_tier="high",
        derivation_method="rule_based",
        derivation_model="local_rules_v1",
    )
    session.add(fact)
    await session.flush()
    return fact


async def _make_embedding(session, archive_id, vec):
    from app.domain.derived_memory.models import Embedding
    emb = Embedding(
        id=uuid.uuid4(),
        raw_archive_id=archive_id,
        embedding=vec,
        embedding_model="all-MiniLM-L6-v2",
    )
    session.add(emb)
    await session.commit()
    await session.refresh(emb)
    return emb


async def test_link_facts_to_group_links_active_ungrouped_facts(db_session_phase2):
    """GPT5.6 #10: facts of involved items are assigned to the conflict group."""
    from app.domain.conflict_detection import create_conflict_group, link_facts_to_group

    item = await _make_archive_item(db_session_phase2)
    f1 = await _make_fact(db_session_phase2, item.id, "alpha")
    f2 = await _make_fact(db_session_phase2, item.id, "beta")
    await db_session_phase2.commit()

    group = await create_conflict_group(db_session_phase2, group_type="duplicate")
    linked = await link_facts_to_group(db_session_phase2, group.id, [item.id])

    assert linked == 2
    await db_session_phase2.refresh(f1)
    await db_session_phase2.refresh(f2)
    assert f1.conflict_group_id == group.id
    assert f2.conflict_group_id == group.id
    # Idempotent: already-grouped facts are not relinked.
    assert await link_facts_to_group(db_session_phase2, group.id, [item.id]) == 0


async def test_detect_and_group_duplicates_links_both_items_facts(db_session_phase2):
    """GPT5.6 #10: a near-duplicate creates a group AND links both items' facts."""
    from app.domain.conflict_detection import detect_and_group_duplicates

    vec = _one_hot(5)
    item_a = await _make_archive_item(db_session_phase2)
    item_b = await _make_archive_item(db_session_phase2)
    await _make_embedding(db_session_phase2, item_a.id, vec)
    emb_b = await _make_embedding(db_session_phase2, item_b.id, vec)  # identical → duplicate
    fact_a = await _make_fact(db_session_phase2, item_a.id, "a")
    fact_b = await _make_fact(db_session_phase2, item_b.id, "b")
    await db_session_phase2.commit()

    detection = await detect_and_group_duplicates(
        db_session_phase2,
        raw_archive_id=item_b.id,
        embedding_id=emb_b.id,
        embedding=vec,
    )

    assert detection is not None
    assert item_a.id in detection.duplicate_archive_ids
    assert detection.linked_fact_count >= 2
    await db_session_phase2.refresh(fact_a)
    await db_session_phase2.refresh(fact_b)
    assert fact_a.conflict_group_id == detection.group.id
    assert fact_b.conflict_group_id == detection.group.id


async def test_detect_and_group_duplicates_none_when_unique(db_session_phase2):
    """GPT5.6 #10: a unique embedding produces no conflict group."""
    from app.domain.conflict_detection import detect_and_group_duplicates

    vec = _one_hot(0)  # orthogonal to every other test vector
    item = await _make_archive_item(db_session_phase2)
    emb = await _make_embedding(db_session_phase2, item.id, vec)
    await db_session_phase2.commit()

    detection = await detect_and_group_duplicates(
        db_session_phase2,
        raw_archive_id=item.id,
        embedding_id=emb.id,
        embedding=vec,
    )
    assert detection is None
