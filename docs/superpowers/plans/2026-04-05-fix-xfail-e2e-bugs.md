# Fix xfailing E2E Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 application bugs so all 27 E2E tests in `backend/tests/e2e/test_live_stack.py` pass without xfail markers.

**Architecture:** Three independent bugs cause 7 xfailing tests: (1) the canonical memory ORM model writes to a PostgreSQL GENERATED ALWAYS column, causing a DB error; (2) the background worker returns early before running FTS indexing when no LLM provider is configured, so keyword search never finds newly-ingested content; (3) the MCP test helper uses the wrong HTTP protocol for SSE-based JSON-RPC (expects 200 with body, but SSE always returns 202 and delivers results on the stream).

**Tech Stack:** Python, FastAPI, SQLAlchemy (async), PostgreSQL (TSVECTOR/GENERATED ALWAYS), `mcp` package v1.26.0 (`mcp.client.sse.sse_client`, `mcp.ClientSession`), `uv run pytest`

---

## File Map

| File | Change |
|------|--------|
| `backend/app/domain/canonical_memory/models.py` | Fix `search_vector` column to use `FetchedValue()` |
| `backend/app/worker/dispatcher.py` | Move FTS step before the `pending_provider` return |
| `backend/app/api/routes/search.py` | Add `POST /api/search/invalidate-cache` dev-only endpoint |
| `backend/app/infrastructure/settings.py` | No change needed (`is_development` property already exists) |
| `backend/tests/e2e/test_live_stack.py` | Rewrite `_mcp_call`, remove all xfail markers |

---

## Task 1: Fix canonical memory `search_vector` GeneratedAlwaysError

**Bug:** `backend/app/domain/canonical_memory/models.py:58` declares `search_vector` as a plain `mapped_column(TSVECTOR, nullable=True)`. SQLAlchemy includes it in INSERT statements (as NULL), but the migration defines it as `GENERATED ALWAYS AS (to_tsvector('english', content)) STORED` — PostgreSQL rejects any INSERT that tries to write a GENERATED ALWAYS column.

**Fix:** Replace with `server_default=FetchedValue(), init=False` so SQLAlchemy never writes this column.

**Files:**
- Modify: `backend/app/domain/canonical_memory/models.py:58-59`

- [ ] **Step 1: Verify the current column definition**

  Read `backend/app/domain/canonical_memory/models.py` and confirm line 58 is:
  ```python
  search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
  ```

- [ ] **Step 2: Apply the fix**

  Replace the import line and column definition. In `models.py`:

  Change the import at line 16 from:
  ```python
  from sqlalchemy import String, Text, TIMESTAMP, ForeignKey, Enum as SAEnum
  ```
  to:
  ```python
  from sqlalchemy import String, Text, TIMESTAMP, ForeignKey, Enum as SAEnum
  from sqlalchemy.schema import FetchedValue
  ```

  Change line 58-59 from:
  ```python
      search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
      # DB-generated: to_tsvector('english', content). Do not set manually.
  ```
  to:
  ```python
      search_vector: Mapped[str | None] = mapped_column(
          TSVECTOR, nullable=True, server_default=FetchedValue(), init=False
      )
      # DB-generated: to_tsvector('english', content). Do not set manually.
  ```

- [ ] **Step 3: Remove the `_CANONICAL_BUG` xfail markers from the test file**

  In `backend/tests/e2e/test_live_stack.py`, remove:
  - The `_CANONICAL_BUG` marker definition (lines ~253-256):
    ```python
    _CANONICAL_BUG = pytest.mark.xfail(
        strict=False,
        reason="App bug: GeneratedAlwaysError — canonical service sets GENERATED ALWAYS column search_vector",
    )
    ```
  - The `@_CANONICAL_BUG` decorator before each of the three canonical tests:
    - before `test_create_canonical_item`
    - before `test_canonical_list_contains_created_item`
    - before `test_delete_canonical_item`

- [ ] **Step 4: Rebuild Docker and run the canonical tests**

  ```bash
  docker compose up --build -d
  sleep 10  # Wait for containers to be healthy; retry the curl/test if the app is still starting
  cd backend && uv run pytest tests/e2e/test_live_stack.py \
      -k "canonical" -v
  ```

  Expected: `test_create_canonical_item`, `test_canonical_list_contains_created_item`, `test_delete_canonical_item` all **PASS** (not xfail, not xpass).

  If they still fail, check the Docker container logs:
  ```bash
  docker compose logs backend --tail=50
  ```
  Look for `GeneratedAlwaysError` — this means the container image wasn't rebuilt. Re-run `docker compose up --build -d`.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/app/domain/canonical_memory/models.py backend/tests/e2e/test_live_stack.py
  git commit -m "fix: use FetchedValue for GENERATED ALWAYS search_vector in canonical_memory"
  ```

---

## Task 2: Move FTS indexing before the `pending_provider` early return

**Bug:** `backend/app/worker/dispatcher.py:261-272` — when no LLM provider is configured, the dispatcher calls `set_pending_provider()` and then `return`s immediately. The FTS indexing step (lines 321-334) is never reached. The comment on line 269 says "FTS still runs even when pending_provider" but the code does the opposite.

**Fix:** Extract the FTS block into a helper call and invoke it before the `return` at line 272.

**Files:**
- Modify: `backend/app/worker/dispatcher.py:261-272` and `321-334`

- [ ] **Step 1: Locate the two code blocks**

  In `dispatcher.py`:
  - Block A (the early return, lines ~261-272):
    ```python
        if not sensitivity_decision.blocked:
            if not _has_llm_provider():
                # No provider — mark pending_provider and skip LLM steps
                await set_pending_provider(
                    session, job,
                    reason="No LLM provider configured. Add an OpenAI, Anthropic, or Ollama key in Settings.",
                )
                # Note: FTS still runs even when pending_provider (local, no external call)
                # But we return here — job status is pending_provider, not completed
                # FTS is a bonus once provider is configured and job is retried
                return
    ```
  - Block B (FTS step, lines ~321-334):
    ```python
        # ── Step 4: FTS indexing (always runs — local, no external call) ─────────
        # Use summary text if available, otherwise raw content
        try:
            existing_summary = await get_existing_summary(session, job.raw_archive_id)
            fts_text = existing_summary.summary_text if existing_summary else raw_text[:10000]
            await write_fts_entry(
                session,
                raw_archive_id=job.raw_archive_id,
                text_content=fts_text,
            )
            logger.debug("Wrote FTS entry for job %s", job.id)
        except Exception as e:
            logger.warning("FTS indexing failed for job %s (non-fatal): %s", job.id, e)
            # FTS failure is non-fatal — job still completes
    ```

- [ ] **Step 2: Apply the fix — move FTS before the `return`**

  Replace Block A with:
  ```python
      if not sensitivity_decision.blocked:
          if not _has_llm_provider():
              # No provider — run FTS first (local, no LLM needed), then mark pending_provider
              try:
                  existing_summary_fts = await get_existing_summary(session, job.raw_archive_id)
                  fts_text = existing_summary_fts.summary_text if existing_summary_fts else raw_text[:10000]
                  await write_fts_entry(
                      session,
                      raw_archive_id=job.raw_archive_id,
                      text_content=fts_text,
                  )
                  logger.debug("Wrote FTS entry for job %s (no LLM provider)", job.id)
              except Exception as e:
                  logger.warning("FTS indexing failed for job %s (non-fatal): %s", job.id, e)
              await set_pending_provider(
                  session, job,
                  reason="No LLM provider configured. Add an OpenAI, Anthropic, or Ollama key in Settings.",
              )
              return
  ```

  Block B (Step 4) remains unchanged — it runs when the LLM provider IS configured.

  Note: `get_existing_summary` and `write_fts_entry` are already imported at the top of `dispatch_job` at lines 217-222.

- [ ] **Step 3: Verify the fix compiles (import check)**

  ```bash
  cd backend && uv run python -c "from app.worker.dispatcher import dispatch_job; print('OK')"
  ```

  Expected: `OK`

- [ ] **Step 4: Commit**

  ```bash
  git add backend/app/worker/dispatcher.py
  git commit -m "fix: run FTS indexing before pending_provider return in dispatcher"
  ```

---

## Task 3: Add dev-only cache invalidation endpoint

**Bug:** `backend/app/domain/retrieval/service.py:38` — the retrieval service uses an in-process `TTLCache` with 60s TTL. E2E tests poll for search results but always hit the stale cache. The `invalidate_cache()` function already exists at lines 103-106, but there is no HTTP endpoint to call it from the test process.

**Fix:** Add `POST /api/search/invalidate-cache` to `backend/app/api/routes/search.py`, gated on `settings.is_development` (returns 403 in production).

**Files:**
- Modify: `backend/app/api/routes/search.py`

- [ ] **Step 1: Add the endpoint to search.py**

  The existing import from `app.domain.retrieval.service` in `search.py` does NOT include `invalidate_cache`.
  Add `invalidate_cache` to the existing import block (do not duplicate the other names):
  ```python
  # Change existing import from:
  from app.domain.retrieval.service import (
      RetrievalFilters,
      RetrievalRequest,
      RetrievalResponse,
      retrieve,
  )
  # To (add invalidate_cache):
  from app.domain.retrieval.service import (
      RetrievalFilters,
      RetrievalRequest,
      RetrievalResponse,
      retrieve,
      invalidate_cache,
  )
  ```

  Also add a new import line for `get_settings` (it is not yet imported in `search.py`):
  ```python
  from app.infrastructure.settings import get_settings
  ```

  Add this new route at the end of `search.py` (before the `_response_to_dict` helper):
  ```python
  @router.post("/search/invalidate-cache", status_code=200)
  async def invalidate_search_cache() -> dict:
      """Invalidate the retrieval LRU cache. Dev/test only — returns 403 in production."""
      settings = get_settings()
      if not settings.is_development:
          raise HTTPException(status_code=403, detail="Only available in development mode")
      invalidate_cache()
      return {"invalidated": True}
  ```

- [ ] **Step 2: Verify the endpoint is registered**

  Note: the `router` object has `prefix="/api"` set at mount time (not on the router itself), so
  route paths on the `router` object are stored without the `/api` prefix.

  ```bash
  cd backend && uv run python -c "
  from app.api.routes.search import router
  routes = [r.path for r in router.routes]
  print(routes)
  assert '/search/invalidate-cache' in routes, 'Route not registered'
  print('OK')
  "
  ```

  Expected: prints list including `/search/invalidate-cache` and then `OK`.
  (The full URL `/api/search/invalidate-cache` is only visible after the router is mounted into the app.)

- [ ] **Step 3: Rebuild the Docker container and verify the endpoint is live**

  ```bash
  docker compose up --build -d
  sleep 10  # Wait for the app to start; retry if curl returns connection refused
  curl -s -X POST http://localhost:8000/api/search/invalidate-cache | python3 -m json.tool
  ```

  Expected output (if `APP_ENV=development` in the container):
  ```json
  {"invalidated": true}
  ```

  If it returns `{"detail": "Only available in development mode"}`, check that the `.env` or `docker-compose.yml` sets `APP_ENV=development`.

- [ ] **Step 4: Commit**

  ```bash
  git add backend/app/api/routes/search.py
  git commit -m "feat: add dev-only POST /api/search/invalidate-cache endpoint"
  ```

---

## Task 4: Update keyword search test to use cache invalidation

**Now that the endpoint exists**, update `test_keyword_search_finds_item` in the E2E tests to call `POST /api/search/invalidate-cache` before each search poll, and remove its `xfail` marker.

**Files:**
- Modify: `backend/tests/e2e/test_live_stack.py:188-221`

- [ ] **Step 1: Locate the test**

  In `test_live_stack.py`, find and replace the **entire block** from the `@pytest.mark.xfail` decorator
  through `_ = found` (approximately lines 188-221). The full existing block is:
  ```python
  @pytest.mark.xfail(
      strict=False,
      reason=(
          "App architecture: FTS indexing is async (background job worker populates fts_entries). "
          "Ingest only enqueues a pending_pipeline job; the search retrieval service also caches "
          "results for 60s, so newly-ingested content is not visible in keyword search immediately."
      ),
  )
  async def test_keyword_search_finds_item(live_client: httpx.AsyncClient) -> None:
      """Ingest a UUID-tagged item, then search for its tag and find it.

      NOTE: This test is expected to xfail because keyword search uses FTS on fts_entries,
      which are populated by the background job pipeline — not synchronously on ingest.
      The retrieval service also caches results for 60s, compounding the delay.
      """
      tag = uuid4()
      content = f"E2E-{tag} keyword search recalium integration"
      ingest_resp = await live_client.post("/api/ingest", json={"content": content})
      assert ingest_resp.status_code == 202
      item_id = ingest_resp.json()["archive_ids"][0]
      live_client.register(item_id)

      async def _search_finds_tag() -> bool:
          resp = await live_client.get(
              "/api/search",
              params={"q": str(tag), "mode": "keyword"},
          )
          if resp.status_code != 200:
              return False
          return any(str(tag) in item.get("content", "") for item in resp.json()["items"])

      found = await wait_for(_search_finds_tag, timeout=15.0)
      # wait_for already calls pytest.fail on timeout; the return value is truthy
      _ = found  # prevent "variable assigned but never used" warnings
  ```

- [ ] **Step 2: Apply the fix**

  Replace the block with (remove the `xfail` decorator and add cache invalidation before search):
  ```python
  async def test_keyword_search_finds_item(live_client: httpx.AsyncClient) -> None:
      """Ingest a UUID-tagged item, then search for its tag and find it.

      Polls with cache invalidation to ensure freshly-indexed FTS data is visible.
      """
      tag = uuid4()
      content = f"E2E-{tag} keyword search recalium integration"
      ingest_resp = await live_client.post("/api/ingest", json={"content": content})
      assert ingest_resp.status_code == 202
      item_id = ingest_resp.json()["archive_ids"][0]
      live_client.register(item_id)

      async def _search_finds_tag() -> bool:
          # Invalidate cache so stale results don't hide newly-indexed content
          await live_client.post("/api/search/invalidate-cache")
          resp = await live_client.get(
              "/api/search",
              params={"q": str(tag), "mode": "keyword"},
          )
          if resp.status_code != 200:
              return False
          return any(str(tag) in item.get("content", "") for item in resp.json()["items"])

      found = await wait_for(_search_finds_tag, timeout=30.0)
      _ = found
  ```

  Note: timeout increased to 30s to give the background worker time to process the job and populate FTS.

- [ ] **Step 3: Run the test**

  ```bash
  cd backend && uv run pytest tests/e2e/test_live_stack.py \
      -k "test_keyword_search_finds_item" -v
  ```

  Expected: **PASSED** (not xfail, not xpass — just PASSED).

- [ ] **Step 4: Commit**

  ```bash
  git add backend/tests/e2e/test_live_stack.py
  git commit -m "test: update keyword search E2E test to invalidate cache before polling"
  ```

---

## Task 5: Rewrite `_mcp_call` using `mcp.client.sse.sse_client`

**Bug:** `backend/tests/e2e/test_live_stack.py:386-421` — the current `_mcp_call` helper:
1. GETs `/mcp/sse`, reads the session endpoint, then closes the stream
2. POSTs directly to the session endpoint and expects a 200 JSON response

This is wrong because the SSE transport always returns 202 from the POST endpoint and delivers the JSON-RPC result on the SSE stream. Also, the MCP `initialize` handshake must be performed before any `tools/call`.

**Fix:** Rewrite `_mcp_call` using `mcp.client.sse.sse_client` from the `mcp` package (v1.26.0, already installed as a backend dependency). This handles the SSE connection, initialize handshake, and message correlation transparently.

**Files:**
- Modify: `backend/tests/e2e/test_live_stack.py`

- [ ] **Step 1: Verify the `mcp` package import works**

  ```bash
  cd backend && uv run python -c "
  from mcp.client.sse import sse_client
  from mcp import ClientSession
  print('mcp imports OK')
  "
  ```

  Expected: `mcp imports OK`

- [ ] **Step 2: Add the import and rewrite `_mcp_call`**

  At the top of `test_live_stack.py`, add the imports after the existing imports:
  ```python
  import json as _json
  from mcp.client.sse import sse_client
  from mcp import ClientSession
  ```

  Replace `_mcp_call` (lines 386-421) with:
  ```python
  async def _mcp_call(client: httpx.AsyncClient, tool: str, arguments: dict) -> dict:
      """Helper: establish MCP SSE session and call a tool.

      Uses mcp.client.sse.sse_client for proper SSE transport handling,
      including the mandatory initialize handshake before any tools/call.

      Returns the parsed result dict (the actual tool output, not the JSON-RPC envelope).
      Raises AssertionError if the session fails or the tool returns an error.
      """
      base_url = str(client.base_url).rstrip("/")
      mcp_url = f"{base_url}/mcp/sse"

      async with sse_client(mcp_url) as (read, write):
          async with ClientSession(read, write) as session:
              await session.initialize()
              result = await session.call_tool(tool, arguments)

      # result.content is a list of TextContent objects
      # FastMCP wraps non-string returns in TextContent with .text = JSON string
      assert result.content, f"MCP tool {tool!r} returned empty content"
      raw_text = result.content[0].text
      try:
          return _json.loads(raw_text)
      except (_json.JSONDecodeError, TypeError):
          # If not JSON, return as-is in a dict for consistent interface
          return {"text": raw_text}
  ```

- [ ] **Step 3: Remove the `_MCP_XFAIL` marker and clean up**

  Find and remove the marker definition:
  ```python
  _MCP_XFAIL = pytest.mark.xfail(
      strict=False,
      reason="MCP SSE transport: POST to session endpoint returns 202 (async), not 200 with JSON-RPC result",
  )
  ```

  And remove the decorator from the three MCP tests:
  - `@_MCP_XFAIL` before `test_mcp_ingest_memory_success`
  - `@_MCP_XFAIL` before `test_mcp_ingest_memory_missing_content`
  - `@_MCP_XFAIL` before `test_mcp_retrieve_returns_results`

  Also update the assertion in `test_mcp_ingest_memory_success` — with the new helper, `result` is already the parsed tool output dict (no JSON-RPC envelope).

  **Verified tool return shapes** (from `backend/app/mcp_server/server.py`):
  - `ingest_memory` with valid content → `{"status": "accepted", "item_count": N, "archive_ids": ["<uuid>", ...]}`
  - `ingest_memory` with empty string → `{"error": "content is required and must be non-empty"}`
  - `retrieve_memory` → `{"query": "...", "retrieval_mode": "...", "items": [...], ...}`

  These are JSON-serialized by FastMCP into `result.content[0].text`, which `_mcp_call` parses back to a dict.

  Replace the three MCP test functions with:
  ```python
  async def test_mcp_ingest_memory_success(live_client: httpx.AsyncClient) -> None:
      """MCP ingest_memory tool with valid content returns accepted status."""
      tag = uuid4()
      content = f"E2E-{tag} MCP ingest memory recalium integration"
      result = await _mcp_call(live_client, "ingest_memory", {"content": content})
      assert "error" not in result
      assert result.get("status") == "accepted"
      if "archive_ids" in result:
          for aid in result["archive_ids"]:
              live_client.register(aid)
  ```

  And for `test_mcp_ingest_memory_missing_content`:
  ```python
  async def test_mcp_ingest_memory_missing_content(live_client: httpx.AsyncClient) -> None:
      """MCP ingest_memory tool with empty content returns descriptive error (not 500)."""
      result = await _mcp_call(live_client, "ingest_memory", {"content": ""})
      assert "error" in result
      assert "content" in result["error"].lower()
  ```

  And for `test_mcp_retrieve_returns_results`:
  ```python
  async def test_mcp_retrieve_returns_results(live_client: httpx.AsyncClient) -> None:
      """MCP retrieve_memory tool with a query returns a results envelope (no 500)."""
      result = await _mcp_call(live_client, "retrieve_memory", {"query": "test memory recalium"})
      assert "items" in result
      assert isinstance(result["items"], list)
  ```

  Note: The `_CANONICAL_BUG` xfail markers were already removed in Task 1 Step 3.

- [ ] **Step 4: Run the MCP tests**

  ```bash
  cd backend && uv run pytest tests/e2e/test_live_stack.py \
      -k "mcp" -v
  ```

  Expected: `test_mcp_ingest_memory_success`, `test_mcp_ingest_memory_missing_content`, `test_mcp_retrieve_returns_results` all **PASS**.

  If `test_mcp_ingest_memory_missing_content` raises an `McpError` exception instead of returning `{"error": ...}`, the MCP framework may surface tool errors as exceptions rather than error-shaped dicts. In that case, check whether the exception message contains "content" and update the test to assert on the exception string:
  ```python
  try:
      result = await _mcp_call(live_client, "ingest_memory", {"content": ""})
      # Tool returned an error dict (preferred path)
      assert "error" in result, f"Expected error key in result, got: {result}"
      assert "content" in result["error"].lower()
  except Exception as e:
      # Tool raised instead of returning an error dict
      assert "content" in str(e).lower(), f"Expected content-related error, got: {type(e).__name__}: {e}"
      raise  # Re-raise if assertion fails so the test fails clearly
  ```
  Note: only use this fallback if the test fails with an exception on the first run. The primary path (tool returns `{"error": ...}`) is correct based on the tool implementation in `backend/app/mcp_server/server.py:123`.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/tests/e2e/test_live_stack.py
  git commit -m "fix: rewrite _mcp_call using mcp.client.sse for proper SSE transport"
  ```

---

## Task 6: Final verification — all 27 tests pass

- [ ] **Step 1: Rebuild Docker containers**

  If you haven't already after Task 1-3 changes:
  ```bash
  docker compose up --build -d
  sleep 10  # Wait for containers to be healthy
  ```

- [ ] **Step 2: Run the full E2E suite**

  ```bash
  cd backend && uv run pytest tests/e2e/ -v
  ```

  Expected output: `27 passed` with no `xfail`, no `xpass`, no `failed`.

- [ ] **Step 3: If any test still fails**

  For canonical tests failing: check Docker container logs:
  ```bash
  docker compose logs backend --tail=50
  ```
  Look for `GeneratedAlwaysError` — the container must be rebuilt.

  For keyword search failing: check that `APP_ENV=development` is set in the container (so the cache invalidation endpoint returns 200, not 403):
  ```bash
  docker compose exec backend env | grep APP_ENV
  ```

  For MCP tests failing: check whether the MCP server is mounted. Look for `/mcp/sse` in the app's route list:
  ```bash
  curl -s http://localhost:8000/openapi.json | python3 -c "import sys,json; d=json.load(sys.stdin); print([p for p in d['paths'] if 'mcp' in p])"
  ```

- [ ] **Step 4: Confirm xfail markers are gone**

  ```bash
  cd backend && grep -n "xfail" tests/e2e/test_live_stack.py
  ```

  Expected: no output (all xfail markers removed).

- [ ] **Step 5: Final commit if any cleanup was needed**

  ```bash
  git add -A
  git commit -m "test: verify all 27 E2E tests pass, remove all xfail markers"
  ```
