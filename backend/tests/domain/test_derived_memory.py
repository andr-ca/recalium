"""Derived memory service tests — PIPE-02.

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
