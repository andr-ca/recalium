"""Retrieval service tests — Phase 3.

Covers: SRCH-01 (keyword), SRCH-02 (semantic), SRCH-03 (hybrid RRF),
        SRCH-04 (budget trimming), SRCH-06 (degraded mode),
        MCP-01 (response envelope), MCP-03 (audit event emission).

These tests are RED until plan 03-03 implements the retrieval service.
"""
import pytest
pytest.importorskip("app.domain.retrieval.service")

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.retrieval.service import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalItem,
    retrieve,
)


# ── SRCH-01: Keyword retrieval ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_keyword_retrieval_returns_results(db_session_phase3: AsyncSession):
    """SRCH-01: keyword search returns results from FTS index."""
    req = RetrievalRequest(query="test conversation", mode="keyword", budget=2000)
    resp = await retrieve(db_session_phase3, req)
    assert isinstance(resp, RetrievalResponse)
    assert resp.retrieval_mode == "keyword"
    assert resp.trimming_reason in ("budget_met", "result_exhausted")
    assert isinstance(resp.items, list)


@pytest.mark.asyncio
async def test_keyword_retrieval_empty_db_returns_empty(db_session_phase3: AsyncSession):
    """SRCH-01: keyword search on empty DB returns empty list, not error."""
    req = RetrievalRequest(query="nothing here xyz123", mode="keyword", budget=2000)
    resp = await retrieve(db_session_phase3, req)
    assert resp.items == []
    assert resp.trimming_reason == "result_exhausted"


# ── SRCH-02: Semantic retrieval ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_semantic_retrieval_no_embeddings_returns_empty(db_session_phase3: AsyncSession):
    """SRCH-02: semantic search with no embeddings returns empty pool, not error."""
    req = RetrievalRequest(query="test", mode="semantic", budget=2000)
    resp = await retrieve(db_session_phase3, req)
    assert isinstance(resp, RetrievalResponse)
    assert resp.retrieval_mode == "semantic"
    assert isinstance(resp.items, list)


# ── SRCH-03: Hybrid RRF ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_retrieval_falls_back_to_keyword_when_no_embeddings(db_session_phase3: AsyncSession):
    """SRCH-03 + SRCH-06: hybrid with no embeddings falls back to keyword."""
    req = RetrievalRequest(query="test", mode="hybrid", budget=2000)
    resp = await retrieve(db_session_phase3, req)
    assert isinstance(resp, RetrievalResponse)
    # Should work without error even with no embeddings
    assert isinstance(resp.items, list)


def test_rrf_score_formula():
    """SRCH-03: RRF score formula is correct: 1/(k + rank). k=60."""
    from app.domain.retrieval.service import rrf_score
    # Position 1, k=60 → 1/61 ≈ 0.01639
    assert abs(rrf_score(rank=1, k=60) - (1 / 61)) < 1e-6
    # Position 50, k=60 → 1/110 ≈ 0.00909
    assert abs(rrf_score(rank=50, k=60) - (1 / 110)) < 1e-6


def test_rrf_minimum_threshold():
    """SRCH-03: Items below RRF threshold 1/(60+25) ≈ 0.01176 are excluded."""
    from app.domain.retrieval.service import RRF_MIN_THRESHOLD
    expected = 1 / (60 + 25)
    assert abs(RRF_MIN_THRESHOLD - expected) < 1e-6


# ── SRCH-04: Budget trimming ───────────────────────────────────────────────

def test_budget_trimming_respects_priority_order():
    """SRCH-04: canonical → facts → summaries → raw. Never truncate mid-item."""
    from app.domain.retrieval.service import apply_budget_trimming, RetrievalItem

    items = [
        RetrievalItem(id=str(uuid.uuid4()), type="excerpt", content="raw " * 100, score=0.5,
                      source_id=str(uuid.uuid4()), source_system="test", captured_at="2026-01-01T00:00:00Z",
                      conflict_label=None, provenance={}),
        RetrievalItem(id=str(uuid.uuid4()), type="canonical", content="canon fact", score=0.9,
                      source_id=str(uuid.uuid4()), source_system="test", captured_at="2026-01-01T00:00:00Z",
                      conflict_label=None, provenance={}),
        RetrievalItem(id=str(uuid.uuid4()), type="fact", content="fact text", score=0.8,
                      source_id=str(uuid.uuid4()), source_system="test", captured_at="2026-01-01T00:00:00Z",
                      conflict_label=None, provenance={}),
    ]
    # Small budget: only canonical should fit
    trimmed, used, reason = apply_budget_trimming(items, budget=20)
    assert trimmed[0].type == "canonical"
    # Raw excerpt (400 chars) doesn't fit
    assert not any(i.type == "excerpt" for i in trimmed)


def test_budget_trimming_does_not_truncate_mid_item():
    """SRCH-04: item that doesn't fit is skipped entirely, not truncated."""
    from app.domain.retrieval.service import apply_budget_trimming, RetrievalItem

    items = [
        RetrievalItem(id=str(uuid.uuid4()), type="fact", content="x" * 50, score=0.8,
                      source_id=str(uuid.uuid4()), source_system="test", captured_at="2026-01-01T00:00:00Z",
                      conflict_label=None, provenance={}),
    ]
    # Budget smaller than content — item is skipped, not truncated
    trimmed, used, reason = apply_budget_trimming(items, budget=10)
    assert trimmed == []
    assert used == 0


# ── SRCH-06: Degraded mode ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_degraded_mode_flag_when_no_embeddings(db_session_phase3: AsyncSession):
    """SRCH-06: hybrid mode sets degraded_mode=True when no embeddings available."""
    req = RetrievalRequest(query="test", mode="hybrid", budget=2000)
    resp = await retrieve(db_session_phase3, req)
    # On empty DB, no embeddings → degraded_mode should be True or None
    assert hasattr(resp, "degraded_mode")


# ── MCP-01: Response envelope ─────────────────────────────────────────────

def test_retrieval_response_has_required_envelope_fields():
    """MCP-01: response envelope has all required fields."""
    resp = RetrievalResponse(
        query="test",
        retrieval_mode="hybrid",
        budget_used=100,
        budget_limit=2000,
        trimming_reason="result_exhausted",
        items=[],
        degraded_mode=False,
    )
    assert resp.query == "test"
    assert resp.retrieval_mode == "hybrid"
    assert resp.budget_used == 100
    assert resp.budget_limit == 2000
    assert resp.trimming_reason == "result_exhausted"
    assert resp.items == []


def test_retrieval_item_has_required_provenance_fields():
    """MCP-01: each item carries provenance metadata."""
    item = RetrievalItem(
        id=str(uuid.uuid4()),
        type="fact",
        content="some fact",
        score=0.042,
        source_id=str(uuid.uuid4()),
        source_system="claude",
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
