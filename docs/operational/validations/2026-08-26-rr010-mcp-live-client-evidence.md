# RR-010 MCP Live-Client Evidence

**Date:** 2026-08-26  
**Gap register row:** RR-010 (M1 remainder)  
**PO decision:** MCP *resources* deferred to M3; M1 delivers live-client evidence only.

## Scope verified

| Requirement | Evidence |
| --- | --- |
| Live tool catalog (all 4 tools) | `test_mcp_live_tool_catalog` |
| Invalid inputs → stable error envelope | `test_mcp_live_retrieve_invalid_mode`, `test_mcp_live_get_fact_links_invalid_uuid`, `test_mcp_live_get_fact_links_invalid_direction` |
| Audit metadata (ingest + retrieve actors) | `test_mcp_live_retrieve_records_audit_actor`, `test_mcp_live_ingest_records_audit_actor` |
| Concurrent SSE clients | `test_mcp_live_concurrent_sse_sessions` |

## Test file

`backend/tests/e2e/test_mcp_live_client.py` — 7 tests against live stack via MCP Python SDK (`sse_client` + `ClientSession`).

## Validation command

```bash
docker compose up -d   # if not running
cd backend && uv run pytest tests/e2e/test_mcp_live_client.py -v
```

**Result (2026-08-26):** 7 passed in ~5.5s against `http://localhost:8000`.

## Deferred (M3, not M1)

MCP *resources* implementation remains out of scope for v1.0 GA per PO decision 2026-08-26 and ADR 0001 timeline.

## Verdict

**RR-010 M1 live-client evidence: CLOSED.** Resources tracked under M3.
