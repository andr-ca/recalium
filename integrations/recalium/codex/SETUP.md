# Codex CLI — Recalium setup

Codex speaks MCP over **stdio**, so we bridge to Recalium's local **SSE** endpoint
with `mcp-remote` (requires Node.js / `npx`).

## MCP connection

Run:

```bash
codex mcp add recalium -- npx -y mcp-remote http://localhost:8000/mcp/sse
```

Or append [config.snippet.toml](config.snippet.toml) to `~/.codex/config.toml`
(Linux/macOS) / `%USERPROFILE%\.codex\config.toml` (Windows):

```toml
[mcp_servers.recalium]
command = "npx"
args = ["-y", "mcp-remote", "http://localhost:8000/mcp/sse"]
```

Verify with `codex mcp list` (expect `recalium`).

## Skill

Copy [skill/SKILL.md](skill/SKILL.md) to `.codex/skills/recalium-memory/SKILL.md`
(repo) or `~/.codex/skills/recalium-memory/SKILL.md` (user).

## Notes

- `mcp-remote` keeps a persistent bridge to the SSE server; the first call may
  take a moment while `npx` fetches it.
- Codex has no shell hooks; the skill + `AGENTS.md`/`CODEX.md` guidance carry the
  retrieve-before / ingest-after workflow.

## Exposed mode

Pass a bearer token via `mcp-remote --header`, reading `APP_AUTH_BEARER` from your
environment (never hardcode):

```toml
args = ["-y", "mcp-remote", "http://<host>:8000/mcp/sse", "--header", "Authorization: Bearer ${APP_AUTH_BEARER}"]
```
