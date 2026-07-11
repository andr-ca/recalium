"""Import routes — POST /api/import (ChatGPT / Claude conversation exports)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.imports.service import import_conversations
from app.infrastructure.db import get_session

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_IMPORT_BYTES = 200 * 1024 * 1024  # 200 MB — full export archives can be large


class ImportResponse(BaseModel):
    status: str = "accepted"
    source_format: str
    conversation_count: int
    imported: int
    skipped: int
    archive_ids: list[str]


@router.post("", response_model=ImportResponse, status_code=202)
async def import_export(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> ImportResponse:
    """Import a ChatGPT or Claude ``conversations.json`` export.

    Each conversation becomes its own archive item so it is summarized,
    extracted, and linked individually with source provenance. Re-importing the
    same export is idempotent (already-imported conversations are skipped).
    """
    if file.size and file.size > MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file.size} bytes. Max: {MAX_IMPORT_BYTES} bytes.",
        )

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="File too large (200 MB limit).")

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="File must be UTF-8 encoded JSON.")

    try:
        result = await import_conversations(session=session, content=content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ImportResponse(
        status="accepted",
        source_format=result.source_format,
        conversation_count=result.conversation_count,
        imported=result.imported,
        skipped=result.skipped,
        archive_ids=[str(aid) for aid in result.archive_ids],
    )
