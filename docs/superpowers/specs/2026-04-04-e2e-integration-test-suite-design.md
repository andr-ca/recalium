# Design: Live-Stack E2E Integration Test Suite

**Date:** 2026-04-04
**Status:** Approved
**Author:** OpenCode

---

## Overview

A separate E2E integration test suite that runs against the live Recalium Docker stack over real HTTP. Tests create isolated data (UUID-tagged), assert behavior, and clean up after themselves via the existing `DELETE /api/archive/{id}` cascade endpoint. A session-scoped cleanup registry acts as a safety net for any test that crashes before its own teardown.

This suite lives alongside (not inside) the existing in-process unit/integration tests and is the authoritative check that the running system behaves correctly end-to-end.

---

## Goals

1. Verify the full happy path: ingest → archive → search → retrieve → delete.
2. Cover key error cases per domain (missing fields, unsupported types, wrong IDs).
3. Leave zero orphan data in the target system after the suite completes.
4. Never interfere with pre-existing data in the running stack.

---

## Non-Goals

- Replacing the existing in-process test suite.
- Load or performance testing.
- Testing internal domain logic (that belongs to unit tests).
- Requiring any changes to production application code.

---

## File Structure

```
backend/tests/e2e/
├── __init__.py
├── conftest.py          # fixtures: base_url, cleanup_registry, live_client, register, wait_for
└── test_live_stack.py   # all ~25 test functions
```

No changes to `backend/tests/conftest.py` or any existing test file.

---

## Runner

```bash
# Default (stack on localhost:8000)
cd backend && uv run pytest tests/e2e/ -v

# Override base URL
BASE_URL=http://myserver:8000 uv run pytest tests/e2e/ -v
```

`BASE_URL` environment variable controls the target. Defaults to `http://localhost:8000`.

The MCP server is mounted at `/mcp` on the same FastAPI app (not a separate port), so all requests go to the same base URL.

---

## Fixtures (`tests/e2e/conftest.py`)

### `base_url` — session-scoped

Reads `BASE_URL` from environment. Defaults to `http://localhost:8000`.

```python
@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("BASE_URL", "http://localhost:8000")
```

### `cleanup_registry` — session-scoped

A list that accumulates archive item IDs created during the session. After all tests complete, it sweeps the list and calls `DELETE /api/archive/{id}` for each entry. This is the safety net — individual tests also delete inline where needed.

```python
@pytest.fixture(scope="session")
async def cleanup_registry(base_url):
    registry = []
    yield registry
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        for item_id in registry:
            await client.delete(f"/api/archive/{item_id}")
```

### `live_client` — function-scoped

A fresh `httpx.AsyncClient` per test. Also provides a `register` callable that adds an ID to the session-scoped cleanup registry.

```python
@pytest.fixture
async def live_client(base_url, cleanup_registry):
    async with httpx.AsyncClient(base_url=base_url, timeout=15.0) as client:
        def register(item_id: str):
            cleanup_registry.append(item_id)
        client.register = register
        yield client
```

Tests use `client.register(item_id)` immediately after creating any archive item.

### `wait_for` — function-scoped helper

Polls an async predicate until it returns a truthy value or a timeout is reached. Used by tests that need background pipeline processing to complete (e.g., fact extraction before canonical promotion).

```python
async def wait_for(async_fn, timeout=15.0, interval=0.5):
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        result = await async_fn()
        if result:
            return result
        if asyncio.get_event_loop().time() > deadline:
            pytest.fail(f"Timed out after {timeout}s waiting for condition")
        await asyncio.sleep(interval)
```

Exposed as a fixture that yields the function, or imported directly as a module-level helper.

---

## Data Isolation Strategy

Every test that creates data:
1. Generates a `uuid4()` tag and embeds it in the content string (e.g., `f"Test memory {tag} ..."`). This makes the data uniquely identifiable and impossible to collide with existing production data or other parallel test runs.
2. Calls `client.register(item_id)` immediately after creation — before any assertions — so cleanup is guaranteed even if the test fails mid-way.
3. For tests that need to assert absence (e.g., deleted item not in search), the test deletes inline and then asserts, rather than relying on the session-scoped sweep.

Pre-existing data in the stack is never touched. The only DELETE calls are on IDs that the test suite itself created (tracked via the registry).

---

## Test Coverage (~25 tests)

### Ingest (4 tests)

| Test | Endpoint | Assert |
|------|----------|--------|
| `test_ingest_text_success` | `POST /api/ingest/text` | 201, item ID returned |
| `test_ingest_text_too_short` | `POST /api/ingest/text` | 422, no ID |
| `test_ingest_file_txt` | `POST /api/ingest/file` | 201, item ID returned |
| `test_ingest_file_unsupported_type` | `POST /api/ingest/file` | 422, no ID |

### Archive (3 tests)

| Test | Endpoint | Assert |
|------|----------|--------|
| `test_archive_list_contains_ingested_item` | `GET /api/archive` | item present in list |
| `test_archive_delete_removes_item` | `DELETE /api/archive/{id}` | 204, item absent from list |
| `test_archive_delete_nonexistent` | `DELETE /api/archive/nonexistent-id` | 404 |

### Search (3 tests)

| Test | Endpoint | Assert |
|------|----------|--------|
| `test_keyword_search_finds_item` | `GET /api/search?q=...` | item in results |
| `test_search_returns_empty_for_no_match` | `GET /api/search?q=<uuid-never-ingested>` | empty results, 200 |
| `test_semantic_search_graceful_degraded` | `GET /api/search?q=...&mode=semantic` | no 500 (may return empty in degraded mode) |

### MCP (3 tests)

| Test | Endpoint | Assert |
|------|----------|--------|
| `test_mcp_ingest_memory_success` | `POST /mcp/...` (ingest tool) | accepted, no error |
| `test_mcp_ingest_memory_missing_content` | `POST /mcp/...` (ingest tool, no content) | descriptive error response |
| `test_mcp_retrieve_returns_results` | `POST /mcp/...` (retrieve tool) | results array present |

### Portability (3 tests)

| Test | Endpoint | Assert |
|------|----------|--------|
| `test_export_bundle_format` | `GET /api/bundle` | 200, `version`, `items` keys present |
| `test_import_bundle_dedup` | `POST /api/bundle` | re-importing same content deduplicates (same count) |
| `test_import_bundle_invalid_version` | `POST /api/bundle` (wrong version) | 400 |

### Canonical Memory (3 tests)

| Test | Endpoint | Assert |
|------|----------|--------|
| `test_promote_fact_to_canonical` | `POST /api/canonical` | 201 (after polling for facts) |
| `test_canonical_list_contains_promoted` | `GET /api/canonical` | promoted item in list |
| `test_delete_canonical_item` | `DELETE /api/canonical/{id}` | 204, item absent from list |

### Health & API Versioning (2 tests)

| Test | Endpoint | Assert |
|------|----------|--------|
| `test_health_check` | `GET /api/health` | 200, `status: ok`, `api_version` present |
| `test_api_version_header` | `GET /api/health` | `X-API-Version` response header present |

### Auth (2 tests)

| Test | Endpoint | Assert |
|------|----------|--------|
| `test_no_auth_required_by_default` | `GET /api/health` | 200 without bearer token |
| `test_bearer_auth_wrong_token` | `GET /api/health` with wrong token | 401 (skipped if `APP_AUTH_BEARER` not set) |

### Cleanup Verification (2 tests)

| Test | Flow | Assert |
|------|------|--------|
| `test_deleted_item_excluded_from_search` | ingest → delete → search | no hit for that UUID tag |
| `test_deleted_item_excluded_from_archive_list` | ingest → delete → list | item absent |

---

## MCP Tool Call Format

The MCP server uses SSE transport mounted at `/mcp`. Tool calls are made via the MCP JSON protocol over HTTP POST. The exact endpoint path and request format will be confirmed during implementation by inspecting the FastMCP SSE transport API. If the SSE transport does not support simple POST-based tool calls in integration tests, tests will use the FastAPI app's `/api/ingest` and `/api/search` routes as proxies instead and note the MCP route limitation.

---

## Prerequisites

- `docker compose up` running (or `make up`)
- Stack healthy at `BASE_URL` (confirmed via `GET /api/health` in a session-scoped setup fixture that skips all tests with a clear message if the stack is unreachable)
- No `APP_AUTH_BEARER` set (or `E2E_BEARER_TOKEN` env var provided for auth tests)

---

## What This Suite Does NOT Do

- It does not truncate tables, modify schema, or access the database directly.
- It does not start or stop Docker containers.
- It does not interfere with the existing `tests/` suite — they share no fixtures and target different database connections.
- It does not test internal service logic — that belongs to the existing unit/integration tests.

---

## Success Criteria

1. All ~25 tests pass against a freshly started `docker compose up` stack.
2. After the suite completes, running it again immediately produces the same results (idempotent).
3. Zero orphan rows left in the archive after the session cleanup sweep.
4. Pre-existing archive items are untouched (verified by checking archive count before and after in a bookend test pair).
