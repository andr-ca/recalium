"""Archive route stubs — implementation in Plan 01-06."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_archive() -> dict:
    """GET /api/archive — returns paginated raw archive items.
    Stub: returns empty list until Plan 01-06 implementation.
    """
    return {"items": [], "total": 0, "offset": 0, "limit": 50}
