"""Facts API route tests."""
from __future__ import annotations

import hashlib
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.models import AuditEvent
from app.domain.archive.models import RawArchiveItem
from app.domain.derived_memory.models import Fact


async def _create_fact(db_session: AsyncSession, *, fact_text: str = "Recalium stores source-backed facts.") -> Fact:
    content = "A conversation that states Recalium stores source-backed facts for later review."
    archive_item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        source_name="facts-api-lifecycle-test",
        raw_content=content,
        content_hash=hashlib.sha256(f"{content}-{uuid.uuid4()}".encode()).hexdigest(),
        conversation_count=1,
    )
    db_session.add(archive_item)
    await db_session.flush()

    fact = Fact(
        id=uuid.uuid4(),
        raw_archive_id=archive_item.id,
        fact_text=fact_text,
        source_span="Recalium stores source-backed facts",
        confidence_tier="medium",
        derivation_method="llm_extraction",
        derivation_model="test-model",
        source_status="active",
    )
    db_session.add(fact)
    await db_session.flush()
    return fact


@pytest.mark.asyncio
async def test_list_facts_returns_active_facts(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /api/facts returns active facts with frontend-compatible fields."""
    content = "A conversation that states Recalium uses MCP for memory retrieval."
    archive_item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        source_name="facts-api-test",
        raw_content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        conversation_count=1,
    )
    db_session.add(archive_item)
    await db_session.flush()

    active_fact = Fact(
        id=uuid.uuid4(),
        raw_archive_id=archive_item.id,
        fact_text="Recalium uses MCP for memory retrieval.",
        source_span="Recalium uses MCP for memory retrieval",
        confidence_tier="high",
        derivation_method="llm_extraction",
        derivation_model="test-model",
        source_status="active",
    )
    removed_fact = Fact(
        id=uuid.uuid4(),
        raw_archive_id=archive_item.id,
        fact_text="Removed facts must not appear in active fact lists.",
        source_span="removed",
        confidence_tier="low",
        derivation_method="llm_extraction",
        derivation_model="test-model",
        source_status="source_removed",
    )
    db_session.add_all([active_fact, removed_fact])
    await db_session.flush()

    resp = await client.get("/api/facts/?limit=50")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["count"] == 1
    assert len(data["facts"]) == 1
    item = data["facts"][0]
    assert item["id"] == str(active_fact.id)
    assert item["raw_archive_id"] == str(archive_item.id)
    assert item["fact_text"] == active_fact.fact_text
    assert item["source_span"] == active_fact.source_span
    assert item["confidence_tier"] == "high"
    assert item["derivation_method"] == "llm_extraction"
    assert item["derivation_model"] == "test-model"
    assert item["conflict_group_id"] is None
    assert item["source_status"] == "active"
    assert item["review_status"] == "active"
    assert "created_at" in item


@pytest.mark.asyncio
async def test_update_fact_edits_review_fields_and_audits(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fact = await _create_fact(db_session)

    resp = await client.patch(
        f"/api/facts/{fact.id}",
        json={
            "fact_text": "Recalium stores source-backed facts with user corrections.",
            "source_span": "source-backed facts",
            "confidence_tier": "high",
            "actor": "tester",
        },
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(fact.id)
    assert data["fact_text"] == "Recalium stores source-backed facts with user corrections."
    assert data["source_span"] == "source-backed facts"
    assert data["confidence_tier"] == "high"
    assert data["review_status"] == "active"

    audit_rows = (
        await db_session.execute(
            AuditEvent.__table__.select().where(AuditEvent.event_type == "fact_updated")
        )
    ).all()
    assert len(audit_rows) == 1
    audit = audit_rows[0]._mapping
    assert audit["actor"] == "tester"
    assert audit["raw_archive_id"] == fact.raw_archive_id
    assert audit["operation_metadata"]["fact_id"] == str(fact.id)
    assert "fact_text" in audit["operation_metadata"]["updated_fields"]


@pytest.mark.asyncio
async def test_mark_fact_disputed_and_stale(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    disputed_fact = await _create_fact(db_session, fact_text="A fact that needs dispute review.")
    stale_fact = await _create_fact(db_session, fact_text="A fact that is now stale.")

    dispute_resp = await client.post(f"/api/facts/{disputed_fact.id}/dispute", json={"actor": "tester"})
    stale_resp = await client.post(f"/api/facts/{stale_fact.id}/mark-stale", json={"actor": "tester"})

    assert dispute_resp.status_code == 200, dispute_resp.text
    assert stale_resp.status_code == 200, stale_resp.text
    assert dispute_resp.json()["review_status"] == "disputed"
    assert stale_resp.json()["review_status"] == "stale"

    list_resp = await client.get("/api/facts/")
    assert list_resp.status_code == 200
    listed_statuses = {item["id"]: item["review_status"] for item in list_resp.json()["facts"]}
    assert listed_statuses[str(disputed_fact.id)] == "disputed"
    assert listed_statuses[str(stale_fact.id)] == "stale"


@pytest.mark.asyncio
async def test_archive_and_delete_fact_hide_from_default_list(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    archived_fact = await _create_fact(db_session, fact_text="A fact to archive.")
    deleted_fact = await _create_fact(db_session, fact_text="A fact to delete.")

    archive_resp = await client.post(f"/api/facts/{archived_fact.id}/archive", json={"actor": "tester"})
    delete_resp = await client.delete(f"/api/facts/{deleted_fact.id}", params={"actor": "tester"})

    assert archive_resp.status_code == 200, archive_resp.text
    assert archive_resp.json()["review_status"] == "archived"
    assert delete_resp.status_code == 204, delete_resp.text

    list_resp = await client.get("/api/facts/")
    assert list_resp.status_code == 200
    listed_ids = {item["id"] for item in list_resp.json()["facts"]}
    assert str(archived_fact.id) not in listed_ids
    assert str(deleted_fact.id) not in listed_ids

    all_resp = await client.get("/api/facts/", params={"review_status": "all"})
    assert all_resp.status_code == 200
    all_statuses = {item["id"]: item["review_status"] for item in all_resp.json()["facts"]}
    assert all_statuses[str(archived_fact.id)] == "archived"
    assert all_statuses[str(deleted_fact.id)] == "deleted"


@pytest.mark.asyncio
async def test_get_fact_returns_single_fact(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /api/facts/{id} returns one fact by id; unknown id 404s."""
    fact = await _create_fact(db_session, fact_text="Recalium links related facts.")

    resp = await client.get(f"/api/facts/{fact.id}")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(fact.id)
    assert data["fact_text"] == "Recalium links related facts."
    assert data["raw_archive_id"] == str(fact.raw_archive_id)
    assert data["source_span"] == fact.source_span
    assert data["confidence_tier"] == fact.confidence_tier
    assert data["review_status"] == "active"

    missing = await client.get(f"/api/facts/{uuid.uuid4()}")
    assert missing.status_code == 404, missing.text

