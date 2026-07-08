# pi — Recalium setup

pi (earendil-works/pi) has **no MCP** by design — it uses Skills (CLI tools with
READMEs) and reaches services over HTTP. So pi integrates with Recalium through
its local **REST API**, not MCP.

## Skill

Copy [skill/SKILL.md](skill/SKILL.md) to:

- Project: `.pi/skills/recalium-memory/SKILL.md`
- Global: `~/.pi/agent/skills/recalium-memory/SKILL.md`

The skill documents the `curl` calls for recall and ingest.

## Instructions

pi reads `AGENTS.md`. Append [AGENTS.snippet.md](AGENTS.snippet.md) to your
project `AGENTS.md` (or `~/.pi/agent/AGENTS.md`).

## REST endpoints used

- Recall: `GET http://localhost:8000/api/search?q=<query>&mode=hybrid`
- Recall (structured): `POST http://localhost:8000/api/retrieve`
- Ingest: `POST http://localhost:8000/api/ingest` with `{"content":"...","source_name":"pi-cli"}`
- Health: `GET http://localhost:8000/api/health`

## Want MCP in pi instead?

pi can load a TypeScript extension that adds MCP support. Place it in
`~/.pi/agent/extensions/` or `.pi/extensions/`. That's optional — the REST skill
above is the pi-idiomatic path.

## Exposed mode

Add `-H "Authorization: Bearer $APP_AUTH_BEARER"` to the `curl` calls, reading the
token from `.env` — never hardcode it.
