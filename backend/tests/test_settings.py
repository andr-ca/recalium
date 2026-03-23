"""Integration tests for BYOK settings — covers BYOK-02, BYOK-03, BYOK-04, BYOK-05.

Key security invariant (D-12, Pitfall 5): API keys MUST NEVER be stored in the database.
The test_key_not_in_db test enforces this at the schema level — it fails if any column
with a forbidden name pattern exists in the settings table.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.infrastructure.db import Base
from app.domain.settings.service import ValidationResult


# ── BYOK-02: GET settings endpoint ──────────────────────────────────────────

async def test_get_byok_status(client: AsyncClient):
    """BYOK-02: GET /api/settings/keys returns provider status without plaintext keys."""
    resp = await client.get("/api/settings/keys")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Must have all three providers
    for provider in ("openai", "anthropic", "ollama"):
        assert provider in data, f"Missing provider {provider!r} in response: {data}"

    # Response must NOT contain full key values — only fingerprints or None
    response_text = resp.text
    # If any known key prefix appears (sk-, anthropic-) it's a leak
    assert "sk-" not in response_text, "OpenAI key prefix 'sk-' leaked in GET response"
    assert "anthropic-" not in response_text.lower(), (
        "Anthropic key prefix leaked in GET response"
    )


# ── BYOK-03: Validate endpoint — mocked external calls ──────────────────────

async def test_validate_openai_key_valid(client: AsyncClient):
    """BYOK-03: POST /api/settings/keys/validate with valid mock OpenAI key returns 'valid'."""
    # Patch at the route module where the name is bound (from X import Y creates a local ref)
    with patch(
        "app.api.routes.settings.validate_openai_key",
        new_callable=AsyncMock,
        return_value=ValidationResult(provider="openai", status="valid", message="Mocked valid"),
    ):
        resp = await client.post(
            "/api/settings/keys/validate",
            json={"provider": "openai", "api_key": "sk-mock-key-for-testing"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "valid"


async def test_validate_invalid_key(client: AsyncClient):
    """BYOK-03: POST /api/settings/keys/validate returns 'invalid' when provider rejects key."""
    with patch(
        "app.api.routes.settings.validate_openai_key",
        new_callable=AsyncMock,
        return_value=ValidationResult(provider="openai", status="invalid", message="Mocked invalid"),
    ):
        resp = await client.post(
            "/api/settings/keys/validate",
            json={"provider": "openai", "api_key": "sk-mock-invalid"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "invalid"


async def test_validate_unknown_provider(client: AsyncClient):
    """BYOK-03: POST /api/settings/keys/validate with unknown provider returns 422.

    The ValidateKeyRequest uses Literal["openai", "anthropic", "ollama"] which causes
    Pydantic to return 422 automatically for any other value.
    """
    resp = await client.post(
        "/api/settings/keys/validate",
        json={"provider": "unknown_provider_xyz"},
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"


# ── BYOK-04: Key never in DB — schema assertion ──────────────────────────────

async def test_key_not_in_db():
    """BYOK-04 / D-12: No column in any SQLAlchemy model is named with a forbidden pattern.

    Scans all mapped tables for column names matching:
      - *_key (e.g., openai_key, api_key)
      - *_secret
      - *_token

    Explicit exceptions (safe columns — fingerprints and booleans, not secrets):
      - *_key_fingerprint
      - *_key_configured
      - *_validation_status
      - *_validated_at

    If this test fails, a column was added that could store a full API key.
    See D-12 and Pitfall 5 in .planning/research/PITFALLS.md for why this matters.
    """
    FORBIDDEN_SUFFIXES = ("_key", "_secret", "_token")
    SAFE_SUFFIXES = (
        "_key_fingerprint",
        "_key_configured",
        "_validation_status",
        "_validated_at",
    )

    violations: list[str] = []
    for table_name, table in Base.metadata.tables.items():
        for col in table.columns:
            col_lower = col.name.lower()
            for suffix in FORBIDDEN_SUFFIXES:
                if col_lower.endswith(suffix):
                    # Check if it's a safe exception
                    if not any(col_lower.endswith(safe) for safe in SAFE_SUFFIXES):
                        violations.append(f"{table_name}.{col.name}")

    assert not violations, (
        f"SECURITY VIOLATION (D-12): The following columns could store plaintext API keys:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nAPI keys must NEVER be stored in the database. "
        "Only fingerprints (*_key_fingerprint) and booleans (*_key_configured) are allowed. "
        "See .planning/research/PITFALLS.md Pitfall 5."
    )


# ── BYOK-05: Degraded mode — no keys configured ─────────────────────────────

async def test_degraded_mode_no_keys(client: AsyncClient):
    """BYOK-05: App serves archive GET correctly even when no BYOK keys are configured.

    Simulates an environment where all provider keys are None/empty.
    The ingest and archive endpoints must work without any configured keys.
    """
    resp = await client.get("/api/archive")
    assert resp.status_code == 200, (
        f"GET /api/archive failed in keyless environment: {resp.text}"
    )

    # Also verify ingest works without keys (BYOK-05 — ingest is key-independent)
    resp = await client.post(
        "/api/ingest",
        json={"content": "User: Test\nAssistant: Test", "source_name": "degraded_mode_test"},
    )
    assert resp.status_code in (200, 202), (
        f"POST /api/ingest failed in keyless environment: {resp.text}"
    )
