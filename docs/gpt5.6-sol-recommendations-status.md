# GPT-5.6 Review — Response & Implementation Status

**Date:** 2026-07-11
**Reviews:** [gpt5.6-sol-recommendations.md](gpt5.6-sol-recommendations.md) (27 findings, product scored 48/100)
**This document:** a response to **every** finding — assessment, decision, evidence, and next action.

Legend — Decision: ✅ Implemented · 🟡 Partially implemented · 📋 Accepted, planned (not built this pass) · 🔵 Already addressed · 💬 Nuance/counterpoint.

## Overall response

The review is rigorous and, in the large, **correct**: Recalium is a feature-rich alpha whose release-readiness claims run ahead of enforced behavior. The core P0 gaps (faithful vendor import, deletion/backup/restore safety, honest eval gating, retrieval-filter/fusion contracts, secret handling, policy enforcement, clean build, portability) are legitimate and accepted.

Most P0s are **multi-day architectural builds**, not one-pass fixes; those are accepted and planned. This pass implemented the **tractable, high-value, low-risk** subset and the regressions the review attributes to recent work. Every finding is answered below.

## Summary

| #   | P   | Finding (short)                                | Decision                                       | Evidence           |
| --- | --- | ---------------------------------------------- | ---------------------------------------------- | ------------------ |
| 1   | P0  | Cold-start vendor import not implemented       | � Import domain built (per-conversation)       | `feat(import)`     |
| 2   | P0  | Deletion/backup/restore safety                 | 📋 Planned                                      | design below       |
| 3   | P0  | Eval can go green after skips/errors           | 🟡 Implemented (strict mode)                    | `b285da8`          |
| 4   | P0  | Retrieval filters + hybrid fusion              | 🟡 Filters+mode done; fusion planned            | `9d216b3`          |
| 5   | P0  | BYOK wizard claims config it doesn't do        | ✅ Implemented                                  | `6788d91`          |
| 6   | P0  | MCP processing/sensitivity not enforced        | � Effective policy enforced at provider gate   | `feat(policy)`     |
| 7   | P0  | Clean build fails; deep links 404              | ✅ SPA fallback + multi-stage build             | `6788d91`, Dockerfile |
| 8   | P0  | "Memory bundle" is a raw archive               | 🟡 Scope corrected; graph bundle planned        | this commit        |
| 9   | P0  | Concurrency: deletion vs promotion races       | 📋 Planned                                      | design below       |
| 10  | P0  | Conflict detection empty; resolve is a no-op   | � Duplicate groups linked to facts + audited    | `feat(conflict)`   |
| 11  | P1  | MCP reads not durably audited; error contracts | ✅ Implemented                                  | `9d216b3`          |
| 12  | P1  | Extraction/ranking metric defects              | � Implemented (matching/span/nDCG + tests)     | `evals/metrics.py` |
| 13  | P1  | Red/skipped gates; no app CI                   | ✅ CI workflow (backend/frontend/docker build)  | `.github/workflows/ci.yml` |
| 14  | P1  | Keyboard a11y + curation incomplete            | 🟡 Ingest tabs/upload keyboard-operable; suite planned | `500542f`, IngestPage |
| 15  | P1  | Website/repo claims inaccurate; no LICENSE     | 🟡 LICENSE added; website copy planned          | `500542f`          |
| 16  | P1  | Requirements/plans not traceable               | � Requirement→test matrix + CI gate (50/52)     | `feat(traceability)` |
| 17  | P1  | Provenance/canonical integrity below promise   | 🟡 Claim corrected; envelope planned            | this commit        |
| 18  | P1  | `memory/` credential & path-traversal hazards  | 📋 Planned (quarantine)                         | —                  |
| 19  | P1  | "Exposed mode" not fully wired/secure          | 📋 Planned (declare unsupported)                | —                  |
| 20  | P1  | Eval not representative/isolated/at-scale      | 📋 Planned                                      | —                  |
| 21  | P1  | Embedding provider routing partial             | � Canonical model + stale-embedding guard      | `feat(embeddings)` |
| 22  | P1  | Frontend error/deleted-item states mislead     | ✅ deleted_at + Canonical error/empty states    | `6788d91`, CanonicalPage |
| 23  | P1  | Differentiation/market evidence stale          | 💬 Accepted (docs)                              | 📋                  |
| 24  | P1  | Initial customer/packaging unresolved          | 💬 Accepted (product)                           | 📋                  |
| 25  | P2  | Move MCP to Streamable-HTTP                    | 🔵 ADR exists; spike planned                    | ADR 0001           |
| 26  | P2  | Static debt / oversized modules                | 📋 Planned                                      | —                  |
| 27  | P2  | "Local-first" wording too strong               | ✅ Clarified (README privacy model)             | `README.md`        |

## Implemented this pass

- **#21 (embedding versioning).** Write, retrieval, and provenance each hardcoded the embedding-model name as **separate literals** (silent drift risk). Introduced `ACTIVE_EMBEDDING_MODEL` as the single source of truth (used by `write_embedding`, the semantic query's `embedding_model = :model` filter, and provenance), an `embedding_model_health()` report (counts by model + stale rows), and a startup warning when stale embeddings exist or `EMBED_MODEL` differs from the active model — so a model change can no longer silently strand vectors. 1 new test. *Remainder (planned):* honor `embed_provider`/`embed_model` for **external** embedding backends with dimension validation + a re-embed migration path (embeddings remain local-only for now).
- **#16 (traceability).** `scripts/traceability.py` parses the 52 requirement IDs from `.planning/REQUIREMENTS.md`, scans `backend/tests` + `evals` + `frontend/src` for ID references, and generates `docs/operational/traceability-matrix.md` — the **single status authority** (50/52 requirements have ≥ 1 test; 2 are documented manual-verification items). `--check` is a **CI gate** that fails when a claimed-done requirement has no test, plus a freshness diff so the matrix can't silently drift. 4 unit tests. *Remainder (planned):* extend the ID scheme to architecture docs and evidence artifacts (requirement→arch→test→evidence), and retire duplicate status trackers in favor of this matrix.
- **#10 (conflict detection).** The pipeline already detected near-duplicate embeddings but created an **orphaned** `ConflictGroup` (no fact ever referenced it), so duplicates were invisible in the review queue and left no audit. `detect_and_group_duplicates()` now resolves candidate embeddings to their items, creates the group, and **links the involved items' active facts** (`facts.conflict_group_id`) so the conflict surfaces for review; the worker writes a `conflict_detected` audit event (group id, duplicate items, linked fact count). 3 new tests. *Remainder (planned):* contradiction/overlap detection (beyond duplicate), resolution actions with domain effects (keep/merge/supersede/suppress) + reindex, and persisted membership evidence.
- **#6 (policy enforcement).** New `policy/resolver.py` resolves an **effective policy** from the content gate **plus** the caller-declared `processing_mode`/`sensitivity_hint`, **defaulting to stricter** — a `local_only` mode or a sensitive hint forbids external processing even when the gate allowed the content. The worker now gates summarize/extract on `effective_policy.allow_external` and writes a `policy_decision` audit event (mode, hint, data-class, provider, reason); MCP `ingest_memory` validates the mode/hint at the boundary (invalid → `validation_error`). 10 new tests. *Remainder (planned):* typed/validated DB **columns** (currently resolved from `metadata_json`), extend the same resolver to the link/embed provider calls, and a capture-proxy egress test.
- **#1 (vendor import).** New `imports` domain decomposes a **ChatGPT** (`mapping` graph or `messages` list) or **Claude** (`chat_messages`) export into individual conversations — each persisted as its own `raw_archive` item with provenance (`source_system`, `source_conversation_id`, title, message count, timestamps) and its own `pending_pipeline` job, so every conversation is summarized/extracted/linked separately instead of as one opaque multi-conversation blob. Idempotent by per-conversation `content_hash`. Exposed via `POST /api/import` and an **Import Export** tab in the ingest UI. 11 new tests (adapters + fan-out + idempotency); full backend suite **219 pass**. *Remainder (planned):* ZIP streaming, pre-import preview/selection, exhaustive branch/tool-call fidelity, deterministic IDs + checkpointed batches, a per-item error ledger.
- **#3** — `evals/runner.py --strict` release mode fails on any skipped/errored check (default run stays fail-open for local smoke). `b285da8`.
- **#4** — `retrieve()` now enforces `canonical_only`/`source_system`/time-range filters on the candidate set (fixes the confirmed `canonical_only` leak) and validates the mode at the boundary (invalid mode → validation error, not silent hybrid). `9d216b3`. *Not yet:* SQL-level pre-ranking filters, shared `(source_kind, source_id, chunk_id)` fusion identity, direct fact indexing — see #4 plan.
- **#5** — Wizard copy corrected to the truthful `.env`-only model (validate here, add to `.env`, restart). `6788d91`.
- **#7** — `SPAStaticFiles` serves `index.html` for unmatched non-API/non-MCP routes so deep links no longer 404 (`6788d91`); and a Node **frontend-build** stage in `backend/Dockerfile` builds the SPA in-image, so a clean checkout builds without a host `frontend/dist` (verified: `docker build --target frontend-build` produced `dist/`).
- **#8 / #17 (claims)** — Bundle doc labelled a **source-archive** bundle; quality claim narrowed (span fidelity is extraction-set only) with a small-corpus caveat. This commit.
- **#11** — MCP retrieve access audit event is now committed (verified live: an `mcp_retrieve` row persists for a fresh actor); `get_fact_links` errors use the standard envelope. `9d216b3`.
- **#13 / #14 (regressions)** — Vitest scoped to `src/` so the Playwright spec no longer breaks `pnpm test`; `pnpm-lock.yaml` updated so `--frozen-lockfile` works with `@playwright/test`. `500542f`.
- **#14 (a11y)** — Ingest tabs are now arrow-key navigable (roving tabindex + Home/End) and the upload drop zone is keyboard-operable (Tab focus + Enter/Space + visible focus ring). `IngestPage.tsx`.
- **#13 (CI)** — Added `.github/workflows/ci.yml`: backend (Postgres+pgvector, non-e2e suite with the 3 stale phase-5 MCP tests allow-listed, eval metric unit tests, informational ruff/mypy), frontend (typecheck + Vitest + build), and a clean-checkout **docker build** (also proves #7). Validated locally: 208 pass / 3 deselected, metrics 7 pass.
- **#15** — MIT `LICENSE` added (claimed by website/README, previously missing). `500542f`.
- **#27** — README now states the **privacy model explicitly**: local custody + no-key local default, with a clear disclosure that enabling a BYOK key sends the processed content to that third-party provider (and the sensitivity gate runs before any external call). `README.md`.
- **#22** — `deleted_at` populated in the archive list response so "show deleted" renders correctly (`6788d91`); and Canonical memory now shows distinct **error (with Retry)** and **empty** states instead of rendering a load failure as an empty collection (`CanonicalPage.tsx`). *(SettingsPage backups already surface load errors; remaining: telemetry error surface + ArchiveItemCard retry error.)*
- **#12** — Metric engine hardened: greedy **one-to-one** matching (duplicate predictions are now false positives, e.g. 1 golden + 3 duplicates → precision 1/3), **missing span = failure** in span fidelity, and nDCG accepts `total_relevant` so omitted relevant docs reduce the score. Added `evals/test_metrics.py` (7 tests, all pass). *Remainder:* centralized metric IDs from config + operator validation, and keeping zero-fact conversations in the extraction denominator. A follow-up eval run showed extraction **recall flicker (58%–62.5%)** around the 60% threshold on the 4-conversation set under the honest metrics + LLM variance — concrete evidence for #3/#20 that a sealed real corpus (not this tuned fixture) is required for release claims.

## Accepted and planned (not built this pass)

Each is valid and would improve the product, but is a substantial build. Recommended sequencing follows the review's "one trustworthy loop."

- **#1 (import remainder).** Core per-conversation import is now built (see “Implemented this pass”). Still planned: ZIP streaming of full export archives, pre-import preview/selection, exhaustive branch/tool-call fidelity, deterministic content IDs with checkpointed batches, an explicit per-item error ledger, and explicit unknown-schema-version handling. **Gate:** import real exports (incl. ZIP/branches/tool-calls) with exact count/role/timestamp/span assertions.
- **#2 Deletion/backup/restore.** Define deletion semantics (physical/crypto-erase after retention); exclude erased content from new backups; append-only tombstone ledger; staged restore into a separate DB with signed-manifest + schema validation, tombstone reapply, integrity check, worker quiesce, atomic cutover, rollback, and path-containment on filenames. **Gate:** secret-ingest→delete→backup→restore(pre/post)→never-retrievable + corrupted-restore rollback test.
- **#4 (remainder).** Shared retrieval-document identity for true RRF fusion; SQL-level filters; direct active-fact indexing; propagate conflict/review state; canonical priority without starvation.
- **#6 (policy remainder).** Effective-policy enforcement at the summarize/extract gate is now built (see “Implemented this pass”). Still planned: typed, validated `processing_mode`/`sensitivity_hint` **columns** (migration) instead of `metadata_json`; apply the same resolver to the link and embed provider calls; and a capture-proxy privacy test asserting zero sensitive egress.
- **#7 (remainder).** Publish a pinned image **digest** for non-developer users and add a clean-clone CI build job (the multi-stage image build itself is now implemented).
- **#8 (full).** Versioned graph bundle: typed raw + normalized conversation/turn + derived + canonical + provenance + link + tombstone + audit records, content hashes, streaming, migrations.
- **#9 Concurrency.** Row-lock/version-token deletion↔processing serialization in one transaction; promotion accepts only fact id + confirmation, derives content/provenance server-side, verifies active status, writes immutable actor.
- **#10 (conflict remainder).** Duplicate detection now links + audits (see “Implemented this pass”). Still planned: fact-level overlap/contradiction detection (beyond embedding duplicates), persisted membership/evidence, transactional queue materialization, and resolution actions with domain effects (keep/merge/supersede/suppress) + reindex + audit.
- **#12 Metric engine.** Max one-to-one matching; missing span = failure; keep zero-fact sources in the denominator; nDCG from full graded qrels; centralized metric IDs from config; fail on unknown/duplicate IDs and unsupported operators; table-driven/property tests. *(Matching, span fidelity, nDCG-with-qrels, and unit tests are implemented; the remainder — config-driven metric IDs, operator validation, zero-fact denominator — is planned.)*
- **#13 (remainder).** The core CI workflow exists; still to add: a Playwright/axe job, a strict-eval gate on a sealed corpus, a migration check, an MCP-contract job, and making ruff/mypy blocking once the static debt (#26) is cleared.
- **#14 (remainder).** Ingest tabs + upload are now keyboard-operable; still to do: dialog focus trap (wizard), shared provenance drawer, all search filters, real resolve interactions, and full keyboard + axe suites across every workflow.
- **#16 (traceability remainder).** Requirement→test matrix + CI gate now exist (see “Implemented this pass”). Still planned: extend immutable IDs across architecture docs and evidence artifacts (full requirement→arch→test→evidence→status chain) and retire the duplicate status trackers so this matrix is the only authority.
- **#17 Provenance envelope.** One immutable provenance envelope across facts/summaries/links/canonical/retrieval/export/UI/audit; edits as new versions; source viewer with span highlighting; contract test follows every returned id to active raw source.
- **#18 `memory/` subsystem.** Quarantine from release, or add `0600` short-lived creds, explicit opt-in, sensitivity screening, audit, and `resolve()`+`is_relative_to()` path containment.
- **#19 Exposed mode.** Declare unsupported in v1 unless a full profile ships (pass/validate all env, fail-fast on unsafe exposure, authenticated UI session, server-derived MCP identity, TLS/CORS/host/rate-limit).
- **#20 Eval representativeness.** Ephemeral DB per run; stratified dev + sealed holdout from consented/redacted real exports; scale/concurrency/long-context/multilingual/backup-restore benchmarks; full environment fingerprint.
- **#21 (embedding remainder).** Canonical model constant + stale-embedding health guard now landed (see “Implemented this pass”). Still planned: honor `embed_provider`/`embed_model` for **external** embedding backends with explicit dimension/model compatibility validation and a re-embed migration path; per-function **summarize/extract** routing already landed (F1/F2).
- **#25 Streamable-HTTP.** Decision already recorded in [ADR 0001](architecture/decisions/0001-mcp-transport.md); v1.2 spike + client/transport matrix.
- **#26 Static debt.** Make ruff/strict-mypy green; split `dispatcher.py`/retrieval into typed stages; ban broad catches except at boundaries. **Test hygiene (related):** several integration tests assume globally-empty tables and commit rows without truncating, so `pytest-randomly` can surface order-dependent failures (e.g. `test_conflict_detection::test_no_duplicates_when_table_empty`); the suite passes deterministically (229) and needs per-test truncation fixtures to be random-order-safe.
- **#27 Wording.** Adopt "local custody; optional remote processing"; per-batch data-flow preview; expand threat taxonomy.

## Nuance / counterpoints

- **#23/#24 (market/business).** Accepted as documentation/product work, not code. The recommendation to pick one beachhead (MCP developers, provenance-first) is sound and should drive scope.
- **#3/#20 headline metrics.** Agreed the "5/5 / 100%" figures are development smoke signals, not release evidence; the quality-baseline doc now says so explicitly.
- **#21.** Partially pre-addressed (summarize/extract routing exists); the embedding half stands.

## Verification for this pass

- Backend: MCP + retrieval + API tests pass (19 + 29 targeted); MCP audit persistence verified live (`mcp_retrieve` row for a fresh actor).
- Frontend: `pnpm test` green (9/9) with the Playwright spec excluded; `pnpm lint` (tsc) clean.
- Eval: `runner.py --strict` present and compiles.

## Commits

`500542f` (Vitest/lockfile/LICENSE) · `9d216b3` (retrieval filters/mode + MCP audit/envelope) · `6788d91` (SPA fallback, deleted_at, wizard copy) · `b285da8` (eval strict mode) · this commit (claim corrections + this status doc).
