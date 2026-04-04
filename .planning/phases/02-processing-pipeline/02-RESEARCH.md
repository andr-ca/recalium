# Phase 2: Processing Pipeline - Research

**Researched:** 2026-03-23
**Domain:** Async job processing, NLP pipeline, PostgreSQL FTS + pgvector, BYOK provider routing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Worker Architecture**
- Single `asyncio.create_task()` loop started in FastAPI lifespan (`lifespan` in `main.py`)
- Worker polls jobs table with `SELECT ... FOR UPDATE SKIP LOCKED`; processes one job at a time with bounded concurrency via `asyncio.Semaphore`
- CPU-heavy work (sentence-transformers inference) dispatched via `asyncio.to_thread()` to avoid blocking the event loop
- All external HTTP (OpenAI/Anthropic/Ollama API calls) via `httpx.AsyncClient`
- Worker loop is a single `asyncio.Task`; concurrency controlled by semaphore, not multiple tasks
- Pending/available jobs survive container restart because queue state is durable in PostgreSQL
- In-progress jobs older than a recovery threshold are re-queued on worker startup

**Sensitivity Classification**
- Two-pass gate: keyword heuristics first (fast path), then a small local ML intent classifier as second pass
- Heuristics use keyword lists for `personal_profile` (name, birthday, address, age, etc.) and `relationship` (wife, husband, kids, friend X, etc.)
- ML classifier: use sentence-transformers zero-shot classification or a small fine-tuned intent model via `asyncio.to_thread()`
- Default sensitivity: `unclassified` — blocked from external processing unless user explicitly overrides
- Gate fires before any external provider call; policy decision recorded in job metadata
- Categories: `personal_profile`, `relationship`, `unclassified` (blocked by default), `general` (allowed)

**LLM Provider Strategy**
- Provider-agnostic routing per function: embedding provider and summarization/extraction provider are independently configurable (satisfies BYOK-08)
- Route to whichever provider key is configured; user can set different providers for embedding vs. extraction
- If no LLM provider configured: skip summarization and LLM extraction; still run local embeddings and FTS indexing
- If no provider configured for embeddings: skip embedding job (not failed — marked `pending_provider`)
- Job status `pending_provider` when blocked on missing provider key; NOT counted as failed
- Invalid/rate-limited key → job enters `retryable_failed` state with error captured (satisfies BYOK-07)
- Provider keys read from settings at job dispatch time (not cached in job record)

**Job Status UI**
- Archive card badge upgrades from Phase 1 `Ingested` to full pipeline state
- Auto-refresh: page polls `/api/archive` every 5 seconds while any item has `Processing` status
- No WebSocket or SSE in Phase 2 — polling is sufficient for personal scale

### the agent's Discretion
- Exact polling interval granularity (5s default is a starting point; agent may tune)
- Specific shadcn/ui component choices for status badges and retry button
- SQL query structure for SKIP LOCKED job claims (exact CTE vs. subquery form)
- Chunk size for summarization (default to whole-conversation for v1 given personal-scale data volumes)
- Exact ML model used for intent classification second pass (zero-shot via sentence-transformers or lightweight HuggingFace model)

### Deferred Ideas (OUT OF SCOPE)
- Real-time WebSocket/SSE push for job status — polling is sufficient for personal scale in v1
- Chunk-level granular processing (splitting conversations into chunks for long content) — whole-conversation as default unit for v1
- Per-provider cost estimation before bulk import (BYOK-06) — deferred to Phase 4
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-01 | Async pipeline produces summaries, extracted facts, embeddings, and FTS index entries without blocking ingest response | Worker loop + SKIP LOCKED + derived_memory ORM models |
| PIPE-02 | Every extracted fact carries source span, confidence tier (high/medium/low), derivation method, and model version | Facts table schema; LLM prompt patterns for span extraction |
| PIPE-03 | Sensitivity gate runs before any external provider call; personal/relationship/unclassified content blocked from external processing by default | Two-pass policy gate architecture; CrossEncoder zero-shot |
| PIPE-04 | Failed jobs retry automatically with bounded attempts; terminal failures surface for manual retry | SKIP LOCKED claim loop; `retryable_failed` status; max_attempts guard |
| PIPE-05 | Reprocessing supported after logic changes or failures | Job reset endpoint; `pending` re-enqueue pattern |
| PRIV-04 | Personal profile and relationship content blocked from external processing by default | Sensitivity gate heuristics + ML classifier; policy decision audit |
| PRIV-05 | Unknown/unclassified content blocked from external processing by default until user explicitly allows | `unclassified` → blocked by default in gate logic |
| BYOK-07 | Invalid/rate-limited keys cause affected jobs to enter retryable failed state with clear error; no silent drops | `retryable_failed` status + error_message on API exception |
| BYOK-08 | User can switch providers per function without reprocessing already-completed items | Per-function routing; completed sub-jobs not re-run |
| CANM-06 | Conflict detection flags contradictory facts across sources | `conflict_groups` table; cosine similarity dedup at embed time |
</phase_requirements>

---

## Summary

Phase 2 builds an in-process async worker that drains the PostgreSQL job queue populated by Phase 1's ingest path. The worker runs as a single `asyncio.Task` inside FastAPI's lifespan, claims jobs with `SELECT … FOR UPDATE SKIP LOCKED`, then dispatches each job through a pipeline: sensitivity gate → LLM summarization/extraction (if provider available) → local embedding (sentence-transformers) → FTS indexing → conflict/duplicate detection. All CPU-heavy work (sentence-transformers inference) runs in `asyncio.to_thread()` to avoid blocking the event loop; external API calls use `httpx.AsyncClient`.

The key data model is a new `derived_memory` domain containing five tables: `summaries`, `facts`, `embeddings`, `fts_entries`, and `conflict_groups`. Every row in these tables must carry a `source_status` column using the `source_status` ENUM created in migration 0001, supporting the Phase 4 cascade deletion contract. The `facts` table must carry `source_span`, `confidence_tier`, `derivation_method`, and `derivation_model` as non-nullable fields per PIPE-02 and the architecture spec.

Provider routing is per-function: the embedding sub-job and the summarization/extraction sub-job each independently check for a configured provider key at dispatch time. Missing key → `pending_provider` (not failed). Invalid/rate-limited key → `retryable_failed` with error captured. The frontend gains a polling-based status badge system using existing shadcn/ui `success`, `warning`, and `destructive` variants.

**Primary recommendation:** Build the worker as one `asyncio.Task` with bounded semaphore; keep the sensitivity gate synchronous and cheap (heuristics first); use `asyncio.to_thread()` strictly for sentence-transformers inference; let the jobs table be the single source of truth for pipeline state visible to the UI.

---

## Standard Stack

### Core (all already in pyproject.toml)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sentence-transformers` | 5.3.0 | Local embeddings (all-MiniLM-L6-v2) + zero-shot classification (CrossEncoder) | Already pinned; runs fully local; no API key needed |
| `sqlalchemy` | 2.0.48 | Async ORM + SKIP LOCKED query | Already in use; `Select.with_for_update(skip_locked=True)` is native |
| `asyncpg` | 0.31.0 | PostgreSQL async driver | Already in use with engine |
| `openai` | >=1.0,<2 | Chat completions + embeddings (AsyncOpenAI) | Already pinned; also used for Ollama compat endpoint |
| `anthropic` | >=0.20,<1 | Messages API (AsyncAnthropic) | Already pinned |
| `httpx` | 0.28.1 | Async HTTP for provider calls | Already in use in settings service |

### Must Add

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `pgvector` | 0.4.2 | `Vector(384)` SQLAlchemy column type + HNSW index | pgvector extension is already created in migration 0001; need Python client |

**Add to pyproject.toml:**
```toml
"pgvector==0.4.2",
```

**Install:**
```bash
uv pip install pgvector==0.4.2
```

> **Note:** The global pip environment has `openai==2.8.1` but the project venv pins `openai>=1.0,<2`. The venv is the only environment that matters. Verify with `uv pip list | grep openai` inside the venv.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sentence-transformers` CrossEncoder for zero-shot | HuggingFace `transformers` ZeroShotClassificationPipeline | Same underlying model; sentence-transformers API is cleaner and already a dep |
| Local embeddings only | OpenAI `text-embedding-3-small` | Requires API key; locked decision is local-first for embeddings |
| PostgreSQL job queue | Celery + Redis | Adds broker dependency; PostgreSQL queue is sufficient for personal scale |

---

## Architecture Patterns

### Recommended Module Structure

```
backend/app/
├── worker/
│   ├── __init__.py
│   ├── loop.py          # asyncio.Task, claim/dispatch loop
│   └── dispatcher.py    # routes job_type → handler coroutine
├── domain/
│   ├── derived_memory/
│   │   ├── __init__.py
│   │   ├── models.py    # Summary, Fact, Embedding, FtsEntry, ConflictGroup
│   │   └── service.py   # write_summary(), write_facts(), write_embedding(), etc.
│   ├── policy/
│   │   ├── __init__.py
│   │   └── gate.py      # SensitivityGate: heuristics + CrossEncoder
│   └── jobs/
│       ├── models.py    # Job ORM (existing — add pending_provider status docs)
│       └── service.py   # claim_job(), complete_job(), fail_job(), reset_stale()
backend/alembic/versions/
└── 0002_derived_memory.py   # summaries, facts, embeddings, fts_entries, conflict_groups
```

### Pattern 1: SKIP LOCKED Job Claim (SQLAlchemy 2.x async)

**What:** Atomically claim exactly one pending job without race conditions.
**When to use:** Every iteration of the worker poll loop.

```python
# Source: SQLAlchemy 2.x docs — Select.with_for_update()
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.jobs.models import Job
from datetime import datetime, timezone

async def claim_next_job(session: AsyncSession) -> Job | None:
    stmt = (
        select(Job)
        .where(Job.status.in_(["pending", "retryable_failed"]))
        .where(Job.attempts < Job.max_attempts)
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        return None
    job.status = "claimed"
    job.attempts += 1
    job.claimed_at = datetime.now(timezone.utc)
    job.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return job
```

> **Existing index:** `ix_jobs_status_created_at` on `(status, created_at)` is already in migration 0001 — this query hits that index directly.

### Pattern 2: Worker Loop with Semaphore

**What:** Single asyncio.Task that polls + processes with bounded concurrency.
**When to use:** Started once in `lifespan`, cancelled on shutdown.

```python
# Source: Python asyncio docs — asyncio.Semaphore, asyncio.create_task
import asyncio
import logging

logger = logging.getLogger(__name__)
_MAX_CONCURRENT = 1  # personal scale; one job at a time in v1

async def worker_loop() -> None:
    """Main worker loop. Runs forever until cancelled."""
    sem = asyncio.Semaphore(_MAX_CONCURRENT)
    while True:
        try:
            async with sem:
                job = await claim_next_job(...)
                if job is None:
                    await asyncio.sleep(2)  # back-off when queue empty
                    continue
                await dispatch_job(job)
        except asyncio.CancelledError:
            logger.info("Worker loop cancelled — shutting down")
            raise  # re-raise so Task completes cleanly
        except Exception as e:
            logger.exception("Worker loop unhandled error: %s", e)
            await asyncio.sleep(5)  # brief pause before retrying
```

**Lifespan integration** (add to `main.py`):
```python
# In lifespan(), after DB pool init:
from app.worker.loop import worker_loop
_worker_task = asyncio.create_task(worker_loop(), name="pipeline-worker")

yield  # FastAPI serves requests here

# Shutdown:
_worker_task.cancel()
try:
    await _worker_task
except asyncio.CancelledError:
    pass
```

### Pattern 3: CPU-Bound Work via asyncio.to_thread()

**What:** Run sentence-transformers inference without blocking the event loop.
**When to use:** All calls to `SentenceTransformer.encode()` or `CrossEncoder.predict()`.

```python
# Source: Python asyncio docs — asyncio.to_thread (Python 3.9+)
import asyncio
from sentence_transformers import SentenceTransformer, CrossEncoder

_embed_model: SentenceTransformer | None = None
_classifier_model: CrossEncoder | None = None

def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model

async def embed_text(text: str) -> list[float]:
    """Embed text in thread pool to avoid blocking event loop."""
    def _encode() -> list[float]:
        model = _get_embed_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()
    return await asyncio.to_thread(_encode)
```

> **Important:** Load models lazily (first use) or eagerly at worker startup, but NOT at module import time — avoids blocking the event loop during app init.

### Pattern 4: OpenAI Chat Completions (fact extraction)

```python
# Source: openai-python SDK docs — AsyncOpenAI
from openai import AsyncOpenAI

async def extract_facts_openai(api_key: str, text: str) -> dict:
    client = AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": FACT_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return response.choices[0].message.content  # parse JSON
```

### Pattern 5: Anthropic Messages API (fact extraction)

```python
# Source: anthropic-python SDK docs — AsyncAnthropic
from anthropic import AsyncAnthropic

async def extract_facts_anthropic(api_key: str, text: str) -> str:
    client = AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=2048,
        messages=[{"role": "user", "content": text}],
        system=FACT_EXTRACTION_SYSTEM_PROMPT,
    )
    return response.content[0].text  # parse JSON from text
```

### Pattern 6: Ollama via OpenAI-Compatible Endpoint

**What:** Ollama exposes `/v1/chat/completions` compatible with the openai SDK.
**How:** Reuse `AsyncOpenAI` with `base_url` pointing to Ollama.

```python
# Source: Ollama OpenAI compatibility docs
from openai import AsyncOpenAI

async def extract_facts_ollama(base_url: str, model: str, text: str) -> str:
    client = AsyncOpenAI(
        api_key="ollama",  # arbitrary non-empty string
        base_url=f"{base_url.rstrip('/')}/v1",
    )
    response = await client.chat.completions.create(
        model=model,  # e.g. "llama3.2"
        messages=[
            {"role": "system", "content": FACT_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0,
    )
    return response.choices[0].message.content
```

> The `base_url` stored in `settings.ollama_base_url` (e.g. `http://host.docker.internal:11434`) is already validated by `validate_ollama_connection()` in `settings/service.py`.

### Pattern 7: pgvector Column + HNSW Index (SQLAlchemy 2.x)

```python
# Source: pgvector-python README — SQLAlchemy integration
from pgvector.sqlalchemy import Vector
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.db import Base

class Embedding(Base):
    __tablename__ = "embeddings"
    # ... other columns ...
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)

# HNSW index for cosine similarity search (add in Alembic migration):
# Index('ix_embeddings_vector', Embedding.embedding,
#       postgresql_using='hnsw',
#       postgresql_with={'m': 16, 'ef_construction': 64},
#       postgresql_ops={'embedding': 'vector_cosine_ops'})
```

**In Alembic migration (raw SQL form):**
```python
op.execute("""
    CREATE INDEX ix_embeddings_vector ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
""")
```

### Pattern 8: PostgreSQL FTS — tsvector Column + GIN Index

```python
# In Alembic migration:
op.add_column("fts_entries",
    sa.Column("search_vector", sa.NULLTYPE, nullable=True)  # use op.execute for TSVECTOR
)
op.execute("""
    ALTER TABLE fts_entries ADD COLUMN search_vector TSVECTOR
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(text_content, ''))) STORED
""")
op.execute("CREATE INDEX ix_fts_search_vector ON fts_entries USING GIN (search_vector)")
```

**Or write `tsvector` explicitly in the worker (preferred for full control):**
```python
# Worker writes tsvector explicitly so it can combine summary + fact text
from sqlalchemy import text

await session.execute(
    text("UPDATE fts_entries SET search_vector = to_tsvector('english', :content) WHERE id = :id"),
    {"content": combined_text, "id": str(entry_id)}
)
```

### Pattern 9: Sensitivity Gate — Zero-Shot Classification

**What:** CrossEncoder NLI model used for zero-shot intent classification.
**Model:** `cross-encoder/nli-MiniLM2-L6-H768` — fast (6-layer MiniLM), ~80MB, ships with sentence-transformers.

```python
# Source: sentence-transformers docs — CrossEncoder zero-shot
from sentence_transformers import CrossEncoder

_gate_model: CrossEncoder | None = None
SENSITIVITY_LABELS = ["personal profile information", "relationship information", "general topic"]

def _get_gate_model() -> CrossEncoder:
    global _gate_model
    if _gate_model is None:
        _gate_model = CrossEncoder("cross-encoder/nli-MiniLM2-L6-H768")
    return _gate_model

def classify_sensitivity(text: str) -> tuple[str, float]:
    """Returns (category, confidence). Runs in asyncio.to_thread()."""
    model = _get_gate_model()
    pairs = [(text, label) for label in SENSITIVITY_LABELS]
    scores = model.predict(pairs)  # shape: (3, 3) — entailment/neutral/contradiction
    entailment_scores = scores[:, 2]  # entailment column
    best_idx = entailment_scores.argmax()
    confidence = float(entailment_scores[best_idx])

    label_map = {0: "personal_profile", 1: "relationship", 2: "general"}
    category = label_map[best_idx]
    if confidence < 0.6:
        category = "unclassified"
    return category, confidence
```

### Anti-Patterns to Avoid

- **Loading sentence-transformers models at module import time:** blocks the event loop during app startup; load lazily or in lifespan startup.
- **Calling `session.commit()` inside `with_for_update()` block before updating status:** the lock is released at commit; the job must be marked `claimed` before committing.
- **Using `asyncio.gather()` with multiple concurrent jobs:** the CONTEXT.md decision is one job at a time via semaphore; gather introduces parallel DB writes that complicate error handling.
- **Hardcoding job status strings as literals:** define `JobStatus` as a `str` enum or constants module used everywhere — avoids typo bugs in status transitions.
- **Not cancelling the worker task on shutdown:** `asyncio.Task` left running causes `asyncio.CancelledError` noise or hangs; always `task.cancel() + await task` in the lifespan shutdown branch.
- **Storing provider API keys in the Job record:** CONTEXT.md says "keys read from settings at job dispatch time" — never embed keys in job payload or error messages.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector similarity search | Custom cosine distance SQL | pgvector `<=>` operator + HNSW index | Handles ANN, index maintenance, NULL guards |
| Zero-shot text classification | Regex + rule engine | CrossEncoder NLI via sentence-transformers | 80MB model, sub-second inference, handles novel text patterns |
| Async job serialization | Custom locking mechanism | `SELECT ... FOR UPDATE SKIP LOCKED` | Atomically prevents double-claim; PostgreSQL native |
| LLM response JSON parsing | Custom parser | OpenAI `response_format={"type":"json_object"}` | Forces valid JSON; no regex parsing of markdown code blocks |
| Embedding normalization | Manual L2 norm | `model.encode(text, normalize_embeddings=True)` | Built-in; returns unit vectors ready for cosine similarity |
| Ollama provider client | Custom httpx wrapper | `AsyncOpenAI(base_url=ollama_url + "/v1")` | Ollama exposes OpenAI-compatible `/v1` endpoint natively |

**Key insight:** The PostgreSQL job queue + SKIP LOCKED is the entire concurrency primitive for v1. Do not add Redis, Celery, or any external broker — the architecture decision is explicit and the personal-scale volume does not need it.

---

## Derived Memory Schema (New Migration 0002)

All five tables must include `source_status` (the ENUM created in 0001) per the cascade contract in `0001_initial.py`.

### summaries
```sql
CREATE TABLE summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_archive_id UUID NOT NULL REFERENCES raw_archive(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    model_used VARCHAR(128) NOT NULL,         -- e.g. "gpt-4o-mini"
    derivation_method VARCHAR(64) NOT NULL,   -- "llm_summarization"
    source_status source_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### facts
```sql
CREATE TABLE facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_archive_id UUID NOT NULL REFERENCES raw_archive(id) ON DELETE CASCADE,
    fact_text TEXT NOT NULL,
    source_span TEXT NOT NULL,                -- REQUIRED; empty string is invalid
    confidence_tier VARCHAR(16) NOT NULL,     -- "high" | "medium" | "low"
    derivation_method VARCHAR(64) NOT NULL,   -- "llm_extraction" | "rule_based"
    derivation_model VARCHAR(128) NOT NULL,   -- "gpt-4o-mini" | "local_rules_v1"
    conflict_group_id UUID REFERENCES conflict_groups(id) ON DELETE SET NULL,
    source_status source_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### embeddings
```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_archive_id UUID NOT NULL REFERENCES raw_archive(id) ON DELETE CASCADE,
    embedding vector(384) NOT NULL,           -- all-MiniLM-L6-v2 output dim
    embedding_model VARCHAR(128) NOT NULL,    -- "all-MiniLM-L6-v2"
    source_status source_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- HNSW index added separately (see Pattern 7)
```

### fts_entries
```sql
CREATE TABLE fts_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_archive_id UUID NOT NULL REFERENCES raw_archive(id) ON DELETE CASCADE,
    text_content TEXT NOT NULL,
    search_vector TSVECTOR,                   -- populated by worker via to_tsvector()
    source_status source_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- GIN index on search_vector added separately
```

### conflict_groups
```sql
CREATE TABLE conflict_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_type VARCHAR(32) NOT NULL,          -- "duplicate" | "contradiction" | "overlap"
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
    -- facts reference this table via conflict_group_id FK
);
```

---

## Common Pitfalls

### Pitfall 1: Blocking the Event Loop with Sentence-Transformers
**What goes wrong:** `model.encode(text)` is a synchronous, CPU-bound call. Calling it directly in an async function blocks uvicorn's event loop for 100–500ms per call.
**Why it happens:** Forgetting that sentence-transformers does not have an async API.
**How to avoid:** Always wrap in `await asyncio.to_thread(lambda: model.encode(text))`.
**Warning signs:** API response times spike during pipeline processing; uvicorn logs show slow request cycles.

### Pitfall 2: Job Claim Race Condition Without SKIP LOCKED
**What goes wrong:** Two workers claim the same job; duplicate derived records written.
**Why it happens:** Using `SELECT … WHERE status='pending' LIMIT 1` followed by `UPDATE status='claimed'` as two separate statements.
**How to avoid:** Single statement with `.with_for_update(skip_locked=True)` — the lock and claim happen atomically.
**Warning signs:** Duplicate `summary` or `fact` rows for the same `raw_archive_id`.

### Pitfall 3: Stale In-Progress Jobs After Restart
**What goes wrong:** Worker crashes mid-job; job stays in `claimed` forever; never retried.
**Why it happens:** No recovery logic on worker startup.
**How to avoid:** On worker startup, execute: `UPDATE jobs SET status='pending', attempts=attempts-1 WHERE status='claimed' AND claimed_at < now() - interval '10 minutes'`. Run this before starting the poll loop.
**Warning signs:** Jobs stuck in `claimed` status visible in DB after restart.

### Pitfall 4: Sensitivity Gate Not Recording Decision
**What goes wrong:** Gate blocks a job but no audit trail; user cannot understand why content wasn't processed.
**Why it happens:** Gate just returns block/allow without persisting the decision.
**How to avoid:** Write gate decision (category, confidence, blocked=true/false) to `operation_metadata` in `audit_events` table. Required for PRIV-04/PRIV-05 compliance.

### Pitfall 5: Missing source_status on Derived Tables
**What goes wrong:** Phase 4 cascade deletion cannot suppress derived data because the column doesn't exist.
**Why it happens:** Omitting `source_status source_status NOT NULL DEFAULT 'active'` on a derived table.
**How to avoid:** The cascade contract in migration 0001 comment is explicit: "Every future derived table MUST include source_status ENUM('active','source_removed')." Enforce in code review.
**Warning signs:** Alembic migration passes but Phase 4 cascade queries fail.

### Pitfall 6: empty source_span Treated as Valid
**What goes wrong:** Facts written with empty `source_span` slip into the search index as `high` or `medium` confidence.
**Why it happens:** LLM may not always return a span; code writes an empty string.
**How to avoid:** Validate in the service layer: if `source_span` is empty/null, force `confidence_tier = "low"`. Do NOT write to search index until span is populated or explicitly `low` confidence.

### Pitfall 7: pgvector Extension Already Created — Don't Re-Create
**What goes wrong:** Migration 0002 tries to `CREATE EXTENSION vector` — fails because 0001 already created it.
**Why it happens:** Copy-pasting migration boilerplate.
**How to avoid:** Migration 0001 already runs `CREATE EXTENSION IF NOT EXISTS vector`. Migration 0002 only needs `CREATE TABLE embeddings` — no extension step needed.

### Pitfall 8: pending_provider vs. retryable_failed Confusion
**What goes wrong:** Missing-provider jobs counted as failures; user sees red badge when no key is configured.
**Why it happens:** Treating all non-completion outcomes as `failed`.
**How to avoid:** Two distinct states: `pending_provider` (blocked on missing key — amber badge, not a failure) vs. `retryable_failed` (API error, wrong key — red badge, auto-retry). The jobs query in the worker must include `retryable_failed` as eligible for retry, but NOT `pending_provider` (those wait for a key configuration event).

### Pitfall 9: Forgetting to Reload pending_provider Jobs When Key Configured
**What goes wrong:** User adds an API key; `pending_provider` jobs stay blocked forever.
**Why it happens:** No mechanism to re-activate them.
**How to avoid:** In the settings route that saves a new key, also run: `UPDATE jobs SET status='pending' WHERE status='pending_provider'`. This re-queues them for the next worker poll cycle.

---

## Code Examples

### Fact Extraction Prompt Pattern (with Source Span)

```python
FACT_EXTRACTION_SYSTEM_PROMPT = """
You are a fact extraction engine. Extract factual statements from the conversation.

For each fact:
1. Write the fact as a single declarative sentence (fact_text)
2. Copy the EXACT quote from the source that supports this fact (source_span)
3. Assign confidence: "high" (explicit statement), "medium" (implied), "low" (uncertain)

Return JSON array:
[
  {
    "fact_text": "User's name is Alice.",
    "source_span": "My name is Alice",
    "confidence_tier": "high"
  }
]

Return [] if no facts can be extracted with a source span.
"""
```

> OpenAI: use `response_format={"type": "json_object"}` and wrap array in `{"facts": [...]}`.
> Anthropic: parse JSON from `response.content[0].text`; no native JSON mode in all models.

### Conflict Detection Pattern (CANM-06)

```python
# After embedding is written, check for near-duplicates using cosine similarity.
# Uses pgvector operator <=> (cosine distance; 0=identical, 2=opposite).
# Threshold: distance < 0.15 (cosine similarity > 0.85) → candidate duplicate.

DUPLICATE_DISTANCE_THRESHOLD = 0.15

async def find_duplicate_candidates(
    session: AsyncSession, embedding: list[float], exclude_id: uuid.UUID
) -> list[uuid.UUID]:
    result = await session.execute(
        text("""
            SELECT id, embedding <=> :vec AS distance
            FROM embeddings
            WHERE id != :exclude_id
              AND source_status = 'active'
              AND embedding <=> :vec < :threshold
            ORDER BY distance
            LIMIT 10
        """),
        {"vec": str(embedding), "exclude_id": str(exclude_id), "threshold": DUPLICATE_DISTANCE_THRESHOLD}
    )
    return [row.id for row in result.fetchall()]
```

### Job Status → Frontend Badge Mapping

| Job status | Badge variant | Badge text | Icon |
|------------|--------------|------------|------|
| `pending` | `warning` | `Processing` | spinner |
| `claimed` | `warning` | `Processing` | spinner |
| `completed` | `success` | `Done` | checkmark |
| `failed` | `destructive` | `Failed` | x-circle + retry button |
| `retryable_failed` | `destructive` | `Failed` | x-circle + retry button |
| `pending_provider` | `warning` | `Pending Provider` | amber + tooltip |

> Badge variants `success`, `warning`, `destructive` already exist in `frontend/src/components/ui/badge.tsx`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Celery + Redis for background tasks | PostgreSQL-backed async job queue | v1 design decision | No extra broker; simpler Docker Compose |
| `asyncio.run_in_executor(None, fn)` | `asyncio.to_thread(fn)` | Python 3.9+ | Cleaner API; same underlying ThreadPoolExecutor |
| pgvector `ivfflat` index | pgvector `hnsw` index | pgvector 0.5.0 (2023) | HNSW is now preferred; better recall, no training phase needed |
| OpenAI `text-davinci` for extraction | `gpt-4o-mini` | 2024 | Much cheaper; JSON mode available |
| Sentence-transformers `from_pretrained()` | `SentenceTransformer("model-name")` | v3+ | Same API; v5.x adds `normalize_embeddings` kwarg to `encode()` |

**Deprecated/outdated in this project:**
- `asyncio.ensure_future()`: replaced by `asyncio.create_task()` (Python 3.7+, prefer `create_task`)
- pgvector `IVFFlat` index: still works but HNSW is preferred for new projects (no training phase)

---

## Open Questions

1. **Which Ollama model name to default to for summarization/extraction?**
   - What we know: Ollama model names are user-configured (e.g. `llama3.2`, `mistral`); the `ollama_base_url` is stored but no `ollama_model` column exists in settings.
   - What's unclear: Does Phase 2 need to add an `ollama_model` settings field, or just document that user must set it in `.env`?
   - Recommendation: Add `OLLAMA_MODEL` env var (read via `get_settings()`); default `"llama3.2"`. Keep the schema change minimal — no new DB column needed, just a new `pydantic-settings` field.

2. **Conflict detection granularity: fact-level or archive-level?**
   - What we know: CANM-06 says "flags contradictory facts across sources"; architecture says `conflict_groups` table links fact IDs.
   - What's unclear: Should the worker compare new facts against ALL existing facts (expensive) or just facts from the same date range?
   - Recommendation: For v1 personal scale, compare all active facts. The dataset will be small; full scan with pgvector ANN is fast enough. Add a date filter as an optimization in Phase 3 if needed.

3. **`pending_provider` activation trigger: pull vs. push?**
   - What we know: CONTEXT.md says `pending_provider` is retryable when user adds a key.
   - Recommendation: Push model — settings route that validates/saves a key runs `UPDATE jobs SET status='pending' WHERE status='pending_provider'` in the same transaction. Cleaner than polling for this edge case.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 1.3.0 |
| Config file | `backend/pyproject.toml` → `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && pytest tests/ -x -q` |
| Full suite command | `cd backend && pytest tests/ -v` |

> `asyncio_mode = "auto"` is already set — all async test functions work without `@pytest.mark.asyncio`.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | Job claimed and status transitions to completed after pipeline | integration | `pytest tests/worker/test_loop.py -x` | ❌ Wave 0 |
| PIPE-02 | Fact written with source_span, confidence_tier, derivation_method, derivation_model | unit | `pytest tests/domain/test_derived_memory.py::test_fact_requires_source_span -x` | ❌ Wave 0 |
| PIPE-03 | Sensitivity gate blocks personal_profile content before external call | unit | `pytest tests/domain/test_policy_gate.py::test_personal_profile_blocked -x` | ❌ Wave 0 |
| PIPE-04 | Job retried on retryable_failed; terminal fail after max_attempts | unit | `pytest tests/domain/test_jobs_service.py::test_retry_logic -x` | ❌ Wave 0 |
| PIPE-05 | Job reset to pending via reprocess endpoint | integration | `pytest tests/api/test_reprocess.py -x` | ❌ Wave 0 |
| PRIV-04 | personal_profile → external provider call not made | unit | `pytest tests/domain/test_policy_gate.py::test_no_external_call_for_sensitive -x` | ❌ Wave 0 |
| PRIV-05 | unclassified → external provider call not made | unit | `pytest tests/domain/test_policy_gate.py::test_unclassified_blocked -x` | ❌ Wave 0 |
| BYOK-07 | Invalid key → retryable_failed with error_message | unit | `pytest tests/worker/test_dispatcher.py::test_invalid_key_retryable_failed -x` | ❌ Wave 0 |
| BYOK-08 | Switching provider does not re-run completed sub-jobs | unit | `pytest tests/worker/test_dispatcher.py::test_completed_subjob_not_rerun -x` | ❌ Wave 0 |
| CANM-06 | Duplicate facts grouped in conflict_groups | unit | `pytest tests/domain/test_conflict_detection.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/ -x -q`
- **Per wave merge:** `cd backend && pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps (all test files must be created)
- [ ] `backend/tests/worker/test_loop.py` — covers PIPE-01, PIPE-04
- [ ] `backend/tests/worker/test_dispatcher.py` — covers BYOK-07, BYOK-08
- [ ] `backend/tests/domain/test_derived_memory.py` — covers PIPE-02
- [ ] `backend/tests/domain/test_policy_gate.py` — covers PIPE-03, PRIV-04, PRIV-05
- [ ] `backend/tests/domain/test_jobs_service.py` — covers PIPE-04, PIPE-05
- [ ] `backend/tests/domain/test_conflict_detection.py` — covers CANM-06
- [ ] `backend/tests/api/test_reprocess.py` — covers PIPE-05
- [ ] `backend/tests/conftest.py` — async session fixtures (already exists for Phase 1; extend for derived_memory)

---

## Sources

### Primary (HIGH confidence)
- SQLAlchemy 2.x docs — `Select.with_for_update(skip_locked=True)` confirmed in ORM query guide
- Python 3.12 asyncio docs — `asyncio.to_thread()`, `asyncio.create_task()`, `asyncio.Semaphore` API confirmed
- pgvector-python GitHub README — `Vector(384)` column type, HNSW index syntax confirmed
- `backend/alembic/versions/0001_initial.py` — cascade contract, existing indexes, ENUM definition confirmed by direct read
- `backend/app/domain/jobs/models.py` — Job ORM fields confirmed by direct read
- `backend/pyproject.toml` — all dependency versions confirmed by direct read
- sentence-transformers PyPI page — v5.3.0 `SentenceTransformer.encode()` API, `CrossEncoder.predict()` API

### Secondary (MEDIUM confidence)
- Ollama OpenAI compatibility: confirmed via settings/service.py existing validation code (`/api/version` endpoint used) + architecture decision docs; `/v1` path inferred from OpenAI compat docs
- OpenAI `response_format={"type":"json_object"}`: confirmed in openai-python SDK docs; global pip has v2.8.1 but project pins <2; API shape is same for `chat.completions.create()`
- Anthropic messages API: confirmed via settings/service.py (`anthropic-version: 2023-06-01` header used); response structure from SDK docs

### Tertiary (LOW confidence)
- CrossEncoder NLI score column index (index 2 = entailment): standard NLI label order for MiniLM2 models; verify with a quick test at implementation time
- DUPLICATE_DISTANCE_THRESHOLD = 0.15: rule-of-thumb for all-MiniLM-L6-v2 cosine distance; tune empirically

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already in pyproject.toml; pgvector is the only addition
- Architecture: HIGH — CONTEXT.md decisions are locked; schema derived from existing migration contract
- Pitfalls: HIGH for DB/async pitfalls (verified against code); MEDIUM for ML threshold values (empirical)

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable stack; no fast-moving deps)
