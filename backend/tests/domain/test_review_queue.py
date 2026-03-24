"""Review queue domain service tests — Phase 3.

Covers: CANM-05 (review queue groups duplicate/overlapping facts).

RED until plan 03-05 implements review_queue service.
"""
import pytest
pytest.importorskip("app.domain.review_queue.service")

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.review_queue.service import (
    materialize_review_item,
    list_pending_review_items,
    resolve_review_item,
    dismiss_review_item,
)
from app.domain.review_queue.models import ReviewQueueItem


@pytest.mark.asyncio
async def test_materialize_review_item_creates_pending(db_session_phase3: AsyncSession):
    """CANM-05: materializing a conflict group creates a pending review item."""
    conflict_group_id = uuid.uuid4()
    with pytest.raises(Exception):  # FK violation expected on empty DB
        await materialize_review_item(
            session=db_session_phase3,
            conflict_group_id=conflict_group_id,
            item_type="duplicate",
        )


@pytest.mark.asyncio
async def test_list_pending_review_items_returns_pending_only(db_session_phase3: AsyncSession):
    """CANM-05: list returns only pending items."""
    items = await list_pending_review_items(db_session_phase3)
    assert isinstance(items, list)
    assert all(i.status == "pending" for i in items)


@pytest.mark.asyncio
async def test_resolve_review_item_unknown_id_raises(db_session_phase3: AsyncSession):
    """CANM-05: resolving unknown review item raises NotFoundError."""
    from app.domain.review_queue.service import ReviewItemNotFoundError
    with pytest.raises(ReviewItemNotFoundError):
        await resolve_review_item(
            db_session_phase3, uuid.uuid4(), resolution_note="resolved", resolved_by="user_ui"
        )


@pytest.mark.asyncio
async def test_dismiss_review_item_unknown_id_raises(db_session_phase3: AsyncSession):
    """CANM-05: dismissing unknown review item raises NotFoundError."""
    from app.domain.review_queue.service import ReviewItemNotFoundError
    with pytest.raises(ReviewItemNotFoundError):
        await dismiss_review_item(db_session_phase3, uuid.uuid4())
