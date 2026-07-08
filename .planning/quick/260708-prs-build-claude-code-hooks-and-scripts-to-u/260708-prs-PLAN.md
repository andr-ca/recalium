---
task_id: 260708-prs
task_name: Build Claude Code ↔ Recalium Integration (Hooks & CLI)
context_level: quick
estimated_duration_minutes: 90
target_context_usage: 30%
created_by: gsd-planner
created_at: 2026-07-08
---

# Objective

Build a reusable Claude Code ↔ Recalium integration: zero-dependency (Python stdlib only) hooks and helper scripts that let any Claude Code session automatically retrieve relevant Recalium memory and ingest finished sessions back into it. All configuration via `.env`, no hardcoded secrets, fail-soft everywhere.

**Deliverables:** 8 focused files in new `integrations/claude-code/` directory:
1. `recalium_client.py` — Shared stdlib HTTP client
2. `cli.py` — Manual `recall`/`remember` CLI
3. Three hooks: `session_start.py`, `user_prompt_submit.py`, `session_end.py`
4. `settings.example.json` — Claude Code hook configuration template
5. `README.md` — Setup and integration guide
6. Update `.env.sample` with new config vars

**Purpose:** Close the memory loop for Claude Code sessions—retrieve context before starting, inject into prompts, and archive finished work back into Recalium without manual steps.

---

# Context

## Project State
- **Phase:** Post-v1 (production ready, now adding integrations)
- **Stack:** Python stdlib only (no uv/pip within hooks); FastAPI backend at `http://localhost:8000`
- **MCP:** SSE endpoint already running at `/mcp/sse` (from recent 260708-a7m work)
- **Patterns:** See `memory/hooks/session-end.py` for session extraction + background dispatch, `memory/scripts/copilot_client.py` for stdlib urllib HTTP

## Contracts (Verified, Don't Change Backend)
- **POST /api/retrieve**: `{"query": str, "mode": "hybrid|keyword|semantic", "budget": int, "limit": int, "filters": {...}, "actor": str}` → `{"items": [...], "budget_used": int, "degraded_mode": bool, ...}`
- **POST /api/ingest**: `{"mode": "text", "content": str, "source_name": str}` → HTTP 202 `{"status": "accepted", "item_count": int, "archive_ids": [...]}`

## Key Constraints
- **Stdlib only:** urllib.request, json, os, sys, pathlib, hashlib, subprocess, argparse — no mcp SDK or external deps
- **Fail-soft:** Down/unreachable Recalium must never break a Claude Code session; hooks return `{}` on any error
- **Config via .env:** RECALIUM_URL (default `http://localhost:8000`), RECALIUM_TOKEN (optional bearer), RECALIUM_TIMEOUT_S (default 5)
- **Secrets:** Bearer token only sent when RECALIUM_TOKEN is set; never hardcode
- **Idempotency:** Session end uses marker files under `~/.recalium/ingested/<session_id>` to prevent duplicate archives

## Existing Patterns to Follow
- Recursion guard: `if os.environ.get("ENV_VAR"): sys.exit(0)`
- Background dispatch: `subprocess.Popen(..., stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)`
- Hook format: Read JSON from stdin → emit JSON to stdout, return `{}` for no-op

---

# Task 1: Core Client Library + Hooks + CLI

**Objective:** Implement the shared HTTP client, all three hooks, and the CLI tool.

**Files:**
- `integrations/claude-code/recalium_client.py` — Stdlib HTTP client with fail-soft error handling
- `integrations/claude-code/hooks/session_start.py` — SessionStart hook
- `integrations/claude-code/hooks/user_prompt_submit.py` — UserPromptSubmit hook
- `integrations/claude-code/hooks/session_end.py` — SessionEnd hook with idempotency
- `integrations/claude-code/cli.py` — Manual recall/remember CLI

**Action:**

### 1.1 Create `integrations/claude-code/recalium_client.py`

Stdlib HTTP client with the following interface:

```python
class RecaliumClient:
    __init__(self, url: str | None = None, token: str | None = None, timeout_s: float | None = None)
    
    def retrieve(self, query: str, mode: str = "hybrid", budget: int = 4096, limit: int = 10, filters: dict = None, actor: str = "claude-code") -> dict | None
        # POST /api/retrieve → returns items list or None on any error (fail-soft)
        
    def ingest(self, content: str, source_name: str) -> dict | None
        # POST /api/ingest → returns response dict or None on any error
```

**Config loading logic:**
1. Check env vars: `RECALIUM_URL`, `RECALIUM_TOKEN`, `RECALIUM_TIMEOUT_S`
2. If not set, search for `.env` in: current working directory → parent directories → repo root (cwd + `/../..`)
3. Load `.env` using pathlib only (no python-dotenv; simple key=value parsing)
4. Defaults: URL=`http://localhost:8000`, TIMEOUT_S=`5`, TOKEN=`None` (no bearer if not set)

**Error handling (fail-soft everywhere):**
- Connection refused, timeout, 4xx/5xx HTTP → return `None` (not an exception)
- Log errors to stderr for debugging, but never block the caller
- Catch: `urllib.error.URLError`, `urllib.error.HTTPError`, `socket.timeout`, `json.JSONDecodeError`, `OSError`

**Request format:**
- POST to URL/path with JSON body
- Add `Authorization: Bearer {TOKEN}` header ONLY when TOKEN is set
- Add `Content-Type: application/json`
- Add `Timeout: TIMEOUT_S`

### 1.2 Create `integrations/claude-code/hooks/session_start.py`

Read hook JSON from stdin (Claude Code SessionStart event), derive a query from the project context, fetch relevant memory, emit hook output.

**Input (stdin):** Claude Code hook JSON with `hookEventName: "SessionStart"`, `sessionId`, `workspacePath`, etc.

**Action:**
1. Parse stdin JSON
2. Recursion guard: `if os.environ.get("RECALIUM_HOOK_ACTIVE"): sys.exit(0)`
3. Set `RECALIUM_HOOK_ACTIVE=1` for child calls
4. Derive query from workspace: extract basename or use "recent context" as fallback
5. Call `retrieve(query, mode="hybrid", budget=2048, limit=5)`
6. If items found: format as `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "<formatted items with source provenance>"}}`
7. If no items or error: emit `{}`

**Formatting:** Include source_name + captured_at for each item so user knows where context came from.

**Max context cap:** Limit formatted output to ~2000 chars to avoid overwhelming the session.

### 1.3 Create `integrations/claude-code/hooks/user_prompt_submit.py`

Use the user's submitted prompt as the retrieval query; inject top-N items as additional context.

**Input (stdin):** Claude Code hook JSON with `hookEventName: "UserPromptSubmit"`, `prompt` (the user's input).

**Action:**
1. Parse stdin JSON
2. Recursion guard: `if os.environ.get("RECALIUM_HOOK_ACTIVE"): sys.exit(0)`
3. Skip if prompt is trivially short (< 15 chars)
4. Set `RECALIUM_HOOK_ACTIVE=1`
5. Call `retrieve(prompt, mode="hybrid", budget=1024, limit=3)`
6. If items: emit `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "<formatted>"}}`
7. Else: emit `{}`

### 1.4 Create `integrations/claude-code/hooks/session_end.py`

Extract finished conversation from transcript JSONL, ingest once per session (idempotency via marker file), spawn background subprocess so hook returns immediately.

**Input (stdin):** Claude Code hook JSON with `hookEventName: "Stop"` or `"SessionEnd"`, `sessionId`, `transcriptPath`.

**Claude Code transcript format (JSONL):** Newline-delimited JSON lines where:
- `type: "user"` → `message.content` is a str
- `type: "assistant"` → `message.content` is a list of blocks; text blocks have `{"type": "text", "text": "..."}`

**Action:**
1. Recursion guard: `if os.environ.get("RECALIUM_HOOK_ACTIVE"): sys.exit(0)`
2. Parse transcript JSONL (like Copilot but for Claude Code format)
3. Extract Human:/Assistant: turns
4. Idempotency: check if marker file exists at `~/.recalium/ingested/{session_id}`. If yes, return `{}` (skip)
5. Spawn background subprocess (Python subprocess, detached) with the actual ingest call
6. Return `{}` immediately (don't wait for background process)
7. Background process:
   - Set `RECALIUM_HOOK_ACTIVE=1`
   - Call `ingest(content, source_name=f"Claude Code — {workspace_name}")`
   - Create marker file at `~/.recalium/ingested/{session_id}` after successful ingest

### 1.5 Create `integrations/claude-code/cli.py`

Manual CLI for terminal use: `recall <query>` and `remember <text | @file>`.

**Usage:**
```bash
python3 integrations/claude-code/cli.py recall "topic to search"
python3 integrations/claude-code/cli.py remember "text to remember"
python3 integrations/claude-code/cli.py remember @path/to/file.txt
```

**Implementation:**
- Use `argparse` for simple command/arg parsing
- `recall`: Call `retrieve(query)`, pretty-print results with source + score
- `remember`: Ingest text, print confirmation with archive IDs
- Use the same `RecaliumClient` for HTTP calls

**Verify:**
```bash
python3 -m py_compile integrations/claude-code/recalium_client.py
python3 -m py_compile integrations/claude-code/hooks/session_start.py
python3 -m py_compile integrations/claude-code/hooks/user_prompt_submit.py
python3 -m py_compile integrations/claude-code/hooks/session_end.py
python3 -m py_compile integrations/claude-code/cli.py
```

All scripts must compile without errors or warnings.

**Done:**
- All 5 files exist in correct locations
- All compile via `python3 -m py_compile`
- Functions match documented signatures
- Error handling is fail-soft (no exceptions escape)
- Env var loading works from .env or defaults
- Bearer token only sent when RECALIUM_TOKEN is set

---

# Task 2: Configuration, Documentation, and Smoke Testing

**Objective:** Create settings template, README, update env.sample, and run smoke tests to verify the integration works end-to-end.

**Files:**
- `integrations/claude-code/settings.example.json` — Claude Code hook config block
- `integrations/claude-code/README.md` — Setup guide
- `.env.sample` — Updated with new env vars

**Action:**

### 2.1 Create `integrations/claude-code/settings.example.json`

Provide a ready-to-copy Claude Code settings block that wires the three hooks.

**Content:** Include:
- Hook invocation paths (use absolute paths or repo-relative with `${workspaceFolder}`)
- Notes on user-scope vs project-scope installation
- Example of setting optional RECALIUM_* env vars in the hook command
- Comments on when each hook fires and what to expect

### 2.2 Create `integrations/claude-code/README.md`

Document:
- **Prerequisites:** Recalium stack running via `docker compose up`
- **Installation:** Copy settings block into `.claude/settings.json`, or set hooks at user scope
- **Environment variables:** RECALIUM_URL, RECALIUM_TOKEN, RECALIUM_TIMEOUT_S
- **Usage:** How hooks work (SessionStart retrieves, UserPromptSubmit injects, SessionEnd archives)
- **Mapping to MCP:** How this mirrors `retrieve_memory` and `ingest_memory` MCP tools
- **Troubleshooting:** Stack down → hooks no-op gracefully; check logs; bearer token issues
- **Idempotency:** SessionEnd marker file behavior — second run with same session_id skips
- **CLI:** How to use `cli.py recall` and `cli.py remember` manually

### 2.3 Update `.env.sample`

Add three new entries:
```
# ── Claude Code Integration ─────────────────────────────────────────────────
# Recalium endpoint for Claude Code hooks and CLI
RECALIUM_URL=http://localhost:8000
# Optional bearer token for authenticated access (leave empty if not using auth)
RECALIUM_TOKEN=
# Timeout for HTTP calls to Recalium (seconds)
RECALIUM_TIMEOUT_S=5
```

### 2.4 Smoke Tests

**Live stack running** (`docker compose up` in the background):

1. **Compilation check (all scripts):**
   ```bash
   python3 -m py_compile integrations/claude-code/recalium_client.py
   python3 -m py_compile integrations/claude-code/cli.py
   # ... all hook files
   ```

2. **CLI round-trip test (remember → recall):**
   ```bash
   python3 integrations/claude-code/cli.py remember "Test memory entry from Claude Code"
   python3 integrations/claude-code/cli.py recall "Claude Code"
   # Expected: Recent entry appears in results with source provenance
   ```

3. **SessionStart hook with synthetic payload:**
   ```bash
   echo '{"hookEventName":"SessionStart","sessionId":"test-001","workspacePath":"/path/to/project"}' | \
     python3 integrations/claude-code/hooks/session_start.py
   # Expected: stdout is valid JSON (either {} or {"hookSpecificOutput": {...}})
   ```

4. **UserPromptSubmit hook with synthetic payload:**
   ```bash
   echo '{"hookEventName":"UserPromptSubmit","sessionId":"test-001","prompt":"How do I retrieve memory from Recalium?"}' | \
     python3 integrations/claude-code/hooks/user_prompt_submit.py
   # Expected: stdout is valid JSON
   ```

5. **SessionEnd hook with synthetic payload:**
   ```bash
   # Create a synthetic transcript JSONL file
   cat > /tmp/test_transcript.jsonl << 'EOF'
   {"type":"user","message":{"content":"What is Recalium?"}}
   {"type":"assistant","message":{"content":[{"type":"text","text":"Recalium is a local-first personal memory platform."}]}}
   EOF
   
   echo '{"hookEventName":"SessionEnd","sessionId":"test-001-end","transcriptPath":"/tmp/test_transcript.jsonl","workspacePath":"/tmp"}' | \
     python3 integrations/claude-code/hooks/session_end.py
   # Expected: stdout is {} (background process spawned); after a short delay, check that ingest happened
   ```

6. **SessionEnd idempotency check:**
   - Verify marker file is created at `~/.recalium/ingested/test-001-end` after first ingest
   - Run the same hook again with same session_id
   - Verify no duplicate archive (same session_id only creates one archive item)

7. **Stack down resilience:**
   - Stop `docker compose`
   - Run CLI recall/remember and hooks with RECALIUM_URL pointing to unused port (e.g., `http://localhost:9999`)
   - Verify: No crashes, graceful no-op (empty results, empty hook output)

**Done:**
- `settings.example.json` is valid JSON and copyable
- `README.md` explains setup, usage, and troubleshooting
- `.env.sample` has sanitized new entries with comments
- All smoke tests pass (compilation, round-trip, hook JSON validation, idempotency, resilience)
- Git status clean except for new integration files

---

# Verification

## Automated Checks
```bash
# 1. All scripts compile
python3 -m py_compile integrations/claude-code/recalium_client.py
python3 -m py_compile integrations/claude-code/hooks/session_start.py
python3 -m py_compile integrations/claude-code/hooks/user_prompt_submit.py
python3 -m py_compile integrations/claude-code/hooks/session_end.py
python3 -m py_compile integrations/claude-code/cli.py

# 2. JSON config files are valid
python3 -c "import json; json.load(open('integrations/claude-code/settings.example.json'))"

# 3. Smoke tests (with live stack)
python3 integrations/claude-code/cli.py remember "smoke test entry"
python3 integrations/claude-code/cli.py recall "smoke"  # Verify entry appears

# 4. Hook output is valid JSON (stdin tests)
echo '{"hookEventName":"SessionStart","sessionId":"test","workspacePath":"/tmp"}' | \
  python3 integrations/claude-code/hooks/session_start.py | python3 -m json.tool

# 5. Idempotency — second SessionEnd doesn't duplicate
# (Verified via marker file and archive count check)
```

## Manual Verification
- [ ] All 8 files created in correct locations
- [ ] No hardcoded URLs, keys, or secrets in any file
- [ ] `.env.sample` entries are sanitized (empty values)
- [ ] `README.md` is clear and actionable
- [ ] `settings.example.json` is copyable and correctly formatted
- [ ] Hook JSON output is always valid (either `{}` or `{"hookSpecificOutput": {...}}`)
- [ ] Bearer token only sent when RECALIUM_TOKEN is set
- [ ] Stack-down scenarios don't crash or hang

---

# Success Criteria

1. **Deliverables:** All 8 files exist with expected content
2. **Compilation:** All Python scripts compile without errors
3. **Config:** Env vars loaded correctly; bearer token only sent when set
4. **Functionality:** CLI round-trip works (remember → recall); hooks emit valid JSON
5. **Resilience:** Down/unreachable stack → graceful no-op (empty results, `{}` output)
6. **Idempotency:** SessionEnd marker file prevents duplicate archives
7. **Documentation:** README is complete; settings.example.json is copy-paste ready
8. **Git:** New integration directory committed cleanly
