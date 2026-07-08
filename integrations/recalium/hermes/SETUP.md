# Hermes Agent — Recalium setup

Recalium exposes MCP over SSE at `http://localhost:8000/mcp/sse`. Hermes speaks
MCP and reads server config from `~/.hermes/config.yaml`. Because Hermes connects
over stdio/HTTP, we bridge to Recalium's SSE endpoint with `mcp-remote` (requires
Node.js / `npx`).

## MCP connection

Merge [config.snippet.yaml](config.snippet.yaml) into `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  recalium:
    command: "npx"
    args: ["-y", "mcp-remote", "http://localhost:8000/mcp/sse"]
```

Then start Hermes — it discovers the server's tools. You can inspect MCP servers
with the `hermes mcp` command (interactive picker). The Recalium server is a
custom entry, not part of the Nous catalog, so add it via the config file above.

## Skill / context

Hermes supports Skills and Context Files that shape every conversation. Use
[skill/SKILL.md](skill/SKILL.md) as the memory skill / context file so Hermes
follows the retrieve-before / ingest-after workflow (place per the Hermes Skills
docs, e.g. under your Hermes skills directory).

## Exposed mode

Add a bearer header in the args and keep the secret in `~/.hermes/.env`; Hermes
resolves `${VAR}` placeholders at connect time — never hardcode the token:

```yaml
    args: ["-y", "mcp-remote", "http://<host>:8000/mcp/sse", "--header", "Authorization: Bearer ${APP_AUTH_BEARER}"]
```
