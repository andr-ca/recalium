"""Derived memory service tests — PIPE-02, PIPE-01.

Tests will FAIL (RED) until app.domain.derived_memory.service is created.
"""
from __future__ import annotations

import uuid

import pytest

pytest.importorskip("app.domain.derived_memory.service", reason="derived_memory.service not yet implemented")

from app.domain.derived_memory.service import write_facts  # noqa: E402


async def _make_archive_item(session):
    """Helper: insert a minimal RawArchiveItem to satisfy FK constraint on derived memory tables."""
    import hashlib
    from app.domain.archive.models import RawArchiveItem
    content = "test content for derived memory"
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
    session.add(item)
    await session.flush()
    return item


async def test_embedding_model_health_reports_stale(db_session_phase2):
    """GPT5.6 #21: health report counts embeddings by model and flags stale rows."""
    import math

    from sqlalchemy import delete

    from app.domain.archive.models import RawArchiveItem
    from app.domain.derived_memory.models import Embedding
    from app.domain.derived_memory.service import (
        ACTIVE_EMBEDDING_MODEL,
        embedding_model_health,
    )

    item_active = await _make_archive_item(db_session_phase2)
    item_stale = await _make_archive_item(db_session_phase2)
    vec = [1.0 / math.sqrt(384)] * 384
    emb_active = Embedding(
        id=uuid.uuid4(),
        raw_archive_id=item_active.id,
        embedding=vec,
        embedding_model=ACTIVE_EMBEDDING_MODEL,
    )
    emb_stale = Embedding(
        id=uuid.uuid4(),
        raw_archive_id=item_stale.id,
        embedding=vec,
        embedding_model="old-model-v0",
    )
    db_session_phase2.add_all([emb_active, emb_stale])
    await db_session_phase2.commit()

    try:
        health = await embedding_model_health(db_session_phase2)
        assert health["active_model"] == ACTIVE_EMBEDDING_MODEL
        assert health["models"].get("old-model-v0", 0) >= 1
        assert health["stale_count"] >= 1
        assert health["active_model_count"] >= 1
    finally:
        # Do not leak committed rows into sibling tests (worker/conflict suites).
        await db_session_phase2.execute(
            delete(Embedding).where(Embedding.id.in_([emb_active.id, emb_stale.id]))
        )
        await db_session_phase2.execute(
            delete(RawArchiveItem).where(
                RawArchiveItem.id.in_([item_active.id, item_stale.id])
            )
        )
        await db_session_phase2.commit()


async def test_fact_requires_source_span(db_session_phase2):
    """PIPE-02: Fact with empty source_span is stored with confidence_tier='low'."""
    archive_item = await _make_archive_item(db_session_phase2)

    facts = await write_facts(
        session=db_session_phase2,
        raw_archive_id=archive_item.id,
        facts_data=[
            {
                "fact_text": "User is a software engineer",
                "source_span": "",  # empty — invalid
                "confidence_tier": "high",  # must be downgraded to 'low'
                "derivation_method": "llm_extraction",
                "derivation_model": "gpt-4o-mini",
            }
        ],
    )

    assert len(facts) == 1
    assert facts[0].confidence_tier == "low"
    assert facts[0].source_span == ""  # stored as-is; confidence downgraded


async def test_fact_all_required_fields_present(db_session_phase2):
    """PIPE-02: Fact written with all required provenance fields populated."""
    archive_item = await _make_archive_item(db_session_phase2)

    facts = await write_facts(
        session=db_session_phase2,
        raw_archive_id=archive_item.id,
        facts_data=[
            {
                "fact_text": "User is based in Berlin",
                "source_span": "I live in Berlin",
                "confidence_tier": "high",
                "derivation_method": "llm_extraction",
                "derivation_model": "gpt-4o-mini",
            }
        ],
    )

    assert len(facts) == 1
    f = facts[0]
    assert f.fact_text == "User is based in Berlin"
    assert f.source_span == "I live in Berlin"
    assert f.confidence_tier == "high"
    assert f.derivation_method == "llm_extraction"
    assert f.derivation_model == "gpt-4o-mini"
    assert f.source_status == "active"


async def test_fact_source_status_defaults_to_active(db_session_phase2):
    """Derived memory service: new facts default to source_status='active'."""
    archive_item = await _make_archive_item(db_session_phase2)
    facts = await write_facts(
        session=db_session_phase2,
        raw_archive_id=archive_item.id,
        facts_data=[
            {
                "fact_text": "Test fact",
                "source_span": "test",
                "confidence_tier": "medium",
                "derivation_method": "rule_based",
                "derivation_model": "local_rules_v1",
            }
        ],
    )
    assert facts[0].source_status == "active"


# ── Embedding tests (PIPE-01: local sentence-transformers) ────────────────────

async def test_embed_text_returns_384_dim_vector():
    """PIPE-01: embed_text returns 384-dim float list from all-MiniLM-L6-v2."""
    pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed (EMBED_BACKEND=none)")
    from app.domain.derived_memory.service import embed_text
    vector = await embed_text("Hello, world! This is a test sentence.")
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert all(isinstance(v, float) for v in vector)


async def test_embed_text_normalized():
    """PIPE-01: embed_text returns L2-normalized vector (norm ≈ 1.0)."""
    pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed (EMBED_BACKEND=none)")
    import math
    from app.domain.derived_memory.service import embed_text
    vector = await embed_text("Recalium is a personal memory platform.")
    norm = math.sqrt(sum(v * v for v in vector))
    assert abs(norm - 1.0) < 0.01  # normalized within 1% tolerance


async def test_write_embedding_stores_vector(db_session_phase2):
    """PIPE-01: write_embedding writes Embedding row with correct model name and source_status."""
    from app.domain.derived_memory.service import write_embedding

    archive_item = await _make_archive_item(db_session_phase2)
    vector = [0.1] * 384  # 384-dim placeholder vector

    embedding = await write_embedding(
        session=db_session_phase2,
        raw_archive_id=archive_item.id,
        vector=vector,
    )

    assert embedding.raw_archive_id == archive_item.id
    assert embedding.embedding_model == "all-MiniLM-L6-v2"
    assert embedding.source_status == "active"
    assert len(embedding.embedding) == 384


async def test_get_existing_embedding_returns_none_when_absent(db_session_phase2):
    """BYOK-08: get_existing_embedding returns None when no embedding exists."""
    from app.domain.derived_memory.service import get_existing_embedding

    result = await get_existing_embedding(db_session_phase2, uuid.uuid4())
    assert result is None


async def test_get_existing_embedding_returns_embedding_when_present(db_session_phase2):
    """BYOK-08: get_existing_embedding returns existing active embedding."""
    from app.domain.derived_memory.service import write_embedding, get_existing_embedding

    archive_item = await _make_archive_item(db_session_phase2)
    vector = [0.2] * 384

    await write_embedding(
        session=db_session_phase2,
        raw_archive_id=archive_item.id,
        vector=vector,
    )

    result = await get_existing_embedding(db_session_phase2, archive_item.id)
    assert result is not None
    assert result.raw_archive_id == archive_item.id
    assert result.source_status == "active"
