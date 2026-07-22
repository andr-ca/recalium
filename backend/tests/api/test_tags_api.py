"""Tags API route tests — facts-by-tag endpoint for the Explore browser."""
from __future__ import annotations

import hashlib
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem
from app.domain.derived_memory.models import Fact, FactTag, Tag


async def _archive(db_session: AsyncSession) -> RawArchiveItem:
    content = f"A conversation {uuid.uuid4()}"
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        source_name="tags-api-test",
        raw_content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        conversation_count=1,
    )
    db_session.add(item)
    await db_session.flush()
    return item


async def _fact(
    db_session: AsyncSession,
    archive_id: uuid.UUID,
    *,
    fact_text: str = "A fact.",
    source_status: str = "active",
) -> Fact:
    fact = Fact(
        id=uuid.uuid4(),
        raw_archive_id=archive_id,
        fact_text=fact_text,
        source_span="span",
        confidence_tier="high",
        derivation_method="llm_extraction",
        derivation_model="test-model",
        source_status=source_status,
    )
    db_session.add(fact)
    await db_session.flush()
    return fact


@pytest.mark.asyncio
async def test_list_tag_facts_returns_active_tagged_facts(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /api/tags/{id}/facts returns the tag name and its active facts only."""
    archive = await _archive(db_session)
    active = await _fact(db_session, archive.id, fact_text="User prefers pnpm.")
    removed = await _fact(db_session, archive.id, fact_text="removed", source_status="source_removed")

    tag = Tag(id=uuid.uuid4(), name="entity:pnpm")
    db_session.add(tag)
    await db_session.flush()
    db_session.add_all([
        FactTag(fact_id=active.id, tag_id=tag.id, assigned_by="pipeline"),
        FactTag(fact_id=removed.id, tag_id=tag.id, assigned_by="pipeline"),
    ])
    await db_session.flush()

    resp = await client.get(f"/api/tags/{tag.id}/facts")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "entity:pnpm"
    assert data["count"] == 1
    assert len(data["facts"]) == 1
    assert data["facts"][0]["id"] == str(active.id)
    assert data["facts"][0]["fact_text"] == "User prefers pnpm."


@pytest.mark.asyncio
async def test_list_tag_facts_unknown_tag_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    resp = await client.get(f"/api/tags/{uuid.uuid4()}/facts")
    assert resp.status_code == 404, resp.text
