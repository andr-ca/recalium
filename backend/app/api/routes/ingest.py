"""Ingest route stubs — implementation in Plan 01-05."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def ingest_text() -> dict:
    """POST /api/ingest — accepts text paste or JSON file upload.
    Stub: returns 501 until Plan 01-05 implementation.
    """
    return {"error": "Not yet implemented — see Plan 01-05"}


@router.post("/file")
async def ingest_file() -> dict:
    """POST /api/ingest/file — accepts file upload.
    Stub: returns 501 until Plan 01-05 implementation.
    """
    return {"error": "Not yet implemented — see Plan 01-05"}
