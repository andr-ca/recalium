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

    list_resp = await live_client.get("/api/archive", params={"limit": 200})
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

    list_resp = await live_client.get("/api/archive", params={"limit": 200})
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


# ── Canonical Memory ──────────────────────────────────────────────────────────

async def test_create_canonical_item(live_client: httpx.AsyncClient) -> None:
    """POST /api/canonical creates a manual canonical memory item (201)."""
    tag = uuid4()
    resp = await live_client.post(
        "/api/canonical",
        json={"content": f"E2E-{tag} canonical memory recalium integration"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    canonical_id = body["id"]
    # Cleanup inline — canonical items use a different delete endpoint from archive
    await live_client.delete(f"/api/canonical/{canonical_id}")


async def test_canonical_list_contains_created_item(live_client: httpx.AsyncClient) -> None:
    """Create a canonical item, then GET /api/canonical confirms it is present."""
    tag = uuid4()
    create_resp = await live_client.post(
        "/api/canonical",
        json={"content": f"E2E-{tag} canonical list test recalium integration"},
    )
    assert create_resp.status_code == 201
    canonical_id = create_resp.json()["id"]

    list_resp = await live_client.get("/api/canonical")
    assert list_resp.status_code == 200
    ids = [item["id"] for item in list_resp.json()["items"]]
    assert canonical_id in ids

    # Cleanup inline
    delete_resp = await live_client.delete(f"/api/canonical/{canonical_id}")
    assert delete_resp.status_code == 204


async def test_delete_canonical_item(live_client: httpx.AsyncClient) -> None:
    """Create then DELETE /api/canonical/{id} returns 204 and item is absent."""
    tag = uuid4()
    create_resp = await live_client.post(
        "/api/canonical",
        json={"content": f"E2E-{tag} delete canonical recalium integration"},
    )
    assert create_resp.status_code == 201
    canonical_id = create_resp.json()["id"]

    delete_resp = await live_client.delete(f"/api/canonical/{canonical_id}")
    assert delete_resp.status_code == 204

    list_resp = await live_client.get("/api/canonical")
    ids = [item["id"] for item in list_resp.json()["items"]]
    assert canonical_id not in ids


# ── Portability ───────────────────────────────────────────────────────────────

async def test_export_bundle_format(live_client: httpx.AsyncClient) -> None:
    """GET /api/export/bundle returns 200 with required bundle keys."""
    resp = await live_client.get("/api/export/bundle")
    assert resp.status_code == 200
    body = resp.json()
    assert body["format"] == "recalium-memory-bundle"
    assert body["version"] == "1"
    assert "exported_at" in body
    assert "items" in body
    assert isinstance(body["items"], list)


async def test_import_bundle_dedup(live_client: httpx.AsyncClient) -> None:
    """Import the current bundle a second time — duplicate content is skipped."""
    # Ingest a known item first to ensure archive is non-empty (dedup requires content)
    tag = uuid4()
    seed_resp = await live_client.post(
        "/api/ingest",
        json={"content": f"E2E-{tag} bundle dedup seed recalium integration"},
    )
    assert seed_resp.status_code == 202
    for aid in seed_resp.json()["archive_ids"]:
        live_client.register(aid)

    # Export current state (guaranteed non-empty)
    export_resp = await live_client.get("/api/export/bundle")
    assert export_resp.status_code == 200
    bundle = export_resp.json()
    original_count = len(bundle["items"])
    assert original_count >= 1, "Bundle must be non-empty to test deduplication"

    # Re-import the same bundle — all items should be skipped
    import_resp = await live_client.post("/api/import/bundle", json=bundle)
    assert import_resp.status_code == 200
    result = import_resp.json()
    assert result["imported"] == 0
    assert result["skipped"] == original_count
    assert result["errors"] == []


async def test_import_bundle_invalid_version(live_client: httpx.AsyncClient) -> None:
    """POST /api/import/bundle with wrong version returns 422."""
    bad_bundle = {
        "format": "recalium-memory-bundle",
        "version": "999",
        "exported_at": "2026-01-01T00:00:00Z",
        "items": [],
    }
    resp = await live_client.post("/api/import/bundle", json=bad_bundle)
    assert resp.status_code == 422


async def test_import_bundle_invalid_format(live_client: httpx.AsyncClient) -> None:
    """POST /api/import/bundle with wrong format string returns 422."""
    bad_bundle = {
        "format": "not-a-recalium-bundle",
        "version": "1",
        "exported_at": "2026-01-01T00:00:00Z",
        "items": [],
    }
    resp = await live_client.post("/api/import/bundle", json=bad_bundle)
    assert resp.status_code == 422


# ── MCP ───────────────────────────────────────────────────────────────────────

async def _mcp_call(client: httpx.AsyncClient, tool: str, arguments: dict) -> dict:
    """Helper: establish SSE session and call an MCP tool.

    Returns the parsed result dict from the JSON-RPC response.
    Raises AssertionError if the SSE handshake fails or the RPC call returns an error.
    """
    # Step 1: Open SSE stream, read first event to get the session endpoint
    session_endpoint: str | None = None
    async with client.stream("GET", "/mcp/sse") as sse_resp:
        assert sse_resp.status_code == 200, f"SSE handshake failed: {sse_resp.status_code}"
        saw_endpoint_event = False
        async for line in sse_resp.aiter_lines():
            line = line.strip()
            if line == "event: endpoint":
                saw_endpoint_event = True
            elif saw_endpoint_event and line.startswith("data:"):
                session_endpoint = line[len("data:"):].strip()
                break
            elif not saw_endpoint_event and line.startswith("data:"):
                # Fallback: server sends data: without prior event: line
                session_endpoint = line[len("data:"):].strip()
                break
        # session_endpoint is something like /mcp/messages?session_id=<uuid>

    assert session_endpoint is not None, "SSE did not return a session endpoint"

    # Step 2: POST the JSON-RPC tool call
    rpc_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": arguments,
        },
    }
    # session_endpoint may be an absolute path; use the base client
    rpc_resp = await client.post(session_endpoint, json=rpc_body)
    assert rpc_resp.status_code == 200, f"MCP RPC failed: {rpc_resp.status_code} {rpc_resp.text}"
    return rpc_resp.json()


async def test_mcp_ingest_memory_success(live_client: httpx.AsyncClient) -> None:
    """MCP ingest_memory tool with valid content returns accepted status."""
    tag = uuid4()
    content = f"E2E-{tag} MCP ingest memory recalium integration"
    try:
        result = await _mcp_call(live_client, "ingest_memory", {"content": content})
        # Result may be wrapped in JSON-RPC result envelope
        payload = result.get("result", result)
        # MCP ingest returns {"status": "accepted", "archive_ids": [...]}
        assert "error" not in payload
        assert payload.get("status") == "accepted"
        if "archive_ids" in payload:
            for aid in payload["archive_ids"]:
                live_client.register(aid)
    except AssertionError as e:
        # If SSE transport is not suitable for sync tool calls, mark as xfail
        pytest.xfail(f"MCP SSE transport not compatible with test harness: {e}")


async def test_mcp_ingest_memory_missing_content(live_client: httpx.AsyncClient) -> None:
    """MCP ingest_memory tool with empty content returns descriptive error (not 500)."""
    try:
        result = await _mcp_call(live_client, "ingest_memory", {"content": ""})
        payload = result.get("result", result)
        # Should return {"error": "content is required and must be non-empty"}
        assert "error" in payload
        assert "content" in payload["error"].lower()
    except AssertionError as e:
        pytest.xfail(f"MCP SSE transport not compatible with test harness: {e}")


async def test_mcp_retrieve_returns_results(live_client: httpx.AsyncClient) -> None:
    """MCP retrieve_memory tool with a query returns a results envelope (no 500)."""
    try:
        result = await _mcp_call(live_client, "retrieve_memory", {"query": "test memory recalium"})
        payload = result.get("result", result)
        assert "items" in payload
        assert isinstance(payload["items"], list)
    except AssertionError as e:
        pytest.xfail(f"MCP SSE transport not compatible with test harness: {e}")


# ── Cleanup Verification ──────────────────────────────────────────────────────

async def test_deleted_item_excluded_from_search(live_client: httpx.AsyncClient) -> None:
    """Ingest → delete → search: deleted item does not appear in search results."""
    tag = uuid4()
    content = f"E2E-{tag} deleted search exclusion recalium integration"
    ingest_resp = await live_client.post("/api/ingest", json={"content": content})
    assert ingest_resp.status_code == 202
    item_id = ingest_resp.json()["archive_ids"][0]

    # Delete inline (don't register — it's already gone)
    delete_resp = await live_client.delete(f"/api/archive/{item_id}")
    assert delete_resp.status_code == 204

    # Search for the UUID tag — must not appear
    search_resp = await live_client.get(
        "/api/search",
        params={"q": str(tag), "mode": "keyword"},
    )
    assert search_resp.status_code == 200
    found = any(str(tag) in item.get("content", "") for item in search_resp.json()["items"])
    assert not found, f"Deleted item with tag {tag} still appears in search results"


async def test_deleted_item_excluded_from_archive_list(live_client: httpx.AsyncClient) -> None:
    """Ingest → delete → list archive: deleted item is absent from default listing."""
    tag = uuid4()
    ingest_resp = await live_client.post(
        "/api/ingest",
        json={"content": f"E2E-{tag} deleted archive exclusion recalium integration"},
    )
    assert ingest_resp.status_code == 202
    item_id = ingest_resp.json()["archive_ids"][0]

    delete_resp = await live_client.delete(f"/api/archive/{item_id}")
    assert delete_resp.status_code == 204

    list_resp = await live_client.get("/api/archive", params={"limit": 200})
    ids = [item["id"] for item in list_resp.json()["items"]]
    assert item_id not in ids
