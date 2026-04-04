"""Archive routes — GET /api/archive with pagination."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem
from app.domain.archive.service import cascade_delete_archive_item, ArchiveItemNotFoundError
from app.domain.jobs.models import Job
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
    status_badge: str  # Phase 2+: derived from pipeline job status
    job_id: str | None
    job_error: str | None
    deleted_at: str | None = None

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


def _job_status_to_badge(status: str | None) -> str:
    """Map job status to display badge label."""
    if status is None:
        return "Ingested"
    return {
        "pending": "Processing",
        "claimed": "Processing",
        "completed": "Done",
        "failed": "Failed",
        "retryable_failed": "Failed",
        "pending_provider": "Pending Provider",
    }.get(status, "Processing")


@router.get("", response_model=ArchiveListResponse)
async def list_archive(
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=50, ge=1, le=200, description="Page size (max 200)"),
    q: str | None = Query(default=None, description="Keyword filter on source_name (future: FTS)"),
    include_deleted: bool = Query(default=False, description="Include soft-deleted items"),
    session: AsyncSession = Depends(get_session),
) -> ArchiveListResponse:
    """GET /api/archive — returns paginated raw archive items.

    Filters:
    - Always excludes soft-deleted items (deleted_at IS NULL) unless include_deleted=true.
    - Optional keyword filter on source_name (basic ILIKE in Phase 1; FTS in Phase 3).

    Ordered by ingested_at DESC (newest first).
    """
    # Base query: exclude soft-deleted items (D-10 — ALL read queries must filter)
    base_stmt = select(RawArchiveItem)
    if not include_deleted:
        base_stmt = base_stmt.where(RawArchiveItem.deleted_at.is_(None))

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
        .outerjoin(Job, Job.raw_archive_id == RawArchiveItem.id)
        .add_columns(
            Job.id.label("job_id"),
            Job.status.label("job_status"),
            Job.error_message.label("job_error"),
        )
        .order_by(desc(RawArchiveItem.ingested_at))
        .offset(offset)
        .limit(limit)
    )
    items_result = await session.execute(items_stmt)
    rows = items_result.all()

    return ArchiveListResponse(
        items=[
            ArchiveItemOut(
                id=str(row.RawArchiveItem.id),
                source_type=_source_badge_label(row.RawArchiveItem.source_type),
                source_name=row.RawArchiveItem.source_name,
                conversation_count=row.RawArchiveItem.conversation_count,
                ingested_at=row.RawArchiveItem.ingested_at.isoformat(),
                status_badge=_job_status_to_badge(row.job_status),
                job_id=str(row.job_id) if row.job_id else None,
                job_error=row.job_error,
            )
            for row in rows
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{item_id}")
async def get_archive_item(item_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    """GET /api/archive/{item_id} — return a single archive item by ID."""
    try:
        archive_uuid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid archive item ID format")
    result = await session.execute(
        select(RawArchiveItem).where(
            RawArchiveItem.id == archive_uuid,
            RawArchiveItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Archive item not found")
    return {
        "id": str(item.id),
        "source_type": item.source_type,
        "ingested_at": item.ingested_at.isoformat(),
        "raw_content": item.raw_content[:2000],
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


@router.delete("/{item_id}", status_code=204)
async def delete_archive_item(
    item_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """DELETE /api/archive/{item_id} — soft-delete archive item and cascade (PRIV-01, PRIV-02)."""
    try:
        archive_uuid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid archive item ID format")
    try:
        await cascade_delete_archive_item(session, archive_uuid, actor="user_ui")
    except ArchiveItemNotFoundError:
        raise HTTPException(status_code=404, detail="Archive item not found or already deleted")
    return Response(status_code=204)
