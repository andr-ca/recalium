# GPT-5.6 Review — Response & Implementation Status

**Date:** 2026-07-11
**Reviews:** [gpt5.6-sol-recommendations.md](gpt5.6-sol-recommendations.md) (27 findings, product scored 48/100)
**This document:** a response to **every** finding — assessment, decision, evidence, and next action.

Legend — Decision: ✅ Implemented · 🟡 Partially implemented · 📋 Accepted, planned (not built this pass) · 🔵 Already addressed · 💬 Nuance/counterpoint.

## Overall response

The review is rigorous and, in the large, **correct**: Recalium is a feature-rich alpha whose release-readiness claims run ahead of enforced behavior. The core P0 gaps (faithful vendor import, deletion/backup/restore safety, honest eval gating, retrieval-filter/fusion contracts, secret handling, policy enforcement, clean build, portability) are legitimate and accepted.

Most P0s are **multi-day architectural builds**, not one-pass fixes; those are accepted and planned. This pass implemented the **tractable, high-value, low-risk** subset and the regressions the review attributes to recent work. Every finding is answered below.

## Summary

| # | P | Finding (short) | Decision | Evidence |
| --- | --- | --- | --- | --- |
| 1 | P0 | Cold-start vendor import not implemented | 📋 Planned | design below |
| 2 | P0 | Deletion/backup/restore safety | 📋 Planned | design below |
| 3 | P0 | Eval can go green after skips/errors | 🟡 Implemented (strict mode) | `b285da8` |
| 4 | P0 | Retrieval filters + hybrid fusion | 🟡 Filters+mode done; fusion planned | `9d216b3` |
| 5 | P0 | BYOK wizard claims config it doesn't do | ✅ Implemented | `6788d91` |
| 6 | P0 | MCP processing/sensitivity not enforced | 📋 Planned | design below |
| 7 | P0 | Clean build fails; deep links 404 | 🟡 SPA fallback done; multi-stage build planned | `6788d91` |
| 8 | P0 | "Memory bundle" is a raw archive | 🟡 Scope corrected; graph bundle planned | this commit |
| 9 | P0 | Concurrency: deletion vs promotion races | 📋 Planned | design below |
| 10 | P0 | Conflict detection empty; resolve is a no-op | 📋 Planned | design below |
| 11 | P1 | MCP reads not durably audited; error contracts | ✅ Implemented | `9d216b3` |
| 12 | P1 | Extraction/ranking metric defects | 📋 Planned (spec below) | — |
| 13 | P1 | Red/skipped gates; no app CI | 🟡 Frontend gate fixed; CI planned | `500542f` |
| 14 | P1 | Keyboard a11y + curation incomplete | 🟡 Starter fixed; full suite planned | `500542f` |
| 15 | P1 | Website/repo claims inaccurate; no LICENSE | 🟡 LICENSE added; website copy planned | `500542f` |
| 16 | P1 | Requirements/plans not traceable | 📋 Planned | — |
| 17 | P1 | Provenance/canonical integrity below promise | 🟡 Claim corrected; envelope planned | this commit |
| 18 | P1 | `memory/` credential & path-traversal hazards | 📋 Planned (quarantine) | — |
| 19 | P1 | "Exposed mode" not fully wired/secure | 📋 Planned (declare unsupported) | — |
| 20 | P1 | Eval not representative/isolated/at-scale | 📋 Planned | — |
| 21 | P1 | Embedding provider routing partial | 💬 + 📋 Planned | — |
| 22 | P1 | Frontend error/deleted-item states mislead | ✅ Implemented (deleted_at) | `6788d91` |
| 23 | P1 | Differentiation/market evidence stale | 💬 Accepted (docs) | 📋 |
| 24 | P1 | Initial customer/packaging unresolved | 💬 Accepted (product) | 📋 |
| 25 | P2 | Move MCP to Streamable-HTTP | 🔵 ADR exists; spike planned | ADR 0001 |
| 26 | P2 | Static debt / oversized modules | 📋 Planned | — |
| 27 | P2 | "Local-first" wording too strong | 📋 Planned (wording) | — |

## Implemented this pass

- **#3** — `evals/runner.py --strict` release mode fails on any skipped/errored check (default run stays fail-open for local smoke). `b285da8`.
- **#4** — `retrieve()` now enforces `canonical_only`/`source_system`/time-range filters on the candidate set (fixes the confirmed `canonical_only` leak) and validates the mode at the boundary (invalid mode → validation error, not silent hybrid). `9d216b3`. *Not yet:* SQL-level pre-ranking filters, shared `(source_kind, source_id, chunk_id)` fusion identity, direct fact indexing — see #4 plan.
- **#5** — Wizard copy corrected to the truthful `.env`-only model (validate here, add to `.env`, restart). `6788d91`.
- **#7 (SPA)** — `SPAStaticFiles` serves `index.html` for unmatched non-API/non-MCP routes; deep links no longer 404. `6788d91`.
- **#8 / #17 (claims)** — Bundle doc labelled a **source-archive** bundle; quality claim narrowed (span fidelity is extraction-set only) with a small-corpus caveat. This commit.
- **#11** — MCP retrieve access audit event is now committed (verified live: an `mcp_retrieve` row persists for a fresh actor); `get_fact_links` errors use the standard envelope. `9d216b3`.
- **#13 / #14 (regressions)** — Vitest scoped to `src/` so the Playwright spec no longer breaks `pnpm test`; `pnpm-lock.yaml` updated so `--frozen-lockfile` works with `@playwright/test`. `500542f`.
- **#15** — MIT `LICENSE` added (claimed by website/README, previously missing). `500542f`.
- **#22** — `deleted_at` populated in the archive list response so "show deleted" renders correctly. `6788d91`.

## Accepted and planned (not built this pass)

Each is valid and would improve the product, but is a substantial build. Recommended sequencing follows the review's "one trustworthy loop."

- **#1 Vendor import.** Create an `import` domain with versioned ChatGPT/Claude adapters (wrapper-object, top-level-array, and `mapping` shapes), canonical conversation/turn records, ZIP streaming, preview/selection, deterministic IDs, checkpointed batches, and a per-item error ledger. Preserve the raw export; treat unknown schema versions explicitly. **Gate:** import real exports (incl. ZIP/branches/tool-calls) with exact count/role/timestamp/span assertions.
- **#2 Deletion/backup/restore.** Define deletion semantics (physical/crypto-erase after retention); exclude erased content from new backups; append-only tombstone ledger; staged restore into a separate DB with signed-manifest + schema validation, tombstone reapply, integrity check, worker quiesce, atomic cutover, rollback, and path-containment on filenames. **Gate:** secret-ingest→delete→backup→restore(pre/post)→never-retrievable + corrupted-restore rollback test.
- **#4 (remainder).** Shared retrieval-document identity for true RRF fusion; SQL-level filters; direct active-fact indexing; propagate conflict/review state; canonical priority without starvation.
- **#6 Policy enforcement.** Typed, validated `processing_mode`/`sensitivity_hint` columns; resolve an effective policy before every provider call (summarize/extract/link/embed), default to stricter, and audit decision+provider+data-class+item-ids. Capture-proxy privacy test asserting zero sensitive egress.
- **#7 (build).** Multi-stage `Dockerfile`: `node` stage runs frozen `pnpm install` + build; python stage installs deps; copy `frontend/dist` + wheels into runtime. Publish a pinned image digest. **Gate:** clean-clone one-command install passes health + serves every deep link.
- **#8 (full).** Versioned graph bundle: typed raw + normalized conversation/turn + derived + canonical + provenance + link + tombstone + audit records, content hashes, streaming, migrations.
- **#9 Concurrency.** Row-lock/version-token deletion↔processing serialization in one transaction; promotion accepts only fact id + confirmation, derives content/provenance server-side, verifies active status, writes immutable actor.
- **#10 Conflict/curation.** Fact-level duplicate/overlap/contradiction detection with persisted memberships/evidence; transactional queue materialization; resolutions with domain effects (keep/merge/supersede/suppress) + reindex + audit.
- **#12 Metric engine.** Max one-to-one matching; missing span = failure; keep zero-fact sources in the denominator; nDCG from full graded qrels; centralized metric IDs from config; fail on unknown/duplicate IDs and unsupported operators; table-driven/property tests.
- **#13 (CI).** PR/release pipelines: frozen install, ruff/mypy, backend+frontend tests with Postgres/pgvector, Playwright/axe, clean image build, migrations, MCP contract, strict evals; allow-listed skips.
- **#14 (a11y).** Tested tab/dialog primitives, native focusable upload, shared provenance drawer, all search filters, real resolve interactions; full keyboard + axe suites.
- **#16 Traceability.** Immutable atomic requirement IDs + generated requirement→arch→test→evidence→status matrix; one status authority.
- **#17 Provenance envelope.** One immutable provenance envelope across facts/summaries/links/canonical/retrieval/export/UI/audit; edits as new versions; source viewer with span highlighting; contract test follows every returned id to active raw source.
- **#18 `memory/` subsystem.** Quarantine from release, or add `0600` short-lived creds, explicit opt-in, sensitivity screening, audit, and `resolve()`+`is_relative_to()` path containment.
- **#19 Exposed mode.** Declare unsupported in v1 unless a full profile ships (pass/validate all env, fail-fast on unsafe exposure, authenticated UI session, server-derived MCP identity, TLS/CORS/host/rate-limit).
- **#20 Eval representativeness.** Ephemeral DB per run; stratified dev + sealed holdout from consented/redacted real exports; scale/concurrency/long-context/multilingual/backup-restore benchmarks; full environment fingerprint.
- **#21 Embedding routing.** Honor `embed_provider`/`embed_model`; version embedding spaces; validate dimension/model compatibility; represent partial completion explicitly. *Nuance:* per-function **summarize/extract** routing already landed (F1/F2); embeddings remain local-only.
- **#25 Streamable-HTTP.** Decision already recorded in [ADR 0001](architecture/decisions/0001-mcp-transport.md); v1.2 spike + client/transport matrix.
- **#26 Static debt.** Make ruff/strict-mypy green; split `dispatcher.py`/retrieval into typed stages; ban broad catches except at boundaries.
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
