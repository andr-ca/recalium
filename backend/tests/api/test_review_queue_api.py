"""Review queue API contract tests."""
from __future__ import annotations

import hashlib
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem
from app.domain.derived_memory.models import ConflictGroup, Fact
from app.domain.review_queue.models import ReviewQueueItem

pytestmark = pytest.mark.asyncio


async def test_review_queue_includes_group_fact_comparison(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /api/review-queue includes group metadata and active fact candidates."""
    archive = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        source_name="review-source",
        raw_content="Fact one source. Fact two source.",
        content_hash=hashlib.sha256(b"review-source").hexdigest(),
    )
    group = ConflictGroup(id=uuid.uuid4(), group_type="overlap")
    included_fact = Fact(
        id=uuid.uuid4(),
        raw_archive_id=archive.id,
        conflict_group_id=group.id,
        fact_text="The project uses FastAPI.",
        source_span="FastAPI backend",
        confidence_tier="high",
        derivation_method="rule_based",
        derivation_model="local_rules_v1",
    )
    archived_fact = Fact(
        id=uuid.uuid4(),
        raw_archive_id=archive.id,
        conflict_group_id=group.id,
        fact_text="Archived candidate should not appear.",
        source_span="Archived source",
        confidence_tier="low",
        derivation_method="rule_based",
        derivation_model="local_rules_v1",
        review_status="archived",
    )
    review_item = ReviewQueueItem(
        id=uuid.uuid4(),
        conflict_group_id=group.id,
        item_type="overlap",
        status="pending",
        source_status="active",
    )
    db_session.add_all([archive, group, included_fact, archived_fact, review_item])
    await db_session.flush()

    response = await client.get("/api/review-queue")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["group_type"] == "overlap"
    assert item["fact_count"] == 1
    assert [fact["id"] for fact in item["facts"]] == [str(included_fact.id)]
    assert item["facts"][0]["fact_text"] == "The project uses FastAPI."
    assert item["facts"][0]["source_name"] == "review-source"


async def test_review_queue_resolve_records_note(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Resolve endpoint persists resolution notes for UI review decisions."""
    group = ConflictGroup(id=uuid.uuid4(), group_type="duplicate")
    review_item = ReviewQueueItem(
        id=uuid.uuid4(),
        conflict_group_id=group.id,
        item_type="duplicate",
        status="pending",
        source_status="active",
    )
    db_session.add_all([group, review_item])
    await db_session.flush()

    response = await client.post(
        f"/api/review-queue/{review_item.id}/resolve",
        json={"resolved_by": "tester", "resolution_note": "Kept the highest confidence fact."},
    )

    assert response.status_code == 200
    item = response.json()
    assert item["status"] == "resolved"
    assert item["resolved_by"] == "tester"
    assert item["resolution_note"] == "Kept the highest confidence fact."
