"""Portability routes — export and import memory bundles (PORT-01).

Bundle format v1:
{
  "format": "recalium-memory-bundle",
  "version": "1",
  "exported_at": "<ISO 8601>",
  "items": [
    {
      "id": "<uuid>",
      "source_type": "<str>",
      "source_name": "<str|null>",
      "ingested_at": "<ISO 8601>",
      "raw_content": "<str>",
      "content_hash": "<str>",
      "conversation_count": <int>,
      "metadata": <dict|null>
    },
    ...
  ]
}

Deleted items are excluded from export (PRIV-03 compliant).
Import skips items whose content_hash already exists (including deleted).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem
from app.domain.ingest.service import ingest_text_content
from app.infrastructure.db import get_session

logger = logging.getLogger(__name__)
router = APIRouter()

_BUNDLE_FORMAT = "recalium-memory-bundle"
_BUNDLE_VERSION = "1"


@router.get("/export/bundle")
async def export_bundle(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """GET /api/export/bundle — export all non-deleted archive items as a JSON bundle."""
    result = await session.execute(
        select(RawArchiveItem)
        .where(RawArchiveItem.deleted_at.is_(None))
        .order_by(RawArchiveItem.ingested_at)
    )
    items = result.scalars().all()

    bundle = {
        "format": _BUNDLE_FORMAT,
        "version": _BUNDLE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "items": [
            {
                "id": str(item.id),
                "source_type": item.source_type,
                "source_name": item.source_name,
                "ingested_at": item.ingested_at.isoformat(),
                "raw_content": item.raw_content,
                "content_hash": item.content_hash,
                "conversation_count": item.conversation_count,
                "metadata": item.metadata_json,
            }
            for item in items
        ],
    }

    return JSONResponse(
        content=bundle,
        headers={"Content-Disposition": 'attachment; filename="recalium-bundle.json"'},
    )


@router.post("/import/bundle")
async def import_bundle(
    bundle: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """POST /api/import/bundle — import a memory bundle JSON."""
    if bundle.get("format") != _BUNDLE_FORMAT:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid bundle format: expected '{_BUNDLE_FORMAT}', "
                   f"got '{bundle.get('format')}'",
        )
    if str(bundle.get("version", "")) != _BUNDLE_VERSION:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported bundle version: expected '{_BUNDLE_VERSION}', "
                   f"got '{bundle.get('version')}'",
        )

    items = bundle.get("items", [])
    if not isinstance(items, list):
        raise HTTPException(status_code=422, detail="Bundle 'items' must be a list")

    imported = 0
    skipped = 0
    errors: list[str] = []

    for i, item in enumerate(items):
        content_hash = item.get("content_hash", "")
        raw_content = item.get("raw_content", "")
        source_name = item.get("source_name")

        if not raw_content:
            errors.append(f"Item {i}: missing raw_content")
            continue

        # Dedup check: skip if content_hash already exists (including deleted)
        if content_hash:
            existing = await session.execute(
                text("SELECT id FROM raw_archive WHERE content_hash = :hash"),
                {"hash": content_hash},
            )
            if existing.fetchone() is not None:
                skipped += 1
                continue

        try:
            await ingest_text_content(
                session=session,
                content=raw_content,
                source_name=source_name,
            )
            await session.flush()
            imported += 1
        except Exception as exc:
            await session.rollback()
            errors.append(f"Item {i} ({source_name!r}): {exc}")

    await session.commit()

    logger.info(
        "Bundle import complete: imported=%d skipped=%d errors=%d",
        imported, skipped, len(errors),
    )
    return {"imported": imported, "skipped": skipped, "errors": errors}
