"""Review queue API routes.

CANM-05: Groups duplicate/overlapping facts for manageable cleanup.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.review_queue.service import (
    ReviewItemNotFoundError,
    dismiss_review_item,
    list_pending_review_items,
    resolve_review_item,
)
from app.infrastructure.db import get_session

router = APIRouter(prefix="/api/review-queue", tags=["review-queue"])


class ResolveBody(BaseModel):
    resolved_by: str = "user_ui"
    resolution_note: str = ""


def _item_to_dict(item) -> dict:
    return {
        "id": str(item.id),
        "conflict_group_id": str(item.conflict_group_id),
        "item_type": item.item_type,
        "status": item.status,
        "source_status": item.source_status,
        "resolution_note": item.resolution_note,
        "resolved_by": item.resolved_by,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
    }


@router.get("")
async def list_items(session: AsyncSession = Depends(get_session)) -> dict:
    items = await list_pending_review_items(session)
    return {"items": [_item_to_dict(i) for i in items], "count": len(items)}


@router.post("/{item_id}/resolve")
async def resolve(
    item_id: uuid.UUID,
    body: ResolveBody,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        item = await resolve_review_item(
            session, item_id,
            resolution_note=body.resolution_note,
            resolved_by=body.resolved_by,
        )
    except ReviewItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _item_to_dict(item)


@router.post("/{item_id}/dismiss")
async def dismiss(
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        item = await dismiss_review_item(session, item_id)
    except ReviewItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _item_to_dict(item)
