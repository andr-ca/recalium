# ADR 0001 — MCP transport: SSE now, Streamable-HTTP later (F11)

**Status:** Accepted (v1.1)
**Date:** 2026-07-09
**Context refs:** ANALYSIS.md F11 · [recommendations.md](../../recommendations.md) §4 · [tech-stack.md](../tech-stack.md)

## Context

Recalium exposes its MCP server over **SSE** at `http://localhost:8000/mcp/sse`
(mounted via `FastMCP(...).sse_app()` in
[backend/app/mcp_server/server.py](../../../backend/app/mcp_server/server.py)).

In the MCP specification, HTTP+SSE is the **legacy** transport; the current
direction is **Streamable-HTTP**. The Python MCP SDK is pinned `>=1.26,<2`
because v2 carries breaking transport changes. SSE works today and every client
we target (Claude Code, Copilot, Codex, Cursor, OpenCode, Hermes via
`mcp-remote`) connects to it, but staying on a legacy transport indefinitely is a
known risk.

## Decision

1. **Stay on SSE through v1.1 (current default).** It is stable, localhost-bound
   (DNS-rebinding-safe), and universally supported by our target clients.
2. **Spike Streamable-HTTP in v1.2** behind the same `/mcp` mount, when the MCP
   SDK v2 (or a stable Streamable-HTTP transport in v1.x) is available. Keep SSE
   mounted in parallel during the spike.
3. **Migrate in v1.3+**: make Streamable-HTTP the default, keep SSE for one
   release as a compatibility shim, then deprecate and remove it.

## Constraints (non-negotiable)

- Transport MUST remain bound to `127.0.0.1` by default (DNS-rebinding
  prevention) regardless of transport.
- The MCP **tool contract** (`retrieve_memory`, `ingest_memory`,
  `get_fact_links`, `list_tags`) and the stable error envelope MUST NOT change as
  a side effect of a transport migration — clients depend on them.
- Exposed mode still requires bearer auth on `/mcp/*`.

## Consequences

- **Positive:** no client churn now; a clear, staged path off the legacy
  transport; the SDK pin (`<2`) is an intentional, documented hold, not neglect.
- **Negative:** we carry SSE longer; the v1.2 spike must validate that
  `mcp-remote`-bridged clients (Codex, Hermes) work over Streamable-HTTP too.

## Follow-ups

- v1.2: prototype `streamable_http_app()` mount; measure client compatibility;
  update this ADR to "Superseded" if we commit to migration.
- Link this ADR from [tech-stack.md](../tech-stack.md) MCP transport line.
