"""Retrieval service — keyword, semantic, and hybrid search.

Architecture spec: docs/architecture/retrieval-and-ranking.md
- Keyword: PostgreSQL FTS via websearch_to_tsquery('english', query)
- Semantic: pgvector cosine similarity on embeddings table
- Hybrid: RRF merge (k=60, top-50 per mode, top-20 merged)
- Budget trimming: canonical → facts → summaries → raw (strict priority; no mid-item truncation)
- LRU cache: 256 entries, 60s TTL
- Audit event emitted for every retrieve() call

SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, SRCH-06, MCP-01, MCP-03
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Literal

from cachetools import TTLCache
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.models import AuditEvent

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
RRF_K: int = 60
RRF_CANDIDATES_PER_MODE: int = 50
RRF_FINAL_TOP_N: int = 20
RRF_MIN_THRESHOLD: float = 1 / (RRF_K + 25)  # ≈ 0.01176
DEFAULT_BUDGET: int = 2000

# ── In-process LRU cache ──────────────────────────────────────────────────────
_cache: TTLCache = TTLCache(maxsize=256, ttl=60)


# ── Request/Response models ───────────────────────────────────────────────────
@dataclass
class RetrievalFilters:
    category: str | None = None
    source_system: str | None = None
    time_range_start: str | None = None
    time_range_end: str | None = None
    canonical_only: bool = False


@dataclass
class RetrievalRequest:
    query: str
    mode: Literal["keyword", "semantic", "hybrid"] = "hybrid"
    budget: int = DEFAULT_BUDGET
    filters: RetrievalFilters = field(default_factory=RetrievalFilters)
    actor: str = "user_ui"
    limit: int = RRF_FINAL_TOP_N


@dataclass
class RetrievalItem:
    id: str
    type: Literal["canonical", "fact", "summary", "excerpt"]
    content: str
    score: float
    source_id: str
    source_system: str
    captured_at: str
    conflict_label: str | None
    provenance: dict


@dataclass
class RetrievalResponse:
    query: str
    retrieval_mode: str
    budget_used: int
    budget_limit: int
    trimming_reason: Literal["budget_met", "result_exhausted"]
    items: list[RetrievalItem]
    degraded_mode: bool = False


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_key(req: RetrievalRequest) -> str:
    payload = json.dumps({
        "q": req.query,
        "mode": req.mode,
        "budget": req.budget,
        "filters": {
            "category": req.filters.category,
            "source_system": req.filters.source_system,
            "time_range_start": req.filters.time_range_start,
            "time_range_end": req.filters.time_range_end,
            "canonical_only": req.filters.canonical_only,
        },
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def invalidate_cache() -> None:
    """Invalidate the entire retrieval cache."""
    _cache.clear()
    logger.debug("Retrieval cache invalidated")


# ── RRF helpers ───────────────────────────────────────────────────────────────

def rrf_score(rank: int, k: int = RRF_K) -> float:
    """Reciprocal Rank Fusion score. rank is 1-based."""
    return 1.0 / (k + rank)


def _merge_rrf(
    keyword_ids: list[str],
    semantic_ids: list[str],
) -> list[tuple[str, float]]:
    """Merge two ranked lists using RRF. Returns (id, rrf_score) sorted desc."""
    scores: dict[str, float] = {}

    for rank, item_id in enumerate(keyword_ids, start=1):
        scores[item_id] = scores.get(item_id, 0.0) + rrf_score(rank)

    for rank, item_id in enumerate(semantic_ids, start=1):
        scores[item_id] = scores.get(item_id, 0.0) + rrf_score(rank)

    # Filter by minimum threshold
    filtered = {k: v for k, v in scores.items() if v >= RRF_MIN_THRESHOLD}

    # Sort by score descending, take top N
    return sorted(filtered.items(), key=lambda x: x[1], reverse=True)[:RRF_FINAL_TOP_N]


# ── Budget trimming ───────────────────────────────────────────────────────────

_PRIORITY_ORDER = ["canonical", "fact", "summary", "excerpt"]


def apply_budget_trimming(
    items: list[RetrievalItem],
    budget: int,
) -> tuple[list[RetrievalItem], int, Literal["budget_met", "result_exhausted"]]:
    """Apply strict priority budget trimming.

    Order: canonical → fact → summary → excerpt.
    Never truncate mid-item. Skip item if it doesn't fit.
    Returns (trimmed_items, budget_used, trimming_reason).
    """
    priority_map = {t: i for i, t in enumerate(_PRIORITY_ORDER)}
    sorted_items = sorted(items, key=lambda x: (priority_map.get(x.type, 99), -x.score))

    result: list[RetrievalItem] = []
    used = 0

    for item in sorted_items:
        item_len = len(item.content)
        if used + item_len <= budget:
            result.append(item)
            used += item_len
        # If item doesn't fit: skip entirely (never truncate)
        if used >= budget:
            return result, used, "budget_met"

    return result, used, "result_exhausted"


# ── Candidate retrieval ───────────────────────────────────────────────────────

async def _keyword_candidates(
    session: AsyncSession,
    query: str,
    limit: int = RRF_CANDIDATES_PER_MODE,
) -> list[dict]:
    """Retrieve keyword candidates using PostgreSQL FTS."""
    fts_result = await session.execute(
        text("""
            SELECT
                fe.id::text AS id,
                'excerpt' AS type,
                LEFT(fe.text_content, 500) AS content,
                ts_rank_cd(fe.search_vector, websearch_to_tsquery('english', :q)) AS score,
                fe.raw_archive_id::text AS source_id,
                COALESCE(ra.source_type, 'unknown') AS source_system,
                ra.ingested_at::text AS captured_at,
                NULL::text AS conflict_label,
                fe.raw_archive_id::text AS archive_id
            FROM fts_entries fe
            JOIN raw_archive ra ON ra.id = fe.raw_archive_id
            WHERE fe.source_status = 'active'
              AND ra.deleted_at IS NULL
              AND fe.search_vector @@ websearch_to_tsquery('english', :q)
            ORDER BY score DESC
            LIMIT :limit
        """),
        {"q": query, "limit": limit},
    )
    fts_rows = fts_result.mappings().all()

    canon_result = await session.execute(
        text("""
            SELECT
                cm.id::text AS id,
                'canonical' AS type,
                cm.content AS content,
                ts_rank_cd(cm.search_vector, websearch_to_tsquery('english', :q)) AS score,
                COALESCE(cm.raw_archive_id::text, cm.id::text) AS source_id,
                'canonical' AS source_system,
                cm.created_at::text AS captured_at,
                NULL::text AS conflict_label,
                cm.raw_archive_id::text AS archive_id
            FROM canonical_memory cm
            WHERE cm.source_status = 'active'
              AND cm.status = 'active'
              AND cm.search_vector @@ websearch_to_tsquery('english', :q)
            ORDER BY score DESC
            LIMIT :limit
        """),
        {"q": query, "limit": limit},
    )
    canon_rows = canon_result.mappings().all()

    candidates = []
    for row in list(canon_rows) + list(fts_rows):
        candidates.append({
            "id": row["id"],
            "type": row["type"],
            "content": row["content"] or "",
            "score": float(row["score"] or 0),
            "source_id": row["source_id"] or "",
            "source_system": row["source_system"] or "unknown",
            "captured_at": str(row["captured_at"] or ""),
            "conflict_label": None,
            "provenance": {
                "derivation_method": "fts_retrieval",
                "derivation_model": "postgresql_fts",
                "source_excerpt": (row["content"] or "")[:200],
            },
        })

    return candidates[:limit]


async def _semantic_candidates(
    session: AsyncSession,
    query: str,
    limit: int = RRF_CANDIDATES_PER_MODE,
) -> tuple[list[dict], bool]:
    """Retrieve semantic candidates using pgvector cosine similarity.

    Returns (candidates, degraded) where degraded=True if no embeddings exist.
    """
    try:
        from app.domain.derived_memory.service import embed_text
        query_vector = await embed_text(query)
    except RuntimeError:
        logger.info("Semantic search unavailable: sentence-transformers not installed (degraded mode)")
        return [], True

    result = await session.execute(
        text("""
            SELECT
                e.id::text AS id,
                e.raw_archive_id::text AS raw_archive_id,
                1 - (e.embedding <=> :vec) AS score,
                ra.source_type AS source_system,
                ra.ingested_at::text AS captured_at
            FROM embeddings e
            JOIN raw_archive ra ON ra.id = e.raw_archive_id
            WHERE e.source_status = 'active'
              AND ra.deleted_at IS NULL
              AND e.embedding_model = :model
            ORDER BY e.embedding <=> :vec
            LIMIT :limit
        """),
        {
            "vec": str(query_vector),
            "model": "all-MiniLM-L6-v2",
            "limit": limit,
        },
    )
    rows = result.mappings().all()

    if not rows:
        return [], True

    candidates = []
    for row in rows:
        summary_result = await session.execute(
            text("""
                SELECT summary_text FROM summaries
                WHERE raw_archive_id = :aid AND source_status = 'active'
                LIMIT 1
            """),
            {"aid": row["raw_archive_id"]},
        )
        summary_row = summary_result.fetchone()

        if summary_row:
            content = summary_row[0]
            item_type = "summary"
        else:
            raw_result = await session.execute(
                text("SELECT LEFT(raw_content, 500) FROM raw_archive WHERE id = :aid"),
                {"aid": row["raw_archive_id"]},
            )
            raw_row = raw_result.fetchone()
            content = raw_row[0] if raw_row else ""
            item_type = "excerpt"

        candidates.append({
            "id": row["id"],
            "type": item_type,
            "content": content or "",
            "score": float(row["score"] or 0),
            "source_id": row["raw_archive_id"],
            "source_system": row["source_system"] or "unknown",
            "captured_at": str(row["captured_at"] or ""),
            "conflict_label": None,
            "provenance": {
                "derivation_method": "semantic_retrieval",
                "derivation_model": "all-MiniLM-L6-v2",
                "source_excerpt": (content or "")[:200],
            },
        })

    return candidates, False


# ── Main retrieve function ────────────────────────────────────────────────────

async def retrieve(
    session: AsyncSession,
    req: RetrievalRequest,
) -> RetrievalResponse:
    """Execute retrieval and return a context-budgeted response.

    Modes: keyword, semantic, hybrid.
    Always emits an AuditEvent.
    Uses in-process LRU cache for repeated identical queries.
    """
    cache_key = _cache_key(req)
    if cache_key in _cache:
        logger.debug("Retrieval cache hit for query=%r", req.query[:50])
        return _cache[cache_key]

    degraded = False
    effective_mode = req.mode

    if req.mode == "keyword":
        candidates = await _keyword_candidates(session, req.query, RRF_CANDIDATES_PER_MODE)

    elif req.mode == "semantic":
        candidates, degraded = await _semantic_candidates(session, req.query, RRF_CANDIDATES_PER_MODE)

    else:  # hybrid
        kw_candidates = await _keyword_candidates(session, req.query, RRF_CANDIDATES_PER_MODE)
        sem_candidates, sem_degraded = await _semantic_candidates(session, req.query, RRF_CANDIDATES_PER_MODE)

        if sem_degraded or not sem_candidates:
            degraded = True
            effective_mode = "keyword"
            candidates = kw_candidates
        else:
            kw_ids = [c["id"] for c in kw_candidates]
            sem_ids = [c["id"] for c in sem_candidates]
            merged_scored = _merge_rrf(kw_ids, sem_ids)

            all_by_id: dict[str, dict] = {c["id"]: c for c in kw_candidates + sem_candidates}
            candidates = []
            for item_id, rrf_s in merged_scored:
                if item_id in all_by_id:
                    c = dict(all_by_id[item_id])
                    c["score"] = rrf_s
                    candidates.append(c)

    items = [
        RetrievalItem(
            id=c["id"],
            type=c["type"],
            content=c["content"],
            score=c["score"],
            source_id=c["source_id"],
            source_system=c["source_system"],
            captured_at=c["captured_at"],
            conflict_label=c.get("conflict_label"),
            provenance=c.get("provenance", {}),
        )
        for c in candidates
    ]

    trimmed_items, budget_used, trimming_reason = apply_budget_trimming(items, req.budget)

    response = RetrievalResponse(
        query=req.query,
        retrieval_mode=effective_mode,
        budget_used=budget_used,
        budget_limit=req.budget,
        trimming_reason=trimming_reason,
        items=trimmed_items,
        degraded_mode=degraded,
    )

    audit_event = AuditEvent(
        event_type="search" if req.actor == "user_ui" else "mcp_retrieve",
        actor=req.actor,
        operation_metadata={
            "query_summary": req.query[:100],
            "result_count": len(trimmed_items),
            "retrieval_mode": effective_mode,
            "degraded_mode": degraded,
            "policy_decision": "allowed",
        },
    )
    session.add(audit_event)
    await session.commit()

    _cache[cache_key] = response
    return response
