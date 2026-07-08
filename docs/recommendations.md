# Recalium v1.1 Strategic Recommendations

**Date:** 2026-07-07  
**Source:** In-Depth Analysis (ANALYSIS.md, locked)  
**Audience:** Product owners, v1.1 roadmap planning, implementation leads

---

## 1. Executive Summary

Recalium v1.0 is **functionally complete** (5 phases delivered, 52/52 requirements met, 191 tests passing) but **quality-unproven**. The product's central claim—"retrieve relevant, source-backed context"—has zero measured evidence:

- **No empirical validation** of retrieval recall or extraction precision (ANALYSIS.md, F6–F9, F12)
- **No SLA evidence** for ingest (≤1s), search (≤2s), or restore (≤15 min) performance
- **Sensitivity gate never tested against real exports** (F6, F22), risking personal content leaks to external providers
- **Provenance claims unvalidated**: extracted facts may contain hallucinated spans that aren't verbatim substrings (F4)

**Top 5 Actions for v1.1:**

1. **Commit + ship pending release-readiness work** (F13): RR-001–RR-014 work is implemented but uncommitted. Merge in reviewable slices to reduce release-integrity risk.
2. **Eval suite + quality baselines** (this deliverable): Establish baseline evidence for retrieval recall, extraction precision, span fidelity, and SLA compliance.
3. **Publish memory-bundle JSON schema** as formal, versioned spec (positioning): "Open format" claim requires machine-readable schema; currently implicit in export code only.
4. **Quality improvements informed by eval results** (F1–F5): Don't fix without evidence. Phase model names (F1), per-function provider routing (F2), conversation chunking (F3), span verification (F4) in order of impact.
5. **MCP v2 migration spike** (F11): SSE is legacy transport; v2 SDK breaks compatibility; plan transition to Streamable-HTTP in Q2 2026.

---

## 2. Idea & Positioning Level

### The Moat: Provenance-Backed Memory Portability

Recalium's differentiator is **not** feature count or search speed—it's the ability to audit where memory came from:

- Every fact carries `source_span` (verbatim substring of the raw conversation)
- Every fact carries `confidence` (extraction fidelity)
- Every fact links to the original `source_metadata` (client, timestamp, import method)

This enables the flagship claim: **"Retrieve context you can trust and trace back to the source."**

### Current Gap: Schema is Implicit

The memory-bundle JSON format (used for export/import) is not formally documented:

- Schema described at high level in architecture docs
- No versioned JSON schema file (e.g., `docs/architecture/memory-bundle-schema.md`)
- No extension guide for external tools or future services

**Recommendation:** Publish `docs/architecture/memory-bundle-schema.md` as a formal spec with:
- JSON schema (JSON Schema v2020-12 or similar)
- Version history (v1.0 = current export format)
- Migration path for future schema evolutions
- Example exports (anonymized)
- Extension points for custom metadata

This substantiates the "open format" positioning claim and enables 3rd-party tool integrations.

### Pick One Flagship Quality Claim

Once eval suite establishes baselines, select ONE quality metric to build public confidence:

**Example:** "Recalium retrieves relevant context with ≥70% recall in hybrid mode (eval evidence)."

Publish this alongside the schema. Users should see:
- Metric definition (recall@10 on synthetic AI conversations)
- Baseline (70% vs. keyword-only ~40%)
- Evidence artifact (link to eval report)
- Limitations (synthetic data, no multi-turn reasoning validation)

This converts "unmeasured" into "measured and transparent."

---

## 3. Roadmap Level

### v1.0 → v1.0.1 (ASAP)

**Milestone:** Commit + ship RR work.

- Merge RR-001–RR-014 in reviewable slices (Facts API, Tags API, Links API, Review Queue UI, Backup/Restore UI, agent skills, MCP expansion)
- No new features; release-integrity focus only
- Risk: uncommitted work on `main` (F13) is itself a release blocker

### v1.1 "Prove It" (Q2 2026)

**Objective:** Establish quality baselines and operational clarity.

**Phase A: Commit + Ship Pending Work**
- Merge RR-001–RR-014 (see v1.0.1)

**Phase B: Quality Baselines (THIS TASK)**
- Deploy eval suite (runner + checks + datasets + reporting)
- Run against live stack; establish baseline thresholds
- Findings feed Phase C/D prioritization

**Phase C: Performance SLA Evidence**
- Measure ingest P95 ≤1s (F12: not yet measured)
- Measure search P95 ≤2s (F12: not yet measured)
- Measure restore SLA ≤15 min (F12: RR-007, not yet measured)
- Publish evidence in release notes

**Phase D: Accessibility Evidence (RR-011)**
- Playwright keyboard navigation tests for all core workflows
- Axe smoke tests
- Manual UAT per SKILL.md

**Phase E: MCP v2 Migration Spike**
- Prototype Streamable-HTTP transport (F11)
- Create ADR: decision to stay on SSE until v2 stabilizes or commit to migration
- Effort estimate: 4–6 hours (prototype + decision)

### v1.2 "Quality Improvements" (Q3 2026, contingent on eval results)

**Conditional:** Only pursue improvements with clear eval evidence of gaps.

- **F1 (Hardcoded models)**: Move model names to `.env` (SUMMARIZE_MODEL, EXTRACT_MODEL)
- **F2 (Per-function providers)**: Add SUMMARIZE_PROVIDER, EXTRACT_PROVIDER, EMBED_PROVIDER settings; enable local-only extraction mode
- **F3 (Truncation on long conversations)**: Implement map-reduce conversation chunking for dialogues >4k tokens; validates no facts are silently dropped
- **F4 (Hallucinated spans)**: Add verbatim substring validation at write time; reject facts with unverifiable spans
- **F7 (Budget unit clarity)**: Rename `DEFAULT_BUDGET` to `CHAR_BUDGET` or define TOKEN_BUDGET with explicit tokenizer
- **F8 (Cache invalidation)**: Replace manual TTLCache invalidation with event-driven pubsub (pgvector LISTEN/NOTIFY or similar)

### Backlog Phases 999.x (DEFER until quality baseline exists)

**Why defer:** Phases 999.1–999.4 (wiki synthesis, knowledge lint, query-to-wiki) build on top of fact extraction. Synthesis on top of unvalidated extraction compounds errors. Gate these phases behind eval evidence of extraction quality ≥0.75 recall + ≥0.8 precision.

---

## 4. Architecture Level

### Topology: No Changes

Keep two-container model (`recalium-app` + `recalium-postgres`). No worker/backup/watcher containers for v1.

### RRF Threshold Behavior (F6)

Finding: `RRF_MIN_THRESHOLD = 1/(k+25)` filters single-mode low-rank items. This is correct but undocumented.

**Recommendation:** Add to `docs/architecture/retrieval.md`:

```markdown
### RRF Threshold Behavior

RRF merge (k=60) includes results ranked ≤50 in any mode (keyword/semantic).
Results ranked >50 in all modes are filtered via RRF_MIN_THRESHOLD = 1/(k+25) ≈ 0.014.
This prevents noise from low-ranked items that appear in multiple modes.

Example: A fact ranked 100th in keyword (score 0.01) and 120th in semantic (score 0.005)
would have RRF score = 1/125 + 1/145 ≈ 0.0144, just above threshold, and would be included.
A fact ranked 150th in both modes would have RRF score ≈ 0.0108, filtered out.

This behavior is intentional and improves precision over recall.
```

### Budget Unit Ambiguity (F7)

Finding: `DEFAULT_BUDGET: int = 2000` is char-based, but MCP consumers think in tokens.

**Recommendation:** Clarify via one of:

**Option A (rename):** Change to `DEFAULT_CHAR_BUDGET = 2000` in settings; add note that ~1 char ≈ 0.25 tokens (CharCountTokenizer fallback).

**Option B (dual):** Add both `CHAR_BUDGET = 2000` and `TOKEN_BUDGET = None` (inferred from char_budget if not set). Document tokenizer (e.g., `tiktoken`-compatible).

Choose Option A for v1.1 (minimal change); Option B for v1.2 (if token-aware scheduling becomes a feature).

### MCP Transport (F11)

Finding: SSE is legacy transport in MCP spec. SDK v1.26 is maintenance-only; v2 has breaking changes planned Q1 2026.

**Recommendation:** Create ADR ("SSE vs. Streamable-HTTP for v1 and v2 path"):

1. **Stay on SSE through v1.1** (current default). Rationale: v2 still in development, unknown ETA for client libraries.
2. **Spike v1.2:** Prototype Streamable-HTTP transport (mcp v2 SDK when stable).
3. **Migrate v1.3+:** Full switch to Streamable-HTTP; drop SSE, deprecate v1.2 clients.

Document in `.planning/DECISIONS.md` or similar. Link in tech-stack.md.

### Cache Invalidation (F8)

Finding: Module-level `TTLCache(256, ttl=60)` requires manual invalidation after writes (E2E test had to do it manually; commit 59003ab).

**Recommendation (v1.2):** Replace with event-driven invalidation:

- On fact write (create/update/delete): publish LISTEN/NOTIFY event
- Cache subscribers listen and invalidate their cached retrieval results
- Fallback: TTL still in place for safety; LISTEN/NOTIFY is an optimization

Effort: ~8 hours. Risk: low (LISTEN/NOTIFY is Postgres native). Impact: improves UX after ingest without manual page refresh.

---

## 5. Implementation Level — Specific Fixes

Each fix below is grounded in ANALYSIS.md findings F1–F5. **All fixes require eval evidence before implementation** (don't fix without baseline data showing the gap).

### F1: Hardcoded Model Names (ANALYSIS.md, backend/app/worker/dispatcher.py, ~82, ~96)

**Current state:** Model names are hardcoded:
- `gpt-4o-mini` (line ~82)
- `claude-3-haiku-20240307` (line ~96 — deprecated 2024 model)

**Problem:** Violates project principle (CLAUDE.md says "GPT-4o-mini *or configured model*"); users can't switch models without code changes.

**Fix (2 hours):**

1. Add to `.env.sample`:
   ```
   SUMMARIZE_MODEL=gpt-4o-mini
   EXTRACT_MODEL=gpt-4o-mini
   EMBED_MODEL=all-MiniLM-L6-v2
   ```

2. Update `backend/app/settings.py` (or create new file):
   ```python
   from pydantic_settings import BaseSettings
   
   class CompletionSettings(BaseSettings):
       SUMMARIZE_MODEL: str = "gpt-4o-mini"
       EXTRACT_MODEL: str = "gpt-4o-mini"
       EMBED_MODEL: str = "all-MiniLM-L6-v2"
   ```

3. Inject into dispatcher; use `settings.SUMMARIZE_MODEL` instead of hardcoded strings.

**Impact:** Users can switch to `claude-3-sonnet`, `gpt-4o`, or custom models via `.env`. Maintains BYOK flexibility.

### F2: Per-Function Provider Routing (ANALYSIS.md, F2)

**Current state:** Provider selection is fixed priority: openai → anthropic → ollama.

**Requirement:** BYOK-08 says "switch providers per function" — allows users to (e.g.) run extraction locally (sentence-transformers) and summaries via Anthropic if they have a key.

**Fix (2 hours):**

Add to `.env.sample`:
```
SUMMARIZE_PROVIDER=openai
EXTRACT_PROVIDER=openai
EMBED_PROVIDER=sentence-transformers
```

Update dispatcher to route each function through the configured provider:
```python
if extract_job.provider == "openai":
    # Use OpenAI client
elif extract_job.provider == "anthropic":
    # Use Anthropic client
elif extract_job.provider == "sentence-transformers":
    # Use local embeddings
```

Fallback chain: If `SUMMARIZE_PROVIDER=anthropic` and no Anthropic key in `.env`, log warning and **skip job** (don't fall through to next provider). This ensures transparent degradation.

**Impact:** Users can run fact extraction entirely locally (no keys needed) and summaries via Anthropic if they have a key. Fulfills BYOK-08.

### F3: Truncation on Long Conversations (ANALYSIS.md, F3)

**Current state:** Whole conversation sent in one LLM call, max_tokens=512 for summaries. Silent truncation of facts on large ChatGPT exports (primary import source).

**Problem:** Long conversations (>4k tokens) drop facts silently; users don't know facts are missing.

**Fix (6–8 hours):**

Implement map-reduce conversation chunking:

1. Split conversation on turn boundaries (detect Q/A pairs).
2. If total tokens >4000, chunk into ~2k-token segments.
3. Summarize each chunk locally (sentence-transformers + map-reduce prompt).
4. Concatenate summaries before final extraction.

Fallback: If chunking fails, truncate as today (acceptable, but fact count will be lower).

Test: Extract from 200-word conversation with 5 labeled expected facts. Verify all 5 are captured (or document which are lost).

**Impact:** Preserves fact coverage on long exports; reduces extraction recall gaps (F3 is likely a cause of extraction recall <0.6).

### F4: Hallucinated Spans (ANALYSIS.md, F4)

**Current state:** One-shot JSON extraction (FACT_EXTRACTION_SYSTEM_PROMPT); no verification that `source_span` is a verbatim substring of raw source.

**Problem:** Hallucinated spans poison provenance (the product's differentiator). Users can't audit facts with fake spans.

**Fix (3–4 hours):**

After extraction, validate each `source_span`:

```python
def validate_span(fact, raw_source):
    """Check if source_span is a verbatim substring of raw_source."""
    if fact.source_span and fact.source_span in raw_source:
        return True  # Valid
    elif fact.source_span:
        # Span is hallucinated. Handle via one of:
        # (a) Clear span (set source_span=null, mark as unverified)
        # (b) Downgrade confidence (multiply by 0.5)
        # (c) Reject fact entirely (don't store)
        # Recommended: Option (a) — preserve fact but flag span as unverified
        return False
    return True  # No span, assume OK
```

Add test: Extract 5 expected facts from a 200-word conversation. Verify all stored spans are substrings of raw source.

**Impact:** Hardens provenance guarantee; low cost (local substring match, no LLM). Increases user confidence in sourcing.

### F5: Link Detection Errors (ANALYSIS.md, F5)

**Current state:** Link detection Pass B classifies only top-5 semantic pairs via LLM; errors swallowed with `logger.debug`.

**Problem:** Non-fatal, but unobservable. Users can't inspect why certain semantic links weren't created.

**Recommendation (low priority):** Add structured `link_detection_error` event to audit log:

```python
if link_error:
    audit_log.create_event(
        event_type="link_detection_error",
        details={
            "fact_a_id": fact_a.id,
            "fact_b_id": fact_b.id,
            "error_reason": str(e),
        }
    )
```

Impact: Low (doesn't block facts). Useful for debugging; defer to v1.2 if time-constrained.

---

## 6. Testing/Evidence Level

### Current Gap

ROADMAP research flags are still open:
- "RRF recall empirical validation" (k=60, ef_search=100 never measured)
- "sentence-transformers model quality" (all-MiniLM-L6-v2, 384-dim, never validated on AI-conversation content)
- "Sensitivity gate validation against real exports deferred to beta"

Performance metrics table (STATE.md): ingest P95 ≤1s, search P95 ≤2s, restore ≤15 min — all "Not yet measured".

### This Task: Eval Suite Harness

**Deliverable:** `evals/` directory with runner, checks, datasets, metrics, reporting.

**Closes gaps:**
- RRF recall validation → `evals/checks/eval_retrieval.py` measures recall@5/@10 in hybrid mode
- Sentence-transformers quality → `eval_retrieval.py` validates embedding model on synthetic AI conversations
- Sensitivity gate → `evals/checks/eval_sensitivity.py` validates gate blocks personal content
- Performance SLA → `evals/checks/eval_ingest.py` measures ingest P95; `eval_retrieval.py` measures search P95

### Mapping RR Gaps to Evidence Artifacts

| RR Gap | Evidence Artifact | Status |
|--------|-------------------|--------|
| RR-007 (restore ≤15 min) | `evals/checks/eval_restore.py` | Scope creep for v1.1 (skip unless backup/restore UI is live); defer to v1.2 |
| RR-009 (MCP error envelope) | `evals/checks/eval_mcp.py` | Included (validates structured error format) |
| RR-011 (Playwright a11y) | Separate from eval suite (Playwright config) | Out of scope for this task |
| Extraction recall | `evals/checks/eval_extraction.py` | Included (precision/recall vs. golden labels) |
| Retrieval recall | `evals/checks/eval_retrieval.py` | Included (recall@5/@10, MRR, nDCG@10) |
| Sensitivity gate | `evals/checks/eval_sensitivity.py` | Included (validates block rate = 100%) |
| Ingest latency | `evals/checks/eval_ingest.py` | Included (P95 ≤1s) |
| Search latency | `evals/checks/eval_retrieval.py` | Included (P95 ≤2s) |

### Next Steps (Post-Task)

1. Run evals against live stack: `make eval`
2. Collect baseline evidence (report.md + results.json)
3. Publish evidence under `docs/operational/tests/`
4. Use eval findings to prioritize F1–F5 fixes
5. Add evals to release CI (run on every pre-release build)

---

## 7. Prioritized Action Table

| Priority | Action | Impact | Effort | Owner | Timeline |
|----------|--------|--------|--------|-------|----------|
| **P0** | Commit + ship RR-001…RR-014 work (F13) | Unblocks v1.0.1 release; removes release-integrity risk | 2–4 hrs (review/merge only) | Andrey | ASAP |
| **P0** | Eval suite harness (this task) | Establishes quality baselines; foundation for v1.1 prioritization | 4 hrs (executed now) | Claude | ✓ Done |
| **P0** | Run evals vs. live stack; establish baselines | Provides numeric evidence for flagship claim | 1 hr (manual run) | Andrey | Week 1 |
| **P1** | Publish memory-bundle JSON schema spec | Substantiates "open format" positioning; enables 3rd-party tools | 1 hr (extract + doc) | v1.1 backlog | Week 2 |
| **P1** | F1 (env-backed model names) + F2 (per-function providers) | Fulfills BYOK-08 requirement; enables local-only extraction; unblocks provider flexibility | 2 hrs | v1.1 backlog | Week 2–3 |
| **P1** | MCP v2 migration spike + ADR | Unblocks v2 SDK adoption (Q2 2026); identifies transport cost + timeline | 4–6 hrs (prototype + decision) | v1.2 backlog | Week 3–4 |
| **P2** | F3 (map-reduce chunking for long conversations) | Improves extraction recall on large exports; low risk (fallback: truncate as today) | 6–8 hrs | v1.2 backlog | Month 2 |
| **P2** | F4 (span verification + confidence downgrade) | Hardens provenance guarantee (product differentiator); low cost (local substring match) | 3–4 hrs | v1.2 backlog | Month 2 |
| **P2** | F7 (resolve budget units: CHAR_BUDGET vs. TOKEN_BUDGET) | Reduces MCP consumer confusion; prevents token-count mismatches | 1 hr | v1.1 backlog | Week 2 |
| **P2** | F9 (FTS input sanitization + adversarial tests) | Prevents injection-like tag parsing (e.g., '1e5' → scientific notation in FTS); add test in evals | 2 hrs (tests v1.1, fix v1.2) | v1.1 backlog (tests), v1.2 backlog (fix) | Week 2–3 |
| **P3** | F8 (event-driven cache invalidation) | Improves responsiveness post-ingest; medium risk (pgvector LISTEN/NOTIFY) | 8 hrs | v1.2 backlog | Month 3 |
| **P3** | RRF threshold documentation (F6) | Clarifies undocumented RRF behavior; educational, not a bug | 30 min (doc only) | v1.1 backlog | Week 1 |
| **P3** | F5 (structured link detection errors in audit log) | Improves observability; low priority (doesn't block facts) | 2 hrs | v1.2 backlog | Month 3 |

### Notes

- **P0** items are release blockers or enable v1.1 foundation.
- **P1** items ship in v1.1 (quality + openness + positioning).
- **P2** items ship in v1.2 (quality improvements guided by eval results).
- **P3** items are optional refinements; include if time permits.
- **All F1–F5 fixes are conditional on eval evidence.** No fixes without baseline showing the gap.

---

## 8. Live Baseline Findings (2026-07-07 eval run)

Two baselines were recorded. **Run 1** (2026-07-07, no-key mode,
`EMBED_BACKEND=none`): evidence in
`docs/operational/tests/artifacts/eval-baseline-2026-07-07/`. **Run 2**
(2026-07-08, local Ollama `qwen3.5:4b` + `EMBED_BACKEND=cpu`): evidence in
`docs/operational/tests/artifacts/eval-baseline-2026-07-08-ollama/` — this run
is what surfaced and then confirmed fixes for F19–F21, and exposed F22.

| Claim | Measured (run 2, embeddings + Ollama) | Verdict |
|-------|----------|---------|
| Ingest P95 ≤ 1s | Milliseconds per paste ingest | ✓ holds at current scale |
| Search P95 ≤ 2s | Keyword 26ms; semantic 116ms; hybrid 122ms (small dataset — re-measure at 100k) | ✓ holds at current scale |
| Relevant retrieval (keyword) | R@5 87.5%, MRR 0.88 | ✓ |
| Relevant retrieval (semantic/hybrid) | R@10 100%, MRR 1.00; hybrid ≥ best single mode | ✓ embeddings genuinely work (after F20 fix) |
| Embeddings add recall beyond FTS | Paraphrase queries: semantic/hybrid 100% vs keyword 0% (`semantic_lift` +100%) | ✓ validated |
| Adversarial queries don't crash FTS | 2/2 non-5xx | ✓ |
| MCP contract (ingest, provenance, budget metadata, structured errors) | 4/4 via real MCP SSE protocol | ✓ |
| Async pipeline produces summaries/facts (PIPE-01/02) | **Zero summaries, zero facts — gate blocks all control content** | ✗ see F22 (P0) |
| Sensitivity gate blocks external dispatch | Differential test inconclusive (control blocked too); direct observability missing | ⚠ F15 + F22 |

Running the eval surfaced three new verified findings:

### F15 (FIXED 2026-07-08): Sensitivity gate decision is unobservable (P0 for trust claims)

The gate's block decision is only written to server logs
(`backend/app/worker/dispatcher.py:499-503` — `logger.info("Sensitivity gate: ... blocked=%s")`).
When blocked, the job skips LLM steps and **completes normally** — no job field,
no audit event, no API surface records that blocking occurred. No external test,
eval, or user can verify the product's most important privacy promise.
**Fix:** emit an `AuditEvent` (e.g. `sensitivity_gate_blocked`) with category +
confidence, and/or expose the gate decision on the job/archive item. Then
un-skip `evals/checks/eval_sensitivity.py`, which documents this dependency.

### F16: Facts cannot be filtered by source archive item

`GET /api/facts` filters by `source_status`/`review_status`/`confidence_tier`
(`backend/app/api/routes/facts.py:131-137`) but not by `raw_archive_id`.
Attribution ("which facts came from this conversation?") requires paging the
whole list and filtering client-side — the eval suite does exactly that
(`evals/checks/eval_extraction.py`), and the provenance UI story would benefit
from the same filter. **Fix:** add a `raw_archive_id` query param.

### F18–F21: Pipeline defects found by running the eval with Ollama (2026-07-07)

Configuring a real provider (local Ollama) + embeddings (`EMBED_BACKEND=cpu`)
for the first time exposed four defects; three were fixed in-session:

- **F19 (FIXED): job status transitions were silently lost.** The worker loop
  claimed a job in one session and dispatched it in another; `complete_job`/
  `fail_job`/`set_pending_provider` mutated the now-detached ORM instance, so
  their commits persisted nothing. Every job stayed `claimed` forever, went
  stale, and was **reprocessed from scratch on each restart** (with LLM cost
  per cycle once a provider exists). Fixed in `backend/app/worker/loop.py`
  (one session spans claim+dispatch) with regression test
  `tests/worker/test_loop.py::test_worker_loop_persists_status_transitions`.
  The 191 green tests missed it because they share a single session; E2E polls
  artifacts, not job state.
- **F20 (FIXED): semantic-adjacent pipeline steps never worked against real
  pgvector.** Conflict detection and link-detection pass A bind vectors as
  `str(embedding)` where `embedding` is read back from the DB as a numpy
  array — numpy's `str()` is space-separated, invalid pgvector input
  (`InvalidTextRepresentationError`). Unit tests fed plain lists and passed;
  CI runs with `EMBED_BACKEND=none` and skips. Fixed in
  `backend/app/domain/conflict_detection.py` and `backend/app/worker/dispatcher.py`.
- **F21 (FIXED): one failed "non-fatal" step wedged the whole job.** A DB error
  inside a non-fatal step aborted the transaction; every subsequent step and
  the final status commit then failed with `InFailedSQLTransactionError`,
  leaving the job `claimed`. Fixed: each step's exception handler now rolls
  back and refreshes the job instance.
- **F18 (OPEN): stale-claim recovery only runs at worker startup.** A job stuck
  in `claimed` (crash mid-dispatch) freezes invisible until the next restart,
  and a restart within 10 minutes of the claim recovers nothing. Recommend a
  periodic `reset_stale_jobs` sweep inside the worker loop, plus a bulk requeue
  API (systemic failures burn `attempts` across the whole queue; only a
  per-job reprocess endpoint exists today).

### F22 (FIXED 2026-07-08): the sensitivity gate blocks essentially all real content — BYOK processing is effectively dead

With a provider configured and `EMBED_BACKEND=cpu` (NLI classifier active), the
gate classified the eval's plainly *technical* conversations (Python async,
PostgreSQL indexing, Rust ownership) as `personal_profile` at 0.95–0.99
confidence or `unclassified` (0.45) — all blocked. Server logs show
`category=personal_profile confidence=0.99 blocked=True` for programming Q&A.
Consequence: jobs "complete" but no summaries and no facts are ever produced;
the product's headline transformation pipeline does not run on realistic
content. Mechanism: `backend/app/domain/policy/gate.py` does zero-shot
classification with a tiny NLI cross-encoder (`cross-encoder/nli-MiniLM2-L6-H768`,
threshold 0.6, labels "personal profile information" / "relationship
information" / "general topic") — a known-degenerate setup for long/technical
premises. The ROADMAP research flag from 2026-03 ("sensitivity heuristics need
domain validation against real export content") predicted exactly this and was
never closed. **Recommendation:** calibrate the gate against the eval's labeled
dataset (it now provides both sensitive and control conversations); consider
keyword-heuristics-first with NLI only as an escalator, a larger zero-shot
model, or chunk-level classification. Do NOT simply lower the threshold —
tune with measured false-block AND false-allow rates (F15's audit event makes
both observable). Blocking-by-default is the right failure direction; blocking
*everything* makes the privacy promise vacuous and the product non-functional.

### Resolution status for F15/F22 + run 3 baseline (2026-07-08, gate calibrated)

- **F15 fixed**: the dispatcher now emits an `AuditEvent(event_type="sensitivity_gate")`
  with category/confidence/blocked/method per job; `GET /api/audit/events`
  exposes `raw_archive_id`. The eval's sensitivity check verifies the gate
  EXACTLY from the audit trail.
- **F22 fixed**: the NLI classifier was replaced with embedding-prototype
  classification (all-MiniLM-L6-v2, cosine vs per-category prototype
  sentences; pure decision-rule function with unit tests). Privacy-first
  asymmetric thresholds: block at sim>=0.25 for sensitive categories, allow
  `general` only at sim>=0.35 with margin>=0.15; unclassified stays blocked
  (PRIV-05 unchanged). Measured: tech conversations -> general 0.71-0.80
  allowed; therapy conversation -> blocked; subtle no-keyword health content ->
  blocked.
- **Ollama pipeline fixes** (found by the eval): the OpenAI-compat endpoint
  cannot disable thinking, so reasoning models returned EMPTY content
  (finish=length) — switched to native `/api/chat` with `think: false` and
  `format: "json"`; robust first-JSON-object parsing (models append stray
  fences).

**Run 3 baseline** (`docs/operational/tests/artifacts/eval-baseline-2026-07-08-gate-calibrated/`),
all 5 checks live for the first time, zero skips:
ingest PASS; retrieval PASS (semantic/hybrid R@10 100%, paraphrase lift +100%);
MCP PASS; **sensitivity PASS (audit-verified: sensitive blocked, controls
allowed, zero leaked facts)**; extraction FAIL — recall 57.7% (needs 60%),
precision 65.6% (needs 70%), span fidelity 100%, provenance completeness 100%.
The extraction shortfall is a measured model-capability finding for
qwen3.5:4b: it extracts accurately but predominantly from the FIRST turn of
multi-turn conversations. Remedies: per-turn/chunked extraction (same fix as
F3) or a larger local model; re-run `make eval` to verify.

### F17: Idempotency replay after deletion returns success for a dead item

MCP `ingest_memory` replays a stored response when an `idempotency_key` is
reused — including after the original archive item was deleted. The caller gets
"accepted" but nothing exists or will be retrievable. Decide the intended
semantics (recreate, or return a `deleted` status) and cover with a test.
Found because the eval suite's cleanup + fixed key produced exactly this state.

---

## Appendix: Analysis Findings Reference

| Finding | File:Line | Brief | Recommendation |
|---------|-----------|-------|-----------------|
| F1 | `backend/app/worker/dispatcher.py:~82, ~96` | Hardcoded model names (gpt-4o-mini, claude-3-haiku-20240307) | Move to `.env` via pydantic-settings (SUMMARIZE_MODEL, EXTRACT_MODEL) |
| F2 | `backend/app/worker/dispatcher.py` | Provider selection is fixed priority (openai → anthropic → ollama) | Add per-function provider settings (SUMMARIZE_PROVIDER, EXTRACT_PROVIDER, EMBED_PROVIDER) |
| F3 | `backend/app/worker/dispatcher.py` | Silent truncation on conversations >4k tokens | Implement map-reduce chunking; summarize each chunk locally before extraction |
| F4 | `backend/app/worker/dispatcher.py:~45–65` | No verification of `source_span` verbatim substring; hallucinated spans possible | Validate span at write time via str.find; clear or downgrade if not found |
| F5 | `backend/app/worker/dispatcher.py` | Link detection errors swallowed with logger.debug | Add structured `link_detection_error` events to audit log (low priority) |
| F6 | `backend/app/domain/retrieval/service.py` | RRF merge with `RRF_MIN_THRESHOLD = 1/(k+25)` undocumented | Document threshold behavior in `docs/architecture/retrieval.md` |
| F7 | `backend/app/domain/retrieval/service.py` | `DEFAULT_BUDGET: int = 2000` is char-based; unit ambiguity | Rename to `CHAR_BUDGET` or add `TOKEN_BUDGET` with explicit tokenizer |
| F8 | `backend/app/domain/retrieval/service.py` | TTLCache requires manual invalidation after writes | Implement event-driven invalidation (pgvector LISTEN/NOTIFY) for v1.2 |
| F9 | Prior E2E bug (commit 132696d) | FTS query input sanitization fragile (tag parsed as scientific notation) | Add adversarial query tests (numbers, '1e5'-like tokens) to eval suite |
| F10 | `backend/app/mcp_server/server.py` | Four MCP tools: retrieve_memory, ingest_memory, get_fact_links, list_tags (SSE transport, 127.0.0.1 bound) | Status: correct (no action needed for v1.1) |
| F11 | `backend/app/mcp_server/server.py` + tech-stack.md | SSE is legacy; `mcp>=1.26,<2` pin; v2 has breaking changes Q1 2026 | Create ADR: stay on SSE through v1.1; spike v1.2 Streamable-HTTP migration |
| F12 | STATE.md Performance Metrics | Restore SLA ≤15 min, ingest P95 ≤1s, search P95 ≤2s all "Not yet measured" | Eval suite (this task) measures ingest P95 and search P95; defer restore to v1.2 if needed |
| F13 | ANALYSIS.md section 2 + git status | RR-001…RR-014 work is implemented but uncommitted on `main` (release-integrity risk) | Merge in reviewable slices for v1.0.1; this task focuses on v1.1 quality evidence |
| F14 | `backend/app/domain/...` (schema) | Embeddings record model_name+dim per row; provider-switch stale-embedding fallback exists | Status: correct (no action needed) |
| F15 | `backend/app/worker/dispatcher.py` | Sensitivity gate block decision only in logs — unverifiable via API | **FIXED** (sensitivity_gate AuditEvent; audit API exposes raw_archive_id; eval verifies exactly) |
| F16 | `backend/app/api/routes/facts.py:131-137` | No `raw_archive_id` filter on facts list; per-source attribution is client-side | Add `raw_archive_id` query param |
| F17 | `backend/app/mcp_server/server.py` (ingest_memory idempotency) | Idempotent replay after source deletion returns "accepted" for a nonexistent item | Define replay-after-delete semantics + test |
| F18 | `backend/app/worker/loop.py` / `jobs/service.py` | Stale-claim recovery only at startup; stuck claims freeze queue until restart | Periodic reset_stale_jobs sweep + bulk requeue API |
| F19 | `backend/app/worker/loop.py` | Detached-session bug: all job status transitions silently lost; jobs reprocessed every restart | **FIXED** (one session for claim+dispatch; regression test added) |
| F20 | `backend/app/domain/conflict_detection.py:54`, `dispatcher.py:244` | numpy `str()` bound as pgvector literal → conflict/link detection never worked with real embeddings | **FIXED** (coerce to list before binding) |
| F21 | `backend/app/worker/dispatcher.py` (steps 4–7) | Aborted transaction from a "non-fatal" step failure wedged status writes | **FIXED** (rollback + refresh per step failure) |
| F22 | `backend/app/domain/policy/gate.py` | Gate's NLI classifier blocked essentially all real content (tech Q&A → `personal_profile` @0.99) | **FIXED** (embedding-prototype classifier, asymmetric privacy-first thresholds, unit-tested decision rule) |

---

*End of recommendations document. For detailed implementation guidance, see the prioritized action table above.*
