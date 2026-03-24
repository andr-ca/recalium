---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: "Wrote Phase 4 plans (04-01 through 04-08) — awaiting execution"
last_updated: "2026-03-23T18:00:00.000Z"
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 32
  completed_plans: 17
---

# State: Recalium

**Project:** Recalium — Local-First MCP-Native Personal Memory Platform
**Milestone:** v1
**Initialized:** 2026-03-22

---

## Project Reference

**Core Value:** A user's future AI session — on any tool, with any model — can retrieve relevant, source-backed context from prior conversations that happened anywhere, without re-explaining anything.

**Current Focus:** Phase 04 — Privacy + Operations (next)

**Stack (committed):** Python 3.12+/FastAPI 0.135.1, React 19+TypeScript/Vite 8/Tailwind v4/shadcn/ui 2.x, PostgreSQL 16+pgvector 0.8.2, SQLAlchemy 2.x async/asyncpg 0.31.0/Alembic, MCP Python SDK ≥1.26,<2, sentence-transformers 5.3.0, uv 0.10.12 + pnpm 10.32.1

---

## Current Position

Phase: 02 (Processing Pipeline) — COMPLETE ✓
Phase: 03 (Retrieval + Review) — COMPLETE ✓ (8/8 plans executed, 126 tests passing)

### Progress Bar

```
Phase 1 [Foundation          ] ░░░░░░░░░░░░░░░░░░░░  0%  (plans not yet created)
Phase 2 [Processing Pipeline ] ████████████████████  100% (8/8 plans complete)
Phase 3 [Retrieval + Review  ] ████████████████████  100% (8/8 plans complete)
Phase 4 [Privacy + Operations] ░░░░░░░░░░░░░░░░░░░░  0%
Phase 5 [Service Hardening   ] ░░░░░░░░░░░░░░░░░░░░  0%

Overall ▓▓▓▓▓░░░░░░░░░░░░░░░  25/52 requirements complete (Phase 2+3 reqs verified by tests)
```

---

## Performance Metrics

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| Ingest P95 latency | ≤ 1s | — | Not yet measured |
| Search P95 latency | ≤ 2s | — | Not yet measured |
| Backup restore SLA | ≤ 15 min | — | Not yet measured |
| Requirements complete | 52/52 | 25/52 | Phase 2+3 reqs (PIPE-01–05, PRIV-04, PRIV-05, BYOK-07, BYOK-08, CANM-06, SRCH-01–06, MCP-01, MCP-03, MCP-04, CANM-01–05, WEBUI-05) verified |

---

## Plan Execution Log

| Plan | Duration (s) | Tasks | Files |
|------|-------------|-------|-------|
| Phase 02 P01 | 299 | 2 | 6 |
| Phase 02 P02 | 360 | 2 | 11 |
| Phase 02 P03 | 11 | 3 | 9 |
| Phase 02 P04 | 673 | 3 | 9 |
| Phase 02 P05 | 1200 | 2 | 3 |
| Phase 02 P06 | 126 | 2 | 3 |
| Phase 02 P07 | 175 | 2 | 5 |
| Phase 02 P08 | 120 | 2 | 1 |
| Phase 03 P01 | — | — | — |
| Phase 03 P02 | — | — | — |
| Phase 03 P03 | — | — | — |
| Phase 03 P04 | — | — | — |
| Phase 03 P05 | — | — | — |
| Phase 03 P06 | — | — | — |
| Phase 03 P07 | — | — | — |
| Phase 03 P08 | — | 3 | 3 |

## Accumulated Context

### Architectural Decisions (Locked)

| Decision | Rationale |
|----------|-----------|
| Two-container topology (app + postgres) | Avoids premature complexity; worker/backup/watcher are in-process tasks |
| PostgreSQL as job queue (SKIP LOCKED) | Avoids Redis/RabbitMQ dependency; sufficient for personal scale |
| Bind mounts, not named volumes | Prevents data loss on `docker compose down -v`; `./data/postgres` and `./backups` on host |
| RRF k=60, top-50/mode, top-20 merged | Architecture-specified parameters for hybrid retrieval recall/precision balance |
| sentence-transformers all-MiniLM-L6-v2 default | Local embeddings, no API key required; 384 dims; fast and small |
| In-process asyncio worker | No separate container; `asyncio.to_thread()` for all CPU-bound work |
| BYOK-first (no Recalium-operated services) | Target audience has provider keys; managed tier is post-v1 |
| Strict priority trimming (canonical→facts→summaries→raw) | Highest-quality memory used first within context budget |
| `source_status` cascade flags from schema v1 | Deletion cascade semantics must be correct before any derived data exists |
| Sensitivity gate architecturally before external dispatch | Gate fires in Phase 2 pipeline; UI ships in Phase 4 — cannot be retrofitted |
| MCP bound to 127.0.0.1 from day one | DNS rebinding attack prevention; Origin validation co-located with transport introduction |
| API keys in .env only; DB stores fingerprint | `pg_dump` safe; startup assertion scans for key columns |
| pytest.importorskip for RED-state test modules | Skips entire test module at collection when implementation absent; avoids misleading xfail noise in CI |
| pytest.importorskip inside test body for optional deps | e.g. sentence_transformers — skips test gracefully when EMBED_BACKEND=none without failing CI |

### Critical Pitfalls to Watch

1. **Deletion orphaning**: Every derived table needs `source_status` cascade flags from migration 001. Test: delete raw item → assert zero search results.
2. **Event loop starvation**: All sentence-transformers inference via `asyncio.to_thread()`; all external HTTP via `httpx.AsyncClient`; concurrency bounded by `asyncio.Semaphore`.
3. **Sensitive content leak**: Pipeline gate order: ingest raw → local sensitivity classification → user declaration check → ONLY THEN dispatch external job. Default BLOCKED for unclassified.
4. **Keys in database**: Keys live in `.env` only; DB stores fingerprint/display name; startup assertion verifies no key columns.
5. **Named volumes**: Use bind mounts (`./data/postgres`); never document or use `docker compose down -v`.
6. **Mixed embedding models**: Record `model_name` + `model_dim` per embedding row; surface warning on provider switch; filter semantic search to current model.
7. **HNSW on empty table**: Build HNSW index after initial data load; `hnsw.ef_search ≥ 100`; `hnsw.iterative_scan = strict_order`; `shared_buffers = 256MB–1GB`.

### Research Flags (Active)

| Flag | Phase | Detail |
|------|-------|--------|
| Sensitivity heuristics | Phase 2 ✓ | Implemented keyword heuristics + CrossEncoder NLI fallback. Domain validation against real exports deferred to beta. |
| RRF recall validation | Phase 3 | k=60, ef_search=100 are specified but not empirically validated; measure during Phase 3 or beta |
| Memory bundle JSON schema | Phase 5 | Format described at high level; needs formal versioned schema spec before Phase 5 implementation |
| sentence-transformers model quality | v1 launch | all-MiniLM-L6-v2 acceptable for v1; revisit if retrieval quality poor on AI conversation content |

### Todos

- [ ] Execute Phase 4 plans (04-01 through 04-08) — plans are written and ready
- [ ] Create Phase 1 plans (via `/gsd-plan-phase 1`) — Foundation scaffold still needed

### Blockers

_(none)_

---

## Session Continuity

### How to Resume

1. Read `.planning/STATE.md` (this file) — understand current position
2. Read `.planning/ROADMAP.md` — understand phase goals and success criteria
3. Read `.planning/REQUIREMENTS.md` — check traceability for current phase
4. Check current phase plans in `.planning/phases/phase-N/` (when created)
5. Continue from last incomplete plan step

### Key File Locations

| File | Purpose |
|------|---------|
| `.planning/PROJECT.md` | Core value, constraints, key decisions, evolution log |
| `.planning/REQUIREMENTS.md` | All 52 v1 requirements with IDs and traceability |
| `.planning/ROADMAP.md` | 5-phase structure with goals and success criteria |
| `.planning/STATE.md` | This file — current position and accumulated context |
| `.planning/research/SUMMARY.md` | Architecture validation, stack versions, pitfall registry |
| `docs/architecture/` | Approved architecture docs (8 docs, reviewed baseline) |
| `docs/architecture/delivery-phases.md` | Pre-approved 5-phase delivery structure |

---

## Phase Transition Log

| Event | Date | Notes |
|-------|------|-------|
| Roadmap created | 2026-03-22 | 5 phases, 52/52 requirements mapped |
| Phase 1 context captured | 2026-03-22 | Decisions logged in `.planning/phases/01-foundation/01-CONTEXT.md` |
| Phase 2 complete | 2026-03-23 | All 8 plans executed; 46 tests green; 10 reqs verified (PIPE-01–05, PRIV-04, PRIV-05, BYOK-07, BYOK-08, CANM-06) |
| Phase 3 complete | 2026-03-23 | All 8 plans executed; 41 new tests (126 total); 15 reqs verified (SRCH-01–06, MCP-01, MCP-03, MCP-04, CANM-01–05, WEBUI-05) |

| Phase 4 plans written | 2026-03-23 | 8 plan files created in `.planning/phases/04-privacy-operations/`; ready for execution |

---

## Resume Point

**Stopped at:** Phase 4 plans written (04-01 through 04-08)
**Resume file:** `.planning/phases/04-privacy-operations/04-01-PLAN.md`
**Next step:** Execute Phase 4 plans in wave order: wave 1 (04-01), wave 1 (04-02), wave 2 (04-03 through 04-05 in parallel), wave 3 (04-06 and 04-07 in parallel), wave 4 (04-08)

---

*Last updated: 2026-03-23 after writing Phase 4 plans (04-01 through 04-08)*
