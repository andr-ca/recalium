<!-- Recalium memory — append to .github/copilot-instructions.md -->

## Recalium memory (MCP: `recalium`)

When the Recalium MCP server is available (`http://localhost:8000/mcp/sse`):

- Before starting a non-trivial task, call `retrieve_memory` to recall relevant
  prior context. Inspect each item's provenance and `conflict_label` before
  trusting it; prefer `canonical_only=true` for vetted memory.
- After finishing, call `ingest_memory` to persist durable, source-backed context
  (`content` >= 10 chars, include `source_metadata` and a stable `idempotency_key`).
- Use `get_fact_links` to expand related facts and `list_tags` to discover tags.
- Never ingest secrets, tokens, or passwords — redact first. Surface conflicts to
  the user instead of resolving them silently.
