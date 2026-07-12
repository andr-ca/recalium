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
async def test_promote_without_source_span_requires_confirmed(
    db_session_phase3: AsyncSession, raw_archive_row
):
    """CANM-04: a fact whose stored source_span is empty requires confirmed=True.

    GPT5.6 #9: the gate is keyed off the REAL stored span, so a client cannot pass
    has_source_span=True to bypass it.
    """
    import uuid as _uuid

    from app.domain.canonical_memory.service import PromotionNotConfirmedError
    from app.domain.derived_memory.models import Fact

    spanless = Fact(
        id=_uuid.uuid4(),
        raw_archive_id=raw_archive_row.id,
        fact_text="A fact with no verbatim source span.",
        source_span="",
        confidence_tier="low",
        derivation_method="llm_extraction",
        derivation_model="test-model",
    )
    db_session_phase3.add(spanless)
    await db_session_phase3.flush()

    with pytest.raises(PromotionNotConfirmedError):
        await promote_fact_to_canonical(
            session=db_session_phase3,
            fact_id=spanless.id,
            raw_archive_id=raw_archive_row.id,
            content="fact without span",
            promoted_by="user_ui",
            has_source_span=True,  # forged claim — must be ignored by the server
            confirmed=False,
        )


@pytest.mark.asyncio
async def test_promote_without_source_span_with_confirmed_succeeds(
    db_session_phase3: AsyncSession, raw_archive_row
):
    """CANM-04: a spanless fact can be promoted when confirmed=True."""
    import uuid as _uuid

    from app.domain.derived_memory.models import Fact

    spanless = Fact(
        id=_uuid.uuid4(),
        raw_archive_id=raw_archive_row.id,
        fact_text="Another spanless fact.",
        source_span="",
        confidence_tier="low",
        derivation_method="llm_extraction",
        derivation_model="test-model",
    )
    db_session_phase3.add(spanless)
    await db_session_phase3.flush()

    item = await promote_fact_to_canonical(
        session=db_session_phase3,
        fact_id=spanless.id,
        raw_archive_id=raw_archive_row.id,
        content="fact without span but confirmed",
        promoted_by="user_ui",
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


# ── GPT5.6 #9: server-authoritative promotion integrity ──────────────────────


@pytest.mark.asyncio
async def test_promote_nonexistent_fact_raises(db_session_phase3: AsyncSession):
    """A promotion referencing a missing fact is rejected, not silently created."""
    from app.domain.canonical_memory.service import FactNotFoundError

    with pytest.raises(FactNotFoundError):
        await promote_fact_to_canonical(
            session=db_session_phase3,
            fact_id=uuid.uuid4(),
            content="forged content",
            promoted_by="user_ui",
        )


@pytest.mark.asyncio
async def test_promote_mismatched_raw_archive_id_rejected(
    db_session_phase3: AsyncSession, raw_archive_row, fact_row
):
    """A client raw_archive_id that contradicts the fact's real source is rejected."""
    from app.domain.canonical_memory.service import SourceMismatchError

    with pytest.raises(SourceMismatchError):
        await promote_fact_to_canonical(
            session=db_session_phase3,
            fact_id=fact_row.id,
            raw_archive_id=uuid.uuid4(),  # not the fact's source
            content="content",
            promoted_by="user_ui",
        )


@pytest.mark.asyncio
async def test_promote_removed_fact_refused(
    db_session_phase3: AsyncSession, raw_archive_row, fact_row
):
    """A suppressed fact cannot be resurrected into canonical memory."""
    from app.domain.canonical_memory.service import SourceRemovedError

    fact_row.source_status = "source_removed"
    await db_session_phase3.flush()

    with pytest.raises(SourceRemovedError):
        await promote_fact_to_canonical(
            session=db_session_phase3,
            fact_id=fact_row.id,
            raw_archive_id=raw_archive_row.id,
            content="content",
            promoted_by="user_ui",
        )


@pytest.mark.asyncio
async def test_promote_deleted_source_refused(
    db_session_phase3: AsyncSession, raw_archive_row, fact_row
):
    """A fact whose underlying source item is soft-deleted cannot be promoted."""
    from datetime import datetime, timezone

    from app.domain.canonical_memory.service import SourceRemovedError

    raw_archive_row.deleted_at = datetime.now(timezone.utc)
    await db_session_phase3.flush()

    with pytest.raises(SourceRemovedError):
        await promote_fact_to_canonical(
            session=db_session_phase3,
            fact_id=fact_row.id,
            content="content",
            promoted_by="user_ui",
        )


@pytest.mark.asyncio
async def test_promote_records_server_provenance(
    db_session_phase3: AsyncSession, raw_archive_row, fact_row
):
    """Promotion records a server-computed provenance chain and server-derived linkage."""
    import json

    item = await promote_fact_to_canonical(
        session=db_session_phase3,
        fact_id=fact_row.id,
        content="user-curated canonical text",
        promoted_by="user_ui",
    )
    # Source linkage is derived from the fact, not the client (which passed none).
    assert item.raw_archive_id == raw_archive_row.id
    assert item.fact_id == fact_row.id

    prov = json.loads(item.provenance_note)
    assert prov["fact_id"] == str(fact_row.id)
    assert prov["raw_archive_id"] == str(raw_archive_row.id)
    assert prov["source_span"] == fact_row.source_span
    assert prov["source_content_hash"] == raw_archive_row.content_hash
    assert prov["promoted_without_source_span"] is False
