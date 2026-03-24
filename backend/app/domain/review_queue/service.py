"""Review queue domain service.

Implements CANM-05: groups duplicate/overlapping facts for manageable review.

All list queries filter source_status='active' per cascade contract.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.review_queue.models import ReviewQueueItem


class ReviewItemNotFoundError(Exception):
    """Raised when a review queue item cannot be found."""


async def materialize_review_item(
    session: AsyncSession,
    conflict_group_id: uuid.UUID,
    item_type: str,
) -> ReviewQueueItem:
    """Create a pending ReviewQueueItem for a conflict group (CANM-05).

    Will raise a DB integrity error if conflict_group_id does not reference
    an existing conflict_groups row (FK enforcement).
    """
    item = ReviewQueueItem(
        id=uuid.uuid4(),
        conflict_group_id=conflict_group_id,
        item_type=item_type,
        status="pending",
        source_status="active",
    )
    session.add(item)
    await session.flush()
    return item


async def list_pending_review_items(
    session: AsyncSession,
) -> list[ReviewQueueItem]:
    """Return all pending, active review queue items (CANM-05)."""
    result = await session.execute(
        select(ReviewQueueItem).where(
            ReviewQueueItem.status == "pending",
            ReviewQueueItem.source_status == "active",
        )
    )
    return list(result.scalars().all())


async def resolve_review_item(
    session: AsyncSession,
    item_id: uuid.UUID,
    resolution_note: str,
    resolved_by: str,
) -> ReviewQueueItem:
    """Resolve a review item, recording note and resolver (CANM-05).

    Raises ReviewItemNotFoundError if the item does not exist.
    """
    result = await session.execute(
        select(ReviewQueueItem).where(ReviewQueueItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise ReviewItemNotFoundError(f"ReviewQueueItem {item_id} not found.")
    item.status = "resolved"
    item.resolution_note = resolution_note
    item.resolved_by = resolved_by
    item.resolved_at = datetime.now(timezone.utc)
    await session.flush()
    return item


async def dismiss_review_item(
    session: AsyncSession,
    item_id: uuid.UUID,
) -> ReviewQueueItem:
    """Dismiss a review item without resolution (CANM-05).

    Raises ReviewItemNotFoundError if the item does not exist.
    """
    result = await session.execute(
        select(ReviewQueueItem).where(ReviewQueueItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise ReviewItemNotFoundError(f"ReviewQueueItem {item_id} not found.")
    item.status = "dismissed"
    item.resolved_at = datetime.now(timezone.utc)
    await session.flush()
    return item
