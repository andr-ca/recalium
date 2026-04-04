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


# ── Ingest ───────────────────────────────────────────────────────────────────

async def test_ingest_text_success(live_client: httpx.AsyncClient) -> None:
    """POST /api/ingest with valid text returns 202 and an archive ID."""
    tag = uuid4()
    resp = await live_client.post(
        "/api/ingest",
        json={"content": f"E2E-{tag} test memory recalium integration suite"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "archive_ids" in body
    assert len(body["archive_ids"]) >= 1
    # Register for cleanup
    for aid in body["archive_ids"]:
        live_client.register(aid)


async def test_ingest_text_too_short(live_client: httpx.AsyncClient) -> None:
    """POST /api/ingest with content under 10 chars returns 422."""
    resp = await live_client.post("/api/ingest", json={"content": "short"})
    assert resp.status_code == 422


async def test_ingest_text_empty(live_client: httpx.AsyncClient) -> None:
    """POST /api/ingest with empty content returns 422."""
    resp = await live_client.post("/api/ingest", json={"content": ""})
    assert resp.status_code == 422


async def test_ingest_file_txt(live_client: httpx.AsyncClient) -> None:
    """POST /api/ingest/file with a .txt file returns 202 and an archive ID."""
    tag = uuid4()
    content = f"E2E-{tag} test file memory recalium integration suite".encode()
    resp = await live_client.post(
        "/api/ingest/file",
        files={"file": ("e2e_test.txt", content, "text/plain")},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "archive_ids" in body
    assert len(body["archive_ids"]) >= 1
    for aid in body["archive_ids"]:
        live_client.register(aid)


async def test_ingest_file_unsupported_type(live_client: httpx.AsyncClient) -> None:
    """POST /api/ingest/file with binary content (non-UTF-8) returns 422."""
    # Send raw bytes that are not valid UTF-8
    resp = await live_client.post(
        "/api/ingest/file",
        files={"file": ("binary.bin", b"\xff\xfe\x00\x01invalid", "application/octet-stream")},
    )
    assert resp.status_code == 422


# ── Archive ───────────────────────────────────────────────────────────────────

async def test_archive_list_contains_ingested_item(live_client: httpx.AsyncClient) -> None:
    """Ingest an item, then GET /api/archive confirms it is present."""
    tag = uuid4()
    ingest_resp = await live_client.post(
        "/api/ingest",
        json={"content": f"E2E-{tag} archive list test recalium integration"},
    )
    assert ingest_resp.status_code == 202
    item_id = ingest_resp.json()["archive_ids"][0]
    live_client.register(item_id)

    list_resp = await live_client.get("/api/archive")
    assert list_resp.status_code == 200
    ids = [item["id"] for item in list_resp.json()["items"]]
    assert item_id in ids


async def test_archive_delete_removes_item(live_client: httpx.AsyncClient) -> None:
    """Ingest an item, DELETE it, confirm it is absent from the archive list."""
    tag = uuid4()
    ingest_resp = await live_client.post(
        "/api/ingest",
        json={"content": f"E2E-{tag} delete test recalium integration"},
    )
    assert ingest_resp.status_code == 202
    item_id = ingest_resp.json()["archive_ids"][0]
    # Do NOT register — we're deleting it inline
    # (cleanup_registry would try to delete again, which is fine but noisy)

    delete_resp = await live_client.delete(f"/api/archive/{item_id}")
    assert delete_resp.status_code == 204

    list_resp = await live_client.get("/api/archive")
    ids = [item["id"] for item in list_resp.json()["items"]]
    assert item_id not in ids


async def test_archive_delete_nonexistent(live_client: httpx.AsyncClient) -> None:
    """DELETE /api/archive/<valid-uuid-that-does-not-exist> returns 404."""
    fake_id = str(uuid4())
    resp = await live_client.delete(f"/api/archive/{fake_id}")
    assert resp.status_code == 404


# ── Search ────────────────────────────────────────────────────────────────────

async def test_keyword_search_finds_item(live_client: httpx.AsyncClient) -> None:
    """Ingest a UUID-tagged item, then search for its tag and find it."""
    tag = uuid4()
    content = f"E2E-{tag} keyword search recalium integration"
    ingest_resp = await live_client.post("/api/ingest", json={"content": content})
    assert ingest_resp.status_code == 202
    item_id = ingest_resp.json()["archive_ids"][0]
    live_client.register(item_id)

    search_resp = await live_client.get(
        "/api/search",
        params={"q": str(tag), "mode": "keyword"},
    )
    assert search_resp.status_code == 200
    body = search_resp.json()
    assert "items" in body
    # At least one result should contain our UUID tag
    found = any(str(tag) in item.get("content", "") for item in body["items"])
    assert found, f"UUID tag {tag} not found in search results: {body['items']}"


async def test_search_returns_empty_for_no_match(live_client: httpx.AsyncClient) -> None:
    """Search for a UUID that was never ingested returns empty results (not error)."""
    never_ingested_tag = str(uuid4())
    resp = await live_client.get(
        "/api/search",
        params={"q": never_ingested_tag, "mode": "keyword"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []


async def test_semantic_search_graceful_degraded(live_client: httpx.AsyncClient) -> None:
    """Semantic search does not 500 — may return empty if embed backend is degraded."""
    resp = await live_client.get(
        "/api/search",
        params={"q": "test memory recalium", "mode": "semantic"},
    )
    # Must not be a 500; 200 is expected (items may be empty in degraded mode)
    assert resp.status_code != 500
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    # degraded_mode may be true if embed backend is not configured
    assert isinstance(body["degraded_mode"], bool)
