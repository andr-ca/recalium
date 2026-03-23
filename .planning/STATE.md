---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
stopped_at: Completed 02-03-PLAN.md
last_updated: "2026-03-23T13:02:39.754Z"
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 16
  completed_plans: 4
---

# State: Recalium

**Project:** Recalium — Local-First MCP-Native Personal Memory Platform
**Milestone:** v1
**Initialized:** 2026-03-22

---

## Project Reference

**Core Value:** A user's future AI session — on any tool, with any model — can retrieve relevant, source-backed context from prior conversations that happened anywhere, without re-explaining anything.

**Current Focus:** Phase 02 — Processing Pipeline

**Stack (committed):** Python 3.12+/FastAPI 0.135.1, React 19+TypeScript/Vite 8/Tailwind v4/shadcn/ui 2.x, PostgreSQL 16+pgvector 0.8.2, SQLAlchemy 2.x async/asyncpg 0.31.0/Alembic, MCP Python SDK ≥1.26,<2, sentence-transformers 5.3.0, uv 0.10.12 + pnpm 10.32.1

---

## Current Position

Phase: 02 (Processing Pipeline) — EXECUTING
Plan: 4 of 8

### Progress Bar

```
Phase 1 [Foundation          ] ░░░░░░░░░░░░░░░░░░░░  0%
Phase 2 [Processing Pipeline ] ░░░░░░░░░░░░░░░░░░░░  0%
Phase 3 [Retrieval + Review  ] ░░░░░░░░░░░░░░░░░░░░  0%
Phase 4 [Privacy + Operations] ░░░░░░░░░░░░░░░░░░░░  0%
Phase 5 [Service Hardening   ] ░░░░░░░░░░░░░░░░░░░░  0%

Overall ▓░░░░░░░░░░░░░░░░░░░  0/52 requirements complete
```

---

## Performance Metrics

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| Ingest P95 latency | ≤ 1s | — | Not yet measured |
| Search P95 latency | ≤ 2s | — | Not yet measured |
| Backup restore SLA | ≤ 15 min | — | Not yet measured |
| Requirements complete | 52/52 | 0/52 | — |

---
| Phase 02 P01 | 299 | 2 tasks | 6 files |
| Phase 02 P02 | 6 min | 2 tasks | 11 files |
| Phase 02 P03 | 11 | 3 tasks | 9 files |

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
| Sensitivity heuristics | Phase 2 | Rules for personal/relationship/unclassified content need domain validation against real ChatGPT/Claude exports before Phase 2 planning |
| RRF recall validation | Phase 3 | k=60, ef_search=100 are specified but not empirically validated; measure during Phase 3 or beta |
| Memory bundle JSON schema | Phase 5 | Format described at high level; needs formal versioned schema spec before Phase 5 implementation |
| sentence-transformers model quality | v1 launch | all-MiniLM-L6-v2 acceptable for v1; revisit if retrieval quality poor on AI conversation content |

### Todos

- [ ] Create Phase 1 plans (via `/gsd-plan-phase 1`)
- [ ] Initialize project scaffold (Docker Compose, backend skeleton, frontend skeleton)
- [ ] Establish `.env` / `.env.sample` pattern before first commit

### Blockers

_(none at roadmap creation — Phase 1 uses standard patterns, no research needed)_

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

---

## Resume Point

**Stopped at:** Completed 02-03-PLAN.md
**Resume file:** None
**Next step:** Execute plan 02-03

---

*Last updated: 2026-03-23 after completing plan 02-02 (Phase 2 test scaffold)*
