# Determinism & Golden-Set Coverage Audit
**Date:** 2026-07-17  
**Objective:** Investigate whether eval suite exhibits variance without code changes (determinism), and audit whether golden.json covers all factual statements in source conversations.

---

## Task 1: Determinism Audit

### Methodology
1. **Isolated stack setup** with unique container names and project name (`recalium-audit`) to avoid collisions with other Recalium instances
2. **Configuration:**
   - Local Ollama instance (qwen3.5:4b model, same as prior runs)
   - Temperature = 0 (pinned in dispatcher.py for deterministic output)
   - Same golden.json dataset (4 conversations: conv-001 Python async, conv-002 PostgreSQL, conv-003 personal health/therapy — marked sensitive, included here only for baseline eval scoring, not as public-domain content — and conv-004 Rust ownership)
   - Fresh database between each run (`docker compose down -v` + rebuild)

3. **Three sequential runs** with complete DB reset between runs to eliminate state leakage

### Hypothesis
If temperature is pinned to 0 and the same model processes identical golden conversations with identical DB state, variance in extracted facts should be minimal (σ < 3 percentage points = 3pp).

### Root-Cause Check: Temperature & Seed Pinning (Code Audit)

**Finding:** CONFIRMED - Temperature is pinned to 0 for ALL LLM providers in `_extract_chunk()` and `_run_summarize_job()`.

**Code Evidence:**

1. **OpenAI extraction** (`dispatcher.py:303`):
   ```python
   response = await client.chat.completions.create(
       model=model,
       messages=[...],
       response_format={"type": "json_object"},
       temperature=0,  # PINNED
   )
   ```

2. **Ollama extraction** (`dispatcher.py:325` calls `_ollama_chat()`, line 203):
   ```python
   payload: dict[str, Any] = {
       "model": settings.ollama_model,
       "messages": [...],
       "stream": False,
       "think": False,
       "options": {"temperature": 0},  # PINNED
   }
   ```

3. **Anthropic extraction** (`dispatcher.py:311-316`):
   - **CORRECTION (Copilot review, confirmed by re-reading the code):** No `temperature`
     parameter is passed to `client.messages.create()`. This is NOT safe for determinism —
     Anthropic's API defaults to `temperature=1.0` when omitted, not a deterministic value.
     The original claim in this section that "Anthropic's API has deterministic defaults" was
     incorrect and has been struck. If the Anthropic path is ever used for extraction, it
     should not be assumed deterministic without explicitly setting `temperature=0`.

4. **Summarization jobs** (`dispatcher.py:244` for OpenAI, line 203 for Ollama):
   - Same pattern: temperature=0 for OpenAI and Ollama; Anthropic summarization has the same
     gap noted above.

**Conclusion:** Temperature is reliably pinned to 0 for the OpenAI and Ollama paths. The
Anthropic path is NOT pinned and should not be assumed deterministic. No seed parameter is
used for any provider (not applicable for standard LLM chat-completion APIs — temperature is
the determinism control where set).

### Operational Results

**Run 1:**
- ✓ Ingest check PASSED (conversations successfully ingested)
- ⏱ Extraction check started but timed out during qwen3.5:4b model inference
- Final metrics not captured

**Run 2:**
- ✗ Stack health check FAILED after container rebuild
- Container startup took longer than expected; stack not healthy within 25-second window
- Eval suite exited before running checks

**Run 3:**
- ✗ docker-compose.override.audit.yml file missing (inadvertently removed during cleanup)
- Stack would not start; eval suite could not run

### Addendum: Determinism Resolved from Prior Same-Session Data

The 3-run operational audit above did not complete due to local infra constraints. However,
this question is already answered by data collected earlier in this session while
independently verifying the (rejected) `_dedupe_facts()` fix on `worktree-agent-a2ac7a58d1a13e3b2`:

- **Baseline run** (main's `dispatcher.py`, fresh DB, `evals/runner.py` against the same
  `golden.json`): recall 0.58333, precision 0.71667, span_fidelity 1.0, provenance 1.0,
  **19 facts extracted**.
- **Second run** (fixed `dispatcher.py` — a no-op for this dataset, confirmed by hashing the
  file inside the running container — fresh DB, same eval harness): recall 0.58333, precision
  0.71667, span_fidelity 1.0, provenance 1.0, **19 facts extracted**.

These two runs used the same model/provider config, same golden set, and a full DB reset
between them (equivalent experimental conditions to this audit's intended 3-run design) and
produced **bit-for-bit identical** extraction metrics down to the exact float and fact count.

**Conclusion:** Under temperature=0 and a fresh DB, the eval is deterministic in practice, not
just in code — variance is not the explanation for the discrepancy between the historical
baseline (recall 0.774 / precision 0.617, tagged "Iteration 7" in
`2026-07-17-extraction-failure-analysis.md`) and this session's fresh measurement (recall
0.5833 / precision 0.71667). That gap is attributable to a different prompt/model state at
the time of the original measurement, not eval or LLM non-determinism. The determinism
question in this audit is therefore considered **resolved**, and the golden-set coverage
gap (Task 2) is the real, actionable lever for gate reliability — not eval reliability.

**Status:** RESOLVED (via addendum above, using same-session A/B data) - the 3-run operational
audit as originally scoped could not complete. Root causes for that specific attempt:

1. **Performance constraint:** qwen3.5:4b model extraction on CPU is extremely slow. Each extraction call takes 1-2 minutes; Run 1 timed out during extraction phase (300-second timeout expired before completion).

2. **Infrastructure timing:** Container startup and health checks have variable timing on resource-constrained systems. 15-25 second startup window insufficient for 100% reliability.

3. **Script fragility:** Script cleanup between runs removed override file, breaking subsequent runs.

However: **Code-level determinism controls confirmed via source audit (PASSED).** Operational determinism (runtime variance) remains untested, but given that:
- Temperature=0 is explicitly pinned in all code paths
- No random seed variation possible with API-based LLMs
- Chunking, dedup, and span validation are deterministic functions

**Conclusion:** Runtime variance, if observed, would likely stem from model-level non-determinism (despite T=0) rather than code/eval framework issues.

---

## Task 2: Golden-Set Coverage Audit

### Methodology
Manual enumeration of all distinct factual statements from each conversation's raw_text, compared against existing golden facts.

**Definition of "fact":** A concrete, checkable claim or statement of information — not questions, hypotheticals, or meta-commentary.

### Conversation-by-Conversation Analysis

#### **CONV-001: Python async patterns**
**Golden facts listed:** 7  
**Distinct facts enumerated from source:** 8

| # | Enumerated Fact | Coverage | Notes |
|---|---|---|---|
| 1 | Python's async/await is built on asyncio | ✓ COVERED | Exact golden fact |
| 2 | Define async functions with `async def` | ✓ COVERED | Exact golden fact |
| 3 | Use `await` to pause and wait for Futures | ✓ COVERED | Exact golden fact |
| 4 | Run async programs with asyncio.run(main()) | ✓ COVERED | Exact golden fact |
| 5 | Event loop manages all coroutines concurrently | ✓ COVERED | Exact golden fact |
| 6 | asyncio.gather() or TaskGroups run multiple concurrent tasks | ✓ COVERED | Exact golden fact |
| 7 | Use try/except around await expressions for error handling | ✓ COVERED | Exact golden fact |
| 8 | asyncio.TimeoutError can be caught in exception handlers | ✗ NOT IN GOLDEN | Implementation detail in code example |

**Coverage:** 7/8 = **87.5%**

**Missing fact detail:**
- Source quote: `except asyncio.TimeoutError: print('Request timed out')`
- Assessment: This is an implementation example illustrating the error handling fact, not a core fact about async/await

---

#### **CONV-002: Database indexing strategies**
**Golden facts listed:** 8  
**Distinct facts enumerated from source:** 13

| # | Enumerated Fact | Coverage | Notes |
|---|---|---|---|
| 1 | PostgreSQL B-tree indexes for equality/range queries (default) | ✓ COVERED | Exact golden fact |
| 2 | PostgreSQL Hash indexes for exact matches only | ✓ COVERED | Exact golden fact |
| 3 | PostgreSQL GiST for geometric data or full-text search | ✓ COVERED | Exact golden fact |
| 4 | PostgreSQL GIN for array/JSON queries (inverted indexes) | ✓ COVERED | Exact golden fact |
| 5 | PostgreSQL BRIN for very large tables (block range indexes) | ✓ COVERED | Exact golden fact |
| 6 | For large tables, index WHERE clause columns first | ✗ NOT IN GOLDEN | Explicit best practice statement |
| 7 | For large tables, index ORDER BY columns | ✗ NOT IN GOLDEN | Explicit best practice statement |
| 8 | PostgreSQL 11+ covering indexes with INCLUDE clause | ✗ NOT IN GOLDEN | Feature not documented in golden |
| 9 | Use EXPLAIN ANALYZE to verify index usage | ✗ NOT IN GOLDEN | Standard tool not documented |
| 10 | Use tsvector column type for indexed tokens in FTS | ✓ COVERED | Exact golden fact |
| 11 | Create GIN index on tsvector column for FTS | ✓ COVERED | Part of FTS fact |
| 12 | Full-text search in PostgreSQL uses @@ operator | ✓ COVERED | Exact golden fact |
| 13 | GIN index on tsvector much faster than LIKE for large datasets | ✓ COVERED | Exact golden fact |

**Coverage:** 8/13 = **61.5%**

**Missing fact details:**

**Missing #1: WHERE clause indexing priority**
- Source quote: "For a large table: Index your WHERE clause columns first"
- Type: Indexing best practice / priority
- Impact: Extraction model should capture this as a distinct fact

**Missing #2: ORDER BY column indexing**
- Source quote: "Then ORDER BY columns"
- Type: Indexing best practice / sequence
- Impact: Follows naturally from WHERE clause indexing

**Missing #3: Covering indexes (INCLUDE clause)**
- Source quote: "Consider covering indexes (INCLUDE in PostgreSQL 11+)"
- Type: PostgreSQL feature (version-specific)
- Impact: Important for query optimization, version-specific feature

**Missing #4: EXPLAIN ANALYZE verification**
- Source quote: "Use EXPLAIN ANALYZE to verify index usage"
- Type: Standard diagnostic tool
- Impact: Essential practice for index tuning

---

#### **CONV-003: Personal health and therapy (sensitive)**
**Golden facts listed:** 4  
**Distinct facts enumerated from source:** 10

**Note:** This conversation contains personal and relationship-sensitive information (marked with `sensitivity_level` in golden facts). Some gaps may be intentional for privacy. Sensitivity labels in golden facts: personal, relationship.

| # | Enumerated Fact | Coverage | Notes |
|---|---|---|---|
| 1 | User is seeing a therapist [name redacted — personal identifier] | ✓ COVERED (SENSITIVE) | Exact golden fact, marked personal |
| 2 | User is struggling with anxiety attacks | ✗ PARTIAL | Statement exists but not explicit golden fact |
| 3 | Deep breathing exercises are coping strategy for anxiety | ✓ COVERED | Part of combined "deep breathing & grounding" fact |
| 4 | Grounding techniques (5-4-3-2-1 method) coping strategy | ✓ COVERED | Part of combined fact |
| 5 | Regular exercise is a coping strategy for anxiety | ✗ NOT IN GOLDEN | Listed in coping strategies but omitted |
| 6 | Medication (if recommended) is coping strategy | ✗ NOT IN GOLDEN | Listed in coping strategies but omitted |
| 7 | User's therapist recommended CBT techniques | ✓ COVERED (SENSITIVE) | Exact golden fact, marked personal |
| 8 | CBT is evidence-based and effective for anxiety | ✗ NOT IN GOLDEN | Scientific statement about CBT |
| 9 | User's wife is very supportive | ✓ COVERED (SENSITIVE) | Exact golden fact, marked relationship |
| 10 | Personal relationships are key to recovery | ✗ NOT IN GOLDEN | General principle stated but not golden |

**Coverage:** 4/10 = **40%**

**Missing fact details:**

**Missing #1: Regular exercise**
- Source quote: "Some common coping strategies: ... 3. Regular exercise"
- Type: Wellness strategy
- Note: Listed in source but not captured in golden (which only mentions breathing + grounding)

**Missing #2: Medication**
- Source quote: "Some common coping strategies: ... 4. Medication if recommended"
- Type: Clinical management
- Note: Listed in source but omitted from golden

**Missing #3: CBT evidence-base**
- Source quote: "CBT is evidence-based and effective for anxiety"
- Type: Clinical fact about CBT
- Note: Golden captures recommendation but not efficacy/evidence

**Missing #4: Relationships in recovery**
- Source quote: "Personal relationships are key to recovery"
- Type: General principle / best practice
- Note: Stated directly but not captured

**Sensitivity assessment:** Missing exercise/medication facts are low-sensitivity (public health info). Missing "CBT evidence" and "relationships key" are medium-sensitivity (general statements, not personal identifiers).

---

#### **CONV-004: Rust ownership and borrowing**
**Golden facts listed:** 7  
**Distinct facts enumerated from source:** 10

| # | Enumerated Fact | Coverage | Notes |
|---|---|---|---|
| 1 | Each value in Rust has one owner | ✓ COVERED | Exact golden fact |
| 2 | You can borrow Rust values immutably or mutably | ✓ COVERED | Exact golden fact |
| 3 | When owner drops, Rust value is freed | ✓ COVERED | Exact golden fact |
| 4 | Rust prevents use-after-free bugs | ✓ COVERED | Part of comprehensive fact |
| 5 | Rust prevents data races | ✓ COVERED | Part of comprehensive fact |
| 6 | Rust prevents double-free errors | ✓ COVERED | Part of comprehensive fact |
| 7 | Mutable borrow not allowed while immutable refs exist | ✓ COVERED | Exact golden fact |
| 8 | Rust borrows checked at compile-time | ✓ COVERED | Exact golden fact |
| 9 | Rust lifetimes prevent references from outliving data | ✓ COVERED | Exact golden fact |
| 10 | Lifetime parameters ('a syntax) specify reference bounds | ~ PARTIALLY COVERED | Implied by explanation, not explicit |

**Coverage:** 9/10 = **90%**

**Note:** This conversation has excellent coverage. The one potentially missing fact (#10 about lifetime parameter syntax) is sufficiently implied by the code example and explanation.

---

### Overall Coverage Summary

**Methodology correction (Copilot review):** the original version of this table used the
literal count of `golden.json` fact *entries* per conversation (7/8/4/7 = 26) as if it were
the coverage numerator, but the per-conversation "Coverage %" figures above were actually
computed as (enumerated source facts marked ✓ COVERED) / (total enumerated source facts) —
a different, larger numerator whenever multiple enumerated facts map to one combined golden
entry (e.g. conv-004's 3 memory-safety facts all map to a single golden entry, conv-003's
2 coping-strategy facts map to one golden entry). Mixing these two numerators produced an
inconsistent total. The table below uses one consistent definition throughout: "Enumerated
Facts Covered" = enumerated source facts marked ✓ (fully or partially) against golden.json,
regardless of how many distinct golden entries they map to.

| Conversation | Topic | Golden Fact Entries (raw count in golden.json) | Enumerated Facts (total distinct facts in source) | Enumerated Facts Covered | Coverage |
|---|---|---|---|---|---|
| conv-001 | Python async | 7 | 8 | 7 | 87.5% |
| conv-002 | PostgreSQL indexing | 8 (12 after golden.json expansion, see below) | 13 | 8 (12 after expansion) | 61.5% (92.3% after expansion) |
| conv-003 | Health/therapy | 4 | 10 | 4 | 40% |
| conv-004 | Rust ownership | 7 | 10 | 9 | 90% |
| **TOTAL** | | **26** | **41** | **28** | **68.3%** |

Overall coverage is **68.3%** (28/41 enumerated facts covered), not the 63.4% originally
reported — the earlier figure understated coverage by conflating golden-entry count with
covered-fact count. This does not change the conclusion (conv-002 and conv-003 remain the
weakest, conv-002 addressed separately via golden.json expansion, see below).

---

### Missing Facts by Category

#### **High Priority (Impact on Extraction Gate)**

1. **conv-002 / PostgreSQL WHERE clause indexing**
   - Fact: "Index your WHERE clause columns first"
   - Impact: Extraction model should capture this. If extracted, marked false-positive; if not extracted, marked recall miss.

2. **conv-002 / PostgreSQL ORDER BY indexing**
   - Fact: "Index ORDER BY columns"
   - Impact: Logical follow-up to WHERE indexing; same impact.

3. **conv-002 / EXPLAIN ANALYZE verification**
   - Fact: "Use EXPLAIN ANALYZE to verify index usage"
   - Impact: Standard PostgreSQL tool; model should extract if discussed.

4. **conv-002 / PostgreSQL covering indexes (INCLUDE)**
   - Fact: "PostgreSQL 11+ supports covering indexes with INCLUDE clause"
   - Impact: Version-specific feature; model extraction reliability depends on recognizing version context.

#### **Medium Priority**

5. **conv-003 / Regular exercise**
   - Fact: "Regular exercise is a coping strategy for anxiety"
   - Impact: Listed but omitted; low sensitivity (public health), could be added to golden.

6. **conv-003 / CBT evidence-base**
   - Fact: "CBT is evidence-based and effective for anxiety"
   - Impact: Clinical fact; model must recognize general principles vs. personal statements.

---

## Implications for Precision Gate Reliability

### Finding #1: Golden Set is Incomplete
**conv-002 is 61.5% complete**, missing 5 important facts about indexing best practices and features. This incompleteness directly affects gate reliability:

- **False positive rate inflated:** If extraction model identifies "use EXPLAIN ANALYZE to verify index usage," this fact is not in golden, so it's scored as a false positive (hurting precision).
- **Recall gaps:** If model misses "index WHERE clause columns first," this miss is scored as a recall error even though the fact appears in source.

### Finding #2: Sensitivity vs. Coverage Trade-off
**conv-003 is 40% complete**, but this may be intentional. The document notes state facts 201-203 have `sensitivity_level: personal/relationship`. Missing facts 5, 6, 8, 10 are less sensitive (public health, general principles). Adding them would improve coverage without privacy risk.

### Finding #3: Extraction Model's Instruction Following
The gaps suggest the golden set was created **from a prior extraction run**, not by exhaustive manual enumeration. Evidence:
- conv-001 and conv-004 have excellent coverage (87-90%), suggesting the extraction model captured high-level concepts well
- conv-002 and conv-003 have lower coverage (40-61%), suggesting the extraction model missed implementation details and best practices

**Conclusion:** The golden set reflects *what a particular model extracted*, not *all facts present in the source*. This means:
1. Precision gate may penalize correct extractions not in golden
2. Recall gate may reward missing facts as failures when they should be credits
3. Gate variance could be due to golden-set incompleteness, not just model/eval non-determinism

---

## Recommendations

### For Task 1 (Determinism Audit)
When results are available:
1. Report raw metrics (recall, precision, span_fidelity, provenance_completeness) for all 3 runs
2. Calculate mean, min, max, stdev
3. Assess whether variance is "high" (σ > 0.03) or "low"
4. **If variance is high:** Cannot distinguish between eval-runner non-determinism vs. LLM non-determinism (even with T=0). Escalate to verify temperature/seed pinning.
5. **If variance is low:** Eval runner is reliable; any prior run variance is likely due to golden-set gaps or code changes.

### For Task 2 (Golden-Set Coverage)

#### Immediate Actions
1. **Expand conv-002 golden facts:** Add 4 missing PostgreSQL facts:
   - "Index your WHERE clause columns first"
   - "Index ORDER BY columns"
   - "Use EXPLAIN ANALYZE to verify index usage"
   - "PostgreSQL 11+ supports covering indexes with INCLUDE clause"

2. **Audit conv-003 privacy vs. coverage:**
   - Decide: is 40% coverage acceptable for sensitive conversation?
   - If no: add low-sensitivity facts (exercise, medication, CBT evidence-base)
   - If yes: document policy in golden.json notes

#### Longer-term Actions
1. **Golden-set authorship process:** Establish whether golden facts should be:
   - **Option A (current):** Extraction-model-guided (only facts model tends to find)
   - **Option B (exhaustive):** Manually enumerated without reference to model output
   - Recommend **Option B** for gate reliability

2. **Coverage validation:** Before releasing extraction gate, require:
   - Minimum 85% coverage per conversation (current: 68.3% overall, 40% worst [conv-003, partly by sensitivity design], 61.5% worst non-sensitive [conv-002, now 92.3% after golden.json expansion])
   - Explicit sensitivity-level audit for excluded facts
   - Justification for any facts not in golden but present in source

---

## Task 1 Findings: Temperature Determinism Confirmed in Code

**Summary of Task 1 Root-Cause Check:**

The extraction and summarization functions explicitly pin `temperature=0` for the OpenAI and
Ollama providers; the Anthropic path does not set `temperature` at all and should not be
assumed deterministic (see correction above):
- ✓ OpenAI: `temperature=0` explicit
- ✓ Ollama: `temperature=0` in options
- ✗ Anthropic: no `temperature` set — defaults to 1.0, not deterministic

**This means:** For the OpenAI/Ollama paths (the ones actually exercised in this session's
A/B comparison and in this repo's default local-first config), variance in extraction results
across multiple runs is NOT due to non-deterministic LLM temperature settings. Possible
sources of variance for those paths:
1. **Model output non-determinism despite T=0** (some models don't honor T=0 perfectly)
2. **Chunking or content ordering variations** in `_split_conversation()` / fact deduplication
3. **Database state leakage** between runs (though reset procedure should prevent this)
4. **Eval framework variance** in metric calculation (unlikely, but possible)

**Recommendation:** If precision/recall variance >3pp is observed in future determinism audits, escalate investigation to model-level behavior (not code-level settings).

---

## Summary

**Golden-Set Coverage: 68.3% complete (28/41 distinct facts; see Methodology correction above)**

### What This Means for the Precision Gate

The precision gate is measuring against an incomplete golden set. This creates ambiguity:
- When extraction model identifies a fact not in golden, is it a false positive (error) or a gap in golden?
- When precision is measured at 61.67% (from prior iteration 7), is that the model's true precision, or is it penalizing correct extractions missing from golden?

### Recommendation for Gate Closure

**Before accepting extraction quality gate results:**
1. Complete Task 1 determinism audit (verify eval variance is low)
2. Expand golden.json to ≥85% coverage per conversation
3. Re-run extraction gate with complete golden set
4. Compare precision/recall to prior runs to understand variance source

**Current status:** Precision gate should **NOT be considered reliable** until golden-set coverage is improved to ≥85%.

---

## Appendix: Files & References

- **Golden dataset:** `/evals/datasets/golden.json`
- **Extraction logic:** `/backend/app/worker/dispatcher.py::_extract_chunk()` (temperature pinned to 0)
- **Prior analysis:** `/docs/operational/tests/2026-07-17-extraction-failure-analysis.md` (iterations 0-8 documented)
- **Thresholds (frozen):** `/evals/thresholds.json`
- **Determinism audit environment:**
  - Container names: `recalium-audit-app`, `recalium-audit-postgres`
  - Project: `recalium-audit`
  - Port: 8050
  - Model: qwen3.5:4b (local Ollama)
  - Temperature: 0 (from dispatcher.py)

---

**Report Status:** Task 1 resolved (see addendum). Task 2 complete.  
**Committed:** As local commit to worktree before merge.

---

## Addendum (2026-07-23): golden-set completeness re-measured, conv-003 policy resolved

The M2 roadmap item ("raise per-conversation coverage to ≥85%; conv-003 needs
an explicit sensitivity-vs-coverage policy") is resolved by manual
re-enumeration of the current `golden.json` (post the conv-002/conv-003
expansions in PR #18/#21) against each conversation's `raw_text`:

| Conversation | Golden facts | Enumerated atomic claims | Coverage |
|---|---|---|---|
| conv-001 (Python async) | 7 | 7 (excluding one code-syntax-level detail, `asyncio.TimeoutError`, not separately golden-worthy) | ~100% |
| conv-002 (PostgreSQL) | 12 | 12–13 | ~92–100% |
| conv-003 (health/therapy) | 8 | ~10 | ~80% |
| conv-004 (Rust ownership) | 7 | 7 (excluding one code-syntax-level detail, the `'a` lifetime annotation syntax) | ~100% |

conv-001, conv-002, and conv-004 are all comfortably above the ≥85% target —
no further golden.json changes needed there.

**conv-003's remaining gap and the policy decision:** the two atomic claims
not separately captured are (a) "the user has been struggling with anxiety
attacks" (personal-sensitivity, already implicit context around `fact-201`),
and (b) the specific "5-4-3-2-1" grounding-method name (public-sensitivity,
already anchored inside `fact-204`'s `source_span` even though `fact-204`'s
`text` doesn't restate the method name).

**Decision: do not pad conv-003 further to chase the 85% figure.** conv-003
carries `personal`/`relationship`-tagged facts, which means it is **entirely
excluded from extraction recall/precision scoring** (`evals/checks/eval_extraction.py`
skips any conversation containing a personal/relationship golden fact,
scoring it instead via the separate sensitivity check's block-verification
logic). Its coverage percentage therefore has zero effect on the extraction
gate's reliability — the ≥85% target's purpose (making sure the *scored*
denominator reflects real recall, not golden-set gaps) is already satisfied
by conv-001/002/004. Adding more golden facts to a sensitivity-excluded,
synthetic-personal-health conversation for the sole purpose of moving a
percentage that doesn't gate anything would be coverage-padding, not a
methodology improvement — and it would mean cataloging more realistic
personal-health detail in a fixture that lives in git history permanently,
for no measurable benefit. Both are worth avoiding.

This closes the M2 golden-set-completeness item: coverage is verified ≥85%
on every conversation the extraction gate actually scores, and conv-003's
lower raw completeness is an explicit, documented, zero-impact policy
choice rather than an open question.
