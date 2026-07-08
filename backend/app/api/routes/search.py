"""Search and retrieval API routes.

SRCH-01: GET /api/search — keyword/semantic/hybrid search via query params
SRCH-02: POST /api/retrieve — structured retrieval request
SRCH-03: Returns full context envelope with provenance and conflict labels
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.retrieval.service import (
    RetrievalFilters,
    RetrievalRequest,
    RetrievalResponse,
    retrieve,
    invalidate_cache,
)
from app.infrastructure.db import get_session
from app.infrastructure.settings import Settings, get_settings

router = APIRouter(prefix="/api", tags=["search"])

_VALID_MODES = {"keyword", "semantic", "hybrid"}


@router.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    mode: str = Query("hybrid", description="Retrieval mode: keyword|semantic|hybrid"),
    budget: int = Query(2000, description="Max character budget"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None),
    source_system: str | None = Query(None),
    canonical_only: bool = Query(False),
    tags: list[str] = Query(default=[], description="Filter by fact tags (all must match)"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if mode not in _VALID_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid mode '{mode}'. Must be one of: {', '.join(sorted(_VALID_MODES))}",
        )
    req = RetrievalRequest(
        query=q,
        mode=mode,
        budget=budget,
        filters=RetrievalFilters(
            category=category,
            source_system=source_system,
            canonical_only=canonical_only,
            tags=tags,
        ),
        actor="user_ui",
        limit=limit,
    )
    try:
        response: RetrievalResponse = await retrieve(session, req)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _response_to_dict(response)


class RetrieveFiltersBody(BaseModel):
    category: str | None = None
    source_system: str | None = None
    time_range_start: str | None = None
    time_range_end: str | None = None
    canonical_only: bool = False
    tags: list[str] = []


class RetrieveRequestBody(BaseModel):
    query: str
    mode: str = "hybrid"
    budget: int = 2000
    filters: RetrieveFiltersBody = RetrieveFiltersBody()
    actor: str = "user_ui"
    limit: int = 20


@router.post("/retrieve")
async def retrieve_structured(
    body: RetrieveRequestBody,
    session: AsyncSession = Depends(get_session),
) -> dict:
    if body.mode not in _VALID_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid mode '{body.mode}'. Must be one of: {', '.join(sorted(_VALID_MODES))}",
        )
    req = RetrievalRequest(
        query=body.query,
        mode=body.mode,
        budget=body.budget,
        filters=RetrievalFilters(
            category=body.filters.category,
            source_system=body.filters.source_system,
            time_range_start=body.filters.time_range_start,
            time_range_end=body.filters.time_range_end,
            canonical_only=body.filters.canonical_only,
            tags=body.filters.tags,
        ),
        actor=body.actor,
        limit=body.limit,
    )
    try:
        response: RetrievalResponse = await retrieve(session, req)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _response_to_dict(response)


@router.post("/search/invalidate-cache")
async def invalidate_search_cache(settings: Settings = Depends(get_settings)) -> dict:
    """Flush the retrieval LRU cache. Only permitted in development mode (APP_ENV=development)."""
    if not settings.is_development:
        raise HTTPException(status_code=403, detail="Only available in development mode")
    invalidate_cache()
    return {"invalidated": True}


def _response_to_dict(response: RetrievalResponse) -> dict:
    return {
        "query": response.query,
        "retrieval_mode": response.retrieval_mode,
        "budget_used": response.budget_used,
        "budget_limit": response.budget_limit,
        "trimming_reason": response.trimming_reason,
        "degraded_mode": response.degraded_mode,
        "items": [
            {
                "id": item.id,
                "type": item.type,
                "content": item.content,
                "score": item.score,
                "source_id": item.source_id,
                "source_system": item.source_system,
                "captured_at": item.captured_at,
                "conflict_label": item.conflict_label,
                "provenance": item.provenance,
                "source_fact_id": item.source_fact_id,
                "link_type": item.link_type,
            }
            for item in response.items
        ],
    }
