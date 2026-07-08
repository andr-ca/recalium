# GitHub Copilot (VS Code) — Recalium setup

Recalium exposes MCP over SSE at `http://localhost:8000/mcp/sse`.

## MCP connection

Workspace scope (writes `.vscode/mcp.json`): copy [mcp.json](mcp.json) to
`.vscode/mcp.json` in the repo root, or run from the repo root:

```bash
code --add-mcp '{"name":"recalium","type":"sse","url":"http://localhost:8000/mcp/sse"}'
```

(Use `code-insiders` for Insiders.) You can also run **MCP: Add Server** from the
Command Palette and choose HTTP/SSE.

User/profile scope: the server can live in your VS Code user `mcp.json`
(`~/.config/Code/User/mcp.json` on Linux, `%APPDATA%\Code\User\mcp.json` on
Windows) so it is available in every workspace.

Start it via **MCP: List Servers → recalium → Start**. The 4 tools then appear in
Copilot's tool picker. No token is required in localhost mode.

## Skill

Copy [skill/SKILL.md](skill/SKILL.md) to `.github/skills/recalium-memory/SKILL.md`
(repo) or your Copilot profile skills folder (`~/.copilot/skills/recalium-memory/SKILL.md`).

## Instructions

Copilot has no shell hooks. To nudge the retrieve-before / ingest-after behavior,
append [copilot-instructions.snippet.md](copilot-instructions.snippet.md) to
`.github/copilot-instructions.md`.

## Exposed mode

Add an `Authorization` header via an input in `mcp.json`:

```jsonc
"recalium": {
  "type": "sse",
  "url": "http://<host>:8000/mcp/sse",
  "headers": { "Authorization": "${input:recalium_bearer}" }
}
```

Provide the value at runtime from `.env` `APP_AUTH_BEARER` — never hardcode it.
