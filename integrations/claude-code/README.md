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

### Option 1: Project-scope hooks (recommended for development)

1. Copy `settings.example.json` content into `.claude/settings.json` in your project root:

   ```bash
   mkdir -p .claude
   cp integrations/claude-code/settings.example.json .claude/settings.json
   ```

2. Edit `.claude/settings.json`:
   - Replace `${workspaceFolder}` with absolute path to your Recalium repo, or keep it if Recalium is your workspace root
   - Set `RECALIUM_URL` if using a non-standard address
   - Set `RECALIUM_TOKEN` if using bearer auth

3. Restart Claude Code to load the new hooks

### Option 2: User-scope hooks (system-wide)

Set hook commands and environment variables in Claude Code settings at the **user scope** (not project scope). Refer to Claude Code documentation for user settings location.

## Configuration

All configuration uses environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `RECALIUM_URL` | `http://localhost:8000` | Recalium API endpoint |
| `RECALIUM_TOKEN` | (empty) | Optional bearer token for authenticated access |
| `RECALIUM_TIMEOUT_S` | `5` | HTTP request timeout in seconds |

### Loading from `.env` file

If you have a `.env` file in your project, these variables will be loaded automatically. Otherwise, set them in the hook environment (see `settings.example.json`).

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

All retrievals include source provenance (`source_name`, `captured_at`) so you know where context came from.

## Troubleshooting

### Hooks not firing or showing no context

1. **Recalium stack is down:**
   - Hooks fail gracefully and emit `{}` (no context)
   - Check: `curl http://localhost:8000/api/health`
   - If down: `cd /path/to/recalium && docker compose up`

2. **Hooks are disabled in settings:**
   - Check `.claude/settings.json` → `hooks.sessionStart.enabled` (and others)
   - Ensure `enabled: true` for each hook you want

3. **Wrong path to hooks:**
   - Verify `args[0]` path points to correct `session_start.py` location
   - Use absolute path or `${workspaceFolder}` macro correctly

4. **Bearer token rejected:**
   - If you set `RECALIUM_TOKEN`, ensure it's valid for your Recalium instance
   - Leave empty if your Recalium doesn't use auth (default localhost)

### Debugging

- **Hooks:** Check Claude Code output panel for error messages
- **CLI:** Run commands with stderr visible to see connection errors
- **Recalium logs:** `docker compose logs recalium-app` for API-side issues

Example debugging:

```bash
# Test the hook with synthetic input
echo '{"hookEventName":"SessionStart","sessionId":"test-001","workspacePath":"/tmp"}' | \
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
echo '{"hookEventName":"SessionStart","sessionId":"test","workspacePath":"/tmp/project"}' | \
  python3 integrations/claude-code/hooks/session_start.py | python3 -m json.tool

# Expected: Valid JSON output (either {} or {"hookSpecificOutput": {...}})
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

Edit `settings.example.json` to customize retrieval:

```json
"environment": {
  "RECALIUM_URL": "http://localhost:8000",
  "RECALIUM_MODE": "keyword",  // Switch to keyword-only (no semantic search)
  "RECALIUM_BUDGET": "1024",   // Reduce budget per request
  "RECALIUM_LIMIT": "3"        // Return fewer items
}
```

Then update `recalium_client.py` method calls to use these env vars.

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
