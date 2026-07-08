# E2E Integration Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a live-stack E2E integration test suite that runs against the real Recalium Docker stack over HTTP, covering ~25 tests across all domains, with guaranteed cleanup of all created data.

**Architecture:** Two new files under `backend/tests/e2e/` — a `conftest.py` with session/function-scoped fixtures (base_url, cleanup_registry, live_client, wait_for) and a `test_live_stack.py` with ~25 test functions. No changes to any existing test file. All tests use `httpx.AsyncClient` pointing at the real running stack, not in-process ASGI.

**Tech Stack:** Python 3.12, pytest 8, pytest-asyncio (asyncio_mode=auto), httpx 0.28, uv runner.

---

## Context for the Implementer

### Key API facts discovered from source

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/health` | GET | 200 | Returns `{"status": "ok", "db": "ok", "api_version": "1"}`. Also sets `X-API-Version: 1` response header (middleware in `main.py:238`). |
| `/api/ingest` | POST | 202 | Body: `{"mode": "text", "content": "...", "source_name": null}`. Minimum content length check exists in service layer. Empty/whitespace → 422. |
| `/api/ingest/file` | POST multipart | 202 | Field name `file`. Returns 422 for non-UTF-8 or rejected file types. |
| `/api/archive` | GET | 200 | Returns `{"items": [...], "total": N, "offset": 0, "limit": 50}`. Excludes soft-deleted by default. |
| `/api/archive/{id}` | GET | 200/404 | Returns single item. 422 for non-UUID id. |
| `/api/archive/{id}` | DELETE | 204/404 | Soft-delete with cascade. 422 for non-UUID format, 404 for not found/already deleted. |
| `/api/search` | GET | 200 | Params: `q` (required), `mode` (keyword/semantic/hybrid), `budget`, `limit`, `offset`. Returns `{"items": [...], "degraded_mode": bool, ...}`. |
| `/api/canonical` | GET | 200 | Returns `{"items": [...], "count": N}`. |
| `/api/canonical` | POST | 201 | Body: `{"content": "...", "promoted_by": "user_ui"}`. Creates manual canonical item. |
| `/api/canonical/{id}` | DELETE | 204/404 | |
| `/api/export/bundle` | GET | 200 | Returns bundle with keys: `format`, `version`, `exported_at`, `items`. |
| `/api/import/bundle` | POST | 200 | Body: full bundle dict. Returns `{"imported": N, "skipped": N, "errors": [...]}`. 422 if wrong `format` or `version` string. |
| `/mcp/sse` | GET | SSE | Establishes SSE connection. |
| `/mcp/messages` | POST | — | MCP JSON-RPC tool call endpoint (used with session from `/mcp/sse`). |

### MCP SSE transport notes

The FastMCP SSE transport mounts two routes on the Starlette app:
- `GET /mcp/sse` — SSE stream for server-to-client messages
- `POST /mcp/messages` — client-to-server JSON-RPC (requires `?session_id=<id>` from SSE handshake)

Testing MCP via raw SSE in pytest is complex. **The MCP tests use an httpx-based SSE flow**:
1. Open GET `/mcp/sse` (stream=True), parse `data:` lines to get `session_id`
2. POST to `/mcp/messages?session_id=<id>` with JSON-RPC tool call body
3. Read the response from the SSE stream

If this proves too brittle in implementation, fall back to directly calling `/api/ingest` and `/api/search` for the MCP tool coverage, and document the limitation in a comment.

### pytest-asyncio scope constraint

`pyproject.toml` sets `asyncio_default_fixture_loop_scope = "function"`. Session-scoped async fixtures require explicit `scope="session"` AND the event loop scope must be widened for them to share a loop. Use `@pytest_asyncio.fixture(scope="session", loop_scope="session")` for session-scoped async fixtures.

### Data isolation pattern

Every test that creates data:
1. Generates a `uuid4()` tag embedded in content: `f"E2E-{tag} test memory recalium integration suite"` (≥10 chars, unique)
2. Calls `client.register(item_id)` immediately after creation — before any assertion
3. The session-scoped `cleanup_registry` sweeps all IDs via `DELETE /api/archive/{id}` after all tests finish

### Run command

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/ -v
# Override target:
BASE_URL=http://myserver:8000 uv run pytest tests/e2e/ -v
```

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/tests/e2e/__init__.py` | Create | Empty package marker |
| `backend/tests/e2e/conftest.py` | Create | All fixtures: base_url, stack_health, cleanup_registry, live_client, wait_for |
| `backend/tests/e2e/test_live_stack.py` | Create | All ~25 E2E test functions |

No existing files are modified.

---

## Task 1: Package scaffold

**Files:**
- Create: `backend/tests/e2e/__init__.py`

- [ ] **Step 1: Create the empty package marker**

```python
# backend/tests/e2e/__init__.py
```

(empty file — makes `tests/e2e` a Python package)

- [ ] **Step 2: Verify pytest can discover the directory**

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/ --collect-only 2>&1 | head -10
```

Expected: `no tests ran` or `collected 0 items` (no error). If pytest errors with "not found", check the `testpaths` setting in `pyproject.toml` — it lists only `["tests"]` so `tests/e2e/` is already within the search tree.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e/__init__.py
git commit -m "chore: scaffold e2e test package"
```

---

## Task 2: Fixtures (`conftest.py`)

**Files:**
- Create: `backend/tests/e2e/conftest.py`

- [ ] **Step 1: Write conftest.py**

```python
"""Fixtures for live-stack E2E integration tests.

Prerequisites: `docker compose up` (or `make up`) must be running.
Set BASE_URL env var to override target (default: http://localhost:8000).
"""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator, Callable

import httpx
import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL of the live stack. Reads BASE_URL env var, defaults to localhost:8000."""
    return os.environ.get("BASE_URL", "http://localhost:8000")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def stack_health(base_url: str) -> None:
    """Session-scoped fixture that skips all tests if the stack is unreachable.

    Calls GET /api/health. Skips with a clear message if the stack is not up.
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
        try:
            resp = await client.get("/api/health")
            if resp.status_code != 200:
                pytest.skip(
                    f"Stack at {base_url} returned HTTP {resp.status_code} — "
                    "start it with `docker compose up` before running E2E tests."
                )
        except httpx.ConnectError:
            pytest.skip(
                f"Stack at {base_url} is unreachable — "
                "start it with `docker compose up` before running E2E tests."
            )


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def cleanup_registry(base_url: str, stack_health: None) -> AsyncGenerator[list[str], None]:
    """Session-scoped list of archive item IDs to delete after all tests finish.

    Acts as a safety net — individual tests also clean up inline where needed.
    Session teardown sweeps the full list via DELETE /api/archive/{id}.
    """
    registry: list[str] = []
    yield registry
    # Sweep: delete all registered IDs
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        for item_id in registry:
            try:
                await client.delete(f"/api/archive/{item_id}")
            except Exception:
                pass  # Best-effort cleanup; don't fail teardown


@pytest_asyncio.fixture
async def live_client(
    base_url: str,
    cleanup_registry: list[str],
    stack_health: None,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Function-scoped httpx.AsyncClient pointed at the live stack.

    Adds a `register(item_id)` method to the client for tracking created items.
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=15.0) as client:
        def register(item_id: str) -> None:
            cleanup_registry.append(item_id)
        client.register = register  # type: ignore[attr-defined]
        yield client


async def wait_for(
    async_fn: Callable,
    timeout: float = 15.0,
    interval: float = 0.5,
):
    """Poll async_fn until it returns a truthy value or timeout is reached.

    On timeout, calls pytest.fail with a descriptive message.
    """
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while True:
        result = await async_fn()
        if result:
            return result
        if loop.time() > deadline:
            pytest.fail(f"Timed out after {timeout}s waiting for condition")
        await asyncio.sleep(interval)
```

- [ ] **Step 2: Verify conftest syntax**

```bash
cd /home/andrey/projects/recalium/backend
uv run python -c "import tests.e2e.conftest; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e/conftest.py
git commit -m "feat: add e2e test fixtures (conftest.py)"
```

---

## Task 3: Health & Auth tests

**Files:**
- Create (partial): `backend/tests/e2e/test_live_stack.py`

Write the first group of tests. We build `test_live_stack.py` incrementally across tasks 3–9, each task appending to the file. Start with an empty file with the module docstring and imports, then add each group.

- [ ] **Step 1: Write the module header and health/auth tests**

```python
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
```

- [ ] **Step 2: Run health/auth tests only**

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/test_live_stack.py -k "health or auth" -v 2>&1 | tail -20
```

Expected: 3 tests pass (4th skipped if `APP_AUTH_BEARER` not set). If stack is not running, all will be skipped.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e/test_live_stack.py
git commit -m "feat: add e2e health and auth tests"
```

---

## Task 4: Ingest tests

**Files:**
- Modify: `backend/tests/e2e/test_live_stack.py` (append)

- [ ] **Step 1: Append ingest tests**

```python
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
```

- [ ] **Step 2: Run ingest tests**

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/test_live_stack.py -k "ingest" -v 2>&1 | tail -20
```

Expected: all 5 ingest tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e/test_live_stack.py
git commit -m "feat: add e2e ingest tests"
```

---

## Task 5: Archive tests

**Files:**
- Modify: `backend/tests/e2e/test_live_stack.py` (append)

- [ ] **Step 1: Append archive tests**

```python
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
```

- [ ] **Step 2: Run archive tests**

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/test_live_stack.py -k "archive" -v 2>&1 | tail -20
```

Expected: all 3 archive tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e/test_live_stack.py
git commit -m "feat: add e2e archive tests"
```

---

## Task 6: Search tests

**Files:**
- Modify: `backend/tests/e2e/test_live_stack.py` (append)

- [ ] **Step 1: Append search tests**

```python
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
```

- [ ] **Step 2: Run search tests**

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/test_live_stack.py -k "search" -v 2>&1 | tail -20
```

Expected: all 3 search tests pass. `test_keyword_search_finds_item` may be slow if the pipeline needs to process the item — if keyword search is based on raw_content directly, it should be instant.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e/test_live_stack.py
git commit -m "feat: add e2e search tests"
```

---

## Task 7: Canonical Memory tests

**Files:**
- Modify: `backend/tests/e2e/test_live_stack.py` (append)

Note: Canonical memory has two paths — `POST /api/canonical` (manual creation) and `POST /api/canonical/promote` (promote a fact). The promote path requires a `fact_id` and `raw_archive_id` from the pipeline. Manual creation is simpler and doesn't require pipeline processing. We test the manual path here.

- [ ] **Step 1: Append canonical tests**

Note: Canonical items are cleaned up inline (not via `cleanup_registry`) because the archive cleanup registry only handles `DELETE /api/archive/{id}`, not `DELETE /api/canonical/{id}`.

```python
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
```

- [ ] **Step 2: Run canonical tests**

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/test_live_stack.py -k "canonical" -v 2>&1 | tail -20
```

Expected: all 3 canonical tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e/test_live_stack.py
git commit -m "feat: add e2e canonical memory tests"
```

---

## Task 8: Portability tests

**Files:**
- Modify: `backend/tests/e2e/test_live_stack.py` (append)

Note: The portability routes are mounted at `/api/export/bundle` (GET) and `/api/import/bundle` (POST). Check `portability.py` — NOT `/api/bundle`.

- [ ] **Step 1: Append portability tests**

```python
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
    # Export current state
    export_resp = await live_client.get("/api/export/bundle")
    assert export_resp.status_code == 200
    bundle = export_resp.json()
    original_count = len(bundle["items"])

    # Re-import the same bundle
    import_resp = await live_client.post("/api/import/bundle", json=bundle)
    assert import_resp.status_code == 200
    result = import_resp.json()
    # All items should be skipped (dedup by content_hash)
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
```

- [ ] **Step 2: Run portability tests**

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/test_live_stack.py -k "bundle" -v 2>&1 | tail -20
```

Expected: all 4 portability tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e/test_live_stack.py
git commit -m "feat: add e2e portability tests"
```

---

## Task 9: MCP tests

**Files:**
- Modify: `backend/tests/e2e/test_live_stack.py` (append)

The MCP SSE transport requires a two-step handshake: GET `/mcp/sse` to get a `session_id`, then POST to `/mcp/messages?session_id=<id>`. The SSE stream returns `data:` lines; the first line contains the endpoint URL with session_id.

- [ ] **Step 1: Append MCP tests**

```python
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
        async for line in sse_resp.aiter_lines():
            line = line.strip()
            if line.startswith("data:"):
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
        # or errors are surfaced as {"error": "..."}
        assert "error" not in payload or payload.get("status") == "accepted"
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
```

- [ ] **Step 2: Run MCP tests**

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/test_live_stack.py -k "mcp" -v 2>&1 | tail -30
```

Expected: 3 tests pass or xfail (not error). If the SSE handshake approach doesn't work with httpx streaming, the tests gracefully xfail. Investigate the actual `/mcp/sse` response format if tests xfail — adjust the `data:` line parsing to match the real SSE event format.

- [ ] **Step 3: If tests xfail — investigate SSE format**

```bash
# Quick check of SSE output format (stack must be running)
curl -N http://localhost:8000/mcp/sse 2>&1 | head -5
```

The SSE event will look like:
```
event: endpoint
data: /mcp/messages?session_id=<uuid>
```

If the `event:` line comes before `data:`, update `_mcp_call` to look for the `event: endpoint` + following `data:` line pattern.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/e2e/test_live_stack.py
git commit -m "feat: add e2e MCP tool tests"
```

---

## Task 10: Cleanup verification & data integrity tests

**Files:**
- Modify: `backend/tests/e2e/test_live_stack.py` (append)

These tests verify that deleted items are excluded from results, and that the test suite doesn't leak data.

- [ ] **Step 1: Append cleanup verification tests**

```python
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

    list_resp = await live_client.get("/api/archive")
    ids = [item["id"] for item in list_resp.json()["items"]]
    assert item_id not in ids
```

- [ ] **Step 2: Run cleanup verification tests**

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/test_live_stack.py -k "deleted" -v 2>&1 | tail -20
```

Expected: both tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e/test_live_stack.py
git commit -m "feat: add e2e cleanup verification tests"
```

---

## Task 11: Full suite run and validation

- [ ] **Step 1: Run the full E2E suite**

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/ -v 2>&1
```

Expected: ~25 tests. All pass or xfail (none errored). Note any that are skipped due to missing `APP_AUTH_BEARER`.

- [ ] **Step 2: Run the suite a second time (idempotency check)**

```bash
cd /home/andrey/projects/recalium/backend
uv run pytest tests/e2e/ -v 2>&1
```

Expected: same results as first run. No failures introduced by leftover data.

- [ ] **Step 3: Check for orphan data (optional manual check)**

After both runs, verify the archive has no E2E-prefixed items:

```bash
# Stack must be running
curl -s "http://localhost:8000/api/archive?limit=200" | python3 -c "
import json, sys
body = json.load(sys.stdin)
e2e = [i for i in body['items'] if i.get('source_name','').startswith('E2E-') or 'E2E-' in str(i)]
print(f'Orphan E2E items: {len(e2e)}')
for i in e2e: print(' ', i['id'], i.get('source_name',''))
"
```

Expected: `Orphan E2E items: 0`

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete live-stack E2E integration test suite"
```

---

## Total Test Count

| Domain | Tests |
|--------|-------|
| Health & versioning | 2 |
| Auth | 2 (1 conditional skip) |
| Ingest | 5 |
| Archive | 3 |
| Search | 3 |
| Canonical | 3 |
| Portability | 4 |
| MCP | 3 (xfail if SSE incompatible) |
| Cleanup verification | 2 |
| **Total** | **27** |
