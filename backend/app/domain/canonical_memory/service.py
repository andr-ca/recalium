"""Canonical memory domain service.

Implements CANM-01 (inspect/edit/delete/promote), CANM-02 (retrieval priority),
CANM-03 (explicit action only), CANM-04 (source_span confirmation).

All read queries filter source_status='active' per cascade contract.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.canonical_memory.models import CanonicalMemoryItem


class PromotionNotConfirmedError(Exception):
    """Raised when promoting a fact without source_span and confirmed=False (CANM-04)."""


class CanonicalItemNotFoundError(Exception):
    """Raised when a canonical item cannot be found."""


async def promote_fact_to_canonical(
    session: AsyncSession,
    fact_id: uuid.UUID,
    raw_archive_id: uuid.UUID,
    content: str,
    promoted_by: str,
    has_source_span: bool = True,
    confirmed: bool = False,
) -> CanonicalMemoryItem:
    """Promote a derived-memory fact into canonical memory (CANM-03/CANM-04).

    If the fact has no source span, the user must explicitly confirm (confirmed=True)
    before promotion is allowed.
    """
    if not has_source_span and not confirmed:
        raise PromotionNotConfirmedError(
            "Facts without a source span require confirmed=True to promote to canonical memory."
        )

    item = CanonicalMemoryItem(
        id=uuid.uuid4(),
        fact_id=fact_id,
        raw_archive_id=raw_archive_id,
        content=content,
        promoted_from="fact",
        promoted_by=promoted_by,
        status="active",
        source_status="active",
    )
    session.add(item)
    await session.flush()
    return item


async def create_manual_canonical(
    session: AsyncSession,
    content: str,
    promoted_by: str,
) -> CanonicalMemoryItem:
    """Create a canonical item manually, not promoted from a fact (CANM-01)."""
    item = CanonicalMemoryItem(
        id=uuid.uuid4(),
        fact_id=None,
        raw_archive_id=None,
        content=content,
        promoted_from="manual",
        promoted_by=promoted_by,
        status="active",
        source_status="active",
    )
    session.add(item)
    await session.flush()
    return item


async def get_canonical_item(
    session: AsyncSession,
    item_id: uuid.UUID,
) -> Optional[CanonicalMemoryItem]:
    """Return a canonical item by id, or None if not found."""
    result = await session.execute(
        select(CanonicalMemoryItem).where(CanonicalMemoryItem.id == item_id)
    )
    return result.scalar_one_or_none()


async def update_canonical_item(
    session: AsyncSession,
    item_id: uuid.UUID,
    content: Optional[str] = None,
    status: Optional[str] = None,
) -> CanonicalMemoryItem:
    """Partially update a canonical item's content and/or status (CANM-01).

    Raises CanonicalItemNotFoundError if the item does not exist.
    """
    item = await get_canonical_item(session, item_id)
    if item is None:
        raise CanonicalItemNotFoundError(f"Canonical item {item_id} not found.")
    if content is not None:
        item.content = content
    if status is not None:
        item.status = status
    item.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return item


async def delete_canonical_item(
    session: AsyncSession,
    item_id: uuid.UUID,
) -> None:
    """Soft-delete a canonical item by setting source_status='source_removed' (CANM-01)."""
    item = await get_canonical_item(session, item_id)
    if item is None:
        raise CanonicalItemNotFoundError(f"Canonical item {item_id} not found.")
    item.source_status = "source_removed"
    item.updated_at = datetime.now(timezone.utc)
    await session.flush()


async def mark_canonical_disputed(
    session: AsyncSession,
    item_id: uuid.UUID,
) -> CanonicalMemoryItem:
    """Mark a canonical item as disputed (CANM-01)."""
    return await update_canonical_item(session, item_id, status="disputed")


async def mark_canonical_stale(
    session: AsyncSession,
    item_id: uuid.UUID,
) -> CanonicalMemoryItem:
    """Mark a canonical item as stale (CANM-01)."""
    return await update_canonical_item(session, item_id, status="stale")


async def list_canonical_items(
    session: AsyncSession,
) -> List[CanonicalMemoryItem]:
    """Return all active canonical items (CANM-02: highest retrieval priority)."""
    result = await session.execute(
        select(CanonicalMemoryItem).where(
            CanonicalMemoryItem.source_status == "active"
        )
    )
    return list(result.scalars().all())
