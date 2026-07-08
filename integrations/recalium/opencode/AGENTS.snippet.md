<!-- Recalium memory — append to AGENTS.md (project) or ~/.config/opencode/AGENTS.md -->

## Recalium memory (MCP: `recalium`)

When the `recalium` MCP server is available (`http://localhost:8000/mcp/sse`):

- Before a non-trivial task, call `retrieve_memory` to recall relevant prior
  context. Inspect each item's provenance and `conflict_label`; prefer
  `canonical_only=true` for vetted memory.
- After finishing, call `ingest_memory` with `content` (>= 10 chars),
  `source_metadata`, and a stable `idempotency_key`.
- Use `get_fact_links` to expand related facts and `list_tags` to discover tags.
- Never ingest secrets, tokens, or passwords — redact first. Surface conflicts to
  the user instead of resolving them silently.
