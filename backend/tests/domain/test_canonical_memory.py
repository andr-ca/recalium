"""Canonical memory domain service tests — Phase 3.

Covers: CANM-01 (inspect/edit/delete/promote), CANM-02 (retrieval priority),
        CANM-03 (explicit action only), CANM-04 (source_span confirmation),
        WEBUI-05 (provenance navigation — source link present).

RED until plan 03-04 implements canonical_memory service.
"""
import pytest
pytest.importorskip("app.domain.canonical_memory.service")

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.canonical_memory.service import (
    promote_fact_to_canonical,
    create_manual_canonical,
    update_canonical_item,
    delete_canonical_item,
    mark_canonical_disputed,
    mark_canonical_stale,
    list_canonical_items,
    get_canonical_item,
)
from app.domain.canonical_memory.models import CanonicalMemoryItem


@pytest.mark.asyncio
async def test_promote_fact_to_canonical_creates_item(db_session_phase3: AsyncSession, raw_archive_row, fact_row):
    """CANM-01 + CANM-03: explicit promote creates canonical item."""
    item = await promote_fact_to_canonical(
        session=db_session_phase3,
        fact_id=fact_row.id,
        raw_archive_id=raw_archive_row.id,
        content="The user prefers Python over JavaScript.",
        promoted_by="user_ui",
    )
    assert item.status == "active"
    assert item.promoted_from == "fact"
    assert item.fact_id == fact_row.id


@pytest.mark.asyncio
async def test_promote_without_source_span_requires_confirmed(db_session_phase3: AsyncSession):
    """CANM-04: fact without source_span requires confirmed=True."""
    from app.domain.canonical_memory.service import PromotionNotConfirmedError
    with pytest.raises(PromotionNotConfirmedError):
        await promote_fact_to_canonical(
            session=db_session_phase3,
            fact_id=uuid.uuid4(),
            raw_archive_id=uuid.uuid4(),
            content="fact without span",
            promoted_by="user_ui",
            has_source_span=False,
            confirmed=False,
        )


@pytest.mark.asyncio
async def test_promote_without_source_span_with_confirmed_succeeds(db_session_phase3: AsyncSession, raw_archive_row, fact_row):
    """CANM-04: fact without source_span but confirmed=True succeeds."""
    item = await promote_fact_to_canonical(
        session=db_session_phase3,
        fact_id=fact_row.id,
        raw_archive_id=raw_archive_row.id,
        content="fact without span but confirmed",
        promoted_by="user_ui",
        has_source_span=False,
        confirmed=True,
    )
    assert item is not None
    assert item.status == "active"


@pytest.mark.asyncio
async def test_create_manual_canonical(db_session_phase3: AsyncSession):
    """CANM-01: user can create canonical item manually (not promoted from fact)."""
    item = await create_manual_canonical(
        session=db_session_phase3,
        content="Manual canonical note about the project.",
        promoted_by="user_ui",
    )
    assert item.promoted_from == "manual"
    assert item.fact_id is None
    assert item.status == "active"


@pytest.mark.asyncio
async def test_mark_canonical_disputed(db_session_phase3: AsyncSession):
    """CANM-01: user can mark a canonical item as disputed."""
    item = await create_manual_canonical(
        session=db_session_phase3, content="test", promoted_by="user_ui"
    )
    updated = await mark_canonical_disputed(db_session_phase3, item.id)
    assert updated.status == "disputed"


@pytest.mark.asyncio
async def test_mark_canonical_stale(db_session_phase3: AsyncSession):
    """CANM-01: user can mark a canonical item as stale."""
    item = await create_manual_canonical(
        session=db_session_phase3, content="test", promoted_by="user_ui"
    )
    updated = await mark_canonical_stale(db_session_phase3, item.id)
    assert updated.status == "stale"


@pytest.mark.asyncio
async def test_delete_canonical_item(db_session_phase3: AsyncSession):
    """CANM-01: user can delete a canonical item (soft delete via source_status)."""
    item = await create_manual_canonical(
        session=db_session_phase3, content="to be deleted", promoted_by="user_ui"
    )
    await delete_canonical_item(db_session_phase3, item.id)
    items = await list_canonical_items(db_session_phase3)
    ids = [i.id for i in items]
    assert item.id not in ids


@pytest.mark.asyncio
async def test_list_canonical_items_active_only(db_session_phase3: AsyncSession):
    """CANM-02: list only returns active items."""
    await create_manual_canonical(db_session_phase3, "active item", "user_ui")
    items = await list_canonical_items(db_session_phase3)
    assert all(i.source_status == "active" for i in items)


@pytest.mark.asyncio
async def test_canonical_item_has_source_link(db_session_phase3: AsyncSession, raw_archive_row, fact_row):
    """WEBUI-05: canonical item retains source archive link for provenance navigation."""
    item = await promote_fact_to_canonical(
        session=db_session_phase3,
        fact_id=fact_row.id,
        raw_archive_id=raw_archive_row.id,
        content="fact content",
        promoted_by="user_ui",
    )
    assert item.raw_archive_id == raw_archive_row.id
