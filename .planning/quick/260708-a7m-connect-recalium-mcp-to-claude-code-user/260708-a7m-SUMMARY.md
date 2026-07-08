# Quick Task 260708-a7m Summary — Recalium connected to Claude Code

**Completed:** 2026-07-08

- Clean canonical start verified: `docker compose down && build && up -d`
  from the committed state — postgres healthy, migrations ran, worker loop up,
  UI served (200), Ollama reachable from container (gateway IP unchanged).
- Registered Recalium as a **user-scoped** MCP server in Claude Code:
  `claude mcp add --scope user --transport sse recalium http://localhost:8000/mcp/sse`
  → `✔ Connected`. User scope = available in every project, matching
  Recalium's core value (memory across all tools/sessions).
- End-to-end proof over the real MCP protocol: `ingest_memory` accepted →
  pipeline processed → `retrieve_memory` returned the item via hybrid search
  with provenance (`source_id`, derivation metadata).
- Documented in docs/guides/local-use-and-test.md (Connect Claude Code section).
- Note: already-open Claude Code sessions must restart to see the tools;
  new sessions get them automatically.
