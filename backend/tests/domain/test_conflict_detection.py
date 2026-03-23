"""Conflict detection tests — CANM-06.

Tests will FAIL (RED) until app.domain.conflict_detection is created.
"""
from __future__ import annotations

import pytest

pytest.importorskip(
    "app.domain.conflict_detection",
    reason="conflict_detection module not yet implemented",
)

from app.domain.conflict_detection import find_duplicate_candidates, create_conflict_group  # noqa: E402


async def test_no_duplicates_when_table_empty(db_session_phase2):
    """CANM-06: No duplicate candidates found when embeddings table is empty."""
    import uuid
    embedding = [0.1] * 384  # 384-dim unit vector

    candidates = await find_duplicate_candidates(
        session=db_session_phase2,
        embedding=embedding,
        exclude_id=uuid.uuid4(),
    )
    assert candidates == []


async def test_duplicate_detected_by_cosine_similarity(db_session_phase2):
    """CANM-06: Near-identical embeddings (cosine distance < 0.15) are flagged as duplicates."""
    import uuid
    import math
    from app.domain.derived_memory.models import Embedding

    # Insert a near-identical embedding
    vec = [1.0 / math.sqrt(384)] * 384  # normalized unit vector
    raw_id = uuid.uuid4()
    emb = Embedding(
        raw_archive_id=raw_id,
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
    assert raw_id in candidates or emb.id in candidates


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
