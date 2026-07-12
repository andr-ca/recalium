"""SQL-level retrieval filters (GPT5.6 #4).

Filters must run inside the candidate SQL (before the per-mode LIMIT), and the
advertised source name ``chatgpt`` must match the stored ``chatgpt_import``.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

import pytest

from app.domain.archive.models import RawArchiveItem
from app.domain.derived_memory.service import write_fts_entry
from app.domain.retrieval.service import (
    RetrievalFilters,
    RetrievalRequest,
    invalidate_cache,
    retrieve,
)

pytestmark = pytest.mark.asyncio


async def _seed(session, *, source_type, data_class, ingested_at, token) -> RawArchiveItem:
    content = f"a conversation about {token} performance and tuning"
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type=source_type,
        raw_content=content,
        content_hash=hashlib.sha256(f"{token}{source_type}{data_class}".encode()).hexdigest(),
        metadata_json={"data_class": data_class},
        ingested_at=ingested_at,
    )
    session.add(item)
    await session.flush()
    await write_fts_entry(session, item.id, content)
    return item


_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


async def test_source_filter_matches_chatgpt_import_alias(db_session):
    """A 'chatgpt' filter must match imported 'chatgpt_import' rows and exclude claude."""
    invalidate_cache()
    token = "quantumzeta"
    await _seed(db_session, source_type="chatgpt_import", data_class="general", ingested_at=_NOW, token=token)
    await _seed(db_session, source_type="claude_import", data_class="general", ingested_at=_NOW, token=token)

    req = RetrievalRequest(
        query=token, mode="keyword", filters=RetrievalFilters(source_system="chatgpt")
    )
    resp = await retrieve(db_session, req)

    assert resp.items, "expected the chatgpt_import row to match the 'chatgpt' filter"
    assert all(i.source_system == "chatgpt_import" for i in resp.items)


async def test_category_filter_excludes_other_data_class(db_session):
    """The category filter (ignored before) restricts to the matching data_class."""
    invalidate_cache()
    token = "quantumtheta"
    general = await _seed(
        db_session, source_type="chatgpt_import", data_class="general", ingested_at=_NOW, token=token
    )
    personal = await _seed(
        db_session, source_type="chatgpt_import", data_class="personal_profile", ingested_at=_NOW, token=token
    )

    req = RetrievalRequest(
        query=token, mode="keyword", filters=RetrievalFilters(category="general")
    )
    resp = await retrieve(db_session, req)

    src_ids = {i.source_id for i in resp.items}
    assert str(general.id) in src_ids
    assert str(personal.id) not in src_ids


async def test_time_range_filter_applied_in_sql(db_session):
    """Items outside the requested time range are excluded."""
    invalidate_cache()
    token = "quantumiota"
    old = await _seed(
        db_session, source_type="chatgpt_import", data_class="general",
        ingested_at=datetime(2020, 1, 1, tzinfo=timezone.utc), token=token,
    )
    recent = await _seed(
        db_session, source_type="chatgpt_import", data_class="general",
        ingested_at=datetime(2026, 6, 1, tzinfo=timezone.utc), token=token,
    )

    req = RetrievalRequest(
        query=token, mode="keyword",
        filters=RetrievalFilters(time_range_start="2025-01-01T00:00:00+00:00"),
    )
    resp = await retrieve(db_session, req)

    src_ids = {i.source_id for i in resp.items}
    assert str(recent.id) in src_ids
    assert str(old.id) not in src_ids


async def test_direct_fact_retrieval_matches_fact_text(db_session):
    """GPT5.6 #4: a fact is retrievable directly by its own text, not only via links."""
    from app.domain.derived_memory.models import Fact

    invalidate_cache()
    content = "a source conversation"
    archive = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content,
        content_hash=hashlib.sha256(b"direct-fact-source").hexdigest(),
        ingested_at=_NOW,
    )
    db_session.add(archive)
    await db_session.flush()
    fact = Fact(
        id=uuid.uuid4(),
        raw_archive_id=archive.id,
        fact_text="The user deploys services on zephyrium clusters.",
        source_span="zephyrium clusters",
        confidence_tier="high",
        derivation_method="llm_extraction",
        derivation_model="test-model",
    )
    db_session.add(fact)
    await db_session.commit()  # Computed search_vector populates on write.

    req = RetrievalRequest(query="zephyrium", mode="keyword")
    resp = await retrieve(db_session, req)

    fact_items = [i for i in resp.items if i.type == "fact"]
    assert str(fact.id) in {i.id for i in fact_items}
    assert any("zephyrium" in i.content.lower() for i in fact_items)

