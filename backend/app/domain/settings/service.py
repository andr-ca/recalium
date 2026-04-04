"""Settings domain service — BYOK key validation and fingerprint storage.

SECURITY RULES (enforced here and by startup assertion):
1. API keys from .env are read at validation request time only.
2. After validation: store ONLY fingerprint (last 4 chars) + configured bool.
3. Never pass, log, or persist the full key string beyond the validation call.
4. Validation calls are "lightweight test calls" — models.list for OpenAI,
   models.list for Anthropic, /api/version for Ollama.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.settings.models import Settings
from app.infrastructure.settings import get_settings

logger = logging.getLogger(__name__)

ValidationStatusLiteral = Literal["valid", "invalid", "insufficient_permissions", "unchecked"]


@dataclass
class KeyStatus:
    configured: bool
    fingerprint: str | None
    validation_status: ValidationStatusLiteral | None
    validated_at: datetime | None


@dataclass
class SettingsState:
    openai: KeyStatus
    anthropic: KeyStatus
    ollama_base_url: str | None
    ollama: KeyStatus


@dataclass
class ValidationResult:
    provider: str
    status: ValidationStatusLiteral  # "valid" | "invalid" | "insufficient_permissions"
    message: str


def _fingerprint(key: str) -> str:
    """Return last 4 characters of an API key (safe for display/storage)."""
    return key[-4:] if len(key) >= 4 else "????"


async def _get_or_create_settings(session: AsyncSession) -> Settings:
    """Get the singleton settings row (id=1), creating it if absent."""
    result = await session.execute(select(Settings).where(Settings.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        row = Settings(id=1)
        session.add(row)
        await session.flush()
    return row


async def get_settings_state(session: AsyncSession) -> SettingsState:
    """Return current key configuration state (no plaintext keys)."""
    row = await _get_or_create_settings(session)
    env_settings = get_settings()

    # Sync configured flags from current environment (keys may have changed since last restart)
    openai_in_env = bool(env_settings.openai_api_key)
    anthropic_in_env = bool(env_settings.anthropic_api_key)
    ollama_in_env = bool(env_settings.ollama_base_url)

    # Update configured flags if they drift from environment
    needs_save = False
    if row.openai_key_configured != openai_in_env:
        row.openai_key_configured = openai_in_env
        if not openai_in_env:
            row.openai_key_fingerprint = None
            row.openai_validation_status = None
        needs_save = True
    if row.anthropic_key_configured != anthropic_in_env:
        row.anthropic_key_configured = anthropic_in_env
        if not anthropic_in_env:
            row.anthropic_key_fingerprint = None
            row.anthropic_validation_status = None
        needs_save = True
    if row.ollama_key_configured != ollama_in_env:
        row.ollama_key_configured = ollama_in_env
        if not ollama_in_env:
            row.ollama_validation_status = None
        needs_save = True

    if needs_save:
        row.updated_at = datetime.now(timezone.utc)

    return SettingsState(
        openai=KeyStatus(
            configured=row.openai_key_configured,
            fingerprint=row.openai_key_fingerprint,
            validation_status=row.openai_validation_status,
            validated_at=row.openai_validated_at,
        ),
        anthropic=KeyStatus(
            configured=row.anthropic_key_configured,
            fingerprint=row.anthropic_key_fingerprint,
            validation_status=row.anthropic_validation_status,
            validated_at=row.anthropic_validated_at,
        ),
        ollama_base_url=row.ollama_base_url,
        ollama=KeyStatus(
            configured=row.ollama_key_configured,
            fingerprint=row.ollama_key_fingerprint,
            validation_status=row.ollama_validation_status,
            validated_at=row.ollama_validated_at,
        ),
    )


async def validate_openai_key(session: AsyncSession, api_key: str) -> ValidationResult:
    """Validate OpenAI key via lightweight models.list call.

    On success: stores fingerprint + sets configured=True + validation_status='valid'.
    On failure: stores fingerprint + sets configured=True + validation_status='invalid'.
    Never stores the plaintext key.
    """
    provider = "openai"
    fingerprint = _fingerprint(api_key)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )

        if response.status_code == 200:
            status = "valid"
            message = "OpenAI key is valid."
        elif response.status_code == 401:
            status = "invalid"
            message = "Invalid API key. Check your OpenAI key and try again."
        elif response.status_code == 403:
            status = "insufficient_permissions"
            message = "Key valid but has insufficient permissions."
        elif response.status_code == 429:
            status = "valid"
            message = "Key is valid (rate limited, but authenticated)."
        else:
            status = "invalid"
            message = f"Unexpected response from OpenAI: HTTP {response.status_code}."

    except httpx.TimeoutException:
        status = "invalid"
        message = "OpenAI validation timed out. Check your network connection."
    except httpx.RequestError as e:
        status = "invalid"
        message = f"Network error during OpenAI validation: {e}"

    # Persist fingerprint (never the key itself)
    row = await _get_or_create_settings(session)
    row.openai_key_fingerprint = fingerprint
    row.openai_key_configured = True
    row.openai_validation_status = status
    row.openai_validated_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)

    logger.info("OpenAI key validation: status=%s, fingerprint=****%s", status, fingerprint)
    return ValidationResult(provider=provider, status=status, message=message)


async def validate_anthropic_key(session: AsyncSession, api_key: str) -> ValidationResult:
    """Validate Anthropic key via lightweight models.list call."""
    provider = "anthropic"
    fingerprint = _fingerprint(api_key)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
            )

        if response.status_code == 200:
            status = "valid"
            message = "Anthropic key is valid."
        elif response.status_code == 401:
            status = "invalid"
            message = "Invalid API key. Check your Anthropic key and try again."
        elif response.status_code == 403:
            status = "insufficient_permissions"
            message = "Key valid but has insufficient permissions."
        elif response.status_code == 429:
            status = "valid"
            message = "Key is valid (rate limited, but authenticated)."
        else:
            status = "invalid"
            message = f"Unexpected response from Anthropic: HTTP {response.status_code}."

    except httpx.TimeoutException:
        status = "invalid"
        message = "Anthropic validation timed out. Check your network connection."
    except httpx.RequestError as e:
        status = "invalid"
        message = f"Network error during Anthropic validation: {e}"

    # Persist fingerprint only
    row = await _get_or_create_settings(session)
    row.anthropic_key_fingerprint = fingerprint
    row.anthropic_key_configured = True
    row.anthropic_validation_status = status
    row.anthropic_validated_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)

    logger.info("Anthropic key validation: status=%s, fingerprint=****%s", status, fingerprint)
    return ValidationResult(provider=provider, status=status, message=message)


async def validate_ollama_connection(
    session: AsyncSession,
    base_url: str,
    api_key: str | None = None,
) -> ValidationResult:
    """Validate Ollama endpoint via /api/version call."""
    provider = "ollama"
    fingerprint = _fingerprint(api_key) if api_key else None

    # Normalize base_url
    base_url = base_url.rstrip("/")

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/api/version", headers=headers)

        if response.status_code == 200:
            status = "valid"
            try:
                version_data = response.json()
                version = version_data.get("version", "unknown")
            except (ValueError, KeyError):
                version = "unknown"
            message = f"Ollama endpoint is reachable (version: {version})."
        elif response.status_code == 401:
            status = "invalid"
            message = "Ollama endpoint requires authentication. Provide an API key."
        else:
            status = "invalid"
            message = f"Ollama endpoint returned HTTP {response.status_code}."

    except httpx.TimeoutException:
        status = "invalid"
        message = f"Ollama endpoint timed out: {base_url}"
    except httpx.RequestError as e:
        status = "invalid"
        message = f"Cannot reach Ollama endpoint {base_url}: {e}"

    # Persist (URL is not sensitive; fingerprint only for key)
    row = await _get_or_create_settings(session)
    row.ollama_base_url = base_url
    row.ollama_key_configured = api_key is not None
    row.ollama_key_fingerprint = fingerprint
    row.ollama_validation_status = status
    row.ollama_validated_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)

    logger.info("Ollama validation: status=%s, url=%s", status, base_url)
    return ValidationResult(provider=provider, status=status, message=message)
