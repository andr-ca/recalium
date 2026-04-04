# Recalium

## What This Is

Recalium is a local-first, MCP-native personal memory platform that captures conversations from any AI tool, transforms them into durable searchable memory, and makes that memory retrievable by any MCP-compatible client. It runs as two Docker containers (`recalium-app` + `recalium-postgres`) on the user's machine. It is designed as infrastructure, not a feature — the app is the reference implementation of an open memory portability format.

## Core Value

A user's future AI session — on any tool, with any model — can retrieve relevant, source-backed context from prior conversations that happened anywhere, without re-explaining anything.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Ingestion**
- [ ] User can import conversations via text paste and file upload (ChatGPT JSON, Claude JSON, generic JSON, plain text/Markdown)
- [ ] System stores raw archive with source metadata and shows item in review UI within P95 ≤ 1s
- [ ] Watched import folder provides low-friction local ingestion
- [ ] MCP-accessible ingestion endpoint accepts raw content with source metadata, client identity, and sensitivity hints

**Processing pipeline**
- [ ] Async pipeline produces summaries, extracted facts, embeddings, and FTS index entries without blocking ingest
- [ ] Every extracted fact carries source span, confidence tier (high/medium/low), derivation method, and model version
- [ ] Duplicate and overlap detection groups similar facts in a review queue
- [ ] Conflict detection flags contradictory facts
- [ ] Reprocessing supported after logic changes or failures
- [ ] Failed jobs retry automatically with bounded attempts; terminal failures surface for manual retry

**Search and retrieval**
- [ ] Keyword search via PostgreSQL FTS
- [ ] Semantic search via pgvector
- [ ] Hybrid retrieval via Reciprocal Rank Fusion (RRF, k=60, top-50 candidates per mode, top-20 merged)
- [ ] Retrieval with context budgeting: strict priority trimming (canonical → facts → summaries → raw excerpts)
- [ ] Search and retrieval meet P95 ≤ 2s on datasets up to 100k stored items
- [ ] Degraded mode: keyword search + cached semantic results when no embeddings or provider available

**MCP interface**
- [ ] MCP `retrieve` tool returns items with source links, type, rank score, provenance metadata, conflict labels, budget/trimming reason, and retrieval-mode metadata
- [ ] MCP ingestion accepts well-formed requests; rejects missing required fields with descriptive error
- [ ] Every MCP access event is recorded with client identity, timestamp, and operation metadata
- [ ] Access-event history retained for at least 90 days

**Canonical memory and review**
- [ ] User can inspect provenance, edit, delete, mark disputed/stale, and promote facts to canonical memory
- [ ] Canonical memory is prioritized over extracted memory in retrieval; conflicting extracted memory returned as lower-ranked evidence with explicit conflict labeling
- [ ] Canonical memory requires explicit user action (no auto-promotion)
- [ ] Facts with no attributable source span cannot be promoted without explicit user confirmation
- [ ] Review queue groups duplicate/overlapping facts for manageable cleanup

**Deletion and privacy**
- [ ] Raw source deletion/redaction immediately cascade-suppresses derived summaries, facts, embeddings, and search entries (marked source-removed)
- [ ] Canonical memory from deleted source retains source-removed marker and required-review state
- [ ] Future backups/exports exclude deleted/redacted data; UI flags older backups that may contain it
- [ ] Personal profile and relationship content blocked from external processing by default
- [ ] Unknown/unclassified content blocked from external processing by default until user explicitly allows
- [ ] Broader-than-localhost exposure requires authentication, session handling, and transport protection

**BYOK provider configuration**
- [ ] First-run wizard explains BYOK model, supported providers, estimated cost per 100 conversations, and links to key creation pages
- [ ] User can configure OpenAI, Anthropic, and Ollama endpoint API keys through settings
- [ ] Key validation runs at configuration time with a lightweight test call (success, failure, or insufficient permissions)
- [ ] Provider-backed processing uses only user's configured keys; no calls to any Recalium-operated service
- [ ] System remains usable for ingestion, local storage, browsing, and keyword search without any configured keys
- [ ] Processing cost estimated and displayed before bulk import confirmation (token count heuristics, order-of-magnitude correctness)
- [ ] Invalid/rate-limited keys cause affected jobs to enter retryable failed state with clear error; no silent drops
- [ ] User can switch providers per function without reprocessing already-completed items

**Backup and restore**
- [ ] Scheduled daily backups, 30-day retention
- [ ] Any successful backup restorable within 15 minutes
- [ ] Restore recovers raw archive, summaries, facts, canonical memory, provenance metadata, retained audit events, and required configuration
- [ ] No acknowledged raw archive item lost after container restart or host reboot (persisted Docker volumes intact)

**Web UI**
- [ ] Left-nav layout: Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, Settings
- [ ] Core workflows operable by keyboard only (ingest, search, fact review, canonical edit, review queue, restore)
- [ ] No critical accessibility failures (missing labels, keyboard traps, unannounced state changes)
- [ ] Chrome/Chromium only in v1
- [ ] Provenance navigable from any summary, fact, or canonical item
- [ ] Audit view: basic event list with per-event detail drawer; more detailed logging configurable

**Portability**
- [ ] JSON export/import (open memory bundle format — v1 spec); re-importable without bespoke conversion
- [ ] Local usage telemetry (searches/day, retrievals/day, facts reviewed, canonical items created, MCP vs UI retrievals) visible in Settings; never leaves local system

### Out of Scope

- Browser extension ("Recalium Capture") — v2; separate release lifecycle and Chrome CSP complexity
- Temporal decay and relevance weighting — v2; requires real usage data to tune
- Confidence-based auto-curation — v2; depends on extraction quality data from real use
- Multi-user support — v2; add when a second tenant exists
- Cloud sync — post-v1 hosted sync tier
- Tenant-aware data model seams — premature; add when a second tenant exists
- Advanced per-agent permissions — beyond v1
- Knowledge graph visualization — beyond v1
- Advanced automatic conflict resolution — beyond v1
- Markdown-plus-assets export — could have; lower priority than core pipeline
- Managed processing tier backend — can be added shortly after v1

## Context

- Architecture is approved baseline (modular monolith, two containers)
- Stack is committed: Python 3.12+/FastAPI/Uvicorn, React 18+TypeScript/Vite/Tailwind/shadcn/ui, PostgreSQL 16+pgvector, SQLAlchemy 2.x async/asyncpg/Alembic, MCP Python SDK, sentence-transformers + OpenAI embeddings, uv + pnpm
- Deployment: Docker Compose, two containers — `recalium-app` (API + UI static serving + in-process worker loop + backup scheduler + import watcher) and `recalium-postgres`
- Extensive architecture documentation exists in `docs/architecture/` covering every subsystem
- Website is already built (separate concern)
- Architecture review is complete; delivery phases are pre-defined in `docs/architecture/delivery-phases.md`

## Constraints

- **Tech Stack**: Python/FastAPI + React/TypeScript + PostgreSQL/pgvector — committed, no deviation without explicit approval and doc update
- **Deployment**: Two containers only (`recalium-app` + `recalium-postgres`) for v1; no separate worker/backup/watcher containers
- **Single-user**: v1 is single-user local-first; no multi-tenant columns, auth systems, or policy engines
- **BYOK by default**: No Recalium-operated processing services in v1; user's own provider keys only
- **Service-ready boundaries**: Clean module separation (domain logic / deployment profile / policy hooks) to allow future hosted service without full rewrite
- **Package managers**: `uv` for Python, `pnpm` for Node
- **Secrets**: All via `.env` file; `.env.sample` must be maintained; never hardcoded

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Two-container topology (app + postgres) | Avoids premature complexity for personal-scale v1; worker/backup/watcher are in-process tasks | — Pending |
| PostgreSQL as job queue | Avoids Redis/RabbitMQ dependency; sufficient for personal scale | — Pending |
| RRF k=60, top-50 per mode, top-20 merged | Balances recall and precision for personal-scale hybrid retrieval | — Pending |
| sentence-transformers all-MiniLM-L6-v2 as default local embedding model | Fast, small, no API key required for local use | — Pending |
| In-process async worker (asyncio task loop) | No separate container for v1; extract to separate container only if horizontal scaling needed | — Pending |
| BYOK-first, managed tier post-v1 | Target audience already has provider keys; managed tier is a convenience upsell | — Pending |
| Strict priority trimming (canonical → facts → summaries → raw) | Ensures highest-quality memory is used first within context budget | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-23 after initialization*
