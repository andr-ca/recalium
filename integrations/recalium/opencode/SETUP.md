# OpenCode — Recalium setup

Recalium exposes MCP over SSE at `http://localhost:8000/mcp/sse`. OpenCode has
native MCP support (`type: "remote"`).

## MCP connection

Project scope: copy [opencode.json](opencode.json) to `opencode.json` in the repo
root (merge the `mcp` block into an existing file):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "recalium": {
      "type": "remote",
      "url": "http://localhost:8000/mcp/sse",
      "enabled": true
    }
  }
}
```

Global scope: put the same `mcp.recalium` entry in
`~/.config/opencode/opencode.json`. OpenCode discovers the server and its 4 tools
on next launch. No token is required in localhost mode.

## Instructions

OpenCode reads `AGENTS.md`. Append [AGENTS.snippet.md](AGENTS.snippet.md) to your
project `AGENTS.md` (or `~/.config/opencode/AGENTS.md`) so the agent follows the
retrieve-before / ingest-after workflow. The full skill is in
[skill/SKILL.md](skill/SKILL.md).

## Hooks

OpenCode supports event hooks via TypeScript plugins in `.opencode/plugin/`. A
plugin can call the Recalium REST API on session events (e.g. `session.start`) —
optional and not required for MCP tool use.

## Exposed mode

Add headers to the server entry, reading the token from `.env` `APP_AUTH_BEARER`
(never hardcode):

```json
"recalium": {
  "type": "remote",
  "url": "http://<host>:8000/mcp/sse",
  "enabled": true,
  "headers": { "Authorization": "Bearer <APP_AUTH_BEARER>" }
}
```
