# Claude Code — Recalium setup

Recalium exposes MCP over SSE at `http://localhost:8000/mcp/sse`.

## MCP connection

Project scope (writes `.mcp.json` in the repo root):

```bash
claude mcp add --transport sse --scope project recalium http://localhost:8000/mcp/sse
```

User scope (available in every project):

```bash
claude mcp add --transport sse --scope user recalium http://localhost:8000/mcp/sse
```

Or copy [mcp.json](mcp.json) to the repo root as `.mcp.json`. Verify with
`claude mcp list` (expect `recalium` and its 4 tools).

## Skill

Copy [skill/SKILL.md](skill/SKILL.md) to `.claude/skills/recalium-memory/SKILL.md`
(repo) or `~/.claude/skills/recalium-memory/SKILL.md` (user profile).

## Hooks

Merge [hooks.settings.json](hooks.settings.json) into `.claude/settings.json`.
The `SessionStart` hook injects a memory reminder + health check; the `Stop` hook
reminds you to persist durable outcomes. Hook scripts live in
[../hooks/](../hooks/) (`.sh` for Linux/macOS, `.ps1` for Windows).

> The repo installer appends these hooks **additively** — it preserves any
> existing hooks in `.claude/settings.json` and backs the file up first.

## One-shot install

From the repo root: `bash integrations/recalium/install.sh` (Linux/macOS) or
`pwsh integrations/recalium/install.ps1` (Windows). Add `--dry-run` / `-DryRun`
to preview.

## Exposed mode

If Recalium is bound beyond localhost, add auth headers:

```bash
claude mcp add --transport sse --scope project recalium http://<host>:8000/mcp/sse \
  --header "Authorization: Bearer $APP_AUTH_BEARER"
```

Read `APP_AUTH_BEARER` from `.env` — never hardcode it.
