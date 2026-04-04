# Pitfalls Research

**Domain:** Local-first MCP-native personal memory / AI conversation archive platform
**Researched:** 2026-03-22
**Confidence:** HIGH (verified against official pgvector docs, MCP spec, Docker docs, and project requirements)

---

## Critical Pitfalls

### Pitfall 1: Deletion Does Not Actually Delete — Derived Data Orphaned

**What goes wrong:**
Raw source is deleted or redacted by the user. The system marks the raw item gone but leaves summaries, facts, embeddings, and FTS index entries in place. Future semantic searches silently return content derived from deleted material. Worse, backup/export runs capture the orphaned derived data even though the raw source was "deleted." The user believes their data is gone. It is not.

**Why it happens:**
Cascade logic is treated as a secondary concern during early pipeline implementation. Each derived artifact (summary → facts → embeddings → tsvector entry) is implemented independently and the team adds cross-artifact DELETE propagation as an afterthought. Soft-delete flags exist on the raw table but derived tables were not designed with a `source_removed` marker from the start.

**How to avoid:**
- Design the schema **from day one** with a `source_status` foreign-key or inherited flag propagated to every derived table (`summaries`, `facts`, `embeddings`, `fts_entries`).
- Implement cascade suppression as a **database-level trigger or transactional stored procedure**, not application-level code, so it cannot be skipped.
- Add a nightly integrity check that finds any row in derived tables whose source `raw_item_id` has `deleted=true` but the derived row is not `source_removed=true`.
- Make the backup/export pipeline filter on `source_removed != true` **at query time**, not by trusting application state.
- Write a test: delete a raw item, run a semantic search for its contents, assert zero results.

**Warning signs:**
- Deletion UI reports success but semantic search still surfaces the deleted content.
- Export ZIP contains summaries referencing a raw item that no longer appears in the archive view.
- `SELECT COUNT(*) FROM facts WHERE raw_item_id IN (SELECT id FROM raw_items WHERE deleted=true) AND source_removed=false` returns > 0.

**Phase to address:** Core pipeline / schema design phase (before any UI work)

---

### Pitfall 2: In-Process Async Worker Blocks the FastAPI Event Loop

**What goes wrong:**
The in-process worker loop (asyncio task) performs CPU-intensive work — sentence-transformer inference, LLM API calls — directly on the asyncio event loop. This starves FastAPI's request handlers. Ingest acknowledgement latency (P95 ≤ 1s) blows out. Health checks time out. The MCP `retrieve` tool hangs mid-session because the event loop is occupied by a summarization call.

**Why it happens:**
`asyncio.create_task()` feels like background processing but it shares the single-threaded event loop. CPU-bound operations (embedding generation via sentence-transformers) block all coroutines. Even I/O-bound provider API calls are problematic if they use a synchronous HTTP client (e.g., `requests`) not wrapped with `asyncio.to_thread`.

**How to avoid:**
- Run all CPU-bound work (sentence-transformer inference) with `asyncio.to_thread()` or `loop.run_in_executor(executor)` using a `ThreadPoolExecutor`.
- Use `httpx.AsyncClient` (already available via FastAPI ecosystem) for all provider API calls — never `requests`.
- Cap the worker's concurrency: use `asyncio.Semaphore` to limit simultaneous pipeline jobs so the loop has headroom for foreground requests.
- Instrument the event loop lag with `asyncio` debug mode during development (`PYTHONASYNCIODEBUG=1`) to detect blocked coroutines before they appear in production.
- Write a concurrent load test: submit 3 parallel ingests while the pipeline is processing a batch and assert P95 acknowledgement < 1s.

**Warning signs:**
- Ingestion acknowledgement times spike when any background processing is active.
- MCP tool calls time out intermittently.
- `asyncio` debug log shows coroutines taking > 100ms per step.

**Phase to address:** Async pipeline phase (foundational; before pipeline job types are added)

---

### Pitfall 3: pgvector HNSW Index Not Built or Built Empty — Approximate Search Returns Wrong Results

**What goes wrong:**
The HNSW index is created **before** data is loaded (or on an empty table), IVFFlat lists are set too low for the actual dataset size, or the index is never created at all. Semantic search falls back to exact sequential scan (fine for < 1k items, slow and inconsistent at 10k+). Alternatively, the HNSW index exists but `hnsw.ef_search` is left at the default of 40, causing the index to return fewer results than requested when WHERE-clause filtering is applied — a silent precision loss that is invisible unless recall is measured.

**Why it happens:**
- Developers test with small datasets where exact scan works fine; the performance/correctness gap appears only in production.
- pgvector's HNSW documentation states that indexes should be built **after** initial data is loaded, but this requirement is easy to miss.
- Filtered queries silently degrade: with `hnsw.ef_search=40` and a WHERE clause matching 10% of rows, only ~4 rows are candidates on average.

**How to avoid:**
- Create the HNSW index **after** initial bulk import, not in the schema migration that runs on empty DB.
- Use `CREATE INDEX CONCURRENTLY` in production to avoid write locks.
- For the RRF hybrid retrieval (top-50 semantic candidates), set `hnsw.ef_search` to at least 100 to ensure enough candidates survive post-index filtering.
- Enable pgvector's iterative index scan (`SET hnsw.iterative_scan = strict_order`) for filtered queries — available in pgvector 0.8.0+.
- Add a recall monitoring query to the health-check suite: compare approximate results against exact results weekly.
- Ensure `shared_buffers` is set to ~25% of container memory in PostgreSQL config — default Docker PostgreSQL has `shared_buffers=128MB`, which is disastrously low for vector workloads.

**Warning signs:**
- `SELECT COUNT(*) FROM pg_indexes WHERE tablename='embeddings' AND indexdef LIKE '%hnsw%'` returns 0.
- Semantic search queries use `Seq Scan` in `EXPLAIN ANALYZE` output.
- RRF returns fewer than 20 results on datasets with > 1000 items.
- Recall comparison (exact vs approximate) diverges by > 20%.

**Phase to address:** Search/retrieval phase; also needs a database initialization checklist enforced in migration scripts

---

### Pitfall 4: MCP Transport Bound to 0.0.0.0 — DNS Rebinding Attack Surface

**What goes wrong:**
The MCP HTTP transport endpoint (Streamable HTTP) is configured to listen on `0.0.0.0` instead of `127.0.0.1`. Any browser tab can now exploit DNS rebinding to interact with the local MCP server from a remote website. The attack surface includes: reading user memory contents, injecting false memory items, and exfiltrating API keys via the MCP settings endpoint. This is documented as an explicit security warning in the current MCP spec.

**Why it happens:**
Docker Compose port mappings (`0.0.0.0:8080:8080`) expose the container port on all interfaces by default. Developers use this for convenience without realizing the host-side binding is the security boundary, not the container's internal binding.

**How to avoid:**
- Bind the MCP HTTP endpoint to `127.0.0.1` explicitly in both the FastAPI server startup (`uvicorn --host 127.0.0.1`) and in Docker Compose port mapping (`127.0.0.1:8080:8080`).
- Validate the `Origin` header on all MCP HTTP requests per the spec requirement: reject requests where `Origin` is not `null` or a known localhost origin.
- Add a startup assertion that verifies the server socket is not bound to `0.0.0.0` in production mode.
- If the user opts into broader network exposure (future feature), enforce that authentication middleware is active before allowing non-localhost bindings — per NFR requirement.

**Warning signs:**
- `docker compose ps` shows port mapping as `0.0.0.0:8080->8080/tcp` (instead of `127.0.0.1:8080->8080/tcp`).
- MCP endpoint reachable from a different machine on the same LAN without authentication.
- No `Origin` header validation in request middleware.

**Phase to address:** MCP interface phase (security must be in-spec from day one, not added later)

---

### Pitfall 5: API Keys Stored in Database or Included in Backups

**What goes wrong:**
Provider API keys (OpenAI, Anthropic) end up in the PostgreSQL `config` table because it was convenient to store all settings in one place. The daily backup includes the full database dump — including the keys table. The backup file is stored unencrypted on a path accessible to other processes. If the backup is shared for debugging or the Docker volume is inspected, all API keys leak.

**Why it happens:**
Settings storage is implemented as a generic key-value table in PostgreSQL before the team thinks through key security. The backup script dumps the entire DB without column exclusions. `.env` files with secrets are never committed but they are included in `pg_dump` output because the keys ended up in the DB.

**How to avoid:**
- Store API keys **only** in the `.env` file / local configuration, never in any database table. The database should store only a key fingerprint or provider name (for display purposes), not the secret.
- Implement a startup-time assertion: scan all database tables for columns named `*_key`, `*_secret`, `*_token` and assert they contain only null or masked values.
- Exclude the `api_keys` config path from `pg_dump` using `--exclude-table-data` if any key-adjacent table exists.
- Document in `.env.sample` which values must never reach the database.
- Write a test: export the full backup archive and grep for known test API key values — assert they do not appear.

**Warning signs:**
- Settings page reads/writes keys from a `/api/settings` endpoint that queries PostgreSQL.
- `pg_dump` output contains any of the strings `sk-`, `ant-`, or other known provider key prefixes.
- Docker volume inspection reveals API key values in `pg_dump` backup files.

**Phase to address:** BYOK configuration phase (establish the pattern before any key storage code is written)

---

### Pitfall 6: Provenance Chain Breaks When Facts Are Edited or Promoted

**What goes wrong:**
A user edits an extracted fact to correct an error, or promotes a fact to canonical memory. The system overwrites the fact's original text with the edited text and updates the `derivation_method` field — but does not record **who made the change, when, and what the previous value was**. The provenance chain now claims a fact was derived from a source span that no longer matches the current fact content. Audits are misleading. The user cannot distinguish AI-extracted content from human-curated content.

**Why it happens:**
Provenance is designed as an immutable set of fields added at creation time. Edit operations are implemented as simple `UPDATE` statements. The audit log records the edit event but does not snapshot the previous value. The result is that "provenance" fields describe the original derivation, not the current state.

**How to avoid:**
- Use an append-only fact versioning table: every edit creates a new version row with `version_number`, `edited_by` (user or MCP client identity), `edited_at`, and `previous_version_id`. The canonical `facts` table points to the current version.
- For canonical promotion: record the promotion event in the audit log with the promoting user/agent identity and timestamp, and mark the fact's `derivation_method` as `user_canonical` (distinct from `llm_extraction` or `rule_based`).
- Expose version history in the UI's provenance drawer.
- Every NFR provenance field requirement (`source item ID`, `derivation process`, `modifying user`) must be verified by a dedicated test that edits a fact and checks all fields are populated correctly.

**Warning signs:**
- `UPDATE facts SET content=... WHERE id=...` without creating a new version row.
- No `edited_by` or `previous_value` field in the facts schema.
- Audit log shows an edit event but the fact record has no version history.

**Phase to address:** Canonical memory and review phase

---

### Pitfall 7: Docker Volume `docker compose down` Destroys Data

**What goes wrong:**
A developer or user runs `docker compose down -v` or `docker compose down --volumes` to "reset" the environment. This removes named volumes, destroying all PostgreSQL data and backups permanently. On macOS with Docker Desktop, Docker volumes are stored in a VM image that is not included in Time Machine backups. There is no recovery path.

**Why it happens:**
`docker compose down` (without `-v`) is safe, but the `-v` flag is documented as "removes volumes" and commonly used in tutorials for "full reset." Users paste commands from the internet without understanding the `-v` distinction. Docker Desktop's volume storage location is not obvious.

**How to avoid:**
- Use **bind mounts** (not named volumes) for the PostgreSQL data directory in the production Docker Compose profile: `./data/postgres:/var/lib/postgresql/data`. This puts data on the host filesystem where users understand it lives and where host-level backup tools apply.
- Document clearly in `README` and first-run UI: "Your data lives at `./data/`. Do not delete this directory."
- Add a warning comment in `docker-compose.yml` above the volume definition.
- For the backup directory, also use a bind mount at a user-visible path: `./backups:/app/backups`.
- Consider adding a `Makefile` target `reset-app` that explicitly never passes `-v` and requires confirmation.
- Note: bind mounts and named volumes have the same durability guarantee across `docker compose stop`/`start` and host reboots — the `docker compose down -v` scenario is the only exception.

**Warning signs:**
- `docker-compose.yml` uses named volumes (`volumes:` at top level) instead of bind mounts.
- No user documentation about where data physically lives on the host.
- No confirmation prompt before destructive operations.

**Phase to address:** Infrastructure / Docker Compose setup phase (must be correct from the first `docker-compose.yml` commit)

---

### Pitfall 8: Hybrid Search RRF Score Drift After Re-Embedding

**What goes wrong:**
User switches embedding providers (e.g., from `all-MiniLM-L6-v2` to OpenAI `text-embedding-3-small`). The system allows per-function provider switching without reprocessing already-completed items (per the BYOK NFR). This creates a mixed-model vector space: some items embedded with model A (384 dimensions), some with model B (1536 dimensions). pgvector's cosine distance comparisons between vectors from different models are geometrically meaningless. RRF semantic scores become nonsense. Hybrid retrieval degrades silently.

**Why it happens:**
The "no reprocessing already-completed items" requirement is implemented as "keep existing embeddings as-is when provider changes." But embedding vectors from different models live in incompatible spaces — they cannot be meaningfully compared via cosine distance.

**How to avoid:**
- Record `embedding_model` and `embedding_dimension` per embedding row in the `embeddings` table.
- When a provider switch is requested, surface a warning: "Switching providers requires re-embedding all items for comparable semantic search. You can switch now and re-embed, or keep the current provider."
- In retrieval, only use semantic search for items where `embedding_model = current_configured_model`. Items with stale embeddings surface only via FTS (keyword) in degraded mode until re-embedded.
- The "no reprocessing already-completed items" requirement should be interpreted narrowly: summaries and extracted facts from one model are compatible across models. Embeddings are NOT — they require provider-specific re-embedding.
- Add a UI indicator: "X items not yet embedded with current provider — semantic results may be incomplete."

**Warning signs:**
- `embeddings` table has no `model_name` or `model_version` column.
- Provider switch completes without any warning about search quality impact.
- Semantic search returns items from only one provider's embeddings while silently excluding the other.

**Phase to address:** BYOK provider configuration phase AND retrieval phase (both must be aware of model-per-embedding metadata)

---

### Pitfall 9: PostgreSQL-as-Job-Queue Grows Unbounded / Polling Starves

**What goes wrong:**
The processing job queue (implemented as a PostgreSQL table per the stack decision) accumulates rows indefinitely. Completed/failed jobs are never purged. The `SELECT ... FOR UPDATE SKIP LOCKED` polling loop runs at a fixed interval (e.g., every 5 seconds) regardless of queue depth. Under bulk import (100 conversations), the worker takes 20 minutes to process all jobs but the polling interval was tuned for steady-state trickle. Jobs pile up and users see no visual progress for the first N minutes.

**Why it happens:**
The job queue table design is straightforward but cleanup and adaptive polling are afterthoughts. The queue grows as a log of all work ever submitted. Completed job rows accumulate over months.

**How to avoid:**
- Implement job table cleanup: archive/delete completed jobs after N days (configurable, default 30). Keep a separate `job_stats` table for aggregate counts to preserve telemetry.
- Use **LISTEN/NOTIFY** for immediate worker wake-up on job insert, with polling as fallback. This gives near-instant pipeline start for interactive ingest without a busy polling loop.
- Set a **backpressure limit**: if the queue depth exceeds a configurable threshold (e.g., 500 pending jobs), reject new ingests with a warning rather than silently accumulating.
- Add an index on `(status, created_at)` to keep job queries fast as the table grows.
- Expose queue depth in the UI progress indicator during bulk import.

**Warning signs:**
- Job table has no `DELETE` or archival logic.
- Worker polls at a fixed interval with no `LISTEN/NOTIFY`.
- No index on job status column.
- Queue depth query takes > 100ms on a 10k-row job table.

**Phase to address:** Async pipeline phase

---

### Pitfall 10: Sensitive Content Classification Runs After External Provider Call

**What goes wrong:**
The pipeline calls OpenAI/Anthropic for summarization or extraction **before** running local sensitivity classification on the content. A conversation containing personal profile data, relationship details, or unclassified content is sent to an external provider before the user has any opportunity to block it. This violates the core NFR and destroys user trust on first discovery.

**Why it happens:**
The "happy path" of the pipeline is: receive content → call provider → store results. Sensitivity classification is added as a post-hoc filter rather than a pre-flight gate. The classification step is deprioritized because it "rarely triggers" during development testing.

**How to avoid:**
- The pipeline MUST enforce a strict gate ordering: (1) ingest raw → (2) local sensitivity classification → (3) user-declared sensitivity check → (4) ONLY THEN call external provider. Steps 1–3 must be synchronous and in-transaction with acknowledgement.
- Implement a `sensitivity_gate` service that is called before **any** job that touches an external provider. This service returns `BLOCKED`, `ALLOWED`, or `REVIEW_REQUIRED`.
- Default to `BLOCKED` for unknown/unclassified content (per NFR): unclassified content requires explicit user allow before external processing.
- Write a test: ingest a conversation with the phrase "my relationship with" and assert no external provider call is made until the user explicitly approves.

**Warning signs:**
- Pipeline job type "summarize" does not check sensitivity status before making the provider call.
- No `sensitivity_status` field on raw items or pipeline jobs.
- Classification runs asynchronously after the provider call has already been dispatched.

**Phase to address:** Processing pipeline phase (must be architecturally enforced, not bolted on)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store all settings (including key display names) in PostgreSQL | Single settings API | Risk of accidentally persisting actual key values near metadata | Never — maintain a hard rule: keys in `.env` only, never in DB |
| Use exact pgvector search (no HNSW index) during development | Simpler setup, perfect recall | Sequential scan is 10–100x slower at 10k+ items; will require index rebuild under load | Acceptable in dev only — must add index before any performance testing |
| Single monolithic pipeline job type ("process everything") | Faster initial implementation | Cannot partially retry (e.g., re-run embeddings without re-running extraction); impossible to add per-step cost tracking | Never — separate job types from the start |
| Polling loop for job queue without LISTEN/NOTIFY | Simpler implementation | Interactive ingest feels sluggish (up to N-second delay before pipeline starts) | Only if LISTEN/NOTIFY complexity is deferred to phase 2, but document the latency consequence |
| Skip embedding model version column | Slightly simpler schema | Cannot safely mix models; cannot re-embed selectively; hybrid search silently degrades on provider switch | Never — add `model_name` and `model_dim` columns from the first migration |
| Use `docker compose down -v` in dev convenience scripts | Easy environment reset | Users copy dev commands into production; data destruction | Never use `-v` in any documented command; always use a named `make reset-dev` target |
| Store audit events in application memory (not DB) | Zero write overhead | Audit log lost on container restart; 90-day retention requirement fails | Never — audit events must be persisted to the database from day one |
| Build HNSW index before initial data load | Simpler migration | IVFFlat fails entirely with too few rows; HNSW is fine but wastes build time on empty table | Build after initial data: add index creation to the post-import step, not the schema migration |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| pgvector HNSW | Using `<=>` cosine distance on non-normalized vectors | Normalize embeddings to unit length before storage, or use `l2_normalize()` at query time; or use `<->` L2 distance which does not require normalization |
| pgvector filtering | Adding a WHERE clause to HNSW queries without raising `ef_search` | Set `hnsw.ef_search ≥ 100` for filtered RRF queries; enable `hnsw.iterative_scan = strict_order` (pgvector 0.8.0+) |
| MCP Streamable HTTP | Not validating `Origin` header | Validate `Origin` on all incoming MCP HTTP requests; reject non-localhost origins |
| MCP Streamable HTTP | Binding to `0.0.0.0` in Docker Compose | Map only `127.0.0.1:port:port` in `docker-compose.yml`; set `uvicorn --host 127.0.0.1` |
| MCP protocol version | Assuming all clients speak the latest protocol | Support `MCP-Protocol-Version` header negotiation; fall back to `2025-03-26` if header absent |
| OpenAI/Anthropic BYOK | Using synchronous `requests` in async FastAPI handler | Use `httpx.AsyncClient` with `async with` context manager; never `requests` in async code |
| sentence-transformers | Running inference in asyncio event loop directly | Use `asyncio.to_thread()` — inference is CPU-bound and will block the loop |
| PostgreSQL FTS | Using `plainto_tsquery` for user input with special characters | Use `websearch_to_tsquery` which handles special chars gracefully; or sanitize input before `to_tsquery` |
| SQLAlchemy async | Using sync session methods inside async routes | Use `AsyncSession` with `await session.execute()` throughout; never mix sync and async session patterns |
| Docker volumes | Named volume removed by `docker compose down -v` | Use bind mounts at user-visible host paths for all persistent data |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Exact pgvector sequential scan (no index) | Search P95 exceeds 2s | Create HNSW index after initial data load | ~5,000 items with 384-dim vectors |
| `maintenance_work_mem` default (64MB) during HNSW build | Index build takes 10+ minutes; "graph no longer fits" notice in logs | Set `maintenance_work_mem = '512MB'` or higher in PostgreSQL config | Any HNSW build on > 10k vectors |
| `shared_buffers` default (128MB) in Docker PostgreSQL | All queries slow; high I/O | Set `shared_buffers = 256MB–1GB` (25% of container memory) via `postgresql.conf` or env | Any non-trivial dataset |
| CPU-bound embedding in asyncio event loop | Ingest P95 spikes during background processing | `asyncio.to_thread()` for all inference; `ThreadPoolExecutor` | Immediate, with any concurrent request |
| SQLAlchemy lazy-loading in async context | `MissingGreenlet` / `greenlet_spawn` errors under async session | Use `selectinload()` or `joinedload()` eagerly; never rely on lazy load in async | First attempt to access a lazy relationship under async |
| Returning full raw text in retrieval response | Context window overrun in MCP tool calls | Enforce strict priority trimming in retrieval: canonical → facts → summaries → raw excerpts (truncated) | Every retrieval call if not enforced |
| Full table scan for job queue polling | Queue polling takes > 100ms | Composite index on `(status, created_at)` on jobs table | ~10,000 accumulated job rows |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| API keys in database or backup files | Key exfiltration via backup file access or database dump | Keys only in `.env`; never in any DB table; `pg_dump` must not include key values; test assertion |
| MCP endpoint on `0.0.0.0` | DNS rebinding allows any webpage to read/write user memory | Bind to `127.0.0.1` explicitly in both Uvicorn and Docker Compose port mapping |
| No `Origin` validation on MCP HTTP | DNS rebinding attack | Validate `Origin` header; reject non-null origins not matching `localhost` |
| Sensitive content sent to external provider before classification | Privacy violation; user trust collapse | Sensitivity gate must run before any external provider job is dispatched |
| Export/backup includes deleted data | User believes data is gone when it is not | Filter `source_removed=true` at query time in all export/backup code paths |
| Audit events not persisted to DB | 90-day retention requirement fails on container restart | Audit events written to DB synchronously with the operation they record |
| Provenance fields mutable without version history | Cannot distinguish AI-extracted from user-edited content | Append-only version table for facts; `derivation_method` set to `user_canonical` on promotion |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No cost estimate before bulk import confirms | User gets unexpected $20+ provider bill on first 500-conversation import | Show token count heuristic and order-of-magnitude cost estimate before confirmation dialog |
| Invalid key silently drops jobs | User thinks processing succeeded; facts are never extracted | Show `retryable_failed` state with "invalid key" label in pipeline status; surface key re-validation prompt |
| Provenance panel shows raw JSON | Non-technical users cannot understand where a fact came from | Render provenance as "Extracted from: [conversation title] on [date] using [model]" |
| Deletion confirmation does not warn about older backups | User deletes sensitive content, exports old backup, shares it | Post-deletion message: "Older backups created before [date] may still contain this content" |
| "Processing" spinner with no progress feedback during bulk import | User cannot tell if the system is working or hung | Show per-item queue depth counter: "Processing 47 of 312 conversations" |
| First-run wizard skippable without BYOK configuration | User sets up app, tries search, gets confusing "no results" for everything that needs embeddings | Make it clear which features are available without keys and which require them — before the user skips |

---

## "Looks Done But Isn't" Checklist

- [ ] **Deletion cascade:** Fact appears deleted in UI — verify `SELECT * FROM embeddings WHERE raw_item_id = <deleted_id>` returns 0 rows with `source_removed=false`
- [ ] **Backup integrity:** Backup reports success — verify `pg_restore` completes and `SELECT COUNT(*) FROM raw_items` matches expected count in a restored environment
- [ ] **API key security:** Key configured in settings — verify `pg_dump` output does NOT contain the key string; verify `.env` file contains it
- [ ] **MCP binding:** MCP server running — verify `curl http://0.0.0.0:8080/mcp` fails from a different host on the same LAN
- [ ] **Sensitivity gate:** Conversation with "my relationship with X" ingested — verify no external provider call is logged until user approval
- [ ] **HNSW index active:** 1000 items indexed — verify `EXPLAIN ANALYZE SELECT... ORDER BY embedding <=> ... LIMIT 20` shows `Index Scan` not `Seq Scan`
- [ ] **Provenance on canonical facts:** User edits a fact — verify audit log shows `user_canonical` derivation method AND previous value AND editor identity
- [ ] **RRF recall adequacy:** Run hybrid search for known content — verify semantic candidates include the target item (recall check against exact search)
- [ ] **Degraded mode:** Provider API key removed — verify keyword search still works and semantic results degrade gracefully (no error, just stale/empty semantic component)
- [ ] **Event loop health:** Submit 3 concurrent ingests while pipeline processes 50 items — verify P95 acknowledgement < 1s

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Deletion cascade failure (orphaned derived data) | HIGH | Audit all derived tables against raw_items; batch-update `source_removed=true`; rebuild FTS index; regenerate backup post-cleanup |
| In-process worker blocks event loop (deployed) | MEDIUM | Add `asyncio.to_thread()` wrapping around all inference; deploy; no data migration required |
| HNSW index missing or built empty | LOW | `CREATE INDEX CONCURRENTLY ... USING hnsw ...` on live table; runs online without locking writes |
| API keys found in database | HIGH | Rotate all affected keys immediately via provider dashboard; audit access logs; purge from DB; add assertion tests |
| Mixed embedding models in production (provider switch without re-embedding) | MEDIUM | Add `model_name` column to `embeddings`; filter semantic search to current model; trigger re-embedding background job for stale items |
| Docker volume destroyed (`-v` flag) | VERY HIGH | Restore from most recent backup file (if backups were on bind mount, not destroyed volume); if backup also lost: no recovery |
| Sensitive content sent to provider without gate | HIGH | Audit provider API call logs for affected content; notify user; implement gate as hotfix; no automated way to "un-send" content |
| PostgreSQL `shared_buffers` default (perf) | LOW | Update `postgresql.conf` or `POSTGRES_INITDB_ARGS`; restart postgres container; no data migration |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Deletion does not delete derived data | Core schema / pipeline design | Integration test: delete raw item, assert all derived tables show `source_removed=true` |
| In-process worker blocks event loop | Async pipeline foundation | Load test: 3 concurrent ingests during background processing; P95 < 1s |
| pgvector HNSW index empty or misconfigured | Search/retrieval phase | EXPLAIN ANALYZE shows Index Scan; recall test passes |
| MCP endpoint DNS rebinding | MCP interface phase | Network test: endpoint unreachable from non-localhost; Origin validation enforced |
| API keys in database or backups | BYOK configuration phase | pg_dump grep test: zero key string matches; `.env.sample` maintained |
| Provenance chain breaks on edit/promotion | Canonical memory phase | Edit a fact, verify version history row and audit event exist |
| Docker volume destroyed by `-v` flag | Infrastructure / Docker Compose setup | Use bind mounts; document clearly; `make reset-dev` never uses `-v` |
| RRF score drift from mixed embedding models | Retrieval + BYOK phase | Provider switch test: assert stale embeddings excluded from semantic scoring |
| PostgreSQL job queue unbounded growth | Async pipeline phase | Job cleanup runs; queue depth bounded; LISTEN/NOTIFY active |
| Sensitive content sent before classification | Processing pipeline phase | Sensitivity gate test: no external call before gate passes |

---

## Sources

- pgvector README and HNSW documentation — https://github.com/pgvector/pgvector (HIGH confidence; official source, verified March 2026)
- MCP Specification — Transports (Streamable HTTP, security warnings) — https://modelcontextprotocol.io/docs/concepts/transports (HIGH confidence; official spec, current)
- MCP Specification — Pagination — https://modelcontextprotocol.io/specification/2025-03-26/server/utilities/pagination (HIGH confidence; official spec)
- Docker Volumes documentation — https://docs.docker.com/engine/storage/volumes/ (HIGH confidence; official Docker docs)
- Project requirements — `/home/andrey/projects/recalium/docs/requirements/nfr.md` (HIGH confidence; canonical project spec)
- Project risk register — `/home/andrey/projects/recalium/docs/requirements/assumptions-and-risks.md` (HIGH confidence; canonical project spec)
- Project scope — `/home/andrey/projects/recalium/.planning/PROJECT.md` (HIGH confidence; canonical project scope)
- SQLAlchemy async patterns — training data + official SQLAlchemy 2.x async docs (MEDIUM confidence; patterns well-established in 2.x docs)
- asyncio event loop blocking patterns — training data (MEDIUM confidence; well-documented Python limitation)

---

*Pitfalls research for: local-first MCP-native personal memory / AI conversation archive platform (Recalium)*
*Researched: 2026-03-22*
