# Recalium multi-agent connector kit

Connect **Claude Code**, **GitHub Copilot**, **Codex CLI**, and **Cursor** to your
local Recalium memory over MCP — with a memory **skill**, **hooks**, **MCP config**,
and **CLI setup** for each tool.

Recalium exposes MCP over SSE at:

```
http://localhost:8000/mcp/sse
```

Tools: `retrieve_memory`, `ingest_memory`, `get_fact_links`, `list_tags`.
In localhost mode **no auth token is required**.

## Layout

```
integrations/recalium/
├── install.sh / install.ps1        # idempotent auto-wire (Linux/macOS + Windows)
├── shared/recalium-memory.md       # canonical skill body (source of truth)
├── claude-code/                    # mcp.json · hooks.settings.json · skill · SETUP.md
├── github-copilot/                 # mcp.json · skill · instructions snippet · SETUP.md
├── codex/                          # config.snippet.toml · skill · SETUP.md
├── cursor/                         # mcp.json · rules/*.mdc · SETUP.md
└── hooks/                          # recalium_session_start / _stop (.sh + .ps1)
```

Each tool folder has its own `SETUP.md` with copy-paste CLI commands. The per-tool
skill files mirror `shared/recalium-memory.md`; edit the shared body and keep them
in sync.

## Quick start (auto-wire)

From the repo root:

```bash
# Linux/macOS — preview first, then apply
bash integrations/recalium/install.sh --dry-run
bash integrations/recalium/install.sh          # repo-level wiring + repo skills
bash integrations/recalium/install.sh --all     # also wire user-level Codex + VS Code
```

```powershell
# Windows (PowerShell 7+)
pwsh integrations/recalium/install.ps1 -DryRun
pwsh integrations/recalium/install.ps1          # repo-level wiring + repo skills
pwsh integrations/recalium/install.ps1 -All      # also wire user-level Codex + VS Code
```

Override the endpoint with `--url <sse-url>` / `-Url <sse-url>`.

## What the installer writes (idempotent, with `.bak` backups)

| Target | Purpose |
| --- | --- |
| `.mcp.json` | Claude Code project MCP (`mcpServers.recalium`) |
| `.vscode/mcp.json` | Copilot workspace MCP (`servers.recalium`) |
| `.cursor/mcp.json` | Cursor MCP (`mcpServers.recalium`) |
| `.cursor/rules/recalium-memory.mdc` | Cursor always-apply rule |
| `.claude/settings.json` | **Appends** Recalium `SessionStart` + `Stop` hooks (existing hooks preserved) |
| `.claude/skills/recalium-memory/SKILL.md` | Claude Code skill |
| `.codex/skills/recalium-memory/SKILL.md` | Codex skill |
| `.github/skills/recalium-memory/SKILL.md` | Copilot skill |
| `~/.codex/config.toml` (`--all`) | Codex user MCP via `mcp-remote` bridge |
| VS Code user `mcp.json` (`--all`) | Copilot user-level MCP |

The installer never writes secrets. Re-running is safe — it detects existing
entries and leaves them unchanged.

## Requirements

- Recalium running locally (`GET http://localhost:8000/api/health` → `200`).
- `python3` (Linux/macOS installer) — for safe JSON merges.
- PowerShell 7+ (`pwsh`) for the Windows installer.
- Node.js / `npx` for the Codex `mcp-remote` bridge.

## Exposed mode (non-localhost)

Each tool's `SETUP.md` shows how to add an `Authorization: Bearer <token>` header.
Read the token from `.env` `APP_AUTH_BEARER` — never hardcode it.
