"""Settings routes — BYOK key management (fingerprints only — no plaintext keys)."""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.jobs.service import reactivate_pending_provider_jobs
from app.domain.settings.service import (
    ValidationResult,
    get_settings_state,
    validate_anthropic_key,
    validate_ollama_connection,
    validate_openai_key,
)
from app.infrastructure.db import get_session

logger = logging.getLogger(__name__)
router = APIRouter()


class KeyStatusOut(BaseModel):
    configured: bool
    fingerprint: str | None
    validation_status: str | None
    validated_at: str | None  # ISO 8601 or None


class OllamaKeyStatusOut(KeyStatusOut):
    base_url: str | None


class SettingsResponse(BaseModel):
    openai: KeyStatusOut
    anthropic: KeyStatusOut
    ollama: OllamaKeyStatusOut


class ValidateKeyRequest(BaseModel):
    provider: Literal["openai", "anthropic", "ollama"]  # Literal enforces valid values
    api_key: str = ""
    base_url: str | None = None  # Ollama only


class ValidateKeyResponse(BaseModel):
    provider: str
    status: str  # "valid" | "invalid" | "insufficient_permissions"
    message: str


@router.get("/keys", response_model=SettingsResponse)
async def get_keys(session: AsyncSession = Depends(get_session)) -> SettingsResponse:
    """GET /api/settings/keys — returns key configuration status.

    SECURITY: Response contains ONLY fingerprints and booleans.
    Plaintext keys are NEVER returned in any response.
    """
    state = await get_settings_state(session)

    def _format_dt(dt) -> str | None:
        return dt.isoformat() if dt else None

    return SettingsResponse(
        openai=KeyStatusOut(
            configured=state.openai.configured,
            fingerprint=state.openai.fingerprint,
            validation_status=state.openai.validation_status,
            validated_at=_format_dt(state.openai.validated_at),
        ),
        anthropic=KeyStatusOut(
            configured=state.anthropic.configured,
            fingerprint=state.anthropic.fingerprint,
            validation_status=state.anthropic.validation_status,
            validated_at=_format_dt(state.anthropic.validated_at),
        ),
        ollama=OllamaKeyStatusOut(
            configured=state.ollama.configured,
            fingerprint=state.ollama.fingerprint,
            validation_status=state.ollama.validation_status,
            validated_at=_format_dt(state.ollama.validated_at),
            base_url=state.ollama_base_url,
        ),
    )


@router.post("/keys/validate", response_model=ValidateKeyResponse)
async def validate_key(
    request: ValidateKeyRequest,
    session: AsyncSession = Depends(get_session),
) -> ValidateKeyResponse:
    """POST /api/settings/keys/validate — validate a provider key with a test call.

    SECURITY:
    - The api_key value is used ONLY for the validation HTTP call and fingerprinting.
    - api_key is NEVER stored in the database.
    - Only fingerprint (last 4 chars) is persisted.
    """
    try:
        result: ValidationResult | None = None
        if request.provider == "openai":
            if not request.api_key:
                raise HTTPException(status_code=422, detail="api_key is required for OpenAI")
            result = await validate_openai_key(session=session, api_key=request.api_key)

        elif request.provider == "anthropic":
            if not request.api_key:
                raise HTTPException(status_code=422, detail="api_key is required for Anthropic")
            result = await validate_anthropic_key(session=session, api_key=request.api_key)

        elif request.provider == "ollama":
            if not request.base_url:
                raise HTTPException(status_code=422, detail="base_url is required for Ollama")
            result = await validate_ollama_connection(
                session=session,
                base_url=request.base_url,
                api_key=request.api_key or None,
            )
        else:
            raise HTTPException(status_code=422, detail=f"Unknown provider: {request.provider!r}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Key validation error for %s: %s", request.provider, e)
        raise HTTPException(status_code=500, detail="Key validation failed unexpectedly.")

    if result is None:  # should be unreachable — Literal enforces valid providers
        raise HTTPException(status_code=500, detail="Key validation failed unexpectedly.")

    # BYOK-08: When a key is validated as "valid", reactivate any pending_provider jobs
    # so they are re-queued and processed with the newly configured provider.
    if result.status == "valid":
        await reactivate_pending_provider_jobs(session)

    return ValidateKeyResponse(
        provider=result.provider,
        status=result.status,
        message=result.message,
    )
