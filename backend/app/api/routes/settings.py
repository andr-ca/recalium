"""Settings / BYOK route stubs — implementation in Plan 01-07."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/keys")
async def get_keys() -> dict:
    """GET /api/settings/keys — returns key configuration status (no plaintext keys).
    Stub: returns unconfigured state until Plan 01-07 implementation.
    """
    unconfigured = {"configured": False, "fingerprint": None, "validation_status": "unchecked", "validated_at": None}
    return {
        "openai": unconfigured,
        "anthropic": unconfigured,
        "ollama": {**unconfigured, "base_url": None},
    }


@router.post("/keys/validate")
async def validate_key() -> dict:
    """POST /api/settings/keys/validate — validates a provider API key.
    Stub: returns error until Plan 01-07 implementation.
    """
    return {"error": "Not yet implemented — see Plan 01-07"}
