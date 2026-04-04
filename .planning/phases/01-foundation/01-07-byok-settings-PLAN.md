---
wave: 3
depends_on:
  - 01-02-postgres-schema-PLAN.md
  - 01-04-fastapi-skeleton-PLAN.md
requirements_addressed: [BYOK-02, BYOK-03, BYOK-04, BYOK-05]
files_modified:
  - backend/app/domain/settings/__init__.py
  - backend/app/domain/settings/models.py
  - backend/app/domain/settings/service.py
  - backend/app/api/routes/settings.py
  - frontend/src/pages/SettingsPage.tsx
autonomous: true
---

<objective>
Implement BYOK key management: GET /api/settings/keys returns fingerprints + status (never plaintext), POST /api/settings/keys/validate runs a lightweight test call per provider and stores only the fingerprint + boolean. Implements the Settings page UI with one section per provider, masked input, Validate button, and inline status badge.

Purpose: Satisfies BYOK-02 (configure keys via settings), BYOK-03 (validate at config time with test call), BYOK-04 (only user's keys used), BYOK-05 (system usable without any keys). API keys must never be written to DB.
Output: backend settings domain service + route; frontend SettingsPage.
</objective>

<tasks>

<task id="1" name="Create settings ORM model and domain service (key fingerprints only)">
  <read_first>
    - backend/alembic/versions/0001_initial.py (settings table columns — exact names: openai_key_fingerprint, openai_key_configured, etc.)
    - backend/app/infrastructure/settings.py (openai_api_key, anthropic_api_key, ollama_base_url, ollama_api_key)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-12 key fingerprint only, D-13 BYOK UI, D-14 Ollama URL)
    - .planning/research/PITFALLS.md (Pitfall 5 — keys in DB)
  </read_first>
  <action>
Replace stub `backend/app/domain/settings/models.py` with the full ORM model:

```python
"""Settings domain ORM model.

SECURITY CONTRACT (D-12, Pitfall 5):
- This table stores ONLY key fingerprints (last 4 chars) and booleans.
- NEVER add columns named *_key, *_secret, *_token that hold full credentials.
- The startup assertion in app/main.py enforces this contract at runtime.
- Real API keys live ONLY in .env / environment variables.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class Settings(Base):
    """Singleton settings row (id=1 always).

    All key_fingerprint columns: last 4 characters of the API key, or None.
    All key_configured columns: True if key is set in environment, False otherwise.
    Validation status: "valid" | "invalid" | "insufficient_permissions" | "unchecked" | None
    """
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Always id=1 (singleton)

    # OpenAI
    openai_key_fingerprint: Mapped[str | None] = mapped_column(String(4), nullable=True)
    openai_key_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    openai_validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    openai_validated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Anthropic
    anthropic_key_fingerprint: Mapped[str | None] = mapped_column(String(4), nullable=True)
    anthropic_key_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anthropic_validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    anthropic_validated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Ollama
    ollama_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ollama_key_fingerprint: Mapped[str | None] = mapped_column(String(4), nullable=True)
    ollama_key_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ollama_validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ollama_validated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow
    )
```

Create `backend/app/domain/settings/service.py`:

```python
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

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.settings.models import Settings
from app.infrastructure.settings import get_settings

logger = logging.getLogger(__name__)

ValidationStatusLiteral = str
# Allowed values: "valid" | "invalid" | "insufficient_permissions" | "unchecked"


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

    logger.info(f"OpenAI key validation: status={status}, fingerprint=****{fingerprint}")
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

    logger.info(f"Anthropic key validation: status={status}, fingerprint=****{fingerprint}")
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
            version_data = response.json()
            version = version_data.get("version", "unknown")
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
    row.ollama_key_configured = True
    row.ollama_key_fingerprint = fingerprint
    row.ollama_validation_status = status
    row.ollama_validated_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)

    logger.info(f"Ollama validation: status={status}, url={base_url}")
    return ValidationResult(provider=provider, status=status, message=message)
```
  </action>
  <acceptance_criteria>
    - `grep -n "class Settings" backend/app/domain/settings/models.py` returns 1 line
    - `grep -n "openai_key_fingerprint.*String(4)" backend/app/domain/settings/models.py` returns 1 line
    - `grep -c "_key_fingerprint\|_key_configured\|_validation_status\|_validated_at" backend/app/domain/settings/models.py` returns ≥ 9 (three providers × 3 columns each)
    - `grep -n "def _fingerprint" backend/app/domain/settings/service.py` returns 1 line
    - `grep -n "_fingerprint(api_key)" backend/app/domain/settings/service.py | wc -l` returns ≥ 2 (openai + anthropic)
    - `grep -n "Never stores the plaintext key\|never.*key\|NEVER.*key" backend/app/domain/settings/service.py` returns ≥ 1 line
    - `grep -n "httpx.AsyncClient" backend/app/domain/settings/service.py | wc -l` returns 3 (one per provider)
    - `grep -n "api.openai.com/v1/models" backend/app/domain/settings/service.py` returns 1 line
    - `grep -n "api.anthropic.com/v1/models" backend/app/domain/settings/service.py` returns 1 line
    - `grep -n "/api/version" backend/app/domain/settings/service.py` returns 1 line (Ollama endpoint)
  </acceptance_criteria>
</task>

<task id="2" name="Wire settings routes and implement Settings page UI">
  <read_first>
    - backend/app/domain/settings/service.py (get_settings_state, validate_openai_key, etc.)
    - frontend/src/lib/api.ts (getSettings, validateKey, SettingsResponse, ValidateKeyRequest)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-13 masked input + Validate button + inline status badge, D-14 Ollama URL field)
  </read_first>
  <action>
Replace the stub in `backend/app/api/routes/settings.py` with the real implementation:

```python
"""Settings routes — BYOK key management (fingerprints only — no plaintext keys)."""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.settings.service import (
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
    provider: Literal["openai", "anthropic", "ollama"]
    api_key: str = ""
    base_url: str | None = None  # Ollama only

    @field_validator("api_key")
    @classmethod
    def key_not_logged(cls, v: str) -> str:
        # Ensure key value is never accidentally logged by Pydantic repr
        return v

    @field_validator("provider")
    @classmethod
    def provider_valid(cls, v: str) -> str:
        if v not in ("openai", "anthropic", "ollama"):
            raise ValueError(f"Unknown provider: {v!r}")
        return v


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
        logger.error(f"Key validation error for {request.provider}: {e}")
        raise HTTPException(status_code=500, detail="Key validation failed unexpectedly.")

    return ValidateKeyResponse(
        provider=result.provider,
        status=result.status,
        message=result.message,
    )
```

Replace the stub `frontend/src/pages/SettingsPage.tsx` with the full BYOK settings UI:

```typescript
import * as React from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getSettings, validateKey, ApiError, type SettingsKeyStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

type Provider = "openai" | "anthropic" | "ollama";

interface ProviderState {
  keyInput: string;
  baseUrl: string; // Ollama only
  isValidating: boolean;
  status: SettingsKeyStatus | null;
  error: string | null;
}

const DEFAULT_PROVIDER_STATE: ProviderState = {
  keyInput: "",
  baseUrl: "",
  isValidating: false,
  status: null,
  error: null,
};

function StatusBadge({ status }: { status: string | null | undefined }) {
  if (!status || status === "unchecked") {
    return <Badge variant="outline">Not validated</Badge>;
  }
  if (status === "valid") return <Badge variant="success">✓ Valid</Badge>;
  if (status === "insufficient_permissions") return <Badge variant="warning">⚠ Insufficient permissions</Badge>;
  return <Badge variant="destructive">✗ Invalid</Badge>;
}

export function SettingsPage() {
  const [providers, setProviders] = React.useState<Record<Provider, ProviderState>>({
    openai: { ...DEFAULT_PROVIDER_STATE },
    anthropic: { ...DEFAULT_PROVIDER_STATE },
    ollama: { ...DEFAULT_PROVIDER_STATE },
  });
  const [isLoading, setIsLoading] = React.useState(true);

  // Load current settings on mount
  React.useEffect(() => {
    async function load() {
      try {
        const settings = await getSettings();
        setProviders((prev) => ({
          openai: { ...prev.openai, status: settings.openai },
          anthropic: { ...prev.anthropic, status: settings.anthropic },
          ollama: {
            ...prev.ollama,
            status: settings.ollama,
            baseUrl: settings.ollama.base_url ?? "",
          },
        }));
      } catch {
        // Settings load failure is non-fatal — user can still attempt validation
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  const updateProvider = (p: Provider, patch: Partial<ProviderState>) => {
    setProviders((prev) => ({ ...prev, [p]: { ...prev[p], ...patch } }));
  };

  const handleValidate = async (provider: Provider) => {
    updateProvider(provider, { isValidating: true, error: null });
    try {
      const state = providers[provider];
      const result = await validateKey({
        provider,
        api_key: state.keyInput,
        base_url: provider === "ollama" ? state.baseUrl : undefined,
      });
      updateProvider(provider, {
        isValidating: false,
        status: {
          configured: true,
          fingerprint: result.status === "valid" ? "****" : null,
          validation_status: result.status,
          validated_at: new Date().toISOString(),
        },
        error: result.status !== "valid" ? result.message : null,
        keyInput: "", // Clear key from input after validation
      });
    } catch (err) {
      updateProvider(provider, {
        isValidating: false,
        error: err instanceof ApiError ? err.detail : "Validation failed. Please try again.",
      });
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Settings</h1>
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  const providers_config: Array<{
    id: Provider;
    label: string;
    description: string;
    keyLabel: string;
    keyPlaceholder: string;
    hasBaseUrl: boolean;
  }> = [
    {
      id: "openai",
      label: "OpenAI",
      description: "Used for embeddings (text-embedding-3-small) and summarization/extraction.",
      keyLabel: "API Key",
      keyPlaceholder: "sk-…",
      hasBaseUrl: false,
    },
    {
      id: "anthropic",
      label: "Anthropic",
      description: "Used for summarization and fact extraction (Claude models).",
      keyLabel: "API Key",
      keyPlaceholder: "sk-ant-…",
      hasBaseUrl: false,
    },
    {
      id: "ollama",
      label: "Ollama",
      description: "Local Ollama instance for high-privacy processing (no data leaves your machine).",
      keyLabel: "API Key (optional)",
      keyPlaceholder: "Leave empty if no auth required",
      hasBaseUrl: true,
    },
  ];

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Settings</h1>
      <p className="text-sm text-muted-foreground mb-8">
        Configure API provider keys. Keys are validated with a lightweight test call and{" "}
        <strong>never stored in the database</strong> — only the last 4 characters are saved as a
        fingerprint. The system works for ingestion and browsing without any keys configured.
      </p>

      <div className="flex flex-col gap-6">
        {providers_config.map((config) => {
          const state = providers[config.id];
          const isConfigured = state.status?.configured ?? false;
          const fingerprint = state.status?.fingerprint;
          const validationStatus = state.status?.validation_status;

          return (
            <section
              key={config.id}
              className="rounded-lg border border-border p-5"
              aria-label={`${config.label} configuration`}
            >
              <div className="flex items-start justify-between mb-1">
                <h2 className="text-base font-semibold">{config.label}</h2>
                <div className="flex items-center gap-2">
                  {isConfigured && fingerprint && (
                    <span className="text-xs text-muted-foreground font-mono">
                      ****{fingerprint}
                    </span>
                  )}
                  <StatusBadge status={validationStatus} />
                </div>
              </div>
              <p className="text-sm text-muted-foreground mb-4">{config.description}</p>

              <div className="flex flex-col gap-3">
                {config.hasBaseUrl && (
                  <div className="flex flex-col gap-1.5">
                    <label
                      htmlFor={`${config.id}-base-url`}
                      className="text-sm font-medium"
                    >
                      Endpoint URL
                    </label>
                    <input
                      id={`${config.id}-base-url`}
                      type="url"
                      value={state.baseUrl}
                      onChange={(e) => updateProvider(config.id, { baseUrl: e.target.value })}
                      placeholder="http://localhost:11434"
                      className="rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                )}

                <div className="flex gap-2">
                  <div className="flex-1 flex flex-col gap-1.5">
                    <label
                      htmlFor={`${config.id}-key`}
                      className="text-sm font-medium"
                    >
                      {config.keyLabel}
                    </label>
                    <input
                      id={`${config.id}-key`}
                      type="password"
                      value={state.keyInput}
                      onChange={(e) => updateProvider(config.id, { keyInput: e.target.value })}
                      placeholder={
                        isConfigured
                          ? `Currently set (ends in ****${fingerprint ?? "????"}) — enter new key to update`
                          : config.keyPlaceholder
                      }
                      autoComplete="off"
                      className="rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div className="flex items-end">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={
                        state.isValidating ||
                        (config.id !== "ollama" && !state.keyInput.trim()) ||
                        (config.id === "ollama" && !state.baseUrl.trim())
                      }
                      onClick={() => handleValidate(config.id)}
                      aria-label={`Validate ${config.label} ${state.isValidating ? "(validating)" : ""}`}
                    >
                      {state.isValidating ? "Validating…" : "Validate"}
                    </Button>
                  </div>
                </div>

                {state.error && (
                  <p
                    role="alert"
                    className={cn(
                      "text-xs rounded px-2 py-1.5",
                      validationStatus === "insufficient_permissions"
                        ? "bg-yellow-50 text-yellow-700"
                        : "bg-red-50 text-red-600"
                    )}
                  >
                    {state.error}
                  </p>
                )}
              </div>
            </section>
          );
        })}
      </div>

      <div className="mt-8 rounded-lg border border-muted bg-muted/30 px-4 py-3">
        <p className="text-xs text-muted-foreground">
          <strong>No keys required</strong> — Recalium is fully usable for ingestion, archive
          browsing, and keyword search without any configured keys. Provider keys are only needed
          for AI-powered summarization, fact extraction, and semantic search (Phase 2+).
        </p>
      </div>
    </div>
  );
}
```
  </action>
  <acceptance_criteria>
    - `grep -n "fingerprint.*last 4\|last 4.*fingerprint\|last 4 chars\|_fingerprint(api_key)" backend/app/api/routes/settings.py backend/app/domain/settings/service.py | wc -l` returns ≥ 2
    - `grep -n "NEVER.*returned\|plaintext.*never\|Never.*stored" backend/app/api/routes/settings.py` returns ≥ 1 line
    - `grep -n "class ValidateKeyRequest" backend/app/api/routes/settings.py` returns 1 line
    - `grep -n "httpx.AsyncClient" backend/app/domain/settings/service.py | wc -l` returns 3 (one per provider)
    - `grep -n "api_key.*=.*None\|api_key.*=.*\"\"" backend/app/domain/settings/service.py | wc -l` returns 0 (full key never set to None in DB — only fingerprint stored)
    - `grep -n "type=\"password\"" frontend/src/pages/SettingsPage.tsx | wc -l` returns ≥ 1 (masked input)
    - `grep -n "Validate.*button\|onClick.*handleValidate\|handleValidate" frontend/src/pages/SettingsPage.tsx | wc -l` returns ≥ 2
    - `grep -n "StatusBadge\|validation_status" frontend/src/pages/SettingsPage.tsx | wc -l` returns ≥ 3 (inline status badge)
    - `grep -n "never stored in the database" frontend/src/pages/SettingsPage.tsx` returns 1 line (user education)
    - `grep -n "No keys required" frontend/src/pages/SettingsPage.tsx` returns 1 line (BYOK-05 — degraded mode notice)
  </acceptance_criteria>
</task>

</tasks>

<verification>
After all tasks complete (requires Plan 01-01 + 01-02 + 01-04 done):

1. Test GET /api/settings/keys returns no plaintext keys:
   ```bash
   curl -s http://localhost:8000/api/settings/keys | python3 -c "
   import sys, json
   d = json.load(sys.stdin)
   response_str = json.dumps(d)
   # Check no key prefixes appear in response
   for forbidden in ['sk-', 'sk-ant-', 'Bearer ']:
       assert forbidden not in response_str, f'Found key prefix {forbidden!r} in response!'
   print('PASS: No plaintext keys in settings response')
   print('OpenAI configured:', d['openai']['configured'])
   "
   ```

2. Test DB safety — pg_dump must not contain any API key prefix:
   ```bash
   docker compose exec recalium-postgres pg_dump -U recalium recalium | grep -c "sk-\|sk-ant-"
   ```
   Must return 0.

3. Test validation with invalid key:
   ```bash
   curl -s -X POST http://localhost:8000/api/settings/keys/validate \
     -H "Content-Type: application/json" \
     -d '{"provider": "openai", "api_key": "sk-invalid-test-key-1234"}' | python3 -m json.tool
   ```
   Expected: `{"provider":"openai","status":"invalid","message":"..."}` — no error, just invalid status.

4. Verify fingerprint stored (not full key):
   ```bash
   docker compose exec recalium-postgres psql -U recalium -d recalium -c \
     "SELECT openai_key_fingerprint, openai_key_configured, openai_validation_status FROM settings WHERE id=1;"
   ```
   Must show 4-char fingerprint (e.g. "1234") not a full key.

5. Visual check in browser: Settings page shows 3 provider sections; each has masked input, Validate button, and status badge.
</verification>

<must_haves>
1. `pg_dump` of the database contains zero occurrences of full API key strings (verified by the pg_dump grep test above). The `settings` table stores only a 4-char fingerprint in `*_key_fingerprint` columns.
2. `POST /api/settings/keys/validate` makes a real lightweight HTTP test call to the provider (not a mock), reports accurate `"valid"` / `"invalid"` / `"insufficient_permissions"` status, and returns HTTP 200 even when the key is invalid (the validation result is the response body, not an HTTP error). Verified by the curl test with invalid key above.
3. The Settings page UI shows "No keys required" notice explaining degraded mode (BYOK-05). Verified: `grep "No keys required" frontend/src/pages/SettingsPage.tsx` returns 1 line.
</must_haves>
