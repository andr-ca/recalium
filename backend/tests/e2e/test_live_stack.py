"""Live-stack E2E integration tests for Recalium.

Prerequisites: docker compose up (or make up) must be running.
Run: cd backend && uv run pytest tests/e2e/ -v

These tests create isolated data (UUID-tagged), assert behavior,
and clean up via the session-scoped cleanup_registry fixture.
"""
from __future__ import annotations

import os
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from tests.e2e.conftest import wait_for


# ── Health & API Versioning ──────────────────────────────────────────────────

async def test_health_check(live_client: httpx.AsyncClient) -> None:
    """GET /api/health returns 200 with status ok and api_version field."""
    resp = await live_client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "api_version" in body


async def test_api_version_header(live_client: httpx.AsyncClient) -> None:
    """GET /api/health response includes X-API-Version header."""
    resp = await live_client.get("/api/health")
    assert "x-api-version" in {k.lower() for k in resp.headers}


# ── Auth ─────────────────────────────────────────────────────────────────────

async def test_no_auth_required_by_default(live_client: httpx.AsyncClient) -> None:
    """GET /api/health returns 200 without any bearer token."""
    resp = await live_client.get("/api/health")
    assert resp.status_code == 200


@pytest.mark.skipif(
    not os.environ.get("APP_AUTH_BEARER"),
    reason="APP_AUTH_BEARER not set — auth enforcement disabled in this stack",
)
async def test_bearer_auth_wrong_token(live_client: httpx.AsyncClient) -> None:
    """GET /api/archive with wrong bearer token returns 401 when auth is enabled.

    NOTE: Uses /api/archive (not /api/health). The auth middleware exempts /health
    (no /api/ prefix) but requires auth for /api/* routes. See main.py:40-41.
    """
    resp = await live_client.get(
        "/api/archive",
        headers={"Authorization": "Bearer definitely-wrong-token"},
    )
    assert resp.status_code == 401
