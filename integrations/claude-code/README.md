# Claude Code ↔ Recalium Integration

Automatic memory retrieval and archival for Claude Code sessions using Recalium.

This integration consists of three hooks and a CLI tool:
- **SessionStart hook** — Retrieves relevant context when a new session starts
- **UserPromptSubmit hook** — Injects related memory based on your prompt
- **SessionEnd hook** — Archives the finished session transcript into Recalium
- **CLI tool** — Manual `recall` and `remember` commands for the terminal

## Prerequisites

1. **Recalium running locally**

   ```bash
   cd /path/to/recalium
   docker compose up
   ```

   Confirm the stack is ready:

   ```bash
   curl http://localhost:8000/api/health
   # Expected: {"status": "ok", ...}
   ```

2. **Python 3.7+** (for hook execution)

3. **Claude Code** (installed and configured)

## Installation

`settings.example.json` is a ready-to-copy Claude Code hooks block. Claude Code's
hook schema uses PascalCase event names (`SessionStart`, `UserPromptSubmit`,
`SessionEnd`), each mapping to a list of `{ "hooks": [ { "type": "command",
"command": "..." } ] }` entries — **not** a VS Code `enabled`/`args`/`environment`
object. Use the example verbatim; only the script path changes between scopes.

### Option 1: Project-scope hooks (only inside the Recalium repo)

Use this when Claude Code is running with the Recalium repo as the project.
`$CLAUDE_PROJECT_DIR` resolves to the project root at hook time.

1. Merge the `hooks` block from `settings.example.json` into `.claude/settings.json`:

   ```bash
   mkdir -p .claude
   cp integrations/claude-code/settings.example.json .claude/settings.json
   ```

   (If `.claude/settings.json` already exists, merge the `SessionStart` /
   `UserPromptSubmit` / `SessionEnd` arrays into its `hooks` object rather than
   overwriting the file.)

2. Restart Claude Code (already-open sessions do not pick up new hooks).

### Option 2: User-scope hooks (every project, system-wide)

To make the hooks fire in **all** projects, add the same block to your user
settings at `~/.claude/settings.json`, but replace `$CLAUDE_PROJECT_DIR` with an
**absolute path to your Recalium checkout** — in another project
`$CLAUDE_PROJECT_DIR` points at *that* project, where these scripts don't exist:

```json
"command": "python3 \"/absolute/path/to/recalium/integrations/claude-code/hooks/session_start.py\""
```

Because the hooks default to `http://localhost:8000` and need no token for a
local stack, no extra environment configuration is required for the common case.

## Configuration

All configuration uses environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `RECALIUM_URL` | `http://localhost:8000` | Recalium API endpoint |
| `RECALIUM_TOKEN` | (empty) | Optional bearer token for authenticated access |
| `RECALIUM_TIMEOUT_S` | `5` | HTTP request timeout in seconds |

These are all optional — the defaults work against a local stack. Set them only
for a non-default URL or bearer auth.

### Loading from `.env` file

The client (`recalium_client.py`) reads these variables from the OS environment
first, then searches for a `.env` file in the current working directory and up to
three parent directories. When Claude Code runs a hook, the working directory is
the active project — so a project-local `.env` (e.g. the Recalium repo's `.env`)
is picked up automatically in project scope. For user-scope hooks running in other
projects, set the variables in your shell/OS environment instead.

## Usage

### Hooks (Automatic)

Once installed, the hooks run automatically:

1. **SessionStart** (fires immediately when you start a new Claude Code session)
   - Queries Recalium with the project name
   - Injects top-5 relevant items into the session context
   - Returns `{}` if Recalium is unreachable or no items found

2. **UserPromptSubmit** (fires after you submit a prompt)
   - Uses your prompt as the search query
   - Retrieves top-3 relevant items
   - Injects context *before* Claude processes your prompt
   - Skips trivially short prompts (< 15 chars)

3. **SessionEnd** (fires when you stop a session)
   - Extracts your entire session transcript
   - Spawns a background process to ingest it into Recalium
   - Returns immediately (non-blocking)
   - Prevents duplicate archives via marker file at `~/.recalium/ingested/<session_id>`

### CLI (Manual)

Use `cli.py` for interactive memory operations in the terminal:

```bash
# Search for related memory
python3 integrations/claude-code/cli.py recall "topic or keywords"

# Store text in memory
python3 integrations/claude-code/cli.py remember "Some important fact or decision"

# Store content from a file
python3 integrations/claude-code/cli.py remember @path/to/session_notes.txt
```

## Mapping to MCP

This integration mirrors Recalium's MCP tools:

| Hook/CLI | MCP Tool | Mode |
|----------|----------|------|
| SessionStart + UserPromptSubmit | `retrieve_memory` | Hybrid (keyword + semantic) |
| SessionEnd | `ingest_memory` | Deferred (background) |
| CLI `recall` | `retrieve_memory` | Hybrid |
| CLI `remember` | `ingest_memory` | Deferred |

All retrievals include source provenance (`source_system`, `type`, `captured_at`) so you know where context came from. Items are labelled `[source_system · type]` (e.g. `[paste_text · excerpt]`).

## Troubleshooting

### Hooks not firing or showing no context

1. **Recalium stack is down:**
   - Hooks fail gracefully and emit `{}` (no context)
   - Check: `curl http://localhost:8000/api/health`
   - If down: `cd /path/to/recalium && docker compose up`

2. **Hooks not registered:**
   - Check `.claude/settings.json` has `SessionStart` / `UserPromptSubmit` /
     `SessionEnd` arrays under `hooks` (PascalCase), matching `settings.example.json`
   - Restart Claude Code — open sessions don't pick up newly added hooks

3. **Wrong path to hooks:**
   - Verify the `command` path resolves to the real script. In project scope
     `$CLAUDE_PROJECT_DIR` must point at the Recalium repo; in user scope use an
     absolute path to the checkout
   - Test resolution: `python3 "$CLAUDE_PROJECT_DIR/integrations/claude-code/hooks/session_start.py" < /dev/null`

4. **Bearer token rejected:**
   - If you set `RECALIUM_TOKEN`, ensure it's valid for your Recalium instance
   - Leave empty if your Recalium doesn't use auth (default localhost)

### Debugging

- **Hooks:** Check Claude Code output panel for error messages
- **CLI:** Run commands with stderr visible to see connection errors
- **Recalium logs:** `docker compose logs recalium-app` for API-side issues

Example debugging:

```bash
# Test the hook with synthetic input (Claude Code fields are snake_case)
echo '{"hook_event_name":"SessionStart","session_id":"test-001","cwd":"/tmp"}' | \
  python3 integrations/claude-code/hooks/session_start.py | python3 -m json.tool

# Should output valid JSON (either {} or {"hookSpecificOutput": {...}})
```

### SessionEnd idempotency

- **First run:** Archives transcript, creates marker at `~/.recalium/ingested/{session_id}`
- **Subsequent runs (same session_id):** Returns `{}` without re-ingesting
- **To re-ingest:** Delete the marker file: `rm ~/.recalium/ingested/{session_id}`

## Testing

### Compilation check

```bash
python3 -m py_compile integrations/claude-code/recalium_client.py
python3 -m py_compile integrations/claude-code/hooks/session_start.py
python3 -m py_compile integrations/claude-code/hooks/user_prompt_submit.py
python3 -m py_compile integrations/claude-code/hooks/session_end.py
python3 -m py_compile integrations/claude-code/cli.py
```

### Round-trip test (remember → recall)

```bash
# Store a test entry
python3 integrations/claude-code/cli.py remember "Claude Code integration test entry"

# Retrieve it
python3 integrations/claude-code/cli.py recall "Claude Code integration"

# Expected: Test entry appears in results with source "Claude Code — CLI"
```

### Hook JSON validation

```bash
# Test SessionStart hook with synthetic input
echo '{"hook_event_name":"SessionStart","session_id":"test","cwd":"/tmp/project"}' | \
  python3 integrations/claude-code/hooks/session_start.py | python3 -m json.tool

# Expected: Valid JSON output (either {} or {"hookSpecificOutput": {...}})

# Test SessionEnd hook (writes an idempotency marker, spawns a background ingest)
printf '%s\n%s\n' \
  '{"type":"user","message":{"content":"remember this test note"}}' \
  '{"type":"assistant","message":{"content":[{"type":"text","text":"noted"}]}}' > /tmp/t.jsonl
echo '{"session_id":"end-test","transcript_path":"/tmp/t.jsonl","cwd":"/tmp/project"}' | \
  python3 integrations/claude-code/hooks/session_end.py
# Expected: {}  — then ~/.recalium/ingested/end-test appears after ingest succeeds
```

### Resilience test (stack down)

```bash
# Stop the Recalium stack
docker compose down

# Test CLI — should gracefully fail with message, not crash
python3 integrations/claude-code/cli.py recall "test"

# Expected: "ERROR: Could not reach Recalium..."

# Test hooks with RECALIUM_URL pointing to unused port
RECALIUM_URL=http://localhost:9999 python3 integrations/claude-code/hooks/session_start.py < /dev/null

# Expected: Output is {} (empty JSON)
```

## Architecture

### Fail-soft design

All components fail gracefully:
- Connection errors → return `None` (hooks) or print error (CLI)
- Invalid JSON → skip processing
- Timeout → no-op gracefully
- Recalium unreachable → hooks emit `{}`, CLI prints friendly error

### Recursion guards

Each hook checks `RECALIUM_HOOK_ACTIVE` env var to prevent infinite loops if a hook triggers the same hook again. **SessionStart** and **UserPromptSubmit** set this guard during execution.

### Idempotency

**SessionEnd** uses marker files to prevent duplicate archives:
- Location: `~/.recalium/ingested/{session_id}`
- First ingest: Creates marker after successful upload
- Subsequent runs: Checks marker, returns `{}` without re-ingesting

### Background dispatch

**SessionEnd** spawns an `asyncio`-free background subprocess for ingestion. The hook returns immediately without waiting for the subprocess, preventing blocking of Claude Code's event loop.

## Performance

- **SessionStart retrieval:** ~500ms–2s (depends on Recalium data volume)
- **UserPromptSubmit retrieval:** ~200ms–1s (smaller budget)
- **SessionEnd ingest:** ~0ms hook return + background ingest (1–5s in subprocess)
- **CLI recall:** ~1–3s (network + retrieval)
- **CLI remember:** ~200ms–2s (network + ingest)

All operations use `RECALIUM_TIMEOUT_S` (default 5s) to avoid blocking indefinitely.

## Advanced: Custom retrieval modes

Retrieval mode, budget, and item limit are set where each hook calls
`client.retrieve(...)` — e.g. `session_start.py` uses
`retrieve(query, mode="hybrid", budget=2048, limit=5)` and `user_prompt_submit.py`
uses `mode="hybrid", budget=1024, limit=3`. To customise, edit those calls
directly (for example switch `mode="keyword"` for keyword-only retrieval, or lower
`limit`). Only `RECALIUM_URL`, `RECALIUM_TOKEN`, and `RECALIUM_TIMEOUT_S` are read
from the environment; the client does not read mode/budget/limit env vars.

## Future extensions

- **Query templating:** Derive query from project metadata, git history, or custom prompt
- **Filtering:** Filter by source system, date range, or tags
- **Semantic search mode:** Switch to semantic-only (no keyword) for code-focused tasks
- **Streaming:** Stream context injection for long retrieval results
- **Conflict resolution:** Surface conflicting facts with source provenance

## Support

For issues with Recalium itself, see:
- Recalium GitHub: https://github.com/andrey/recalium
- Issue tracker
- MCP specification: https://modelcontextprotocol.io

For Claude Code issues, consult the Claude Code documentation.

## License

Same as Recalium.
