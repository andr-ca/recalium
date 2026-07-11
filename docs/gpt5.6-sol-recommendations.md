# Recalium GPT-5.6 Solution Review and Recommendations

**Review dates:** 2026-07-10 through 2026-07-11 \
**Frozen baseline commit:** `0d7ea28` \
**Frozen intermediate remediation commit:** `c83d0c8` \
**Latest frozen remediation commit independently revalidated:** `ba7f686b8d8452d1642293f54a0cd96c9f7c74eb` \
**Decision:** **No-go for a public v1 release; continue as a promising alpha** \
**Latest independently revalidated score:** **54/100** (**intermediate: 53/100; baseline: 48/100**)

> **Snapshot note:** The detailed ranked findings preserve the evidence found at
> `0d7ea28`, which scored 48/100. Seventeen follow-up commits then addressed
> parts of that review. The
> [remediation delta](#remediation-delta-at-c83d0c8) records what was independently
> revalidated at `c83d0c8` and is authoritative for the intermediate 53/100 score.
> The [further remediation delta](#further-remediation-delta-at-ba7f686) then
> evaluates the eight commits through exact commit
> `ba7f686b8d8452d1642293f54a0cd96c9f7c74eb`, which scores 54/100. The existing
> dirty working tree and every commit after that exact target are excluded so the
> review remains reproducible rather than chasing a moving branch. A higher score
> does not itself change the public-release decision; the release gates still
> require direct evidence.

## Executive assessment

Recalium addresses a real and increasingly important problem: people accumulate valuable context across AI products but cannot reliably inspect, curate, move, or reuse it. The raw/derived/canonical memory model, source-span emphasis, local custody, and MCP interface form a coherent product thesis. The repository also contains much more than a concept: a working API, PostgreSQL schema, asynchronous processing pipeline, UI, MCP server, website, tests, and an evaluation harness.

At the baseline, the release-readiness claim was nevertheless ahead of the product. The most important first-run workflow did not actually import and normalize a real ChatGPT history; a clean checkout could not build the application image; the key-setup wizard validated but did not configure a usable provider; several advertised retrieval filters were ignored; hybrid fusion combined row IDs that cannot match across retrieval modes; MCP retrieval audits were rolled back; deletion was not safe across backups or concurrent processing; and restore ran destructively against the active database. The evaluation suite was useful for development, but it could pass after skipped or errored checks and its tiny, tuned fixture made the headline 100% metrics non-diagnostic.

The remediation pass materially improved packaging, per-conversation JSON import, frontend tests, selected retrieval filters, first-access MCP audit persistence, evaluation strict mode, metric helpers, keyboard ingest controls, error states, CI, licensing, and claim accuracy. It did **not** close the highest-risk data-safety, policy-enforcement, transaction-integrity, conflict-resolution, portability, hybrid-fusion, representative-evaluation, or exposed-mode gaps. Some fixes are also incomplete: category remains ignored, filters run after top-50 candidate selection, cache-hit MCP reads remain unaudited, the corrected nDCG denominator is not passed by the evaluator, and the SPA fallback turns unknown API routes into HTTP 200 HTML responses.

The correct product classification is therefore **feature-rich alpha**, not release candidate. The fastest route to a credible v1 is to narrow scope around one trustworthy loop:

1. Import a real vendor export from a clean install.
2. Preserve conversations and provenance faithfully.
3. Process them according to an enforced privacy policy.
4. Retrieve the right fact with working filters and complete audit evidence.
5. Curate or delete it with transactional and backup-safe behavior.
6. Prove that loop on a sealed, representative evaluation corpus.

## Scorecard

| Aspect | Weight | Baseline | c83d0c8 | ba7f686 | Latest assessment |
| --- | ---: | ---: | ---: | ---: | --- |
| Product idea | 15% | **68** | **68** | **68** | The problem and trust model remain strong, but the four narrow remediations do not add market, differentiation, or initial-customer evidence. |
| Documentation | 15% | **61** | **66** | **66** | Generated token-reference inventory and freshness checking help navigation, but they do not prove semantic closure or resolve competing status authorities. |
| Implementation | 30% | **43** | **49** | **50** | Bounded partial credit for policy-gated summarize/extract, linked duplicate facts, and embedding-model inventory; their original privacy, conflict, and routing gates remain open. |
| Evaluation suite | 20% | **32** | **39** | **39** | Focused tests increased, but representative, isolated, fail-closed release evaluation is still absent and a conflict probe remains order-dependent. |
| Code quality | 20% | **47** | **54** | **54** | Added tests are offset by three stale default-suite failures, 27 Ruff errors, 113 mypy errors, non-blocking static CI, and reproduced fixture leakage. |
| **Weighted total** | **100%** | **48.05 → 48** | **53.40 → 53** | **53.70 → 54** | **+0.30 raw from c83d0c8 and +5.65 raw from baseline; stronger alpha, with public release still blocked.** |

Latest raw score:
`0.15*68 + 0.15*66 + 0.30*50 + 0.20*39 + 0.20*54 = 53.70`.
Using conventional nearest-integer rounding for nonnegative scores
(`floor(raw + 0.5)`), `53.70 → 54`.

Scoring interpretation used for this review:

- **90–100:** exceptional, independently evidenced release quality.
- **75–89:** release-ready with bounded follow-up work.
- **60–74:** usable beta with material gaps.
- **40–59:** promising implementation, but core contracts or release gates are unreliable.
- **1–39:** concept or prototype with fundamental execution risk.

## Scope and review method

The review covered the five requested aspects and their cross-cutting contracts:

- Product requirements, personas, differentiation, architecture, plans, operational evidence, guides, and website claims.
- Backend API, domain services, worker, database behavior, provider routing, backups, portability, deletion, canonical memory, links, and review queue.
- MCP schemas, transports, retrieval, provenance, filters, errors, identity, audit persistence, and live tool behavior.
- Frontend routes, onboarding, ingest, search, facts, canonical memory, review queue, settings, error states, keyboard operation, build, and tests.
- Evaluation datasets, runner control flow, thresholds, metrics, isolation, artifacts, reproducibility, and the claims derived from them.
- The separate `memory/` agent-memory subsystem, website, Compose/Docker packaging, repository hygiene, static analysis, and CI coverage.

The audit used source inspection, targeted metric probes, a live Docker Compose stack, a clean-checkout Docker build, backend and frontend test suites, static checks, production-route probes, live MCP calls, direct audit-table verification, website builds, and local-link validation. No paid or external-provider quality run was performed, no destructive restore was attempted against the live database, and no claim in this report depends on either.

## Remediation delta at `c83d0c8`

Seventeen commits landed after the baseline review. They are a useful response to the findings, but a commit mentioning a finding is not treated as closure: closure requires the original acceptance gate to pass. On that basis, no P0 finding is fully closed yet.

| # | Baseline finding | Status at `c83d0c8` | Revalidated disposition |
| ---: | --- | --- | --- |
| 1 | Cold-start vendor import | **Partial** | A new import domain splits ChatGPT/Claude JSON into per-conversation rows and jobs with metadata and 11 tests. ZIP streaming, preview/selection, branch fidelity, raw-export preservation, checkpointing, per-item errors, and real-export evidence remain open. |
| 2 | Deletion/backup/restore safety | **Open** | No committed change to physical deletion, backup exclusion, staged restore, tombstone replay, containment, cutover, or rollback. |
| 3 | Eval false-green behavior | **Partial** | `--strict` now fails on skipped/errored checks. Non-200 retrieval cases and recorded search errors can still be omitted from pass logic; strict release eval is not in CI. |
| 4 | Retrieval filters and fusion | **Partial** | Canonical/source/time filters and mode validation were added. Category remains ignored; filters run after candidate generation; imported `chatgpt_import` sources do not match the advertised `chatgpt` example; fact indexing and stable-identity RRF remain open. |
| 5 | Misleading BYOK wizard | **Partial** | UI copy now truthfully says the key is validation-only and requires `.env` plus restart. The first-run workflow still does not configure a usable provider, so the false claim is closed but the product requirement is not. |
| 6 | Processing/sensitivity controls ignored | **Open at frozen snapshot** | `c83d0c8` still stores the fields without worker enforcement. A policy-enforcement commit landed after the snapshot freeze and is intentionally not credited until it receives the same clean-snapshot validation. |
| 7 | Clean build and deep links | **Partial** | Frozen clean image build and all UI deep links now pass. The fallback also serves `index.html` for unknown `/api/*` routes, producing HTTP 200 HTML instead of an API 404; CI builds but does not start/probe the image. |
| 8 | Raw-only “memory bundle” | **Partial** | Documentation now calls it a source-archive bundle. The implementation remains raw-only and lossy on re-import. |
| 9 | Delete/promotion races | **Open** | No committed concurrency or server-side promotion-integrity change. |
| 10 | Empty conflict groups/no-op review | **Open** | No committed fact membership, queue materialization, contradiction classification, or domain-effect resolution. |
| 11 | MCP audit/error inconsistency | **Partial** | A fresh MCP retrieval now commits one audit event and fact-link errors use the standard envelope. Two identical live reads produced only one audit row because cache hits are still skipped; actor identity remains client-supplied and touched IDs/outcomes remain absent. |
| 12 | Metric correctness | **Partial** | Missing spans, duplicate matching, and an optional full-qrel nDCG denominator were fixed with seven tests. The retrieval evaluator still calls nDCG without `total_relevant`; zero-fact sources and centralized configured thresholds remain unfixed. |
| 13 | Red gates/no application CI | **Partial** | Application CI, frozen frontend install, Vitest scoping, and clean Docker build landed. The exact allow-listed CI backend command passes, but the documented default backend command still fails three stale MCP tests; Ruff/mypy are informational and Playwright/eval/MCP release gates are absent. |
| 14 | Keyboard accessibility/curation | **Partial** | Ingest tabs and upload controls are keyboard-operable. Dialog focus management, end-to-end keyboard/axe evidence, source navigation, search controls, and effective conflict resolution remain open. |
| 15 | Public/OSS claims | **Partial** | An MIT license landed. Website repository, port, route, variable, ZIP, wizard, and tool-schema claims were not all corrected. |
| 16 | Traceability/status drift | **Open** | A response/status document exists, but no immutable atomic-ID traceability matrix or single generated status authority exists. |
| 17 | Provenance/canonical integrity | **Partial** | Quality wording was narrowed. The provenance envelope, source viewer, server-derived promotion fields, and immutable derivation chain remain open. |
| 18 | Separate `memory/` security hazards | **Open** | No committed quarantine, permission, consent, provider, or path-containment fix. |
| 19 | Exposed-mode security | **Open** | No committed secured deployment profile or explicit v1 disablement. Compose propagation and UI authentication gaps remain. |
| 20 | Eval representativeness/isolation | **Open** | Dataset, live-DB pollution, scale coverage, holdout design, and artifact provenance remain materially unchanged. |
| 21 | Provider/embedding routing | **Open** | Embedding settings are still not honored and partial completion remains ambiguous. |
| 22 | Misleading frontend states | **Partial** | `deleted_at` and Canonical error/retry states were fixed. Telemetry and archive retry error surfaces remain incomplete. |
| 23 | Competitive thesis | **Open** | Accepted in the response document; the dated, sourced competitive rewrite and user evidence are not complete. |
| 24 | ICP/packaging/business | **Open** | No committed product decision or validation evidence. |
| 25 | Current MCP transport | **Open/planned** | The ADR remains; Streamable HTTP and the client compatibility matrix are not implemented. |
| 26 | Static/maintainability debt | **Open** | Ruff remains at 27 errors; strict mypy increased to 110 errors across 29/67 files after new code. CI explicitly treats both as informational. |
| 27 | Local-first overstatement | **Partial** | README now accurately distinguishes local custody from optional remote processing. Runtime policy enforcement and network-capture evidence remain open under finding 6. |

### Release priorities after `c83d0c8`

After accounting for the remediation, the highest-value order is now:

1. Make deletion and restore tombstone-safe, staged, and rollback-capable.
2. Enforce processing/sensitivity policy before every provider call.
3. Serialize deletion with processing and validate canonical promotion server-side.
4. Implement fact-backed conflict detection and resolutions with domain effects.
5. Build a hermetic, representative, fail-closed release evaluation.
6. Fix stable-identity RRF, direct fact retrieval, and all SQL-level filters.
7. Deliver full-fidelity graph portability or retain the narrower source-archive promise.
8. Complete real-export ZIP import, preview, branch fidelity, resumability, and evidence.
9. Audit every MCP access, including cache hits, with server-derived identity and touched IDs.
10. Make production fallback preserve API 404s and make every default/static/CI gate blocking and green.

### Fresh remediation validation

The following results were obtained from a detached clean worktree at exactly `c83d0c8`, avoiding concurrent uncommitted changes:

| Validation | Result |
| --- | --- |
| `uv sync --frozen` | **Pass.** |
| CI-equivalent backend test command | **Pass:** 219 passed, 10 skipped, 3 explicitly deselected. |
| Default backend suite excluding live E2E | **Fail:** 3 failed, 219 passed, 10 skipped; all failures are stale MCP expectations. |
| `uv run ruff check app tests` | **Fail:** 27 errors. |
| `uv run mypy app` | **Fail:** 110 errors in 29 of 67 files. |
| Frontend frozen install | **Pass.** |
| Frontend Vitest | **Pass:** 4 files, 9 tests. |
| Frontend typecheck/lint | **Pass.** |
| Frontend production build | **Pass.** |
| Eval metric unit tests | **Pass:** 7 tests. |
| Clean Docker build with `EMBED_BACKEND=none` | **Pass:** complete production image built from the clean worktree. |
| Built-image startup and health | **Pass:** migrations, startup, database health, worker, and MCP registration completed. |
| Built-image UI deep links | **Pass:** `/`, `/facts`, `/search`, `/settings`, and `/review-queue` returned 200. |
| Unknown API route | **Fail:** `/api/definitely-missing` returned 200 HTML from the SPA instead of an API 404. |
| MCP canonical-only probe | **Partial pass:** no non-canonical type leaked, but the matching query returned zero items, so relevance/recall was not established. |
| MCP audit probe | **Partial:** two identical successful accesses produced one committed audit row; the cache hit was not audited. |
| GitHub CI at `c83d0c8` | **Pass**, but static checks are informational and the backend suite uses three deselections. |

## Further remediation delta at `ba7f686`

Eight commits after `c83d0c8` form four implementation-plus-documentation
slices: `855ce11`/`28972da` (policy), `66ea868`/`14c29e9` (conflicts),
`4966a0a`/`b1c4226` (traceability), and `e7a1a60`/`ba7f686`
(embeddings). The dispositions below are based on the code and validation at
exact commit `ba7f686b8d8452d1642293f54a0cd96c9f7c74eb`, not the optimistic
labels in the response document.

- **Finding 6 — Partial.** The worker now resolves effective policy from the
  content gate plus caller-declared processing mode and sensitivity hint,
  defaults conflicts to the stricter decision, gates summarize/extract external
  calls, and emits a policy audit; MCP rejects undeclared mode/hint values.
  Policy inputs still live in `metadata_json`, however, and Pass B link
  classification still invokes an external LLM solely when a provider is
  available, without consulting the resolved policy. An idempotent replay can
  echo a newly requested stricter mode in its response while leaving the
  original durable policy metadata unchanged. Policy-audit failure is nonfatal,
  and its `provider` field is populated by `_provider_name()`, which actually
  returns a model label. There is no provider × mode × hint capture matrix,
  link/embed coverage, or capture-proxy proof of zero blocked egress. The
  original all-external-stage policy-matrix gate therefore remains open.
- **Finding 10 — Partial.** Near-duplicate candidates now create a group, link
  active facts from the involved archive items, and emit a
  `conflict_detected` audit. The worker still never calls
  `materialize_review_item`, while queue listing selects only existing
  `ReviewQueueItem` rows. Resolve/dismiss remains a note/status transition with
  no keep/merge/supersede/suppress domain effect or reindexing. Detection still
  lacks overlap/contradiction classification and durable membership/evidence
  semantics beyond `facts.conflict_group_id`; group creation, fact linking, and
  audit use split commits. A clean two-test reversed-order probe produced one
  pass and one fail because a committed fixture leaked into the empty-table
  assertion. The original evidence-backed queue-to-resolution gate remains
  open.
- **Finding 16 — Partial.** A generator now inventories 52 requirements, 50
  automated references and two documented manual checks, with freshness and CI
  checks. This is useful token-reference inventory, not semantic closure:
  scanning treats any requirement-ID mention in a `.py`, `.ts`, or `.tsx` file
  under backend tests, evals, or `frontend/src`—including frontend
  implementation—as test evidence. Concrete false assurances include SRCH-05,
  whose cited integration tests explicitly say “structural only — no timing”;
  BKUP-02, whose cited restore test only asserts 404 for a missing file; and
  WEBUI-02/03, whose cited integration tests cover deletion/listing and audit
  filtering/pagination rather than keyboard operation or accessibility. The
  matrix lacks owners, severity, architecture and implementation links, release
  disposition, and an immutable review record; duplicate status authorities
  remain. The original requirement-to-architecture-to-implementation-to-
  evidence-to-status gate remains open.
- **Finding 21 — Partial.** One active local embedding-model constant now drives
  writes, semantic retrieval filtering, and provenance, while startup reports
  stale rows and configured-model drift. Configured embedding provider/model
  values still are not honored. Conflict and link SQL can compare or combine
  stale model spaces, and `get_existing_embedding()` accepts any active row, so
  a stale row suppresses re-embedding. There is no model/dimension compatibility
  enforcement, re-embedding migration, explicit per-stage partial/degraded
  status, or provider-routing matrix. The original provider/model/policy routing
  gate remains open.

### Current risk ranking at `ba7f686`

This table reorders the residual risks at the latest frozen commit while keeping
the baseline finding IDs and their historical evidence intact. Partial work is
demoted only where it reduces expected harm; privacy and integrity closure gates
remain near the top when their bypasses are still reachable.

| Current rank | Baseline finding | Residual priority | Current status | Residual risk | Why it ranks here |
| ---: | ---: | --- | --- | --- | --- |
| 1 | 2 | P0 | Open | Deleted data can survive backups or be resurrected by destructive restore. | Irreversible privacy loss and active-database damage remain the highest-consequence failure. |
| 2 | 6 | P0 | Partial | Caller policy can still be bypassed by external link classification, replay metadata drift, or nonfatal audit loss. | Summarize/extract gating narrows exposure, but an unguarded external path keeps the original privacy gate release-blocking. |
| 3 | 9 | P0 | Open | Deletion races can recreate derivatives and client-supplied promotion can forge source integrity. | Concurrent integrity failures can defeat both deletion and canonical trust. |
| 4 | 3 | P0 | Partial | Release evaluation can omit failures and overstate tiny tuned-corpus results. | Weak evidence can green-light every other unsafe behavior. |
| 5 | 20 | P0 | Open | Evaluation is neither representative nor isolated and lacks scale/concurrency evidence. | Even correct helper metrics cannot establish release behavior on real data. |
| 6 | 4 | P0 | Partial | Filters/fusion/fact retrieval still violate the advertised search contract. | Core retrieval can return the wrong evidence despite selected filter fixes. |
| 7 | 10 | P0 | Partial | Duplicate facts are linked but not guaranteed to enter a queue or change domain/retrieval state when resolved. | Linking lowers invisibility risk, but no-op curation and split transactions leave memory integrity unresolved. |
| 8 | 8 | P0 | Partial | The portable bundle still omits derived, canonical, provenance, link, tombstone, and audit state. | Source-archive wording reduces claim harm, not portability/data-loss risk. |
| 9 | 17 | P0 | Partial | Returned and curated memory still lacks one immutable, navigable provenance chain. | The product's main trust differentiator remains unverifiable end to end. |
| 10 | 1 | P0 | Partial | JSON import lacks ZIP, branch/tool-call fidelity, preview, resumability, and real-export proof. | Per-conversation fan-out is meaningful, so it falls below fully unmitigated integrity risks. |
| 11 | 11 | P1 | Partial | Cache-hit reads and failures lack complete durable, server-derived MCP audit evidence. | Machine access remains incompletely accountable after the first-access commit fix. |
| 12 | 19 | P1 | Open | Documented exposed-mode controls are not a complete secured deployment profile. | Manual exposure can create a broad unauthenticated data surface. |
| 13 | 18 | P1 | Open | The separate memory subsystem can leak transcripts/credentials or escape intended paths. | Direct security hazards remain, though the subsystem is separable from the core loop. |
| 14 | 13 | P1 | Partial | Default tests are red and important static/release gates remain non-blocking or absent. | CI exists, but its allow-list and informational checks cannot certify the shipped state. |
| 15 | 5 | P1 | Partial | First-run validation does not configure a runtime provider. | Corrected copy reduces deception, but onboarding can still fail after restart. |
| 16 | 12 | P1 | Partial | Evaluator wiring, zero-fact accounting, and threshold authority remain incorrect. | Helper fixes reduce metric defects without making the release decision trustworthy. |
| 17 | 14 | P1 | Partial | Full keyboard/accessibility and effective curation flows lack evidence. | Ingest controls improved, but core workflows remain unproven. |
| 18 | 15 | P1 | Partial | Public commands and capabilities still diverge from the application. | License correction removes one legal mismatch; operational trust debt remains. |
| 19 | 16 | P1 | Partial | Token-reference inventory can certify semantically unrelated files and status authorities still conflict. | Freshness helps navigation, so it ranks below untouched security/gate failures; it cannot support closure claims. |
| 20 | 21 | P1 | Partial | Stale/incompatible embeddings can be mixed or suppress re-embedding, and configured routing is ignored. | Health visibility reduces silent drift, but no compatibility or migration enforcement exists. |
| 21 | 7 | P1 | Partial | Unknown API routes return HTTP 200 SPA HTML and no pinned user image is proven. | Clean build/start and deep links materially reduce installation risk, explaining the demotion. |
| 22 | 22 | P1 | Partial | Some load/retry/degraded states can still misrepresent data. | Canonical and deleted-item fixes reduce, but do not eliminate, misleading UI state. |
| 23 | 26 | P2 | Open | Static debt, broad catches, and oversized orchestration obscure partial failure. | It amplifies higher-ranked defects but is less directly harmful than their runtime outcomes. |
| 24 | 27 | P2 | Partial | Runtime/network proof still lags the corrected local-custody wording. | Accurate README language reduces immediate claim risk; policy evidence is tracked above. |
| 25 | 25 | P2 | Open/planned | Legacy SSE transport lacks a current client compatibility/concurrency matrix. | Migration risk matters after the core privacy and integrity contract is dependable. |
| 26 | 24 | P2 | Open | Initial customer, packaging, support, and business model remain unresolved. | Product focus affects adoption but not immediate stored-data safety. |
| 27 | 23 | P2 | Open | Competitive claims and user validation remain stale or absent. | Market evidence is important, but it is the least immediate release-safety risk. |

### Fresh validation at `ba7f686`

These results are the authoritative latest-snapshot record. Focused and
eval/trace runs are supporting subsets and are not added to the CI-equivalent
backend total.

| Validation | Result |
| --- | --- |
| CI-equivalent backend gate | **Pass:** 233 passed, 10 skipped, 3 intentionally deselected. |
| Default non-live backend suite | **Fail:** 3 failed, 233 passed, 10 skipped; the three failures are stale MCP expectations. |
| Focused policy/conflict/embedding/traceability-related set | **Pass:** 41 passed, 2 skipped; reported separately, not double-counted into the backend gate. |
| Eval metrics plus traceability tests | **Pass:** 11 passed; reported separately, not double-counted into the backend gate. |
| Frontend Vitest | **Pass:** 9 tests. |
| Frontend lint/typecheck and production build | **Pass.** |
| Clean image build/startup | **Pass:** clean image built and started; health, `/`, and `/facts` probes passed. |
| Unknown API route | **Fail:** unknown `/api` returned HTTP 200 SPA HTML rather than an API 404. |
| `uv run ruff check app tests` | **Fail:** 27 errors. |
| `uv run mypy app` | **Fail:** 113 errors in 30 of 68 files. |
| Live MCP policy probe | **Partial pass:** `local_only` was accepted and completed, and its durable policy audit recorded `allow_external=false`; this does not exercise the unguarded link/provider matrix. |
| Conflict reversed-order isolation probe | **Fail:** one pass and one fail; the committed fixture leaked into the clean two-test reversed-order empty-table check. |

## Ranked findings and recommendations

The findings below are ordered by expected user harm and release risk, not by file order. **P0** blocks a trustworthy v1; **P1** blocks a strong beta or materially damages credibility; **P2** should follow once the core loop is sound.

**Baseline citation rule:** Every unqualified repository path and `path:line`
reference in the ranked findings below refers to the file as stored at frozen
commit `0d7ea28`, not the later working tree. The remediation table above is the
source of truth for which baseline findings changed by `c83d0c8`.

### 1. P0 — The flagship cold-start import is not implemented

**Aspects:** idea, documentation, implementation, evaluation, code

**Evidence**

- Product requirements make importing an existing ChatGPT or Claude history the primary cold-start and “aha” path (`docs/requirements/product-overview.md`; `docs/requirements/nfr.md`). The active work plan and release gate do not require proof of this path.
- `backend/app/domain/ingest/parsers.py:74-110` recognizes ChatGPT only as a wrapper object containing `conversations`. The repository's own purported ChatGPT fixture is a single object containing `mapping` (`backend/tests/test_ingest.py:48-76`), so it is classified as generic JSON. The test checks only that at least one item was accepted, not that the format, turns, roles, timestamps, or conversation count were correct.
- Common top-level arrays of ChatGPT conversation objects are also classified as generic JSON. Claude is recognized only through one narrow `uuid` plus `chat_messages` shape.
- `backend/app/domain/ingest/service.py:110-155` stores the entire upload as one `RawArchiveItem` and creates one processing job, while returning `item_count=conversation_count`. It does not split conversations or normalize messages, roles, timestamps, stable vendor IDs, attachments, tool calls, or branches.
- File upload accepts only `.json`, `.txt`, and `.md` (`service.py:82-96`); the website advertises uploading a ChatGPT ZIP.
- There is no import preview, filtering, provider/cost estimate, resumable batch state, per-conversation result, or quality summary. The evaluation uses four hand-built synthetic conversations, not real vendor exports.

**Impact**

The product's defining first-run promise can report success while storing one opaque JSON blob. Retrieval and provenance then operate at the export level rather than the conversation or turn level. A user cannot determine what imported, resume safely, filter sensitive histories, or trust the returned item count.

**Recommendation**

Create a dedicated import domain with versioned ChatGPT and Claude adapters, canonical conversation/turn records, ZIP streaming, preview, selection, deterministic IDs, checkpointed batches, and a per-item error ledger. Preserve the untouched raw export alongside normalized records. Treat unknown schema versions explicitly rather than silently downgrading them to generic JSON.

**Closure gate**

- Import current, independently obtained ChatGPT and Claude exports, including ZIPs, branches, long conversations, deleted/empty messages, tool calls, and multilingual text.
- Assert exact conversation and message counts, roles, timestamps, source IDs, source spans, restart/resume behavior, deduplication, and per-item errors.
- Complete the first trustworthy retrieval from a clean checkout within the documented onboarding target.

### 2. P0 — Deletion, backup, and restore do not provide the promised safety boundary

**Aspects:** documentation, implementation, evaluation, code

**Evidence**

- Deletion sets `raw_archive.deleted_at` but retains `raw_content` (`backend/app/domain/archive/models.py:15-34`; `backend/app/domain/archive/service.py:45-103`).
- Backup performs a full `pg_dump` of the database (`backend/app/domain/backup/service.py:47-92`), so a backup created after deletion still contains the supposedly deleted plaintext.
- Restore accepts a filename, joins it to the backup directory without a resolved-path containment check, and runs `pg_restore --clean --if-exists` directly against the active database (`service.py:121-180`). It has no quiesce phase, manifest/schema validation, integrity check, staged database, transaction/cutover plan, rollback image, tombstone reapplication, cache invalidation, or worker restart coordination.
- The approved architecture describes tombstone-safe staged restore, but implementation does not follow it. Relevant integration tests were skipped because `pg_dump`/`pg_restore` were unavailable, and no live restore evidence exists.

**Impact**

Deletion does not mean removal from new backups, and restoring an older dump can resurrect deleted data. A partial or failed restore can damage the active installation. This is an irreversible data-integrity and privacy risk, not a cosmetic release gap.

**Recommendation**

Define deletion semantics explicitly. If the promise is physical erasure, purge or cryptographically erase raw content after a retention window and ensure post-deletion backups exclude it. Maintain an append-only tombstone ledger outside restorable user data. Stage restores into a separate database, validate the signed manifest and schema, reapply tombstones, run integrity checks, stop workers, atomically cut over, invalidate caches, and retain a rollback point. Reject paths escaping the backup directory.

**Closure gate**

An automated end-to-end test must ingest a unique secret, delete it, create a backup, prove the bytes and all active indexes are absent, restore both pre- and post-deletion backups into staging, reapply the tombstone, verify the secret never becomes retrievable, and prove rollback after an intentionally corrupted restore.

### 3. P0 — The evaluation runner and dataset can produce a misleading green release result

**Aspects:** documentation, evaluation, code

**Evidence**

- `evals/runner.py:95-113` converts check exceptions into `skipped=True`; `runner.py:181-184` determines overall success from non-skipped checks. A broken check can therefore disappear from the release result.
- Retrieval evaluation discards non-200 responses and records ordinary search exceptions without making `search_errors` part of the pass decision (`evals/checks/eval_retrieval.py:182-195,292-314`).
- The golden set contains four synthetic conversations, 26 facts, 13 queries, only eight ordinary scored queries, and two adversarial queries. Recall@10 is calculated over four source archives.
- Golden fact IDs are converted to parent archive IDs (`eval_retrieval.py:51-65`), so retrieving any content from a conversation satisfies all fact labels in that conversation. With `k=10` and only four eval documents, 100% recall is a very weak result.
- The same fixture informed sensitivity tuning, matching changes, expanded labels, and retrieval changes. There is no sealed holdout set.
- The published baseline says hybrid P95 is 175 ms, while its linked artifact reports 216 ms. It extends extraction span fidelity to “every returned item,” which the check does not establish.

**Impact**

The “5/5” and “100% recall/span fidelity” claims cannot support release readiness, product marketing, or regression decisions. They are useful local smoke signals, but they can remain green while a check crashes, queries error, or relevance quality is poor.

**Recommendation**

Add strict development and release modes. Release mode must fail on every skip, exception, missing dependency, missing expected case, empty cohort, search error, or unknown metric. Separate a mutable development set from a sealed holdout. Use fact-level graded qrels, hard negatives, `k` well below corpus size, human judgments, multiple seeds/models, and an isolated ephemeral database.

**Closure gate**

CI must deliberately crash each check and prove the suite exits non-zero; alter each frozen threshold and prove the decision changes; run a sealed representative corpus with immutable hashes and complete per-case output; and have an independent reviewer reproduce the report from a clean environment.

### 4. P0 — Retrieval filters and hybrid fusion do not implement the advertised contract

**Aspects:** implementation, evaluation, code

**Evidence**

- `RetrievalFilters` exposes category, source system, time range, canonical-only, and tags (`backend/app/domain/retrieval/service.py:45-53`), but `retrieve()` passes only tags to candidate queries (`service.py:531-569`).
- A live MCP request with `canonical_only=true` returned five non-canonical `excerpt` items, directly confirming the filter is ignored.
- Keyword candidates use full-text-index row IDs while semantic candidates use embedding row IDs. `service.py:576-586` fuses those IDs with reciprocal-rank fusion. The same source cannot share an ID across the two tables, so the two rankings do not reinforce one another; they are merely interleaved.
- Direct fact retrieval is absent. Keyword search returns canonical items plus raw excerpts, semantic search returns embeddings/summary-backed content, and facts generally appear only through link traversal.
- Conflict labels are returned as `None`; contradiction state is not incorporated into ranking. Invalid modes fall into the hybrid branch rather than returning validation errors.

**Impact**

Search and MCP clients cannot rely on declared filters, “hybrid” quality is not true fusion, user-curated facts are not first-class candidates, and the current retrieval evaluation masks the problem by scoring at archive level.

**Recommendation**

Define a stable retrieval-document identity such as `(source_kind, source_id, chunk_id)` and map all rankers to it before fusion. Apply every filter in SQL before ranking. Index and retrieve active facts directly, add canonical priority without starving relevant evidence, propagate contradiction/review state, and validate modes and date ranges at the boundary.

**Closure gate**

Property and integration tests must prove every filter changes the candidate set, the same document gains score when ranked by both modes, fact-level qrels improve over each single mode, canonical-only never leaks another type, deleted/disputed sources never return, and invalid requests receive a stable error.

### 5. P0 — The first-run BYOK wizard reports configuration it does not perform

**Aspects:** documentation, implementation, code

**Evidence**

- The wizard says a submitted key is validated and “stored only in `.env`” (`frontend/src/pages/WizardPage.tsx:220-224`).
- The settings endpoint uses the submitted value only to make a validation call and persist a fingerprint/configured flag (`backend/app/api/routes/settings.py:55-119`). It cannot update the host `.env` file.
- Runtime dispatch reads provider keys from process environment settings (`backend/app/infrastructure/settings.py:40-66`). The submitted UI value is never made available to the worker.
- Configuration state is reconciled from the current environment, and pending jobs can be reactivated even though the worker still lacks the key.
- Ollama URL/model changes have the same runtime-source mismatch.

**Impact**

A new user receives a success message, processing resumes, and jobs then fail or remain pending. This breaks the onboarding loop and creates a misleading secret-handling claim.

**Recommendation**

Choose one security model. The lowest-risk v1 option is `.env`-only: the UI may test the currently loaded configuration, but it must not accept or claim to store new secrets; provide exact edit-and-restart instructions. If runtime configuration is essential, use a documented local secret store with restrictive permissions, encryption/key lifecycle, explicit restart semantics, backup exclusion, and a threat model.

**Closure gate**

From a clean install with no provider key, complete the documented flow, restart the service, process a queued item, and prove no plaintext key exists in the database, logs, API responses, browser storage, telemetry, backups, or repository files.

### 6. P0 — MCP processing and sensitivity controls are stored but not enforced

**Aspects:** idea, documentation, implementation, evaluation, code

**Evidence**

- `ingest_memory` accepts `sensitivity_hint`, `project_hint`, and `processing_mode` and stores them in archive metadata (`backend/app/mcp_server/server.py:280-365`).
- The worker does not read these metadata fields. It runs its own sensitivity classifier and normal configured pipeline regardless of a client-declared sensitive or local/store-only mode.
- Optional external summarization/extraction is enabled by provider configuration. Link classification can also call the configured provider over fact pairs without a policy check for each target pair.
- The sensitivity evaluation uses one synthetic sensitive conversation, observes the system's own audit flag and absence of facts, and was run with local Ollama. It does not capture outbound traffic to prove an external provider received no sensitive content.

**Impact**

An MCP client can request conservative processing and receive an acknowledgement even though the request has no effect. Sensitive content may be sent to an external provider contrary to the caller's intent and the documented local-first trust model.

**Recommendation**

Convert processing mode and sensitivity hints into typed, validated policy inputs stored in dedicated columns. Resolve an effective policy before every provider call, default conflicts to the stricter option, and record the decision, provider, permitted data class, and item IDs. Use a capture/stub external provider in privacy tests and assert zero sensitive outbound payloads.

**Closure gate**

A policy matrix test must cover every processing mode × hint × provider combination, including links and embeddings, and prove both network behavior and durable audit evidence.

### 7. P0 — A clean checkout cannot build the app, and production deep links return 404

**Aspects:** documentation, implementation, code

**Evidence**

- `backend/Dockerfile` copies `frontend/dist` from the host rather than building it in a Node stage. The directory is ignored and absent in a clean checkout.
- In a clean archive at `/tmp/recalium-audit-clean-20260710`, `docker compose build recalium-app` failed at the `COPY frontend/dist/` step.
- The frontend uses `BrowserRouter` (`frontend/src/App.tsx:29-46`), while the backend mounts plain Starlette `StaticFiles(html=True)` (`backend/app/main.py:281`). There is no SPA index fallback.
- Live production probes returned `/` 200 but `/facts`, `/search`, `/settings`, and `/review-queue` 404.
- The README requires host-side frontend build steps, despite the product requirement that non-developer setup should approach `docker compose up`.

**Impact**

The documented primary install path fails from source, and refreshing or bookmarking a core page breaks a running installation.

**Recommendation**

Use a reproducible multi-stage image: frozen pnpm install, frontend build, Python dependency install, then copy artifacts into the runtime image. Add an explicit fallback that serves `index.html` only for non-API/non-MCP application routes. Publish a pinned image digest for non-developer users.

**Closure gate**

A CI job must clone into an empty directory, run the documented one-command install, pass health checks, and return the SPA for every registered UI deep link while preserving correct API/MCP 404 behavior.

### 8. P0 — The “stable memory bundle” is a raw archive, not portable memory

**Aspects:** idea, documentation, implementation, evaluation

**Evidence**

- Canonical portability requirements promise raw content, summaries, facts, canonical memory, provenance, and metadata (`docs/requirements/nfr.md`; `docs/architecture/portability-and-export.md`).
- `docs/architecture/memory-bundle-schema.md:3-10,49-52` explicitly excludes summaries, facts, links, embeddings, and canonical items while calling the format stable.
- `backend/app/api/routes/portability.py:47-79` exports only active `RawArchiveItem` rows.
- Import reads only `raw_content`, `source_name`, and optional content hash (`portability.py:109-139`). It ignores original ID, source type, metadata, ingest time, and conversation count, then reprocesses content under the current provider/model.
- Export materializes every raw item and all plaintext in memory rather than streaming.

**Impact**

Round-trip import loses curation, derivation identity, provenance, links, audit history, stable IDs, and potentially the semantic content produced by a different model. Calling it portable memory overstates the implementation and weakens the proposed interoperability moat.

**Recommendation**

Either rename v1 to “source archive bundle” and narrow all claims, or define a versioned, independently specified graph bundle containing typed raw, normalized conversation/turn, derived, canonical, provenance, link, tombstone, and audit records. Include content hashes, schema migrations, streaming, and conflict rules.

**Closure gate**

Export from one installation and import into a blank installation without provider access; verify stable IDs and byte/semantic equality of all portable records, deleted-item non-resurrection, deterministic retrieval, and conformance against an implementation-independent fixture.

### 9. P0 — Concurrent deletion and canonical promotion can violate source integrity

**Aspects:** implementation, code

**Evidence**

- The dispatcher checks `RawArchiveItem.deleted_at IS NULL` only when a job begins (`backend/app/worker/dispatcher.py:647-672`). Later helper stages commit summaries, facts, FTS rows, embeddings, conflicts, and links independently.
- Deletion marks current derived rows removed but does not cancel or lock active jobs. A worker can create new active derived rows after the delete transaction completes.
- Canonical promotion accepts client-supplied `fact_id`, `raw_archive_id`, `content`, and `has_source_span` (`backend/app/api/routes/canonical.py:32-49`). `backend/app/domain/canonical_memory/service.py:27-57` inserts those values without loading or locking the fact, checking that it belongs to the archive, verifying active/deleted status, or deriving content/span state from the database.
- `promoted_by` and arbitrary status updates are also client-controlled.

**Impact**

Deleted memory can reappear through a race. A caller can construct a canonical item from mismatched, inactive, fake, or span-less source data and bypass the intended confirmation check.

**Recommendation**

Serialize deletion with processing through row locks or a durable cancellation/version token checked before every write. Make cascade updates and job cancellation one transaction. Promotion should accept only a fact ID plus explicit confirmation; load and lock the fact/source, derive all content/provenance fields server-side, verify active status, and write an immutable actor identity from authentication context.

**Closure gate**

Deterministic concurrency tests must pause the worker before each stage, delete the source, resume it, and prove no active derivative is committed. Adversarial API tests must fail all mismatched/deleted/fabricated promotions.

### 10. P0 — Conflict detection creates empty groups, and review resolution does not resolve memory

**Aspects:** documentation, implementation, evaluation, code

**Evidence**

- `backend/app/domain/conflict_detection.py:67-89` accepts `fact_ids` but explicitly does not store them.
- The worker compares archive-level embeddings, creates an empty duplicate group, and never calls `materialize_review_item` (`backend/app/worker/dispatcher.py:851-871`).
- No contradiction classification is performed by this path, despite contradiction being a v1 promise.
- Review queue “resolve” records only a status, note, resolver, and timestamp (`backend/app/domain/review_queue/service.py:57-78`). It does not choose, merge, correct, archive, suppress, or relink candidate facts.

**Impact**

Conflict groups are not connected to evidence, the queue is generally not populated by processing, and marking an item resolved leaves the underlying retrieval candidates unchanged. The curation loop is present as UI/schema scaffolding but not as product behavior.

**Recommendation**

Detect conflicts between fact records, persist memberships and evidence, distinguish duplicate/overlap/contradiction, and materialize queue items transactionally. Define explicit resolutions with domain effects: keep A, keep B, merge, mark temporal update, mark both context-dependent, or suppress. Reindex and audit each resolution.

**Closure gate**

Seed known duplicate and contradictory facts from different sources, prove they reach one evidence-backed queue item, apply every resolution, and assert the resulting facts, canonical items, links, retrieval results, provenance, and audit entries.

### 11. P1 — MCP retrieval access is not durably audited and error contracts are inconsistent

**Aspects:** documentation, implementation, evaluation, code

**Evidence**

- `retrieve()` adds and flushes an `AuditEvent`, leaving commit to the caller (`backend/app/domain/retrieval/service.py:628-641`).
- `retrieve_memory` exits its standalone session without committing (`backend/app/mcp_server/server.py:102-105`). A live request using actor `codex-gpt5.6-solution-review` returned results, while a direct database query found zero events for that actor.
- Cache hits intentionally emit no audit event (`retrieval/service.py:543-548`), contradicting “every machine access” semantics.
- Audit metadata omits touched item IDs, success/failure, transport/session identity, cache status, and policy detail.
- `ingest_memory` uses a structured error envelope, but `get_fact_links` returns free-form `{"error": ...}` responses (`mcp_server/server.py:132-167`). Some stale MCP integration tests expect the old format and currently fail.

**Impact**

The audit log cannot answer which client read which memory. That undermines the primary trust and governance claim and makes incident investigation impossible.

**Recommendation**

Use a transaction boundary owned by each MCP tool or an explicit committed audit writer. Audit every attempt, including cache hits and failures, using authenticated server-derived client identity and touched record IDs. Standardize all tools on one versioned success/error envelope and validate inputs before domain execution.

**Closure gate**

For cached, uncached, successful, invalid, empty, degraded, and failed MCP calls, assert exactly one durable audit event with immutable client identity, outcome, policy, item IDs, and correlation ID after reconnecting with a new database session.

### 12. P1 — Extraction and ranking metrics contain correctness defects

**Aspects:** evaluation, code

**Evidence**

- `evals/metrics.py:169-173` treats a missing source span as faithful.
- Matching is not one-to-one (`metrics.py:254-317`): multiple duplicate predictions can match one golden fact. A direct probe with one golden fact and three duplicate predictions returned recall 1.0 and precision 1.0 instead of precision 0.333.
- Conversations that produce zero facts are absent from the evaluated extraction set (`evals/checks/eval_extraction.py:178-211`), inflating recall.
- nDCG builds its ideal ordering from returned relevance rather than complete qrels (`metrics.py:132-151`), so omitted relevant documents need not reduce the denominator.
- Thresholds are loaded from `evals/thresholds.json`, but individual checks hardcode values. Report comparison expects metric names the checks do not emit, leaving the committed threshold table empty; the `>` operator is unsupported.
- There are no focused unit or property tests for the metric and threshold engine.

**Impact**

Extraction precision, provenance fidelity, ranking quality, and frozen-threshold compliance can all be overstated independently of the small dataset problem.

**Recommendation**

Implement maximum one-to-one matching, count missing spans as failures, retain every expected source in the denominator, calculate nDCG from full graded qrels, and evaluate canonical metric IDs centrally from configuration. Fail on duplicate/unknown/missing IDs and unsupported operators.

**Closure gate**

Add table-driven and property tests for empty outputs, duplicates, ambiguous matches, missing spans, missing relevant documents, ties, every comparison operator, unknown metrics, and threshold mutation.

### 13. P1 — The declared test and quality gates are red, skipped, or absent from CI

**Aspects:** documentation, implementation, evaluation, code

**Evidence**

- Backend: `uv run pytest -q -rs` produced **3 failed, 234 passed, 11 skipped**. Failures are stale MCP integration expectations. Skips include backup/restore, embeddings/policy without optional dependencies, and live auth.
- Backend static checks: `uv run ruff check app tests` reported **27 errors**; `uv run mypy app` reported **103 errors in 28 of 63 files**, despite strict configuration.
- Frontend: `pnpm build` passed, but `pnpm test` failed because Vitest collected the Playwright spec. Four scoped component files and nine tests pass.
- `@playwright/test` is in `package.json` but absent from the lockfile; `pnpm install --frozen-lockfile` fails and `pnpm test:e2e` cannot run.
- The only GitHub Actions workflows deploy or preview `website/**`. There is no application build, test, migration, Compose, MCP, accessibility, eval, or release workflow. The Makefile's validation target omits Playwright and evals.

**Impact**

The repository cannot enforce its own documented commands on a clean change. Important tests are silently skipped, and a green website deployment can coexist with a broken application.

**Recommendation**

Create required PR and release pipelines for frozen installs, lint/type checks, backend/unit/integration tests with Postgres/pgvector and optional dependencies, frontend component tests, Playwright/axe, clean image build, migrations, MCP contract/live clients, and strict evals. Upload immutable evidence and fail on unexpected skips.

**Closure gate**

All documented validation commands pass from a clean checkout in CI; the release job uses the same image and configuration users receive; and any expected skip is explicitly allow-listed with an owner and expiry.

### 14. P1 — Keyboard accessibility and core curation workflows are incomplete

**Aspects:** documentation, implementation, evaluation, code

**Evidence**

- Ingest tabs place inactive tabs at `tabIndex=-1` without arrow-key behavior (`frontend/src/pages/IngestPage.tsx:62-76`), so a keyboard user cannot reach Upload through the tablist pattern.
- The upload drop zone has `role="button"` but no `tabIndex`, Enter/Space handler, or focus behavior, while its file input is hidden (`IngestPage.tsx:135-163`).
- The first-run dialog lacks initial focus, focus containment, Escape handling, and restoration (`frontend/src/pages/WizardPage.tsx:124-199`).
- Fact, canonical, and review views display partial source text but do not provide a complete source/provenance navigation surface.
- Search exposes query and mode only; documented category, source, time, canonical, tag, and budget controls are absent.
- The only Playwright file calls itself a starter and covers a main landmark, one focus movement, and route smoke. It omits full workflows, review queue, settings, dialogs, errors, keyboard-only operation, multiple viewports, and axe.

**Impact**

Acceptance criterion 28 is not met, and users cannot complete important ingest and curation work without a pointer. The UI skeleton is broad but does not yet prove the trust loop.

**Recommendation**

Adopt tested primitives for tabs and dialogs, use native focusable upload controls, add a shared provenance drawer, implement all search filters, and design actual review-resolution interactions. Run keyboard-only and automated accessibility tests against the production image.

**Closure gate**

Record and automate complete keyboard-only flows for first run, upload, retry, search/filter, source inspection, promotion, conflict resolution, deletion, backup, and restore confirmation with zero serious axe violations.

### 15. P1 — Public website and repository claims are materially inaccurate

**Aspects:** idea, documentation, implementation

**Evidence**

- The website points to `github.com/recalium/recalium`, while this repository's configured origin is `github.com/andr-ca/recalium`.
- Website setup uses UI port 8080, MCP port 3000, `/mcp`, and variables such as `RECALIUM_PORT`, `MCP_PORT`, and `SENSITIVITY_GATE`. The actual stack uses port 8000 and `/mcp/sse`; those variables are not implemented.
- It advertises uploading a ChatGPT ZIP, a working key wizard, and an `ingest(...)` tool shape that do not match the application.
- Pricing, features, and footer say “MIT License” and “always OSS,” but the repository contains no `LICENSE`, `COPYING`, or `NOTICE` file.
- README release status, MCP gaps, and operational gap entries contradict newer implementation logs and artifacts.

**Impact**

New users follow instructions that fail, and legal/open-source claims are unsupported. This creates trust and adoption risk before users reach the product.

**Recommendation**

Treat public copy as executable documentation. Generate commands and tool schemas from tested source, verify links/ports in CI, and block deployment when examples fail. Choose and commit an OSI-approved license before using “open source” or “MIT.” Label aspirational capabilities as roadmap items.

**Closure gate**

Every website command and API/MCP example runs in a clean CI environment, the repository URL and ports are canonical, capability claims map to passing evidence, and counsel/maintainers approve the committed license and contribution policy.

### 16. P1 — Requirements, plans, and operational status are not traceable or internally current

**Aspects:** documentation, implementation, evaluation

**Evidence**

- Requirements remain “draft ready for review” while README describes release-readiness implementation.
- Stable requirement IDs were deferred until before implementation, but implementation is already advanced. There is no bidirectional requirement → architecture → epic → test/evidence → status matrix.
- The requirements-review directory contains a handoff and blank template, while the handoff simultaneously claims a checklist passed and requests review.
- The v1 plan includes a post-v1 workstream containing browser extension, temporal decay, auto-curation, and ecosystem clients; conflict detection appears both as v1 and post-v1.
- Architecture says React 18 while the project uses React 19, lists a deferred browser extension as a primary actor, and does not index the stable bundle schema/ADR.
- The gap register retains resolved items as blockers and cites metric values that differ from linked artifacts.

**Impact**

“52/52 requirements met,” approved architecture, and release-ready status cannot be independently audited. Contributors and agents can select contradictory sources of truth.

**Recommendation**

Assign immutable atomic IDs now. Build a generated traceability matrix with one current status authority and immutable point-in-time review records. Separate v1 and roadmap packages. Add documentation assertions for stack versions, ports, tool names, scope, evidence links, and metric values.

**Closure gate**

Every v1 requirement has an owner, severity, architecture decision, implementation link, automated/manual evidence, status, and release disposition; no release claim is derived from prose alone.

### 17. P1 — Provenance and canonical-memory integrity are below the product's trust promise

**Aspects:** idea, documentation, implementation, evaluation

**Evidence**

- Retrieval provenance commonly includes derivation method/model and an excerpt plus top-level source fields, but not the full required conversation/session ID, import method, source hash, derivation timestamp, modifying identity, or complete source-span coordinates.
- MCP audit events do not list returned IDs, and cache hits are absent.
- Facts and canonical items do not consistently navigate to their full raw source in the UI.
- Canonical promotion trusts client content and source-span flags rather than immutable database provenance (finding 9).
- The quality baseline measures span fidelity only for extracted facts, then overgeneralizes it to returned items.

**Impact**

The strongest differentiation claim—inspectable, trustworthy memory—cannot be consistently demonstrated from an MCP response or UI item back to immutable source evidence.

**Recommendation**

Define one provenance envelope used by facts, summaries, links, canonical items, retrieval results, exports, UI, and audit. Make source coordinates and derivation identity immutable; model user edits as new versions. Provide a source viewer that highlights the exact span and shows the full derivation chain.

**Closure gate**

For every returned item type, an automated contract test follows IDs to an active raw source, verifies a byte-valid span and source hash, identifies the derivation and editor, and fails closed when any link is missing.

### 18. P1 — The separate `memory/` subsystem introduces credential and prompt-injection hazards

**Aspects:** implementation, code

**Evidence**

- `memory/scripts/copilot_client.py:29-36,50-52,183-207` uses GitHub's `copilot_internal` token endpoint and an OpenAI-compatible Copilot endpoint, stores both OAuth and Copilot tokens as plaintext JSON under the user's home directory, and does not explicitly set mode `0600`.
- Automatic hooks can send conversation context to that external service (`memory/scripts/flush.py:76-121`; `memory/hooks/session-end.py`; `memory/hooks/pre-compact.py`) outside Recalium's sensitivity policy and audit model.
- Model-controlled paths are joined to `ROOT_DIR` and written without resolved-path containment checks (`memory/scripts/compile.py:147-160`; `memory/scripts/query.py:101-115`). Prompt-injected `../` or absolute paths can escape the intended knowledge directories.
- The subsystem duplicates the main product's memory behavior while bypassing its storage, provider, provenance, deletion, and policy contracts.

**Impact**

Local transcripts can leave the machine unexpectedly, credentials may be exposed to other local users or backups, and untrusted model output can write outside intended directories. The code also depends on an internal service contract that can change without notice.

**Recommendation**

Quarantine or remove the subsystem from the release. If retained for development, use documented APIs, OS credential storage or strictly permissioned short-lived files, explicit opt-in, sensitivity screening, redaction, audit, and path containment via `resolve()` plus `is_relative_to()`. Prefer consuming the main Recalium MCP contract instead of maintaining a shadow memory system.

**Closure gate**

Security tests must prove no automatic external call without consent, restrictive credential permissions and rotation, zero secret logging, containment against absolute/traversal/symlink paths, and consistent deletion/audit behavior.

### 19. P1 — “Exposed mode” is neither fully configured nor securely implemented

**Aspects:** documentation, implementation, code

**Evidence**

- `.env.sample` advertises bind host, bearer authentication, watch directory, and provider/model overrides, but Compose does not pass several of these variables to the application container.
- The container therefore retained default bind/auth/provider settings during inspection. The entrypoint binds internally to `0.0.0.0`, while host mapping is fixed to loopback.
- The frontend API client does not attach a bearer token, so enabling bearer auth would also break the UI without an authenticated session design.
- Architecture requires authentication, UI sessions, client identity, and encrypted transport but does not implement credential lifecycle, CSRF/CORS/Host protections, TLS termination, or rate limiting.

**Impact**

Operators may believe documented environment controls are active when they are not. Manually exposing the service can make a local, unauthenticated application reachable without the security profile the documentation implies.

**Recommendation**

Declare network exposure unsupported in v1 unless a complete deployment profile is shipped. Pass and validate all supported environment settings, fail startup on unsafe exposure, implement authenticated UI sessions and server-derived MCP identity, and document a TLS reverse proxy, origin/host policy, rate limits, and secret rotation.

**Closure gate**

Configuration-contract tests inspect the running container, and an external black-box security test proves unauthenticated rejection, authenticated UI/MCP use, secure cookies/headers, allowed origins/hosts, TLS, rate limiting, and immutable audit identity.

### 20. P1 — The evaluation suite lacks representative, isolated, and scale evidence

**Aspects:** documentation, evaluation, implementation

**Evidence**

- Requirements call for 200 real anonymized ChatGPT/Claude conversations; the committed suite has four synthetic conversations.
- Ingest latency P95 is computed over four tiny payloads. There is no 5 MB import, 100k-item corpus, concurrency/load, long-context, multilingual, branch/tool-call, backup/restore, canonical conflict, deletion race, or exposed-auth benchmark.
- Evals write into the user's normal database. Cleanup soft-deletes earlier eval items but leaves tombstones/jobs/audits and some marker data. Live retrieval during this audit was dominated by eval, smoke, E2E, and debug material; all listed tags were test-oriented.
- Reports lack complete raw per-case data, git/image digest, dirty state, dataset/threshold hashes, provider parameters, seed, hardware, full command/stdout, and environment fingerprint.

**Impact**

The suite contaminates the product it measures, cannot estimate real-world quality, and cannot reproduce performance or provider-dependent results independently.

**Recommendation**

Run each evaluation in an ephemeral database/schema and disposable service stack. Build stratified development and sealed holdout corpora from consented/redacted real exports, plus synthetic adversarial sets. Record immutable inputs, per-case outputs, environment, commit/image, models, seeds, cost, and timing distributions.

**Closure gate**

Meet the documented real-corpus and scale requirements with confidence intervals, no production-data contamination, human-reviewed labels, multiple provider/model runs, and a signed artifact reproducible from a clean checkout.

### 21. P1 — Provider and embedding routing only partially implements the configuration model

**Aspects:** documentation, implementation, code

**Evidence**

- Summarization and extraction resolve configured providers/models, but embedding uses local `all-MiniLM-L6-v2` and does not honor advertised `embed_provider` or `embed_model` settings.
- Retrieval SQL and provenance hardcode the same local embedding model (`backend/app/domain/retrieval/service.py:341-429`).
- Provider errors are often handled as non-fatal warnings, which can mark a job complete with missing derivative types unless callers inspect secondary state.
- Link classification reuses extraction provider configuration rather than a clearly defined, separately policy-gated operation.

**Impact**

Users cannot rely on the configuration or cost/privacy preview, changing models can strand incompatible vectors, and “complete” does not necessarily mean the requested processing finished.

**Recommendation**

Make every processing stage a typed operation with effective provider/model/policy recorded per job. Version embedding spaces, validate dimension/model compatibility, schedule reindex migrations, and represent partial completion explicitly rather than swallowing failures.

**Closure gate**

Matrix tests prove every documented provider/model setting affects the intended stage, policy gates every network call, incompatible vectors cannot mix, and status exposes complete/partial/degraded/failed outcomes precisely.

### 22. P1 — Frontend error and deleted-item states can misrepresent the system

**Aspects:** implementation, code

**Evidence**

- Canonical load failures are logged and then shown as an empty collection (`frontend/src/pages/CanonicalPage.tsx:15-31`). Settings and telemetry failures are swallowed; retry failures in `ArchiveItemCard` have no durable error surface.
- The frontend uses `deleted_at` to render deleted archive items, while the backend list response constructor omits that field for list entries (`backend/app/api/routes/archive.py:109-128`). “Show deleted” can therefore render a deleted item as active with another Delete action.
- Several pages conflate loading, empty, degraded, and failed states.

**Impact**

An outage can look like “no memory,” and destructive/restore decisions may be made from incorrect state.

**Recommendation**

Use generated or shared API types and explicit loading/empty/error/degraded states with retry and correlation IDs. Add contract tests for every response field and visual tests for failure conditions.

**Closure gate**

Simulated 4xx, 5xx, timeout, malformed, offline, partial, and deleted responses render distinct accessible states and never expose an invalid destructive action.

### 23. P1 — The differentiation thesis and market evidence need a 2026 reset

**Aspects:** idea, documentation

**Evidence**

- The competitive document says ChatGPT memory cannot be inspected and portrays Mem0 as cloud-only/API-only with no visible storage or audit trail. Current official material documents ChatGPT memory controls and Mem0's self-hosted open-source stack, dashboard/audit capabilities, and MCP offering.
- Gemini now documents cross-platform import and importing complete AI chat histories, weakening the claim that no major provider helps users bring prior context.
- Primary validation remains repository-authored requirements and a synthetic evaluation; there is no documented evidence that target users prefer source-span provenance, a canonical layer, or self-hosting enough to switch behavior.

Current sources: [OpenAI memory controls](https://help.openai.com/en/articles/8983136-what-is-memory_.pdf), [Mem0 open-source setup](https://docs.mem0.ai/open-source/setup), [Mem0 MCP](https://docs.mem0.ai/platform/mem0-mcp), and [Gemini import documentation](https://support.google.com/gemini/answer/16868299?hl=en).

**Impact**

Local-first and MCP-native are no longer durable differentiators on their own. Stale comparisons damage credibility and can drive the roadmap toward already-commoditized features.

**Recommendation**

Replace prose claims with a dated, cited capability matrix and user research. Focus the wedge on independently verifiable provenance, raw/derived/canonical separation, deletion-safe local custody, cross-provider conformance, and user-controlled conflict resolution—only where Recalium actually proves those capabilities.

**Closure gate**

Interview and observe at least the three named personas using a working import/retrieval loop; document willingness to adopt/pay, switching barriers, and which trust features change decisions; refresh the competitor matrix quarterly.

### 24. P1 — The initial customer, packaging, and business model are unresolved

**Aspects:** idea, documentation, implementation

**Evidence**

- One primary persona is a non-developer research user who may lack provider keys and abandons complex setup; the business model assumes the primary audience already has keys.
- Current source installation requires frontend build knowledge and fails from a clean checkout. The UI is simultaneously positioned as a consumer product and an audit console for MCP developers.
- A managed paid tier is described as near-term while tenant isolation, identity, billing, abuse controls, support, hosted key custody, compliance, and service economics are explicitly out of v1 scope.
- “Always open source” has no committed license.

**Impact**

The product risks optimizing for incompatible onboarding, security, and feature expectations and cannot make credible pricing or adoption forecasts.

**Recommendation**

Choose an initial beachhead. For developers, ship a reliable MCP/API memory service with an audit console and explicit local-operator setup. For research users, ship a signed prebuilt image/desktop experience, vendor import, no-terminal onboarding, and a safe default processing option. Treat managed processing as a separately validated business and security program.

**Closure gate**

Define one v1 ICP, activation event, distribution channel, acceptable setup time, retention measure, support model, and pricing hypothesis; then validate them with external users before expanding scope.

### 25. P2 — MCP transport and client evidence should move to the current standard

**Aspects:** documentation, implementation, evaluation

**Evidence**

- The implementation and metadata identify the transport as legacy HTTP+SSE (`/mcp/sse`). The MCP specification says Streamable HTTP replaced the older HTTP+SSE transport in the 2025-03-26 protocol revision.
- The repository locks MCP Python SDK 1.26.0 and has limited live-client evidence; concurrent clients, reconnect/replay, backpressure, auth identity, and cancellation are not exercised.

Current sources: [MCP transport specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) and [official Python SDK](https://github.com/modelcontextprotocol/python-sdk).

**Impact**

Legacy transport increases compatibility and migration risk for a product positioning itself as MCP-native.

**Recommendation**

Add Streamable HTTP behind a versioned endpoint, retain SSE only for a documented compatibility window, and test the target clients against the exact deployed image.

**Closure gate**

Publish a client/transport/version matrix with automated concurrent connection, reconnect, cancellation, auth, error, and compatibility tests.

### 26. P2 — Maintainability is constrained by static debt and oversized orchestration modules

**Aspects:** implementation, code

**Evidence**

- Ruff reports 27 backend errors and seven more under `memory/scripts` and `memory/hooks`.
- Mypy reports 103 errors across 28 backend modules despite strict configuration.
- `backend/app/worker/dispatcher.py` is roughly 886 lines, retrieval service roughly 644 lines, and settings/front-end pages also combine many responsibilities.
- Broad exception handlers frequently log, roll back, and continue, obscuring invariant violations and partial outcomes.

**Impact**

Type contracts do not protect high-risk data paths, changes have large blast radii, and “non-fatal” recovery can hide corruption or missing output.

**Recommendation**

Make static checks green before adding features. Split orchestration into explicit stages with typed inputs/outcomes, central transaction policy, retry classification, and domain invariants. Ban broad catches except at process boundaries and surface partial completion.

**Closure gate**

Ruff and strict mypy pass with no blanket suppressions; complexity budgets and ownership boundaries are enforced; mutation/fault-injection tests show stage failures cannot produce a false complete state.

### 27. P2 — “Local-first” wording is stronger than the implemented privacy model

**Aspects:** idea, documentation, implementation, evaluation

**Evidence**

- External summarization, extraction, and potentially other processing are part of normal configured operation, while public copy foregrounds that data stays local.
- The gate taxonomy emphasizes profile and relationships, although full AI histories can contain health, finance, credentials, legal, employment, minors, and intimate data.
- Privacy evidence uses one synthetic sensitive item and does not capture outbound network payloads.

**Impact**

Users may interpret local-first as local processing rather than local storage/custody with optional remote processing.

**Recommendation**

Use the precise phrase **“local custody; optional remote processing”** until fully local processing is the default. Show a per-batch data-flow preview, provider destination, categories, estimated data volume/cost, and explicit consent. Expand and independently test the threat taxonomy.

**Closure gate**

User-facing copy, runtime network behavior, policy audit, and a capture-proxy privacy test all describe and demonstrate the same data flow.

## Aspect-by-aspect review

### Product idea — revalidated 68/100 (baseline 68)

**What is strong**

- The pain is clear: accumulated AI context is fragmented, opaque, and difficult to move.
- The “stop re-explaining” activation moment is easy to understand and potentially frequent.
- Separating immutable raw evidence, derived memory, and explicitly curated canonical memory is a better trust model than a single mutable vector store.
- Source-span provenance, deletion propagation, offline custody, and open interchange are meaningful user values when they are truly implemented.
- The personas contain real workflows, friction limits, and outcomes rather than demographic filler.

**What limits the score**

- The competitive comparison is stale in a rapidly converging category.
- The initial customer alternates between a non-technical researcher and an MCP developer.
- The v1 scope includes ingestion, extraction, retrieval, curation, conflict management, portability, backup/restore, multiple providers, UI, MCP, and exposed mode before the core loop is proven.
- The interchange format and provenance layer are aspirations rather than demonstrated ecosystem advantages.
- There is little external discovery, usability, retention, willingness-to-pay, or switching evidence.

**Product recommendation**

Position v1 as a **provenance-first, locally custodied memory service for AI power users and MCP developers**. Make the UI an audit/curation console. Win on faithful import, transparent retrieval, deletion safety, and portable evidence before adding broad automation or a managed tier.

### Documentation — revalidated 66/100 (baseline 61)

**What is strong**

- The repository has unusually broad coverage across requirements, architecture, plans, operations, and guides.
- Architecture is strongest around module boundaries, queue semantics, deterministic ranking intent, source-status propagation, tombstones, and staged restore.
- Requirements generally use direct language and include acceptance criteria and non-functional targets.
- Relative-link validation found **zero broken local paths across 69 Markdown files**.
- The evaluation documentation discloses that its data is synthetic rather than hiding the limitation.
- The remediation response narrows the flagship claim, distinguishes source-archive portability, clarifies local custody versus remote processing, and adds a concrete status ledger.
- An MIT license now supports the repository's core open-source claim.

**What limits the score**

- There is no stable, auditable traceability system despite advanced implementation.
- “Draft,” “approved,” “release-ready,” and “blocked” states conflict across documents.
- Current stack versions, ports, routes, tool schemas, and implemented gaps have drifted.
- Canonical portability requirements still exceed the implemented source-archive bundle.
- Several website commands and capability claims remain inconsistent with the application, despite the license correction.
- Measured evidence is sometimes copied incorrectly or generalized beyond what a check proves.

**Documentation recommendation**

Make one machine-checked release manifest the status authority. Give each atomic requirement a permanent ID and evidence link. Archive historical reviews, generate public examples from contracts, and fail CI when claims, versions, metrics, or commands diverge.

### Implementation — revalidated 49/100 (baseline 43)

**What is strong**

- A live health endpoint, Postgres/pgvector storage, API, worker, MCP tools, UI, and audit schema are present and largely connected.
- Ingest is asynchronous and records raw source, hash, audit event, and job transactionally.
- Source-status filtering appears in many read paths, and idempotency support exists for MCP ingestion.
- Canonical memory, links, review queue, portability, settings, backup, and provider abstractions have concrete schema/service foundations.
- The system degrades from semantic to keyword retrieval when local embedding support is unavailable.
- The committed remediation adds per-conversation ChatGPT/Claude JSON import, a reproducible image build, SPA deep-link handling, selected retrieval filters, durable first-access MCP audits, and corrected deleted-item state.

**What limits the score**

- Vendor import is now a meaningful JSON-only foundation, but ZIP streaming, exact branch/raw fidelity, preview, checkpointing, and representative evidence remain; first-run provider configuration, full portability, conflict resolution, and exposed security are incomplete.
- Deletion, processing, promotion, and restore have high-risk transaction/integrity gaps.
- Category/pre-ranking filters, RRF fusion, fact indexing, conflict labels, provenance, cache-hit audit, and server-derived identity do not meet their contracts.
- Privacy-related MCP inputs are metadata only.
- Packaging now builds and starts reproducibly, but its SPA fallback incorrectly converts unknown API routes into HTTP 200 HTML responses.

**Implementation recommendation**

Freeze feature expansion. Implement and verify the six-step trusted loop in the executive assessment, using explicit transaction boundaries and contract tests. Remove or label every non-functional surface instead of keeping optimistic scaffolding in the release UI/API.

### Evaluation suite — revalidated 39/100 (baseline 32)

**What is strong**

- The harness calls a real live API and MCP client rather than testing only mocks.
- It polls asynchronous processing, captures degraded modes, uses server-assigned IDs for current-run retrieval, and produces JSON/Markdown artifacts.
- The suite has already found real pipeline defects and is useful as a local development diagnostic.
- Five named quality areas—ingest, extraction, retrieval, sensitivity, and MCP—are represented.
- A strict mode now fails on skipped/errored checks, and seven focused tests cover corrected span, duplicate-matching, and nDCG helper behavior.

**What limits the score**

- Default development mode remains fail-open, and even strict mode does not make every recorded/non-200 retrieval error part of check pass logic.
- Labels are tiny, synthetic, tuned, archive-level, and not held out.
- Several metric helpers improved, but the evaluator does not pass full-qrel counts to corrected nDCG, excludes zero-fact sources, and still hardcodes thresholds outside the frozen configuration.
- It runs in the user's normal database and pollutes later retrieval.
- It does not cover actual vendor imports, scale, concurrency, deletion races, restore, accessibility, exposed auth, or full MCP contracts.
- Reports lack the provenance required for independent reproduction.

**Evaluation recommendation**

Treat the current suite as `dev-smoke`, fix its mathematics and fail behavior, and build a separate hermetic `release-eval` with sealed data, human labels, strict dependencies, complete provenance, representative scale, and independent reproduction.

### Code quality — revalidated 54/100 (baseline 47)

**What is strong**

- Backend domain folders and frontend API centralization provide a reasonable structure.
- At the remediation snapshot, the CI-equivalent backend command passed **219 tests** with 10 skips and three explicit deselections; nine frontend component tests passed.
- Frozen frontend install, frontend production build/typecheck, website check/build, clean Docker build/startup, seven eval-metric tests, `uv lock --check`, and Python compilation of the memory scripts passed.
- SQL generally filters active/deleted state on read paths, secrets are not modeled as database columns, and many UI controls use native elements and visible focus styles.

**What limits the score**

- Frontend defaults are now green, but the default backend suite remains red with three stale MCP tests; Ruff reports 27 errors and strict mypy reports 110.
- Application CI now enforces an allow-listed backend suite, frontend checks, and image build, but static checks are informational and startup/API semantics, Playwright/axe, live MCP, migrations, and strict release eval are not gated.
- Large orchestration modules and broad exception handling hide partial or invalid states.
- The separate `memory/` subsystem contains plaintext credential, external-data-flow, internal-API, and path-containment risks.
- API/domain boundaries trust client-supplied identity and provenance in high-value operations.

**Code recommendation**

Make clean, hermetic validation non-negotiable; reduce module responsibilities; use typed domain commands and server-derived identity/provenance; and complete a focused security review before any public deployment.

## Recommended remediation sequence

### Phase 0 — Correct public status and stop unsafe release paths

- Change release status to alpha/no-go.
- Remove or qualify 100% quality, ZIP import, working key wizard, full portability, MIT/OSS, and secure exposed-mode claims.
- Mark legacy `memory/` automation experimental and disabled by default.
- Keep public website commands and capability claims synchronized with tested behavior; the MIT license itself is now present.

### Phase 1 — Establish a clean, enforced engineering baseline

- Preserve the now-green clean Docker build and frozen frontend install; make default backend tests, Ruff, and mypy pass.
- Extend the new application CI with startup/API-semantic probes, Playwright/axe, MCP contracts, migrations, strict eval, and a strict skip policy.
- Restrict SPA fallback to non-API/non-MCP paths and fix Compose environment propagation.
- Split development and release evaluation modes and databases.

### Phase 2 — Deliver the real first-run loop

- Build versioned ChatGPT/Claude ZIP import with normalized conversations/turns, preview, selection, checkpointing, and evidence.
- Choose and correctly implement the BYOK secret model.
- Add complete provenance/source navigation.
- Prove first useful retrieval from a clean install.

### Phase 3 — Repair trust and integrity primitives

- Enforce processing policy before every provider call.
- Fix deletion/worker races and server-validated canonical promotion.
- Implement staged tombstone-safe backup/restore.
- Replace raw-only portability or narrow its name and promise.
- Build fact-backed conflict groups and semantic resolution actions.

### Phase 4 — Make retrieval and MCP dependable

- Apply all filters, index facts, fuse on stable document identity, integrate conflict state, and validate inputs.
- Commit every MCP audit attempt and standardize envelopes.
- Add Streamable HTTP and real-client compatibility/concurrency tests.

### Phase 5 — Earn release-quality evidence

- Freeze a representative, consented, anonymized holdout corpus.
- Correct metrics and centralized thresholds.
- Run scale, privacy capture, deletion/restore, accessibility, and end-to-end user studies.
- Publish reproducible artifacts tied to an immutable image digest.

## Minimum release gates

Recalium should not be called v1 release-ready until all of the following are true:

| Gate | Required evidence |
| --- | --- |
| Clean install | Empty checkout/image pull to healthy stack and every deep link, with no undocumented host build. |
| Real import | Current ChatGPT and Claude ZIP fixtures plus independently sourced exports; exact normalized counts and resumability. |
| Provider setup | One documented secret model; successful post-restart processing; no plaintext leakage. |
| Privacy | Capture-proxy proof that blocked/local-only content never reaches any external stage. |
| Retrieval | Fact-level held-out relevance; working filters; true cross-mode fusion; deleted/disputed exclusion. |
| Provenance | Every returned type resolves to immutable source bytes/span, derivation identity, and audit record. |
| Curation | Server-validated promotion and effective duplicate/contradiction resolution. |
| Deletion | Race-safe cascade plus proof that post-deletion backup/restore cannot resurrect content. |
| Recovery | Staged restore, validation, tombstone replay, cutover, rollback, and measured recovery time. |
| MCP | Versioned schema/errors, committed per-access audit, authenticated identity, current transport, real-client matrix. |
| Accessibility | Complete keyboard-only workflows and zero serious automated violations on the production image. |
| Quality suite | Strict fail-closed runner, sealed representative data, correct metrics, immutable provenance, independent reproduction. |
| Engineering | Default tests, frozen installs, Ruff, mypy, image build, migration, UI, MCP, and eval CI all green with no unexpected skips. |
| Legal/public claims | Committed license and public documentation whose commands and claims are CI-verified. |

## Baseline validation evidence at `0d7ea28`

This table preserves the original evidence that produced the 48/100 baseline. The later clean-snapshot results used for the revalidated 53/100 score are recorded under [Fresh remediation validation](#fresh-remediation-validation).

| Validation | Result |
| --- | --- |
| Live `/api/health` | **Pass:** `status=ok`, `db=ok`, API version 1. |
| Live production routes | **Fail:** `/` 200; `/facts`, `/search`, `/settings`, and `/review-queue` 404. |
| Clean-checkout `docker compose build recalium-app` | **Fail:** missing ignored `frontend/dist` at Docker `COPY`. |
| Backend `uv run pytest -q -rs` | **Fail:** 3 failed, 234 passed, 11 skipped. |
| Backend `uv run ruff check app tests` | **Fail:** 27 errors. |
| Backend `uv run mypy app` | **Fail:** 103 errors in 28/63 files. |
| Backend `uv lock --check` | **Pass.** |
| Frontend `pnpm build` | **Pass.** |
| Frontend `pnpm lint` | **Pass.** |
| Frontend `pnpm test` | **Fail:** nine component tests passed; Playwright spec was collected by Vitest and failed to resolve. |
| Frontend frozen install | **Fail:** lockfile is stale for `@playwright/test`. |
| Frontend Playwright command | **Fail:** Playwright package/command unavailable after the stale install. |
| Website `pnpm check` | **Pass:** zero errors and warnings. |
| Website `pnpm build` | **Pass:** five pages generated. |
| Memory `ruff check scripts hooks` | **Fail:** seven errors. |
| Memory script compilation | **Pass.** |
| Documentation relative links | **Pass:** zero missing local targets across 69 Markdown files. |
| Live MCP `canonical_only=true` | **Fail:** returned five non-canonical excerpts. |
| Live MCP audit persistence | **Fail:** successful actor-tagged retrieval; zero matching committed audit rows. |
| Eval duplicate precision probe | **Fail:** one golden plus three duplicate predictions scored precision 1.0. |
| Eval missing-span probe | **Fail:** missing span scored fidelity 1.0. |
| Eval artifact integrity | Committed files match the corresponding local outputs, but provenance is incomplete and claims exceed the measured scope. |

## Final verdict

Recalium is not vaporware and should not be discarded. It has a differentiated trust-oriented design, broad implementation, and a useful diagnostic test base. Its strongest assets are the problem framing, raw/derived/canonical separation, source-evidence intent, local custody, and a working cross-surface skeleton.

The project is also not ready for a public v1. Too many user-visible and safety-critical contracts currently exist as documentation, fields, UI surfaces, or schema scaffolding without enforced behavior. The evaluation suite then gives those incomplete surfaces more confidence than the data and mathematics justify.

**Latest independently revalidated score: 53/100; original baseline: 48/100.** The five-point rounded improvement is earned by real work in import decomposition, reproducible packaging, frontend/test reliability, selected retrieval and MCP fixes, evaluation strictness/metric helpers, CI, accessibility, licensing, and claim accuracy through `c83d0c8`. The score remains in alpha territory because the irreversible and trust-defining contracts—deletion/restore, processing policy at the frozen snapshot, transactional integrity, conflict resolution, graph portability, true hybrid retrieval, comprehensive audit, and representative release evidence—remain open. Later remediation commits require their own clean-snapshot verification before receiving score credit. Closing the ranked P0 gates with independent evidence would justify a fresh release-readiness review and rescore.
