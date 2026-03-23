"""Archive routes — GET /api/archive with pagination."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem
from app.infrastructure.db import get_session

logger = logging.getLogger(__name__)
router = APIRouter()


class ArchiveItemOut(BaseModel):
    """Archive item response schema — safe for client consumption."""
    id: str
    source_type: str
    source_name: str | None
    conversation_count: int
    ingested_at: str  # ISO 8601 string
    status_badge: str  # Phase 1: always "Ingested"; Phase 2+ adds pipeline status

    model_config = {"from_attributes": True}


class ArchiveListResponse(BaseModel):
    items: list[ArchiveItemOut]
    total: int
    offset: int
    limit: int


def _source_badge_label(source_type: str) -> str:
    """Human-readable source label for badge display."""
    labels = {
        "chatgpt_json": "ChatGPT",
        "claude_json": "Claude",
        "generic_json": "JSON",
        "paste_text": "Text Paste",
        "paste_markdown": "Markdown",
    }
    return labels.get(source_type, source_type.replace("_", " ").title())


@router.get("", response_model=ArchiveListResponse)
async def list_archive(
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=50, ge=1, le=200, description="Page size (max 200)"),
    q: str | None = Query(default=None, description="Keyword filter on source_name (future: FTS)"),
    session: AsyncSession = Depends(get_session),
) -> ArchiveListResponse:
    """GET /api/archive — returns paginated raw archive items.

    Filters:
    - Always excludes soft-deleted items (deleted_at IS NULL).
    - Optional keyword filter on source_name (basic ILIKE in Phase 1; FTS in Phase 3).

    Ordered by ingested_at DESC (newest first).
    """
    # Base query: exclude soft-deleted items (D-10 — ALL read queries must filter)
    base_stmt = select(RawArchiveItem).where(RawArchiveItem.deleted_at.is_(None))

    # Optional keyword filter
    if q and q.strip():
        search_term = f"%{q.strip()}%"
        base_stmt = base_stmt.where(
            RawArchiveItem.source_name.ilike(search_term)
        )

    # Count total matching items
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Paginated results, ordered newest first
    items_stmt = (
        base_stmt
        .order_by(desc(RawArchiveItem.ingested_at))
        .offset(offset)
        .limit(limit)
    )
    items_result = await session.execute(items_stmt)
    items = list(items_result.scalars().all())

    return ArchiveListResponse(
        items=[
            ArchiveItemOut(
                id=str(item.id),
                source_type=_source_badge_label(item.source_type),
                source_name=item.source_name,
                conversation_count=item.conversation_count,
                ingested_at=item.ingested_at.isoformat(),
                status_badge="Ingested",  # Phase 1 only; Phase 2 adds pipeline status
            )
            for item in items
        ],
        total=total,
        offset=offset,
        limit=limit,
    )
