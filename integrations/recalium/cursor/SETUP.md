# Cursor — Recalium setup

Recalium exposes MCP over SSE at `http://localhost:8000/mcp/sse`.

## MCP connection

Project scope: copy [mcp.json](mcp.json) to `.cursor/mcp.json` in the repo root:

```json
{
  "mcpServers": {
    "recalium": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

Global scope: put the same file at `~/.cursor/mcp.json`. Or open
**Settings → MCP → Add new MCP server**. Cursor shows `recalium` with its 4 tools
once connected.

## Rule

Copy [rules/recalium-memory.mdc](rules/recalium-memory.mdc) to
`.cursor/rules/recalium-memory.mdc`. It is an `alwaysApply` rule that teaches the
retrieve-before / ingest-after workflow. Cursor has no shell hooks — rules are the
mechanism.

## Exposed mode

Add a header, reading `APP_AUTH_BEARER` from `.env` (never hardcode):

```json
{
  "mcpServers": {
    "recalium": {
      "url": "http://<host>:8000/mcp/sse",
      "headers": { "Authorization": "Bearer <APP_AUTH_BEARER>" }
    }
  }
}
```
