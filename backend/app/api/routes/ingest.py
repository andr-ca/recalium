"""Ingest routes — POST /api/ingest and POST /api/ingest/file."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ingest.service import ingest_file_content, ingest_text_content
from app.domain.policy.resolver import (
    ALLOWED_PROCESSING_MODES,
    ALLOWED_SENSITIVITY_HINTS,
    is_valid_processing_mode,
    is_valid_sensitivity_hint,
)
from app.infrastructure.db import get_session

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB hard limit


class IngestTextRequest(BaseModel):
    """Paste / programmatic text ingest.

    UI paste keeps the minimal shape (``content`` + optional ``source_name``).
    Daemon / outbox clients may also send the MCP-aligned metadata fields so
    REST can flush the same payloads as ``ingest_memory`` without speaking SSE.
    """

    mode: str = "text"
    content: str
    source_name: str | None = None
    source_metadata: dict[str, Any] | None = None
    client_identity: str | None = None
    import_method: str | None = None
    idempotency_key: str | None = None
    sensitivity_hint: str | None = None
    project_hint: str | None = None
    processing_mode: str = "deferred"

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
    idempotent_replay: bool = False
    idempotency_key: str | None = None


@router.post("", response_model=IngestResponse, status_code=202)
async def ingest_text(
    request: IngestTextRequest,
    session: AsyncSession = Depends(get_session),
) -> IngestResponse:
    """POST /api/ingest — ingest plain text or JSON via paste / HTTP clients.

    Returns: HTTP 202 with item_count and archive_ids.
    P95 target: ≤ 1s (no processing, just parse + DB write).

    Optional MCP-aligned fields (``source_metadata``, ``idempotency_key``, …)
    enable durable client-side outbox replay without MCP SSE.
    """
    if not is_valid_processing_mode(request.processing_mode):
        raise HTTPException(
            status_code=422,
            detail=(
                f"invalid processing_mode {request.processing_mode!r}; "
                f"allowed: {sorted(ALLOWED_PROCESSING_MODES)}"
            ),
        )
    if not is_valid_sensitivity_hint(request.sensitivity_hint):
        raise HTTPException(
            status_code=422,
            detail=(
                f"invalid sensitivity_hint {request.sensitivity_hint!r}; "
                f"allowed: {sorted(ALLOWED_SENSITIVITY_HINTS)}"
            ),
        )

    source_metadata = request.source_metadata or {}
    source_type = str(
        source_metadata.get("source_type")
        or source_metadata.get("system")
        or ("api" if source_metadata or request.idempotency_key else "paste")
    )
    effective_source_name = str(
        source_metadata.get("source_name")
        or source_metadata.get("session_id")
        or source_metadata.get("conversation_id")
        or request.source_name
        or "Paste Import"
    )
    actor = request.client_identity or "user_ui"
    import_method = request.import_method or (
        "rest_api" if source_metadata or request.idempotency_key else "paste"
    )

    metadata: dict[str, Any] = {
        "import_method": import_method,
        "processing_mode": request.processing_mode,
        "transport": "rest",
    }
    if source_metadata:
        metadata["source_metadata"] = source_metadata
    if request.client_identity:
        metadata["client_identity"] = request.client_identity
    if request.idempotency_key:
        metadata["idempotency_key"] = request.idempotency_key
    if request.sensitivity_hint:
        metadata["sensitivity_hint"] = request.sensitivity_hint
    if request.project_hint:
        metadata["project_hint"] = request.project_hint

    try:
        result = await ingest_text_content(
            session=session,
            content=request.content,
            source_name=effective_source_name,
            actor=actor,
            source_type=source_type,
            extra_metadata=metadata,
            idempotency_key=request.idempotency_key,
        )
    except ValueError as e:
        detail = str(e)
        if "idempotency key" in detail:
            raise HTTPException(
                status_code=409,
                detail={
                    "status": "error",
                    "error": {
                        "code": "idempotency_conflict",
                        "message": detail,
                        "details": {"field": "idempotency_key"},
                        "retryable": False,
                    },
                },
            ) from e
        raise HTTPException(status_code=422, detail=detail) from e

    return IngestResponse(
        status="accepted",
        item_count=result.item_count,
        archive_ids=[str(aid) for aid in result.archive_ids],
        idempotent_replay=result.idempotent_replay,
        idempotency_key=request.idempotency_key,
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
