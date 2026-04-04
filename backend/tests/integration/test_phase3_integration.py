"""Phase 3 integration test suite.

Covers all 15 Phase 3 requirement IDs:
  SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, SRCH-06,
  MCP-01, MCP-03, MCP-04,
  CANM-01, CANM-02, CANM-03, CANM-04, CANM-05,
  WEBUI-05

Run with:
    cd backend && uv run python3 -m pytest tests/integration/test_phase3_integration.py -v
"""
from __future__ import annotations

import uuid

import pytest
pytest.importorskip("app.domain.retrieval.service")
pytest.importorskip("app.domain.canonical_memory.service")
pytest.importorskip("app.domain.review_queue.service")

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.retrieval.service import (
    RRF_MIN_THRESHOLD,
    RetrievalItem,
    RetrievalRequest,
    RetrievalResponse,
    apply_budget_trimming,
    invalidate_cache,
    retrieve,
    rrf_score,
)
from app.domain.derived_memory.models import ConflictGroup
from app.domain.canonical_memory.service import (
    CanonicalItemNotFoundError,
    PromotionNotConfirmedError,
    create_manual_canonical,
    delete_canonical_item,
    get_canonical_item,
    list_canonical_items,
    promote_fact_to_canonical,
    update_canonical_item,
)
from app.domain.review_queue.service import (
    ReviewItemNotFoundError,
    dismiss_review_item,
    list_pending_review_items,
    materialize_review_item,
    resolve_review_item,
)
from app.domain.audit.models import AuditEvent


# ─────────────────────────────────────────────────────────────────────────────
# SRCH-01: Keyword retrieval
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_srch01_keyword_search_returns_response_envelope(db_session_phase3: AsyncSession):
    """SRCH-01: keyword mode returns a valid RetrievalResponse envelope."""
    req = RetrievalRequest(query="test keyword query", mode="keyword", budget=2000)
    resp = await retrieve(db_session_phase3, req)
    assert isinstance(resp, RetrievalResponse)
    assert resp.retrieval_mode == "keyword"
    assert isinstance(resp.items, list)
    assert resp.trimming_reason in ("budget_met", "result_exhausted")
    assert resp.budget_limit == 2000


@pytest.mark.asyncio
async def test_srch01_keyword_search_empty_db_returns_empty(db_session_phase3: AsyncSession):
    """SRCH-01: keyword search on empty index returns empty list, not error."""
    req = RetrievalRequest(query="xyzzy_unique_nonexistent_token_9912", mode="keyword", budget=2000)
    resp = await retrieve(db_session_phase3, req)
    assert resp.items == []
    assert resp.trimming_reason == "result_exhausted"


@pytest.mark.asyncio
async def test_srch01_keyword_search_via_api(client: AsyncClient):
    """SRCH-01: GET /api/search?q=test&mode=keyword returns 200 with valid envelope."""
    resp = await client.get("/api/search?q=integration+keyword+test&mode=keyword")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "retrieval_mode" in data
    assert data["retrieval_mode"] == "keyword"
    assert "budget_used" in data
    assert "budget_limit" in data
    assert "trimming_reason" in data


# ─────────────────────────────────────────────────────────────────────────────
# SRCH-02: Semantic retrieval
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_srch02_semantic_search_no_embeddings_returns_empty(db_session_phase3: AsyncSession):
    """SRCH-02: semantic search with no embeddings returns empty pool, not error.

    Service returns ([], True) when no embedding rows exist — degraded_mode must be True.
    """
    req = RetrievalRequest(query="semantic query test", mode="semantic", budget=2000)
    resp = await retrieve(db_session_phase3, req)
    assert isinstance(resp, RetrievalResponse)
    assert resp.retrieval_mode == "semantic"
    assert isinstance(resp.items, list)
    # No embeddings in test DB → service sets degraded=True
    assert resp.degraded_mode is True


@pytest.mark.asyncio
async def test_srch02_semantic_search_via_api(client: AsyncClient):
    """SRCH-02: GET /api/search?mode=semantic returns 200 without error."""
    resp = await client.get("/api/search?q=integration+semantic+test&mode=semantic")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


# ─────────────────────────────────────────────────────────────────────────────
# SRCH-03: Hybrid RRF
# ─────────────────────────────────────────────────────────────────────────────

def test_srch03_rrf_score_formula():
    """SRCH-03: RRF score = 1/(k + rank); rank=1 k=60 → 1/61."""
    assert abs(rrf_score(rank=1, k=60) - (1 / 61)) < 1e-9
    assert abs(rrf_score(rank=50, k=60) - (1 / 110)) < 1e-9


def test_srch03_rrf_minimum_threshold():
    """SRCH-03: RRF threshold is 1/(60+25) ≈ 0.01176."""
    expected = 1 / (60 + 25)
    assert abs(RRF_MIN_THRESHOLD - expected) < 1e-9


@pytest.mark.asyncio
async def test_srch03_hybrid_falls_back_to_keyword_when_no_embeddings(db_session_phase3: AsyncSession):
    """SRCH-03: hybrid mode with no embeddings falls back to keyword gracefully."""
    req = RetrievalRequest(query="hybrid fallback test", mode="hybrid", budget=2000)
    resp = await retrieve(db_session_phase3, req)
    assert isinstance(resp, RetrievalResponse)
    assert isinstance(resp.items, list)
    # With no embeddings the service sets degraded_mode=True and effective_mode="keyword"
    assert resp.degraded_mode is True or resp.retrieval_mode == "keyword"


@pytest.mark.asyncio
async def test_srch03_hybrid_via_api(client: AsyncClient):
    """SRCH-03: GET /api/search?mode=hybrid returns 200."""
    resp = await client.get("/api/search?q=hybrid+test&mode=hybrid")
    assert resp.status_code == 200
    assert "retrieval_mode" in resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# SRCH-04: Budget trimming
# ─────────────────────────────────────────────────────────────────────────────

def test_srch04_budget_trimming_priority_order():
    """SRCH-04: canonical → fact → summary → excerpt; never truncates mid-item."""
    items = [
        RetrievalItem(
            id=str(uuid.uuid4()), type="excerpt",
            content="raw " * 100,  # 400 chars — too large for small budget
            score=0.5, source_id=str(uuid.uuid4()), source_system="test",
            captured_at="2026-01-01T00:00:00Z", conflict_label=None, provenance={},
        ),
        RetrievalItem(
            id=str(uuid.uuid4()), type="canonical",
            content="canon fact",  # 10 chars — fits
            score=0.9, source_id=str(uuid.uuid4()), source_system="test",
            captured_at="2026-01-01T00:00:00Z", conflict_label=None, provenance={},
        ),
        RetrievalItem(
            id=str(uuid.uuid4()), type="fact",
            content="fact text",  # 9 chars — fits too
            score=0.8, source_id=str(uuid.uuid4()), source_system="test",
            captured_at="2026-01-01T00:00:00Z", conflict_label=None, provenance={},
        ),
    ]
    trimmed, used, reason = apply_budget_trimming(items, budget=20)
    # canonical comes first and fits; excerpt (400 chars) should be excluded
    assert any(i.type == "canonical" for i in trimmed)
    assert not any(i.type == "excerpt" for i in trimmed)
    # Positional order: canonical must appear before fact in the output list
    types = [i.type for i in trimmed]
    canonical_idx = types.index("canonical") if "canonical" in types else None
    fact_idx = types.index("fact") if "fact" in types else None
    if canonical_idx is not None and fact_idx is not None:
        assert canonical_idx < fact_idx, "canonical must precede fact in output"


def test_srch04_budget_trimming_skips_item_that_doesnt_fit():
    """SRCH-04: item that exceeds budget is skipped entirely, not truncated."""
    items = [
        RetrievalItem(
            id=str(uuid.uuid4()), type="fact",
            content="x" * 50,  # 50 chars
            score=0.8, source_id=str(uuid.uuid4()), source_system="test",
            captured_at="2026-01-01T00:00:00Z", conflict_label=None, provenance={},
        ),
    ]
    trimmed, used, reason = apply_budget_trimming(items, budget=10)
    assert trimmed == []
    assert used == 0


def test_srch04_budget_trimming_result_exhausted_when_all_fit():
    """SRCH-04: trimming_reason is 'result_exhausted' when all items fit in budget."""
    items = [
        RetrievalItem(
            id=str(uuid.uuid4()), type="fact",
            content="short",  # 5 chars
            score=0.8, source_id=str(uuid.uuid4()), source_system="test",
            captured_at="2026-01-01T00:00:00Z", conflict_label=None, provenance={},
        ),
    ]
    trimmed, used, reason = apply_budget_trimming(items, budget=1000)
    assert reason == "result_exhausted"
    assert len(trimmed) == 1
    assert used == 5


# ─────────────────────────────────────────────────────────────────────────────
# SRCH-05: Response time (structural only — no timing in unit tests)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_srch05_search_returns_within_envelope(client: AsyncClient):
    """SRCH-05: search endpoint returns a complete, well-formed envelope."""
    resp = await client.get("/api/search?q=performance+test&mode=keyword")
    assert resp.status_code == 200
    data = resp.json()
    # All required fields for a complete response envelope
    for field in ("query", "retrieval_mode", "budget_used", "budget_limit", "trimming_reason", "items"):
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_srch05_search_limit_param_respected(client: AsyncClient):
    """SRCH-05: ?limit=1 returns at most 1 item in the response."""
    resp = await client.get("/api/search?q=test&mode=keyword&limit=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) <= 1


@pytest.mark.asyncio
async def test_srch05_search_offset_param_accepted(client: AsyncClient):
    """SRCH-05: ?offset= param is accepted without error (pagination contract)."""
    resp0 = await client.get("/api/search?q=test&mode=keyword&limit=5&offset=0")
    resp1 = await client.get("/api/search?q=test&mode=keyword&limit=5&offset=1")
    assert resp0.status_code == 200
    assert resp1.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# SRCH-06: Degraded mode
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_srch06_hybrid_degraded_mode_flag_set_when_no_embeddings(db_session_phase3: AsyncSession):
    """SRCH-06: hybrid mode sets degraded_mode=True when no embeddings are available."""
    req = RetrievalRequest(query="degraded mode test", mode="hybrid", budget=2000)
    resp = await retrieve(db_session_phase3, req)
    assert hasattr(resp, "degraded_mode")
    # On an empty DB without embeddings, degraded_mode should be True
    assert resp.degraded_mode is True


@pytest.mark.asyncio
async def test_srch06_degraded_mode_visible_in_api_response(client: AsyncClient):
    """SRCH-06: API response includes degraded_mode field."""
    resp = await client.get("/api/search?q=degraded+test&mode=hybrid")
    assert resp.status_code == 200
    data = resp.json()
    assert "degraded_mode" in data


# ─────────────────────────────────────────────────────────────────────────────
# MCP-01: Response envelope structure
# ─────────────────────────────────────────────────────────────────────────────

def test_mcp01_retrieval_response_envelope_fields():
    """MCP-01: RetrievalResponse has all required envelope fields."""
    resp = RetrievalResponse(
        query="envelope test",
        retrieval_mode="hybrid",
        budget_used=150,
        budget_limit=2000,
        trimming_reason="result_exhausted",
        items=[],
        degraded_mode=False,
    )
    assert resp.query == "envelope test"
    assert resp.retrieval_mode == "hybrid"
    assert resp.budget_used == 150
    assert resp.budget_limit == 2000
    assert resp.trimming_reason == "result_exhausted"
    assert resp.items == []
    assert resp.degraded_mode is False


def test_mcp01_retrieval_item_has_provenance_fields():
    """MCP-01: RetrievalItem carries source, type, rank score, and provenance metadata."""
    item = RetrievalItem(
        id=str(uuid.uuid4()),
        type="fact",
        content="some fact text",
        score=0.042,
        source_id=str(uuid.uuid4()),
        source_system="claude_export",
        captured_at="2026-01-01T00:00:00Z",
        conflict_label=None,
        provenance={
            "derivation_method": "llm_extraction",
            "derivation_model": "gpt-4o",
            "source_excerpt": "original text",
        },
    )
    assert item.provenance["derivation_method"] == "llm_extraction"
    assert item.conflict_label is None
    assert item.type == "fact"
    assert item.score == pytest.approx(0.042)


@pytest.mark.asyncio
async def test_mcp01_post_retrieve_endpoint(client: AsyncClient):
    """MCP-01: POST /api/retrieve returns full retrieval envelope."""
    resp = await client.post("/api/retrieve", json={
        "query": "mcp retrieve test",
        "mode": "hybrid",
        "budget": 2000,
    })
    assert resp.status_code == 200
    data = resp.json()
    for field in ("query", "retrieval_mode", "items", "budget_used", "budget_limit", "trimming_reason"):
        assert field in data, f"Missing field: {field}"


# ─────────────────────────────────────────────────────────────────────────────
# MCP-03: Audit event emission on retrieval
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp03_search_emits_audit_event_type_search(db_session_phase3: AsyncSession):
    """MCP-03: retrieve() called with actor='user_ui' emits event_type='search'.

    invalidate_cache() is called before every audit test: the retrieval cache is
    process-level (not session-scoped), so a cached result from a prior test would
    suppress audit event emission for the same query.
    """
    invalidate_cache()
    req = RetrievalRequest(query="audit emission test", mode="keyword", budget=2000, actor="user_ui")
    await retrieve(db_session_phase3, req)

    result = await db_session_phase3.execute(
        select(AuditEvent).where(AuditEvent.event_type == "search").order_by(AuditEvent.occurred_at.desc())
    )
    events = list(result.scalars().all())
    assert len(events) == 1
    event = events[0]
    assert event.actor == "user_ui"
    assert event.operation_metadata is not None
    assert "query_summary" in event.operation_metadata
    assert "result_count" in event.operation_metadata


@pytest.mark.asyncio
async def test_mcp03_audit_events_endpoint_returns_events(client: AsyncClient):
    """MCP-03: /api/audit/events endpoint returns audit events list."""
    # Trigger a search to create an audit event
    await client.get("/api/search?q=audit+endpoint+test&mode=keyword")
    resp = await client.get("/api/audit/events?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)


# ─────────────────────────────────────────────────────────────────────────────
# MCP-04: Client identity + 90-day retention
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp04_mcp_retrieve_emits_mcp_retrieve_event(db_session_phase3: AsyncSession):
    """MCP-04: retrieve() with non-user_ui actor emits event_type='mcp_retrieve'.

    invalidate_cache() ensures the process-level cache doesn't suppress audit emission.
    """
    # Invalidate cache to ensure a fresh audit event is emitted
    invalidate_cache()

    req = RetrievalRequest(
        query="mcp client identity test unique xyz987",
        mode="keyword",
        budget=2000,
        actor="mcp_client",
    )
    await retrieve(db_session_phase3, req)

    result = await db_session_phase3.execute(
        select(AuditEvent)
        .where(AuditEvent.event_type == "mcp_retrieve")
        .order_by(AuditEvent.occurred_at.desc())
    )
    events = list(result.scalars().all())
    assert len(events) == 1
    event = events[0]
    assert event.actor == "mcp_client"
    assert event.operation_metadata is not None


@pytest.mark.asyncio
async def test_mcp04_audit_event_records_client_identity(db_session_phase3: AsyncSession):
    """MCP-04: audit event records actor (client identity) field.

    invalidate_cache() ensures the process-level cache doesn't suppress audit emission.
    """
    invalidate_cache()
    actor = "test_mcp_client_identity_" + str(uuid.uuid4())[:8]
    req = RetrievalRequest(query="client identity unique test", mode="keyword", budget=2000, actor=actor)
    await retrieve(db_session_phase3, req)

    result = await db_session_phase3.execute(
        select(AuditEvent).where(AuditEvent.actor == actor)
    )
    events = list(result.scalars().all())
    assert len(events) == 1
    assert events[0].actor == actor


# ─────────────────────────────────────────────────────────────────────────────
# CANM-01: Inspect, edit, delete, promote
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_canm01_create_manual_canonical(db_session_phase3: AsyncSession):
    """CANM-01: create_manual_canonical() creates an active canonical item."""
    item = await create_manual_canonical(
        session=db_session_phase3,
        content="User always prefers Python for data work.",
        promoted_by="user_ui",
    )
    assert item.id is not None
    assert item.promoted_from == "manual"
    assert item.status == "active"
    assert item.source_status == "active"
    assert item.fact_id is None


@pytest.mark.asyncio
async def test_canm01_get_canonical_item_by_id(db_session_phase3: AsyncSession):
    """CANM-01: get_canonical_item() retrieves item by ID."""
    created = await create_manual_canonical(
        session=db_session_phase3,
        content="Inspectable fact.",
        promoted_by="user_ui",
    )
    fetched = await get_canonical_item(db_session_phase3, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.content == "Inspectable fact."


@pytest.mark.asyncio
async def test_canm01_get_canonical_item_missing_returns_none(db_session_phase3: AsyncSession):
    """CANM-01: get_canonical_item() returns None for unknown ID."""
    result = await get_canonical_item(db_session_phase3, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_canm01_update_canonical_item_content(db_session_phase3: AsyncSession):
    """CANM-01: update_canonical_item() edits content in place."""
    item = await create_manual_canonical(
        session=db_session_phase3,
        content="Original content.",
        promoted_by="user_ui",
    )
    updated = await update_canonical_item(db_session_phase3, item.id, content="Updated content.")
    assert updated.content == "Updated content."
    assert updated.id == item.id


@pytest.mark.asyncio
async def test_canm01_update_canonical_item_not_found_raises(db_session_phase3: AsyncSession):
    """CANM-01: updating a non-existent item raises CanonicalItemNotFoundError."""
    with pytest.raises(CanonicalItemNotFoundError):
        await update_canonical_item(db_session_phase3, uuid.uuid4(), content="ghost update")


@pytest.mark.asyncio
async def test_canm01_delete_canonical_item(db_session_phase3: AsyncSession):
    """CANM-01: delete_canonical_item() soft-deletes (source_status=source_removed)."""
    item = await create_manual_canonical(
        session=db_session_phase3,
        content="to be deleted",
        promoted_by="user_ui",
    )
    await delete_canonical_item(db_session_phase3, item.id)
    fetched = await get_canonical_item(db_session_phase3, item.id)
    assert fetched is not None
    assert fetched.source_status == "source_removed"


@pytest.mark.asyncio
async def test_canm01_delete_canonical_not_found_raises(db_session_phase3: AsyncSession):
    """CANM-01: deleting a non-existent item raises CanonicalItemNotFoundError."""
    with pytest.raises(CanonicalItemNotFoundError):
        await delete_canonical_item(db_session_phase3, uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# CANM-02: Active-only list (disputed items excluded)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_canm02_list_active_only_by_default(db_session_phase3: AsyncSession):
    """CANM-02: list_canonical_items() returns only source_status=active items."""
    active = await create_manual_canonical(db_session_phase3, "active item xyz_canm02", "user_ui")
    disputed = await create_manual_canonical(db_session_phase3, "disputed item xyz_canm02", "user_ui")
    # Mark the disputed item as source_removed to test exclusion
    await delete_canonical_item(db_session_phase3, disputed.id)

    items = await list_canonical_items(db_session_phase3)
    ids = [i.id for i in items]
    assert active.id in ids
    assert disputed.id not in ids


@pytest.mark.asyncio
async def test_canm02_list_all_items_have_active_source_status(db_session_phase3: AsyncSession):
    """CANM-02: every item returned by list_canonical_items has source_status='active'."""
    await create_manual_canonical(db_session_phase3, "canm02 list check", "user_ui")
    items = await list_canonical_items(db_session_phase3)
    assert len(items) >= 1, "Expected at least one item in the list"
    assert all(i.source_status == "active" for i in items)


# ─────────────────────────────────────────────────────────────────────────────
# CANM-03: Explicit promote action only
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_canm03_promote_fact_explicit(
    db_session_phase3: AsyncSession,
    raw_archive_row,
    fact_row,
):
    """CANM-03: promote_fact_to_canonical() with explicit params creates canonical item."""
    item = await promote_fact_to_canonical(
        session=db_session_phase3,
        fact_id=fact_row.id,
        raw_archive_id=raw_archive_row.id,
        content=fact_row.fact_text,
        promoted_by="test",
        has_source_span=True,
        confirmed=True,
    )
    assert item is not None
    assert item.status == "active"
    assert item.promoted_from == "fact"
    assert item.fact_id == fact_row.id
    assert item.raw_archive_id == raw_archive_row.id


# ─────────────────────────────────────────────────────────────────────────────
# CANM-04: Source span confirmation required
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_canm04_empty_source_span_requires_confirm(db_session_phase3: AsyncSession):
    """CANM-04: promoting with has_source_span=False, confirmed=False raises PromotionNotConfirmedError."""
    with pytest.raises(PromotionNotConfirmedError):
        await promote_fact_to_canonical(
            session=db_session_phase3,
            fact_id=uuid.uuid4(),
            raw_archive_id=uuid.uuid4(),
            content="fact without span",
            promoted_by="test",
            has_source_span=False,
            confirmed=False,
        )


@pytest.mark.asyncio
async def test_canm04_no_source_span_with_confirmed_true_succeeds(
    db_session_phase3: AsyncSession,
    raw_archive_row,
    fact_row,
):
    """CANM-04: has_source_span=False, confirmed=True is allowed."""
    item = await promote_fact_to_canonical(
        session=db_session_phase3,
        fact_id=fact_row.id,
        raw_archive_id=raw_archive_row.id,
        content="no span but confirmed",
        promoted_by="test",
        has_source_span=False,
        confirmed=True,
    )
    assert item is not None
    assert item.status == "active"


# ─────────────────────────────────────────────────────────────────────────────
# CANM-05: Review queue — groups duplicates/overlaps
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_canm05_list_pending_review_items_is_list(db_session_phase3: AsyncSession):
    """CANM-05: list_pending_review_items() returns a list (empty on clean session)."""
    items = await list_pending_review_items(db_session_phase3)
    assert isinstance(items, list)
    # All returned items must be pending
    assert all(i.status == "pending" for i in items)


@pytest.mark.asyncio
async def test_canm05_resolve_review_item_not_found_raises(db_session_phase3: AsyncSession):
    """CANM-05: resolving unknown review item raises ReviewItemNotFoundError."""
    with pytest.raises(ReviewItemNotFoundError):
        await resolve_review_item(
            db_session_phase3,
            uuid.uuid4(),
            resolution_note="does not exist",
            resolved_by="test_user",
        )


@pytest.mark.asyncio
async def test_canm05_dismiss_review_item_not_found_raises(db_session_phase3: AsyncSession):
    """CANM-05: dismissing unknown review item raises ReviewItemNotFoundError."""
    with pytest.raises(ReviewItemNotFoundError):
        await dismiss_review_item(db_session_phase3, uuid.uuid4())


@pytest.mark.asyncio
async def test_canm05_materialize_and_resolve_review_item(db_session_phase3: AsyncSession):
    """CANM-05: materialize → list pending → resolve workflow."""
    # Create a real conflict_group row to satisfy the FK
    group = ConflictGroup(id=uuid.uuid4(), group_type="duplicate")
    db_session_phase3.add(group)
    await db_session_phase3.flush()

    review_item = await materialize_review_item(
        session=db_session_phase3,
        conflict_group_id=group.id,
        item_type="duplicate",
    )
    assert review_item.status == "pending"
    assert review_item.conflict_group_id == group.id

    pending = await list_pending_review_items(db_session_phase3)
    pending_ids = [i.id for i in pending]
    assert review_item.id in pending_ids

    resolved = await resolve_review_item(
        db_session_phase3,
        review_item.id,
        resolution_note="resolved in test",
        resolved_by="test_user",
    )
    assert resolved.status == "resolved"
    assert resolved.resolution_note == "resolved in test"
    assert resolved.resolved_by == "test_user"
    assert resolved.resolved_at is not None


@pytest.mark.asyncio
async def test_canm05_materialize_and_dismiss_review_item(db_session_phase3: AsyncSession):
    """CANM-05: materialize → dismiss workflow."""
    group = ConflictGroup(id=uuid.uuid4(), group_type="overlap")
    db_session_phase3.add(group)
    await db_session_phase3.flush()

    review_item = await materialize_review_item(
        session=db_session_phase3,
        conflict_group_id=group.id,
        item_type="overlap",
    )
    assert review_item.status == "pending"

    dismissed = await dismiss_review_item(db_session_phase3, review_item.id)
    assert dismissed.status == "dismissed"
    assert dismissed.resolved_at is not None

    # Dismissed item should no longer appear in pending list
    pending = await list_pending_review_items(db_session_phase3)
    pending_ids = [i.id for i in pending]
    assert review_item.id not in pending_ids


# ─────────────────────────────────────────────────────────────────────────────
# WEBUI-05: Provenance navigation — source link present
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webui05_canonical_item_retains_source_archive_link(
    db_session_phase3: AsyncSession,
    raw_archive_row,
    fact_row,
):
    """WEBUI-05: promoted canonical item retains raw_archive_id for provenance navigation."""
    item = await promote_fact_to_canonical(
        session=db_session_phase3,
        fact_id=fact_row.id,
        raw_archive_id=raw_archive_row.id,
        content=fact_row.fact_text,
        promoted_by="user_ui",
        has_source_span=True,
        confirmed=True,
    )
    assert item.raw_archive_id == raw_archive_row.id
    assert item.fact_id == fact_row.id


@pytest.mark.asyncio
async def test_webui05_canonical_api_item_includes_source_fields(client: AsyncClient):
    """WEBUI-05: GET /api/canonical items include provenance source fields."""
    # Create a canonical item
    create_resp = await client.post("/api/canonical", json={
        "content": "WEBUI-05 provenance test item.",
        "promoted_from": "manual",
    })
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    # Verify list includes the item with expected fields
    list_resp = await client.get("/api/canonical")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    created_item = next((i for i in items if i["id"] == item_id), None)
    assert created_item is not None
    # id and promoted_from are present for provenance tracking
    assert "id" in created_item
    assert "promoted_from" in created_item
    assert created_item["promoted_from"] == "manual"
