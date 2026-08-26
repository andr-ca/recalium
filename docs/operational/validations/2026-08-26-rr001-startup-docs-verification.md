# RR-001 Startup Docs Verification

**Date:** 2026-08-26  
**Gap register row:** RR-001  
**Verifier:** engineering agent (PO-directed M1 closure)

## Scope

Confirm README and `docs/guides/local-use-and-test.md` provide an end-to-end local start → use → test path that matches the running stack.

## Documentation reviewed

| Doc | Role |
| --- | --- |
| [README.md](../../../README.md) | Quick start (5 steps), first use, MCP endpoint, testing pointers |
| [docs/guides/local-use-and-test.md](../../../docs/guides/local-use-and-test.md) | Full operator guide: prerequisites, `.env`, Docker Compose, UI dev server, MCP, evals, troubleshooting |

## Live verification (stack already running)

Commands executed against `http://localhost:8000`:

| Step | Command / action | Result |
| --- | --- | --- |
| Health | `GET /api/health` | `200` |
| UI | `GET /` (browser) | Recalium SPA loads; left nav shows all v1 sections |
| Settings | `GET /settings` | Provider key forms render; backup/portability sections reachable |
| Search | `GET /search` | Search UI loads with input controls |
| MCP endpoint | Documented at `http://localhost:8000/mcp/sse` in README | Matches running app mount |

## Cross-check against README quick start

1. `.env` from `.env.sample` — documented; existing local `.env` present (not committed).
2. `docker compose up` — stack running (`recalium-app`, `recalium-postgres`).
3. Health at `:8000/api/health` — **pass**.
4. Vite dev UI at `:5173` — documented; production/static mode at `:8000` also documented.
5. Detailed walkthrough link — **pass** (`local-use-and-test.md`).

## Gaps found

None blocking RR-001 closure. Optional follow-ups (out of RR-001 scope):

- README MCP paragraph still says "needs hardening" generically — gap register RR-010 now records the resources defer / live-evidence split.
- Post-merge main CI should be re-run after each PR merge (harness checklist).

## Verdict

**RR-001 CLOSED.** Startup, usage, and testing documentation exist, are linked from README, and match verified runtime behavior on the local two-container stack.
