"""Canonical memory API routes.

CANM-01: Create, edit, delete, mark-disputed/stale
CANM-02: List returns source_status='active' items
CANM-03: Promote requires explicit user action
CANM-04: Promote with empty source_span requires confirmed=True
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.canonical_memory.service import (
    CanonicalItemNotFoundError,
    FactNotFoundError,
    PromotionNotConfirmedError,
    SourceMismatchError,
    SourceRemovedError,
    create_manual_canonical,
    delete_canonical_item,
    get_canonical_item,
    list_canonical_items,
    mark_canonical_disputed,
    mark_canonical_stale,
    promote_fact_to_canonical,
    update_canonical_item,
)
from app.infrastructure.db import get_session

router = APIRouter(prefix="/api/canonical", tags=["canonical"])


class CreateCanonicalBody(BaseModel):
    content: str
    promoted_by: str = "user_ui"


class UpdateCanonicalBody(BaseModel):
    content: str | None = None
    status: str | None = None


class PromoteBody(BaseModel):
    fact_id: uuid.UUID
    raw_archive_id: uuid.UUID
    content: str
    has_source_span: bool = True
    confirmed: bool = False
    promoted_by: str = "user_ui"


def _item_to_dict(item) -> dict:
    return {
        "id": str(item.id),
        "raw_archive_id": str(item.raw_archive_id) if item.raw_archive_id else None,
        "fact_id": str(item.fact_id) if item.fact_id else None,
        "content": item.content,
        "status": item.status,
        "source_status": item.source_status,
        "promoted_from": item.promoted_from,
        "promoted_by": item.promoted_by,
        "provenance_note": item.provenance_note,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@router.get("")
async def list_items(session: AsyncSession = Depends(get_session)) -> dict:
    items = await list_canonical_items(session)
    return {"items": [_item_to_dict(i) for i in items], "count": len(items)}


@router.post("", status_code=201)
async def create_item(
    body: CreateCanonicalBody,
    session: AsyncSession = Depends(get_session),
) -> dict:
    item = await create_manual_canonical(
        session,
        content=body.content,
        promoted_by=body.promoted_by,
    )
    return _item_to_dict(item)


# IMPORTANT: /promote must be declared BEFORE /{item_id} to avoid
# FastAPI trying to parse "promote" as a UUID and returning 422.
@router.post("/promote", status_code=201)
async def promote_fact_endpoint(
    body: PromoteBody,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Promote a fact to canonical memory (CANM-03/CANM-04).

    GPT5.6 #9: source linkage and the source-span attestation are derived from the
    stored fact server-side; the client-supplied ``has_source_span`` is ignored.
    """
    try:
        item = await promote_fact_to_canonical(
            session,
            fact_id=body.fact_id,
            raw_archive_id=body.raw_archive_id,
            content=body.content,
            promoted_by=body.promoted_by,
            confirmed=body.confirmed,
        )
    except FactNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SourceMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SourceRemovedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PromotionNotConfirmedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _item_to_dict(item)


@router.get("/{item_id}")
async def get_item(
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    item = await get_canonical_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Canonical item {item_id} not found")
    return _item_to_dict(item)


@router.patch("/{item_id}")
async def update_item(
    item_id: uuid.UUID,
    body: UpdateCanonicalBody,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        item = await update_canonical_item(
            session,
            item_id=item_id,
            content=body.content,
            status=body.status,
        )
    except CanonicalItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _item_to_dict(item)


@router.delete("/{item_id}", status_code=204)
async def delete_item(
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    try:
        await delete_canonical_item(session, item_id=item_id)
    except CanonicalItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{item_id}/dispute")
async def dispute_item(
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        item = await mark_canonical_disputed(session, item_id=item_id)
    except CanonicalItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _item_to_dict(item)


@router.post("/{item_id}/mark-stale")
async def stale_item(
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        item = await mark_canonical_stale(session, item_id=item_id)
    except CanonicalItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _item_to_dict(item)
