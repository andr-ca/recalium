# Architecture Research

**Domain:** Local-first MCP-native personal memory platform
**Researched:** 2026-03-22
**Confidence:** HIGH — architecture is an approved, reviewed baseline with extensive documentation

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           recalium-app container                             │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Transport Layer                               │    │
│  │  ┌────────────────┐  ┌────────────────┐  ┌───────────────────────┐  │    │
│  │  │  React UI      │  │  REST API      │  │  MCP (StreamableHTTP/ │  │    │
│  │  │  (static SPA)  │  │  (FastAPI)     │  │  SSE via FastMCP)     │  │    │
│  │  └───────┬────────┘  └───────┬────────┘  └──────────┬────────────┘  │    │
│  └──────────┼───────────────────┼──────────────────────┼───────────────┘    │
│             │                   │                       │                    │
│  ┌──────────┴───────────────────┴──────────────────────┴───────────────┐    │
│  │                      Domain Modules                                  │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │    │
│  │  │  ingest  │  │ archive  │  │retrieval │  │canonical │             │    │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  │ memory  │             │    │
│  │       │             │             │        └────┬─────┘             │    │
│  │  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐            │    │
│  │  │  jobs   │  │ derived  │  │ policy   │  │  audit   │            │    │
│  │  │ (queue) │  │ memory   │  │          │  │provenance│            │    │
│  │  └────┬─────┘  └──────────┘  └──────────┘  └──────────┘            │    │
│  └───────┼──────────────────────────────────────────────────────────────┘    │
│          │                                                                   │
│  ┌───────┴────────────────────────────────────────────────────────────┐     │
│  │                  In-process Background Tasks (asyncio)              │     │
│  │  ┌──────────────────────┐  ┌──────────────┐  ┌──────────────────┐  │     │
│  │  │  Worker loop         │  │  Backup      │  │  Import watcher  │  │     │
│  │  │  (polls PG job queue)│  │  scheduler   │  │  (optional)      │  │     │
│  │  └──────────────────────┘  └──────────────┘  └──────────────────┘  │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │ pgvector + FTS + job queue
┌──────────────────────────────────────┴───────────────────────────────────────┐
│                           recalium-postgres container                        │
│   raw_archive │ derived_memory │ canonical_memory │ jobs │ audit │ ops       │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `ingest` | Validate payloads, normalize metadata, persist raw archive, enqueue jobs | `archive`, `policy`, `jobs`, `audit` |
| `archive` | Raw item storage, source metadata, deletion/redaction state | Domain modules (read-only from retrieval) |
| `derived-memory` | Summaries, chunks, facts, embeddings, dedup groupings, derivation lineage | `archive` (source), `jobs` (produced by) |
| `canonical-memory` | User-approved durable entries, provenance linkage, source-removed state | `retrieval` (reads), user via API/UI (writes) |
| `policy` | Sensitivity gate, external-provider eligibility, retrieval suppression, exposure checks | All domain modules (called before external ops) |
| `retrieval` | Keyword/semantic/hybrid search, RRF merge, conflict labeling, budget trimming, response assembly | `archive`, `derived-memory`, `canonical-memory`, `policy`, `audit` |
| `audit` | Provenance read models, access-event emission, mutation-event emission, audit queries | All domain modules (write); UI/MCP/API (read) |
| `jobs` | Durable enqueue/dequeue, retry bookkeeping, dead-letter state, worker concurrency | `ingest` (enqueues), worker (consumes), PostgreSQL (durable state) |
| `operations` | Backup metadata, restore state, watcher operational state, reprocessing state | backup scheduler, import watcher, API |
| `portability` | JSON export/import generation, version compatibility | `archive`, `derived-memory`, `canonical-memory`, `audit` |

---

## Recommended Project Structure

```
recalium/
├── backend/                    # Python package root (uv-managed)
│   ├── app/
│   │   ├── main.py             # FastAPI app factory + lifespan + worker startup
│   │   ├── api/                # Transport: REST route handlers (thin)
│   │   │   ├── ingest.py
│   │   │   ├── retrieval.py
│   │   │   ├── archive.py
│   │   │   ├── canonical.py
│   │   │   └── admin.py        # settings, backup, restore
│   │   ├── mcp/                # Transport: FastMCP server + tool definitions
│   │   │   └── server.py       # @mcp.tool() for ingest, retrieve, etc.
│   │   ├── domain/             # Domain modules — pure business logic
│   │   │   ├── ingest/
│   │   │   ├── archive/
│   │   │   ├── derived_memory/
│   │   │   ├── canonical_memory/
│   │   │   ├── policy/
│   │   │   ├── retrieval/
│   │   │   ├── audit/
│   │   │   ├── jobs/
│   │   │   ├── operations/
│   │   │   └── portability/
│   │   ├── worker/             # Worker loop: picks up jobs, dispatches handlers
│   │   │   └── loop.py         # asyncio task: poll → claim → dispatch → ack
│   │   ├── background/         # Other in-process tasks
│   │   │   ├── backup.py       # asyncio cron: pg_dump + artifact copy
│   │   │   └── watcher.py      # asyncio inotify/poll: watched-folder import
│   │   ├── db/                 # SQLAlchemy models + Alembic migrations
│   │   │   ├── models.py
│   │   │   └── migrations/
│   │   └── config.py           # Settings from .env via pydantic-settings
├── frontend/                   # React + TypeScript (pnpm-managed)
│   ├── src/
│   │   ├── pages/              # Route-level page components
│   │   ├── components/         # Shared UI components (shadcn/ui)
│   │   ├── api/                # API client (fetch wrappers / React Query)
│   │   └── main.tsx
│   └── vite.config.ts
├── docker/
│   ├── Dockerfile.app          # Multi-stage: build frontend + package backend
│   └── init.sql                # PostgreSQL init (pgvector extension)
├── docker-compose.yml
├── .env.sample
└── pyproject.toml              # uv-managed backend dependencies
```

### Structure Rationale

- **`domain/`:** Each module is a Python sub-package owning its models, services, and repo functions. No imports across domain modules except through defined interfaces. This enforces the dependency rules in `component-boundaries.md`.
- **`api/` and `mcp/`:** Thin transport adapters. They call domain services; they contain no business logic.
- **`worker/loop.py`:** A single asyncio `create_task` started in the FastAPI lifespan. It polls the PostgreSQL `jobs` table using `SELECT ... FOR UPDATE SKIP LOCKED`, claims one batch, dispatches to domain handlers, then sleeps briefly. This is the entire "worker" process — no separate container needed.
- **`background/`:** Backup scheduler and import watcher are separate asyncio tasks started in the same lifespan. They share the DB connection pool but operate independently of the worker loop.
- **`db/`:** SQLAlchemy 2.x async models + Alembic migrations. All domain modules get DB sessions through dependency injection — no module holds a DB handle directly.

---

## Architectural Patterns

### Pattern 1: Ingest-Acknowledge-Then-Queue

**What:** Synchronous path only persists the raw archive record and inserts job rows into PostgreSQL, then returns HTTP 202 to the caller. All derivation (chunking, summarization, embedding, dedup, indexing) is async.

**When to use:** Always for ingest. This is the core pattern keeping P95 ≤ 1s ingest latency achievable even when the embedding model is slow.

**Trade-offs:** Caller must poll for job status; derived results are not immediately available. Acceptable because memory retrieval is always "eventually consistent" by nature.

**Example (Python):**
```python
async def handle_ingest(payload: IngestRequest, db: AsyncSession) -> IngestResponse:
    async with db.begin():
        archive_item = await archive_repo.create(db, payload)
        await audit_repo.record(db, "ingest", archive_item.id)
        await jobs_repo.enqueue(db, "derive_memory", archive_item.id)
    # Transaction committed: archive + job both durable before we return
    return IngestResponse(id=archive_item.id, status="accepted")
```

### Pattern 2: PostgreSQL SKIP LOCKED Job Queue

**What:** The worker loop polls a `jobs` table using `SELECT ... FOR UPDATE SKIP LOCKED` to atomically claim a batch of jobs without blocking concurrent workers and without needing Redis/RabbitMQ.

**When to use:** Exactly this scenario — single-user personal scale, in-process worker, PostgreSQL already present.

**Trade-offs:** Slightly higher polling latency than event-driven queues (configurable poll interval, typically 0.5–2s). Acceptable for personal scale. The architecture doc notes the clean extraction path to a separate container if horizontal scaling is ever needed.

**Example (Python):**
```python
async def claim_jobs(db: AsyncSession, batch_size: int = 5) -> list[Job]:
    result = await db.execute(
        select(Job)
        .where(Job.status == "available", Job.available_at <= func.now())
        .order_by(Job.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    jobs = result.scalars().all()
    for job in jobs:
        job.status = "claimed"
        job.claimed_at = datetime.utcnow()
    await db.commit()
    return jobs
```

### Pattern 3: Retrieval Precedence + RRF + Budget Trimming

**What:** Results are fetched from three candidate pools (keyword FTS, vector cosine, filtered metadata), merged via Reciprocal Rank Fusion (k=60, top-50 per mode, top-20 merged), then trimmed by strict priority order (canonical → facts → summaries → raw excerpts) to fit within a token budget.

**When to use:** Always for the hybrid retrieval path. The architecture specifies exact parameters; don't tune unless benchmarks reveal a problem.

**Trade-offs:** RRF is simple and well-understood but doesn't leverage semantic scores directly. An optional cross-encoder reranker can be layered on the top-20 RRF results if quality issues arise.

### Pattern 4: Modular Monolith with Deploy-Profile Seams

**What:** All domain modules run in a single Python process, but each module is a clean sub-package with explicit interfaces. "Deploy-profile" configuration (local vs. hosted) is externalized to settings, not baked into domain logic. Policy hooks are explicit call sites, not ambient globals.

**When to use:** For v1. The architecture documentation explicitly calls out that splitting to microservices before scale is needed is an anti-pattern for this product.

**Trade-offs:** Requires discipline to keep module boundaries clean (no circular imports, no domain module reaching into transport layer). Justified by faster development velocity and simpler operations for a single-user local product.

---

## Data Flow

### Ingest Flow (Sequence A)

```
UI/API/MCP  →  ingest (validate + idempotency check)
                  ↓
              policy (sensitivity gate, provider eligibility hints)
                  ↓
              archive (persist raw item + source metadata)
                  ↓
              audit (record ingest event)
                  ↓
              jobs (enqueue derivation tasks — same transaction)
                  ↓
              [HTTP 202 returned to caller]

              ← asyncio worker loop polls jobs table →

              worker picks up job →  derived-memory
                  ↓
              summarization → fact extraction → dedup → embedding → FTS index
                  ↓
              review queue materialized
                  ↓
              audit (record derivation completion)
```

### Retrieval Flow (Sequence B)

```
UI/API/MCP  →  retrieval (normalize filters + mode)
                  ↓
              policy (access/suppression rules)
                  ↓
              retrieval queries three candidate pools:
                  ├── canonical-memory (FTS + metadata filter)
                  ├── derived-memory facts/summaries (FTS + vector cosine)
                  └── archive raw excerpts (FTS)
                  ↓
              RRF merge (k=60, top-50 per mode → top-20)
                  ↓
              [optional cross-encoder reranker]
                  ↓
              conflict labeling
                  ↓
              strict budget trimming (canonical → facts → summaries → raw)
                  ↓
              audit (record retrieval event + policy decision)
                  ↓
              response assembled with source links, provenance, scores
```

### Deletion Cascade Flow

```
User initiates delete/redact via UI/API →  archive (mark removed)
                  ↓
              jobs (enqueue suppression cascade)
                  ↓
              worker: derived-memory suppressed (summaries, facts, embeddings)
                         FTS and vector search entries suppressed
                         canonical-memory moved to source-removed/review-required state
                  ↓
              deletion tombstone persisted (durable, survives restore)
                  ↓
              retrieval cache invalidated for affected items
                  ↓
              audit (record removal + suppression events)
```

---

## Build Order

The delivery phases in `docs/architecture/delivery-phases.md` reflect the correct dependency order:

| Phase | What to Build | Why First |
|-------|--------------|-----------|
| **1 — Foundation** | Docker topology, PostgreSQL + pgvector + FTS, raw archive ingest, web UI shell, provenance/audit foundations | Everything else depends on durable storage and the ingest path. No pipeline, no UI completeness needed yet. |
| **2 — Pipeline** | Background worker loop, job queue, chunking, summarization, fact extraction, dedup/overlap grouping, reprocessing support | Retrieval is useless without derived memory. Worker loop must be solid before retrieval can be meaningful. |
| **3 — Retrieval + Review** | Keyword/semantic/hybrid retrieval, RRF, budget trimming, canonical-memory workflows, review queue | Retrieval depends on Phase 2 derived artifacts. Canonical memory workflows require fact extraction to exist. |
| **4 — Privacy + Operations** | Sensitivity gate, deletion cascade, backup/restore UI, degraded-mode, BYOK setup flow | Privacy enforcement and backups can be layered on top once core pipeline and retrieval are stable. |
| **5 — Service Hardening** | Deploy-profile separation, API/MCP contract hardening, boundary review | Final cleanup for future hosted service. Cannot be done meaningfully before the system is feature-complete. |

**Critical dependency chain:**
```
PostgreSQL schema + pgvector
    ↓
raw archive + ingest API + job queue tables
    ↓
worker loop + derivation handlers
    ↓
retrieval (FTS + vector indexes populated)
    ↓
canonical memory + review queue UI
    ↓
privacy gates + deletion cascade
    ↓
backup/restore
```

**Within Phase 1, recommended micro-order:**
1. Docker Compose + PostgreSQL container + pgvector extension
2. Alembic migration baseline (archive, jobs, audit schema groups)
3. FastAPI app skeleton + lifespan + DB connection pool
4. Raw archive ingest endpoint (synchronous path only)
5. Web UI shell with left-nav layout + ingest form
6. Audit event persistence (ingest event)

---

## In-Process Worker: Risks and Mitigations

The architecture chose an in-process asyncio worker loop over a separate container. This is the right call for personal scale, but has specific risks worth calling out explicitly.

### Risk 1: CPU-bound tasks blocking the event loop

**What goes wrong:** sentence-transformers inference and LLM extraction calls are CPU or I/O bound. If run directly in an `async def`, they block the event loop and starve API requests.

**Mitigation:** Use `asyncio.to_thread()` for all CPU-bound work (embedding generation, heavy text processing). Use `httpx.AsyncClient` for all external provider calls. Never call blocking libraries (requests, synchronous model inference) directly from an async context.

**Detection:** P95 ingest latency suddenly spikes to >1s during batch processing — a sign the event loop is being starved.

### Risk 2: Worker loop silently dying

**What goes wrong:** An unhandled exception in the worker loop task kills the task silently. asyncio tasks that aren't referenced can also be garbage-collected mid-execution.

**Mitigation:**
- Hold a strong reference to the worker task in the app lifespan context (not just fire-and-forget).
- Wrap the polling loop in a `try/except Exception` catch-all that logs errors and continues — never let a single bad job kill the loop.
- Add a health-check endpoint or startup log that confirms the worker task is alive.
- The architecture's queue durability model means jobs survive a restart; the risk is silent dropped processing, not lost jobs.

**Example:**
```python
# In FastAPI lifespan — hold strong reference
background_tasks: set[asyncio.Task] = set()

async def worker_loop():
    while True:
        try:
            await process_next_batch(db)
        except Exception as e:
            logger.exception("Worker loop error (continuing): %s", e)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

task = asyncio.create_task(worker_loop())
background_tasks.add(task)
task.add_done_callback(background_tasks.discard)
```

### Risk 3: Worker concurrency interfering with API latency

**What goes wrong:** Multiple worker claims run concurrently and overwhelm the asyncio event loop or the PostgreSQL connection pool, causing API requests to queue.

**Mitigation:** Bound worker concurrency explicitly (e.g., max 3 concurrent derivation jobs). Use a semaphore in the worker loop. Size the PostgreSQL connection pool to account for both API requests and worker claims.

### Risk 4: In-progress jobs lost on container restart

**What goes wrong:** Jobs in `claimed` status when the container restarts are stuck — they won't be picked up because they appear claimed.

**Mitigation:** On worker startup, re-queue any jobs that have been in `claimed` status for longer than a configurable recovery threshold (e.g., 5 minutes). The architecture document specifies this recovery model in `queue-and-jobs.md`.

### Risk 5: Scaling wall — when to extract to a separate container

**What this looks like:** Embedding generation or summarization backlog grows faster than the in-process worker can drain it, and the user is waiting minutes for facts to appear.

**When it matters:** Personal scale (≤100k items, single user) means the in-process worker is almost certainly sufficient. The documented scaling path is: extract `worker/loop.py` into a separate `recalium-worker` container pointed at the same PostgreSQL job queue. No domain logic changes required — only deployment configuration.

---

## Integration Points

### External Services (BYOK)

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| OpenAI embeddings / GPT-4o | `httpx.AsyncClient` + `asyncio.to_thread` for sync SDKs | Policy gate runs before every call; key validated at config time |
| Anthropic Claude | Same pattern as OpenAI | Same policy gate |
| Ollama (local) | HTTP to Ollama endpoint — no key required | Default local embedding path; no policy gate needed for local |
| sentence-transformers | In-process Python — `asyncio.to_thread` | CPU-bound; must not block event loop |

### Internal Module Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `api/mcp` → `domain/*` | Direct async function calls | Transport must not contain domain logic |
| `worker` → `domain/*` | Direct async function calls via job handlers | Worker dispatches by job type |
| `policy` → everywhere | Sync/async function call — returns allow/deny decision | Must be called before any external provider call |
| `archive` ↔ `retrieval` | Retrieval reads archive; archive must NOT import retrieval | Enforced by dependency rule in component-boundaries.md |
| `jobs` ↔ `worker` | Worker polls PostgreSQL table via `jobs` module interface | Queue interface is adapter-based for future swap |
| `ingest` → `jobs` | Same-transaction job enqueue | Atomicity is critical — both archive write and job insert commit together |

---

## Scaling Considerations

| Scale | Architecture Adjustment |
|-------|------------------------|
| 1 user, ≤100k items (v1 target) | In-process worker, single app container, PG job queue — current architecture |
| 1 user, growing backlog | Increase worker concurrency bound; add connection pool headroom |
| Future hosted service | Extract worker to separate container (documented path); introduce queue adapter; add auth/session layer; add tenant-aware policy seams |
| Multi-user hosted | Add tenant columns (seams already planned); extract to microservices only when specific bottlenecks emerge |

### Scaling Priorities

1. **First bottleneck:** Embedding/derivation throughput — the in-process worker hits a wall if inference is slow. Fix: extract worker container, or upgrade Ollama hardware, or throttle batch size.
2. **Second bottleneck:** PostgreSQL vector index scan time beyond 100k items — fix: tune `pgvector` HNSW index parameters, or implement pre-filter by metadata before vector scan.
3. **Third bottleneck (future service only):** Concurrent multi-user API load — current single-process Uvicorn is fine for personal use; add workers or move to gunicorn+uvicorn pool for service profile.

---

## Anti-Patterns

### Anti-Pattern 1: Long-running work in the synchronous ingest path

**What people do:** Call the embedding model or LLM during the HTTP ingest handler to "immediately have derived results."

**Why it's wrong:** Embedding a large conversation file can take 2–30 seconds. This violates the P95 ≤ 1s ingest latency requirement and blocks the event loop.

**Do this instead:** Persist the raw archive + enqueue jobs in a single transaction, return 202 Accepted. Derived results appear asynchronously. The UI polls job status.

### Anti-Pattern 2: Blocking calls inside async handlers

**What people do:** Call `requests.post(...)` or `model.encode(text)` (synchronous) directly inside an `async def` route handler or worker coroutine.

**Why it's wrong:** Blocks the single-threaded asyncio event loop for the duration of the call. All other coroutines (API requests, the heartbeat, the backup scheduler) are starved until it returns.

**Do this instead:** Wrap all blocking operations in `await asyncio.to_thread(blocking_fn, args)`. Use `httpx.AsyncClient` for all HTTP. Use async SQLAlchemy (`asyncpg` driver).

### Anti-Pattern 3: Domain logic in the MCP tool handlers

**What people do:** Put retrieval logic, policy checks, or fact management directly inside the `@mcp.tool()` decorated functions.

**Why it's wrong:** Duplicates logic between MCP and REST paths; makes testing harder; couples the MCP transport format to business rules.

**Do this instead:** MCP tool handlers should be identical in structure to REST endpoint handlers — they call a domain service function and return its result. The domain service owns the logic.

### Anti-Pattern 4: Bypassing the policy gate for external calls

**What people do:** Add a "quick" path that calls an embedding provider directly without checking sensitivity classification, because the policy check "is slow."

**Why it's wrong:** Personal/relationship content ends up in an external provider's training data or logs. This is a hard user trust violation and violates the documented privacy requirements.

**Do this instead:** The policy check is a fast in-memory rule evaluation. Make it mandatory — the `policy` module must be in the call chain before any external provider call, with no exception.

### Anti-Pattern 5: Fire-and-forget asyncio tasks without strong references

**What people do:** `asyncio.create_task(worker_loop())` without saving the task reference anywhere.

**Why it's wrong:** Python's asyncio event loop only holds weak references to tasks. The task can be garbage-collected mid-execution with no error or warning.

**Do this instead:** Save the task in the app lifespan context set. Add a `done_callback` to log and alert if the task exits unexpectedly.

### Anti-Pattern 6: Splitting to containers prematurely

**What people do:** Create separate Docker containers for the worker, backup scheduler, and import watcher from day one "to be ready to scale."

**Why it's wrong:** Five containers instead of two means: more Docker Compose complexity, five container logs to check, inter-container networking to manage, deployment scripts for every component — for a product that serves one user on a laptop.

**Do this instead:** In-process asyncio tasks for all background work. The extraction path to a separate worker container is documented and clean when actually needed.

---

## Sources

- `docs/architecture/component-boundaries.md` — definitive module ownership and dependency rules (HIGH confidence — reviewed baseline)
- `docs/architecture/container-topology.md` — two-container deployment model and scaling path (HIGH confidence — reviewed baseline)
- `docs/architecture/delivery-phases.md` — ordered implementation slices (HIGH confidence — reviewed baseline)
- `docs/architecture/processing-pipeline.md` — synchronous and async ingest path contract (HIGH confidence — reviewed baseline)
- `docs/architecture/queue-and-jobs.md` — PostgreSQL SKIP LOCKED queue model (HIGH confidence — reviewed baseline)
- `docs/architecture/retrieval-and-ranking.md` — RRF parameters, budget trimming, caching (HIGH confidence — reviewed baseline)
- `docs/architecture/performance-and-operability.md` — P95 targets and design tactics (HIGH confidence — reviewed baseline)
- `docs/architecture/future-service-compatibility.md` — service-ready seams (HIGH confidence — reviewed baseline)
- FastAPI documentation — `BackgroundTasks` caveat: "for heavy background computation, use Celery" (confirms that in-process workers are appropriate only when task isolation and GIL pressure are bounded) (MEDIUM confidence — official docs, 2025)
- Python asyncio docs — `create_task` weak reference warning: tasks must be saved to avoid GC (HIGH confidence — official Python 3.12+ docs)
- MCP Python SDK README — `FastMCP` supports mounting to existing ASGI server; `streamable-http` transport mounts cleanly to FastAPI (HIGH confidence — official SDK docs, 2025)

---
*Architecture research for: local-first MCP-native personal memory platform (Recalium)*
*Researched: 2026-03-22*
