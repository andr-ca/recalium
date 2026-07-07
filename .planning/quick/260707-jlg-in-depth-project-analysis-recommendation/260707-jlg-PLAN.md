---
phase: quick-260707-jlg-recommendations
plan: 01
type: execute
autonomous: true
requirements: []
files_modified:
  - docs/recommendations.md
  - evals/README.md
  - evals/runner.py
  - evals/metrics.py
  - evals/report.py
  - evals/thresholds.json
  - evals/checks/eval_ingest.py
  - evals/checks/eval_extraction.py
  - evals/checks/eval_retrieval.py
  - evals/checks/eval_sensitivity.py
  - evals/checks/eval_mcp.py
  - evals/datasets/conversations/
  - evals/datasets/golden.json
  - .env.sample
  - Makefile
---

<objective>
Deliver two locked artifacts grounded in ANALYSIS.md: (1) a comprehensive recommendations document (`docs/recommendations.md`) addressing product positioning, roadmap, and implementation-level fixes with file:line anchors to F1–F14 findings, and (2) a complete eval suite (`evals/`) that measures Recalium's core claims (memory capture, transformation, retrieval quality) against synthetic datasets, runs gracefully in no-key mode against the live stack, and provides baseline evidence for quality/performance SLAs.

Purpose: Close the gap between "v1 is functionally complete" and "v1 is proven to work" by providing structured evidence of retrieval quality, extraction fidelity, and SLA compliance, plus a roadmap for quality improvements.

Output: 
- `docs/recommendations.md` — executive summary + 6-section strategic/tactical guidance
- `evals/` — complete harness (runner, checks, datasets, metrics, reporting) + `make eval` target
- `.env.sample` updates — new eval-specific vars if any
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md

Use `.claude/skills/recalium-use-and-test/SKILL.md` for stack start/validation workflows during eval testing.
</execution_context>

<context>
Source of truth (LOCKED — do not re-derive findings):
@.planning/quick/260707-jlg-in-depth-project-analysis-recommendation/260707-jlg-ANALYSIS.md

Project context:
@.planning/STATE.md
@./CLAUDE.md

Existing documentation for reference:
@docs/guides/local-use-and-test.md
@docs/operational/validations/recalium-v1-release-readiness-gap-register.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write docs/recommendations.md grounded in ANALYSIS.md findings F1–F14</name>
  <files>docs/recommendations.md</files>
  <action>
Create `docs/recommendations.md` following ANALYSIS.md section 4 structure exactly, with file:line anchors to each finding (F1–F14). Content organization:

**1. Executive Summary (¶1–4)**
- v1 is functionally complete (191 tests, 52/52 requirements) but quality-unproven (core claim "retrieve relevant, source-backed context" has zero measured evidence per F6–F9, F12)
- Top 5 action summary: (a) commit + ship pending RR work (F13), (b) publish memory-bundle JSON schema as open spec (positioning), (c) eval suite + baselines (this task), (d) quality improvements informed by evals (F1–F5), (e) MCP v2 migration spike (F11)

**2. Idea/Positioning Level (¶5–8)**
- Moat is provenance-backed memory portability, not feature count
- Flagship claim: "source-backed retrieval you can audit" → anchor to fact.source_span + link.source_metadata; identify that current schema supports this but code doesn't validate it (F4: no span verification)
- Recommendation: publish `docs/architecture/memory-bundle-schema.md` as formal, versioned spec (currently implicit in export code only) — required for "open format" claim credibility
- Recommend picking ONE public-facing quality claim to build evidence for (e.g., "retrieval recall ≥70% on hybrid mode per eval baseline" from task 2)

**3. Roadmap Level (¶9–15)**
- v1.0 milestone complete 2026-03-24; v1.0.1 (pending RR work) ready for commit; propose v1.1 "Prove It" (Q2 2026):
  - Phase A: commit + ship pending RR-001…RR-014 work in reviewable slices (F13 — release risk)
  - Phase B: eval suite + quality baselines (this task delivers harness; findings feed prioritization)
  - Phase C: performance SLA evidence (F12: restore SLA ≤15 min not measured; F7: ingest/search P95 not measured)
  - Phase D: Playwright keyboard/a11y UAT (RR-011: pending)
  - Phase E: MCP v2/Streamable-HTTP migration spike (F11: SSE is legacy, v1.x maintenance-only, v2 breaking changes)
- Propose v1.2 (Q3 2026) for retrieval quality improvements (chunking for long conversations F3, span verification F4, per-function provider routing F2) — contingent on eval results showing clear gaps
- Defer backlog phases 999.1–999.4 (wiki synthesis, knowledge lint, query promotion) AFTER quality baseline exists — synthesis on unvalidated extraction compounds errors (meta-recommendation based on F4)

**4. Architecture Level (¶16–20)**
- Keep two-container topology (app + postgres) — no changes
- Document RRF threshold behavior: F6 finding that `RRF_MIN_THRESHOLD = 1/(k+25)` filters single-mode low-rank items is undocumented; add to `docs/architecture/retrieval.md`
- Resolve budget unit ambiguity (F7): `DEFAULT_BUDGET: int = 2000` is char-based but MCP consumers think in tokens; rename to `CHAR_BUDGET` and add explicit tokenizer mention or define `TOKEN_BUDGET` with CharCountTokenizer fallback
- Plan MCP transport migration (F11): document decision to stay on SSE until v2 SDK stabilizes (Q2 2026); create ADR-X for Streamable-HTTP upgrade path
- Event-driven cache invalidation (F8): current TTLCache requires manual invalidation after writes (seen in live-stack E2E, commit 59003ab); recommend pubsub-based invalidation (use pgvector LISTEN/NOTIFY or similar) for v1.2

**5. Implementation Level — Specific Fixes (¶21–28)**
For each of F1–F5, provide concrete code-level guidance:

- **F1 (hardcoded models)**: Move model names from hardcoded strings to `.env`-backed Pydantic settings; ref `backend/app/worker/dispatcher.py` line ~82 (`gpt-4o-mini`) and ~96 (deprecated `claude-3-haiku-20240307`). Use `pydantic-settings` to load `SUMMARIZE_MODEL`, `EXTRACT_MODEL`, defaulting to `gpt-4o-mini` and `claude-3-haiku` respectively; update `.env.sample`.

- **F2 (provider selection fixed)**: Per BYOK-08 requirement ("switch providers per function"), add `.env` settings `SUMMARIZE_PROVIDER` (default: openai), `EXTRACT_PROVIDER` (default: openai), `EMBED_PROVIDER` (default: sentence-transformers). Route each function's CompletionAdapter call through the configured provider. Fallback chain: if `SUMMARIZE_PROVIDER=anthropic` and key missing, log warning and skip job (don't fall through to next provider). This allows users to run extraction locally (sentence-transformers only) and summaries via Anthropic key if available.

- **F3 (truncation on long conversations)**: Implement map-reduce conversation chunking for dialogues >4k tokens. Split on turn boundaries, summarize each chunk locally (sentence-transformers + map-reduce prompt), concatenate summaries before extraction. Prevents silent truncation of facts from long ChatGPT exports (primary import source). Cost: adds ~1-2 summarization passes for long conversations, but preserves fact coverage.

- **F4 (hallucinated spans)**: After JSON extraction, validate each `source_span` is a verbatim substring of the raw source text (simple str.find). If span not found: (a) clear span (mark as `source_span=null`, (b) downgrade confidence, or (c) reject fact entirely. This is cheap (no LLM) and catches hallucination at write time, protecting provenance (the product's differentiator). Add test: extract from a 200-word conversation with 5 labeled expected facts, verify all stored spans are substrings.

- **F5 (link detection errors)**: Link errors are currently swallowed with `logger.debug` (non-fatal, acceptable). Recommend: add structured `link_detection_error` event to audit log, not just debug log, so users can inspect why certain semantic links weren't created. Low priority (doesn't block facts).

**6. Testing/Evidence Level (¶29–32)**
- Current gap: ROADMAP research flags still open — "RRF recall empirical validation" (k=60, ef_search=100 never measured), "sentence-transformers model quality" never validated on AI-conversation content, "sensitivity gate validation against real exports deferred to beta"
- This task delivers the eval suite harness to close these gaps
- Map each RR gap (RR-001…RR-014 from gap register) to the evidence artifact it requires:
  - RR-007 (restore SLA ≤15 min): requires benchmark in `evals/checks/eval_restore.py` (note: scope creep — skip for v1.1, defer to v1.2 if backup/restore UI not live)
  - RR-011 (Playwright a11y): separate from eval suite (Playwright config, not Python runner)
  - RR-009 (MCP error envelope standardization): `evals/checks/eval_mcp.py` validates structured error format
  - Others (facts/tags/links lifecycle, review queue UI): supported by eval datasets and retrieval checks
- Recommend running evals as part of release CI once baseline is established

**7. Prioritized Action Table (¶33–end)**
| Priority | Action | Impact | Effort | Owners | Timeline |
|----------|--------|--------|--------|--------|----------|
| P0 | Commit + ship pending RR work (F13) | Unblocks v1.0.1 release; removes release-integrity risk | 2–4 hrs (review/merge only) | Andrey | ASAP |
| P0 | Eval suite harness (this task) | Establishes quality baselines; foundation for v1.1 | 4 hrs (runner+checks+datasets) | Claude (executed now) | ✓ Done |
| P0 | Run evals against live stack; establish baselines | Provides numeric evidence for flagship claim | 1 hr (initial run) | Andrey (manual) | Week 1 |
| P1 | F1 (env-backed model names) + F2 (per-function providers) | Fulfills BYOK-08; enables local-only extraction; unblocks provider flexibility | 2 hrs | Backlog v1.1 | Week 2–3 |
| P1 | Publish memory-bundle JSON schema spec | Substantiates "open format" positioning claim | 1 hr (extract + doc) | Backlog v1.1 | Week 2 |
| P1 | MCP v2 migration spike + ADR | Unblocks v2 SDK adoption (Q2 2026); identifies transport cost | 4–6 hrs (prototype + decision) | Backlog v1.2 | Week 3–4 |
| P2 | F3 (map-reduce chunking for long conversations) | Improves extraction recall on long exports; low risk (fallback: truncate as today) | 6–8 hrs | Backlog v1.2 | Month 2 |
| P2 | F4 (span verification + confidence downgrade) | Hardens provenance guarantee; low cost (local substring match) | 3–4 hrs | Backlog v1.2 | Month 2 |
| P2 | Event-driven cache invalidation | Improves responsiveness post-ingest; medium risk (pgvector LISTEN/NOTIFY) | 8 hrs | Backlog v1.2 | Month 3 |
| P2 | F7 (resolve budget units) | Reduces confusion; potential token-count mismatch | 1 hr | Backlog v1.1 | Week 2 |
| P2 | F9 (FTS input sanitization) | Prevents injection-like tag parsing (e.g., '1e5' → scientific notation); add adversarial query tests to eval | 2 hrs | Backlog v1.1 (tests), v1.2 (fix) | Week 2–3 |

Notes:
- P0 items are release blockers or enable v1.1 foundation
- P1 items are v1.1 commits (quality + openness + positioning)
- P2 items are v1.2 refinements (quality improvements + operations)
- All F1–F5 fixes are informed by eval results (no fixes without baseline evidence)
  </action>
  <verify>
    <automated>
      # Verify file exists and has required sections
      test -f docs/recommendations.md && \
      grep -q "Executive Summary" docs/recommendations.md && \
      grep -q "Positioning" docs/recommendations.md && \
      grep -q "Roadmap" docs/recommendations.md && \
      grep -q "Architecture" docs/recommendations.md && \
      grep -q "Implementation" docs/recommendations.md && \
      grep -q "Testing/Evidence" docs/recommendations.md && \
      grep -q "Prioritized Action" docs/recommendations.md && \
      echo "✓ docs/recommendations.md complete with all 7 sections"
    </automated>
  </verify>
  <done>
    docs/recommendations.md created with all 7 required sections (executive summary, positioning, roadmap, architecture, implementation-level fixes for F1–F5, testing/evidence, prioritized action table). Each section grounded in ANALYSIS.md findings F1–F14 with file:line anchors. File committed to git.
  </done>
</task>

<task type="auto">
  <name>Task 2: Build evals/ framework with runner, checks, datasets, and make eval target</name>
  <files>
    evals/README.md
    evals/runner.py
    evals/metrics.py
    evals/report.py
    evals/thresholds.json
    evals/checks/__init__.py
    evals/checks/eval_ingest.py
    evals/checks/eval_extraction.py
    evals/checks/eval_retrieval.py
    evals/checks/eval_sensitivity.py
    evals/checks/eval_mcp.py
    evals/datasets/conversations/synthetic_conversations.json
    evals/datasets/conversations/long_conversation.json
    evals/datasets/golden.json
    .env.sample
    Makefile
  </files>
  <action>
Build the complete eval suite per ANALYSIS.md section 5 design (locked). No production code changes.

**Directory Structure:**
```
evals/
  README.md                           # Usage, metric definitions, thresholds rationale
  runner.py                           # CLI entry point: asyncio-based runner
  metrics.py                          # recall@k, precision@k, MRR, nDCG@10, span_fidelity, latency percentiles
  report.py                           # JSON report writer + markdown summary
  thresholds.json                     # Baseline thresholds (frozen for v1.1 comparison)
  checks/
    __init__.py
    eval_ingest.py                    # Ingest latency P95 (claim: ≤1s), success rate
    eval_extraction.py                # Fact precision/recall vs golden, span_fidelity ≥0.95
    eval_retrieval.py                 # recall@5/@10, MRR, nDCG@10, latency P95 (claim: ≤2s), adversarial queries
    eval_sensitivity.py               # Personal/relationship-labeled facts blocked from external dispatch
    eval_mcp.py                       # MCP tool behavior: retrieve_memory returns provenance, error envelope structured
  datasets/
    conversations/
      synthetic_conversations.json    # 8–10 synthetic ChatGPT/Claude-like exports (generic structure)
      long_conversation.json          # Single 8–12k-token conversation (expose truncation risk F3)
    golden.json                       # Ground truth: {facts: [{text, span, confidence}], queries: [{q, relevant_ids, sensitivity}]}
```

**Key Implementation Details:**

1. **runner.py** — Plain asyncio CLI (not pytest-based for flexibility in output format):
   - Entry: `if __name__ == "__main__": asyncio.run(main())`
   - Args: `--base-url` (default http://localhost:8000), `--output-dir` (default evals/results/<timestamp>/)
   - Flow: (a) health check on base_url/api/health, (b) graceful exit with reason if stack down, (c) run each check module sequentially, (d) aggregate results, (e) emit report.md + results.json
   - No provider keys required; graceful skip for evals that need providers

2. **metrics.py** — Pure functions (no side effects):
   ```python
   def recall_at_k(relevant_ids, retrieved_ids, k):
       """Fraction of top-k retrieved that are in relevant set."""
   
   def mrr(relevant_ids, retrieved_ids):
       """Mean Reciprocal Rank — position of first relevant item."""
   
   def ndcg_at_10(relevance_scores, k=10):
       """Normalized Discounted Cumulative Gain."""
   
   def span_fidelity(facts):
       """% of facts where source_span is verbatim substring of raw_source."""
       
   def latency_percentiles(latencies):
       """Return {p50, p95, p99} ms."""
   ```

3. **Dataset structure (golden.json):**
   ```json
   {
     "schema_version": "1.0",
     "conversations": [
       {
         "id": "conv-001",
         "source": "ChatGPT export",
         "raw_text": "...",
         "facts": [
           {
             "id": "fact-001",
             "text": "Expected fact text",
             "source_span": "verbatim span from raw_text",
             "confidence": 0.9
           }
         ]
       }
     ],
     "queries": [
       {
         "id": "q-001",
         "text": "search query",
         "relevant_fact_ids": ["fact-001", "fact-005"],
         "sensitivity_level": "public" | "personal" | "relationship"
       }
     ]
   }
   ```

4. **eval_ingest.py:**
   - Ingest each conversation via `/api/ingest` POST (existing endpoint)
   - Measure latency per ingest; P95 should be ≤1s
   - Assert: no 500 errors, response has canonical ID
   - Skip if stack is down (print "⊘ Ingest checks skipped — stack down" and continue)

5. **eval_extraction.py:**
   - After ingest pipeline completes (poll fact count), compare extracted facts against golden
   - Fuzzy match: extracted text contains ≥80% of expected text or vice versa
   - Span fidelity: % of extracted facts where source_span is substring of raw source
   - Skip if no LLM provider configured (print "⊘ Extraction checks skipped — no LLM provider" and continue)
   - Report precision, recall, span_fidelity; threshold: extraction recall ≥0.6, precision ≥0.7, span ≥0.95

6. **eval_retrieval.py:**
   - For each query: retrieve via `/api/search` in keyword + semantic + hybrid modes
   - Compute recall@5, recall@10, MRR, nDCG@10 vs golden labels
   - Hybrid mode must beat or match best single mode
   - Measure latency; P95 should be ≤2s
   - Adversarial queries: include number-heavy queries, '1e5'-like tokens, punctuation-only to ensure no 500 errors
   - Skip semantic if EMBED_BACKEND is not configured; still run keyword
   - Thresholds: hybrid recall@10 ≥0.7, latency P95 ≤2s

7. **eval_sensitivity.py:**
   - Ingest facts labeled `sensitivity_level: "personal"` or `"relationship"`
   - Assert: no external LLM calls (check job audit log for provider dispatch; verify job status is `deferred` or `local` only)
   - No provider key needed — validates gate logic via audit, not by triggering external calls
   - Threshold: 100% block rate (all sensitive facts remain local)

8. **eval_mcp.py:**
   - Call MCP tools via HTTP POST to `/mcp/sse` (SSE endpoint)
   - `retrieve_memory`: assert returns `provenance` field + `conflict_labels` + `budget_metadata`
   - `ingest_memory` with malformed input (missing `content`): assert structured error envelope (per RR-009)
   - No provider key needed
   - Threshold: 100% error correctness

9. **report.py:**
   - Collect results from all checks
   - Emit `evals/results/<timestamp>/report.md` with:
     - Summary table (check name, status, key metrics)
     - Detailed findings per check
     - Comparison vs thresholds (PASS/FAIL per metric)
     - Recommendations (e.g., "Extraction recall 0.58 < 0.6 threshold — F3 truncation likely")
   - Emit `results.json` with full numeric payload
   - Exit code 0 if all thresholds met, 1 if any fail

10. **thresholds.json:**
    ```json
    {
      "ingest_latency_p95_ms": 1000,
      "extraction_recall": 0.6,
      "extraction_precision": 0.7,
      "extraction_span_fidelity": 0.95,
      "retrieval_recall_at_10_hybrid": 0.7,
      "retrieval_latency_p95_ms": 2000,
      "sensitivity_block_rate": 1.0,
      "mcp_error_correctness": 1.0
    }
    ```

11. **README.md:**
    - How to run: `make eval` or `uv run --project backend python evals/runner.py`
    - Metric definitions: recall, precision, MRR, nDCG, span_fidelity, latency percentiles
    - Thresholds rationale: based on product claims (ingest P95 ≤1s, search P95 ≤2s) + evaluation best practice (recall ≥0.7 for hybrid, span ≥0.95 for provenance)
    - No-key mode behavior: extraction evals skip gracefully when no provider; retrieval keyword still runs; semantic skips unless EMBED_BACKEND=cpu
    - Dataset schema: reference golden.json structure and extension guide for users

12. **Makefile target:**
    Add to `Makefile`:
    ```makefile
    .PHONY: eval
    eval:
        cd backend && uv run --project . python ../evals/runner.py --base-url http://localhost:8000
    ```

**Environment (.env.sample updates):**
Add if not present:
```
# Eval suite configuration
EVAL_OUTPUT_DIR=evals/results
EVAL_BASE_URL=http://localhost:8000
```

**Constraints (locked from ANALYSIS.md section 5):**
- No production code changes (evals use existing API/MCP surface only)
- No new backend endpoints
- Datasets are synthetic (no real personal data), shaped like ChatGPT/Claude exports
- One long conversation (>8k tokens) to expose truncation (F3)
- Personal-content cases for sensitivity gate
- Golden labels in ONE file with documented schema
- Runner is plain asyncio (not pytest), can emit report files
- Keep runnable via `make eval`
- Follow .env conventions (env vars with defaults, never hardcode secrets)
- Update .env.sample if new vars introduced
- Graceful degradation: skip checks when stack down or provider missing, with clear reason messages
- Evidence output path: `docs/operational/tests/` already exists; runner outputs to `evals/results/<timestamp>/` and can be symlinked or copied there post-run

**Offline Verification:**
To allow verification that the runner is valid even when stack is down, ensure it can be checked without execution:
- `uv run --project backend python -m compileall evals` (syntax check)
- `uv run --project backend python evals/runner.py --help` (CLI help, no actual run)
  </action>
  <verify>
    <automated>
      # Verify evals directory structure
      test -d evals && \
      test -f evals/README.md && \
      test -f evals/runner.py && \
      test -f evals/metrics.py && \
      test -f evals/report.py && \
      test -f evals/thresholds.json && \
      test -d evals/checks && \
      test -f evals/checks/__init__.py && \
      test -f evals/checks/eval_ingest.py && \
      test -f evals/checks/eval_extraction.py && \
      test -f evals/checks/eval_retrieval.py && \
      test -f evals/checks/eval_sensitivity.py && \
      test -f evals/checks/eval_mcp.py && \
      test -d evals/datasets && \
      test -f evals/datasets/golden.json && \
      test -d evals/datasets/conversations && \
      echo "✓ evals/ directory structure complete" && \
      
      # Verify Makefile has eval target
      grep -q "^\.PHONY: eval" Makefile && \
      grep -q "python.*evals/runner.py" Makefile && \
      echo "✓ Makefile has eval target" && \
      
      # Offline syntax check
      cd backend && uv run --project . python -m compileall ../evals 2>&1 | grep -q "Listing" && \
      echo "✓ evals/ Python syntax valid" && \
      
      # Verify runner has help
      cd backend && uv run --project . python ../evals/runner.py --help 2>&1 | grep -q -E "(usage|base-url|output-dir)" && \
      echo "✓ runner.py CLI interface valid"
    </automated>
  </verify>
  <done>
    evals/ framework complete: runner (asyncio CLI with graceful degradation), metrics (recall/precision/MRR/nDCG/span_fidelity/latency), checks (ingest/extraction/retrieval/sensitivity/mcp), datasets (8–10 synthetic conversations + 1 long conversation + golden labels with schema), report (markdown summary + JSON payload), thresholds (baseline per product claims). `make eval` target added to Makefile. .env.sample updated with EVAL_OUTPUT_DIR and EVAL_BASE_URL. Offline syntax/help verification passes. No production code changes. Ready for manual run against live stack to establish baselines.
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

1. **Recommendations doc (Task 1):**
   - [ ] File exists at `docs/recommendations.md` with 7 major sections
   - [ ] Each F1–F5 fix has concrete code-level guidance (file:line anchors to backend/app/worker/dispatcher.py, backend/app/domain/retrieval/service.py, etc.)
   - [ ] Prioritized action table aligns findings to P0/P1/P2 with effort estimates
   - [ ] Positioned as input to v1.1 planning (not v1.0 scope creep)

2. **Eval suite (Task 2):**
   - [ ] Directory structure matches ANALYSIS.md section 5 layout exactly
   - [ ] runner.py is async CLI with --base-url, --output-dir, graceful stack-down handling
   - [ ] Datasets include synthetic conversations shaped like ChatGPT/Claude exports + golden labels with documented schema
   - [ ] metrics.py has recall@k, precision@k, MRR, nDCG@10, span_fidelity, latency_percentiles functions
   - [ ] Each check module (eval_ingest, eval_extraction, eval_retrieval, eval_sensitivity, eval_mcp) can skip gracefully with reason when provider missing or stack down
   - [ ] report.py emits markdown + JSON to `evals/results/<timestamp>/`
   - [ ] thresholds.json grounded in product claims (ingest ≤1s, search ≤2s, recall ≥0.7, span ≥0.95, sensitivity block=1.0)
   - [ ] `make eval` target added and runnable (syntax check passes at minimum)
   - [ ] .env.sample updated with EVAL_OUTPUT_DIR, EVAL_BASE_URL if added

3. **Quality gates:**
   - [ ] No production code modified in backend/ or frontend/
   - [ ] All .env-referenced vars are documented in .env.sample
   - [ ] Eval runner can be verified offline: `uv run --project backend python -m compileall evals` and `uv run --project backend python evals/runner.py --help` both pass
   - [ ] Both files committed to git
</verification>

<success_criteria>
Deliverable 1 (docs/recommendations.md):
- Executive summary + 6 strategic/tactical sections, all grounded in ANALYSIS.md findings F1–F14
- File:line anchors to source code (backend/app/worker/dispatcher.py, backend/app/domain/retrieval/service.py, etc.)
- Prioritized action table (P0/P1/P2) with effort estimates and timeline
- Positioned as input to v1.1 "Prove It" roadmap, not v1.0 feature

Deliverable 2 (evals/ framework):
- Complete harness: runner + metrics + checks (5 modules) + datasets (synthetic + golden labels) + reporting
- All checks can skip gracefully when stack down or provider missing, with clear messages
- Thresholds match product claims (ingest ≤1s, search ≤2s, hybrid recall ≥0.7, span fidelity ≥0.95, sensitivity block=1.0)
- `make eval` target functional (offline verification: syntax check + help pass)
- No production code changes; no real personal data in datasets
- .env.sample updated with eval-specific vars

Both deliverables address the core gap from ANALYSIS.md section 2: "the product's central claim is unmeasured" → now has a measurement harness and strategic recommendations for quality improvements.
</success_criteria>

<output>
After completion, create `.planning/quick/260707-jlg-in-depth-project-analysis-recommendation/260707-jlg-SUMMARY.md` with:
- Files created/modified (absolute paths)
- Key findings from recommendations doc (summary of top 5 actions)
- Baseline eval thresholds (reference thresholds.json)
- Next steps: run `make eval` against live stack to establish initial evidence
</output>
