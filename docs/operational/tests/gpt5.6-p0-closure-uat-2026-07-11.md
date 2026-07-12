# GPT-5.6 P0 Backlog Closure — UAT Evidence (2026-07-11)

## Scope

Live-stack and automated validation for the eleven-wave P0 closure delivered on branch
`fix/gpt5.6-p0-backlog-closure` (PR [#5](https://github.com/andr-ca/recalium/pull/5)).
Every P0 in the GPT-5.6 review risk ranking (ranks 1–9) is addressed; see the response
tracker: [../../gpt5.6-sol-recommendations-status.md](../../gpt5.6-sol-recommendations-status.md).

## Findings → commits

| Finding | Commit | Area |
| --- | --- | --- |
| #2 deletion/backup/restore safety | `4849828` | deletion, backup |
| #6 external egress policy gate | `4a657cc` | policy, worker |
| #9 deletion/promotion concurrency | `b830279` | deletion, canonical |
| #4 RRF fusion | `9bce2ef` | retrieval |
| #4 SQL-level filters + source aliasing | `1ead3f7` | retrieval |
| #4 direct fact retrieval (migration 0008) | `787ad29` | retrieval |
| #8 / #17 portable bundle v2 | `f0bd9bc` | portability |
| #10 conflict-queue curation | `1da5f3a` | review queue |
| #3 eval strict gate | `15267e4` | eval |
| #20 scale/concurrency check + corpus | `ed98bb2` | eval |
| #7 / #13 / #26 quick wins | `099add4` | tests, api, ci |
| #8 E2E bundle assertion (v2) | `e661178` | e2e |
| #16 status/traceability docs | `47fb59f` | docs |

## Validation results

| Layer | Command | Result |
| --- | --- | --- |
| Backend unit/integration | `pytest tests --ignore=tests/e2e` | **273 passed / 13 skipped**, random-order-safe (`-p randomly`) |
| Eval metric tests | `pytest evals/test_metrics.py` | **18 passed** |
| Live-stack E2E | `BASE_URL=http://localhost:8000 pytest tests/e2e` | **26 passed / 1 skipped** |
| MCP SSE endpoint | `GET /mcp/sse` | **HTTP 200** |
| Traceability gate | `scripts/traceability.py --check` | passed (every claimed-done requirement has a test) |
| Migrations (real Postgres) | `alembic upgrade head` on scratch DB | full chain incl. `0007`+`0008` clean; `facts.search_vector` generated + `ix_facts_fts` present |

The single skipped E2E test is `test_semantic_search_graceful_degraded` (expected without an
embedding model configured).

## Live E2E coverage of the delivered waves

The live-stack suite exercises the running app (this branch's code + migrations applied):

- `test_keyword_search_finds_item` — **#4** retrieval works live (after `0008`).
- `test_deleted_item_excluded_from_search`, `test_deleted_item_excluded_from_archive_list` — **#2** deletion suppression.
- `test_export_bundle_format` — **#8** bundle is v2 with `canonical_memory` + `tombstones`.
- `test_mcp_ingest_memory_success`, `test_mcp_retrieve_returns_results` — MCP tools live.

## End-to-end safety/scale proofs (in-container / live)

- **#2 deletion→backup→restore:** proven end-to-end against real `pg_dump`/`pg_restore` in the
  app container against a guarded `*_test` DB — crypto-erase, redacted post-deletion backup,
  and pre-deletion-restore tombstone reapply (secret never recoverable), plus corrupted-archive
  and path-traversal rejection.
- **#20 scale/concurrency (`make eval-scale`, size=10 live):** precision 1.00, retrieval p95
  ≈126 ms, 0 concurrency errors, no resurrection after a concurrent delete.

## Notable finding

The scale check surfaced that `GET /api/search?mode=keyword` returns HTTP 500 until migration
`0008` (the `facts` FTS column) is applied. This is expected: the app entrypoint runs
`alembic upgrade head` on container start, so fresh deploys apply it automatically; a
hot-reloaded dev process does not re-run migrations. The migration was applied to the live dev
DB during UAT and keyword search recovered.

## Reproduce

```bash
# Backend (test DB on :5435)
cd backend && uv run python -m pytest tests -q --ignore=tests/e2e
uv run --project ../ python -m pytest ../evals/test_metrics.py -q   # or: cd .. && uv run --project backend python -m pytest evals/test_metrics.py -q

# Live stack
docker compose up -d
cd backend && BASE_URL=http://localhost:8000 uv run python -m pytest tests/e2e -q

# Scale/concurrency (opt-in; live stack up)
make eval-scale
```

## Outstanding (not code-closeable)

- **#16** traceability matrix — process/docs; the generator + CI gate are green.
- **#20** real vendor-export corpus + a dedicated load harness — needs real data, not code.
