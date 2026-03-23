"""Ingest route stubs — implementation in Plan 01-05."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("")
async def ingest_text() -> JSONResponse:
    """POST /api/ingest — accepts text paste or JSON file upload.
    Stub: returns 501 until Plan 01-05 implementation.
    """
    return JSONResponse(
        status_code=501,
        content={"error": "Not yet implemented — see Plan 01-05"}
    )


@router.post("/file")
async def ingest_file() -> JSONResponse:
    """POST /api/ingest/file — accepts file upload.
    Stub: returns 501 until Plan 01-05 implementation.
    """
    return JSONResponse(
        status_code=501,
        content={"error": "Not yet implemented — see Plan 01-05"}
    )
