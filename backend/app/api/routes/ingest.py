"""Ingest routes — POST /api/ingest and POST /api/ingest/file."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ingest.service import ingest_file_content, ingest_text_content
from app.infrastructure.db import get_session

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB hard limit


class IngestTextRequest(BaseModel):
    mode: str = "text"
    content: str
    source_name: str | None = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content must not be empty")
        return v


class IngestResponse(BaseModel):
    status: str = "accepted"
    item_count: int
    archive_ids: list[str]


@router.post("", response_model=IngestResponse, status_code=202)
async def ingest_text(
    request: IngestTextRequest,
    session: AsyncSession = Depends(get_session),
) -> IngestResponse:
    """POST /api/ingest — ingest plain text or JSON via paste.

    Returns: HTTP 202 with item_count and archive_ids.
    P95 target: ≤ 1s (no processing, just parse + DB write).
    """
    try:
        result = await ingest_text_content(
            session=session,
            content=request.content,
            source_name=request.source_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return IngestResponse(
        status="accepted",
        item_count=result.item_count,
        archive_ids=[str(aid) for aid in result.archive_ids],
    )


@router.post("/file", response_model=IngestResponse, status_code=202)
async def ingest_file(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> IngestResponse:
    """POST /api/ingest/file — ingest a .json, .txt, or .md file upload.

    Returns: HTTP 202 with item_count and archive_ids.
    P95 target: ≤ 1s (no processing, just parse + DB write).
    """
    if file.size and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file.size} bytes. Max: {MAX_UPLOAD_BYTES} bytes.",
        )

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (50 MB limit).")

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail="File must be UTF-8 encoded text (.json, .txt, .md).",
        )

    filename = file.filename or "upload"
    try:
        result = await ingest_file_content(
            session=session,
            filename=filename,
            content=content,
            source_name=filename,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return IngestResponse(
        status="accepted",
        item_count=result.item_count,
        archive_ids=[str(aid) for aid in result.archive_ids],
    )
