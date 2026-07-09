# Recalium v1.1 Recommendations — Implementation Status

**Date:** 2026-07-09
**Source of record:** [recommendations.md](recommendations.md) (v1.1 strategic recommendations)
**Method:** code/doc audit against the live repo + `make eval` evidence, then implementation.

Legend: ✅ Done · 🟡 Partial · ⛔ Not started · ⏭️ Deferred (by design)

## Summary

| Item | Area | Status | Evidence |
| --- | --- | --- | --- |
| F1 Hardcoded model names | Impl | ✅ Done | `SUMMARIZE_MODEL`/`EXTRACT_MODEL`/`EMBED_MODEL` settings + dispatcher routing — commit `0b3b156` |
| F2 Per-function provider routing | Impl | ✅ Done | `SUMMARIZE_PROVIDER`/`EXTRACT_PROVIDER`/`EMBED_PROVIDER` + `_resolve_provider/_resolve_model`, transparent skip — `0b3b156` |
| F3 Conversation chunking | Impl | ✅ Done (pre-existing) | `_split_conversation` + `_dedupe_facts` — commit `35f5b89` |
| F4 Hallucinated spans | Impl | ✅ Done | `_validate_spans` clears non-verbatim spans (→ low confidence) — `0b3b156` |
| F5 Link-detection errors | Impl | ✅ Done | `AuditEvent(event_type="link_detection_error")` in link Pass B — `0b3b156` |
| F6 RRF threshold docs | Arch | ✅ Done (pre-existing) | Documented in [retrieval-and-ranking.md](architecture/retrieval-and-ranking.md) |
| F7 Budget unit clarity | Arch | ✅ Done | `CHAR_BUDGET` + char-unit docstring (alias kept) — `0b3b156` |
| F8 Cache invalidation | Arch | ✅ Done | Event-driven `notify_cache_invalidation` + LISTEN/NOTIFY listener + worker-loop hook — `a5e50a8` |
| F9 FTS input sanitization | Testing | ✅ Done | `_sanitize_fts_query` at retrieve entry + adversarial eval queries — `a5e50a8` |
| F11 MCP v2 / SSE ADR | Arch | ✅ Done | [ADR 0001](architecture/decisions/0001-mcp-transport.md); linked from tech-stack.md |
| F13 Commit RR work | Roadmap | ✅ Done (pre-existing) | RR-001…014 on `main` |
| Eval suite harness | Testing | ✅ Done | [evals/](../evals/) + baselines in [artifacts/](operational/tests/artifacts/); re-run this pass |
| Memory-bundle JSON schema | Positioning | ✅ Done | [memory-bundle-schema.md](architecture/memory-bundle-schema.md) |
| Flagship quality claim | Positioning | ✅ Done | [v1.1-quality-baseline.md](operational/validations/v1.1-quality-baseline.md) |
| Performance SLA evidence | Testing | 🟡 Partial | ingest/search P95 measured in evals; restore SLA (RR-007) ⏭️ deferred |
| Accessibility (RR-011) | Testing | 🟡 Partial | Playwright starter added ([frontend/e2e/](../frontend/e2e/)); full keyboard/axe suite pending |
| MCP error envelope (RR-009) | Testing | ✅ Done (pre-existing) | Stable envelope; note stale unit tests below |

## Detail by recommendation section

### §2 Positioning

- **Memory-bundle schema (open format)** — ✅ Published as a formal, versioned
  spec ([memory-bundle-schema.md](architecture/memory-bundle-schema.md)) with a
  JSON Schema (2020-12), item schema, import/dedup semantics, versioning, and
  extension points — matched to `portability.py` v1 bundle.
- **Flagship quality claim** — ✅ Published
  ([v1.1-quality-baseline.md](operational/validations/v1.1-quality-baseline.md)):
  hybrid recall@10 = 1.00, semantic lift +1.00, span fidelity 1.00, with method,
  thresholds, and limitations. Reproducible via `make eval`.

### §3 Roadmap

- **Phase A (commit RR work / F13)** — ✅ Done.
- **Phase B (eval baselines)** — ✅ Done; re-run after code changes this pass.
- **Phase C (perf SLA)** — 🟡 ingest P95 (~18 ms) and hybrid search P95 (~175 ms)
  measured and well under thresholds; **restore SLA (RR-007) ⏭️ deferred** (no
  timed restore evidence yet).
- **Phase D (accessibility / RR-011)** — 🟡 Playwright scaffold + a keyboard
  smoke test added; the exhaustive per-workflow keyboard + axe suite remains.
- **Phase E (MCP v2 spike / F11)** — ✅ Decision recorded as [ADR 0001](architecture/decisions/0001-mcp-transport.md).
- **Backlog 999.x** — ⏭️ Correctly gated behind extraction quality (≥0.75/≥0.8);
  current extraction is 0.625/0.767, so these stay deferred.

### §4 Architecture

- **F6 RRF threshold** — ✅ Already documented (threshold `1/(k+25) ≈ 0.012`).
- **F7 budget units** — ✅ `CHAR_BUDGET` with explicit char-unit note; `DEFAULT_BUDGET`
  kept as a deprecated alias for compatibility.
- **F8 cache invalidation** — ✅ Replaced forget-prone manual invalidation with an
  event-driven signal: writes call `notify_cache_invalidation()` (clears local
  cache + Postgres `NOTIFY`); a lifespan-managed `cache_invalidation_listener()`
  `LISTEN`s and clears (multi-process safe); the worker loop invalidates after
  every processed job; the 60 s TTL remains a safety net.
- **F11 MCP transport** — ✅ ADR: stay on SSE through v1.1, spike Streamable-HTTP
  in v1.2, migrate v1.3+, with non-negotiable constraints (127.0.0.1 bind, stable
  tool contract).

### §5 Implementation fixes

- **F1 / F2** — ✅ Model names and providers are per-function and env-configurable
  (`auto` = provider default / first configured key). An explicit provider with no
  key degrades transparently to `pending_provider` instead of silently switching.
- **F4** — ✅ Verbatim-substring validation clears hallucinated `source_span`s at
  write time (local, no LLM cost); the fact is kept but flagged via the empty-span
  → low-confidence rule.
- **F5** — ✅ Non-fatal link-classification failures now emit
  `link_detection_error` audit events (source/target fact ids + reason).

### §6 Testing / evidence

- **Eval suite** — ✅ Complete (`ingest`, `extraction`, `retrieval`,
  `sensitivity`, `mcp`) with golden dataset, thresholds, and Markdown/JSON
  reporting. Latest run: 5/5 passed.
- **F9 FTS** — ✅ Query input sanitized (NUL/control strip, length cap) before FTS;
  adversarial retrieval queries already exercised in the eval (0 crashes).
- **RR-009 MCP error envelope** — ✅ Implemented. ⚠️ Three stale unit tests in
  `tests/integration/test_phase5_integration.py` still assert the pre-envelope
  string format and omit the now-required `source_metadata`; they pre-date this
  work. Left untouched to avoid test-DB cross-pollution (fixing the success case
  makes it create a job that breaks order-dependent worker tests). **Next action:**
  update those 3 assertions to the envelope + add per-test job cleanup/isolation.

## What changed in this pass

| Commit | Scope |
| --- | --- |
| `0b3b156` | F1, F2, F4, F5, F7 (settings + dispatcher + retrieval + `.env.sample`) |
| `a5e50a8` | F8, F9 (event-driven cache invalidation + FTS sanitization) |
| (docs)   | memory-bundle schema, ADR 0001, v1.1 quality baseline, this status doc, Playwright starter |

Backend regression: **208 non-e2e tests pass** (3 pre-existing stale MCP tests
excepted, see above). New logic covered by resolver/span unit checks and the
existing worker/retrieval suites.

## Remaining / deferred

- **RR-007 restore SLA (≤15 min)** — ⏭️ needs a timed backup→restore run with saved evidence.
- **RR-011 full a11y suite** — 🟡 exhaustive keyboard + axe coverage for every core workflow (starter added).
- **Stale phase-5 MCP tests** — align 3 assertions to the RR-009 envelope + isolate.
- **F11 Streamable-HTTP spike** — v1.2, per ADR 0001.
- **Backlog 999.x** — gated on extraction ≥0.75 recall / ≥0.8 precision.
