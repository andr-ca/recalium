# Recalium In-Depth Analysis — Input for Recommendations Doc + Eval Suite

**Analyst:** Claude (orchestrator session), 2026-07-07
**Purpose:** Ground-truth findings for (a) `docs/recommendations.md` and (b) a new eval suite under `evals/`. Planner and executor MUST treat these findings as verified against the codebase — do not re-derive, do not invent findings not listed here without checking the code.

---

## 1. Project state (verified)

- GSD milestone v1 marked complete 2026-03-24: 5 phases, 52/52 requirements, 191 tests green (`.planning/ROADMAP.md`, `.planning/STATE.md`).
- A second wave of release-readiness work (2026-04-27+) is tracked in `docs/operational/validations/recalium-v1-release-readiness-gap-register.md` (RR-001…RR-014). Much of it is implemented but **uncommitted on `main`** (large modified/untracked set in `git status`): facts lifecycle API, tags/links, MCP ingest contract expansion, review-queue UI, backup/restore UI, agent skills.
- Backend ~6.7k LOC app + 4.4k routes; tests: unit/domain/api/mcp/integration + live-stack E2E (`backend/tests/e2e/test_live_stack.py`); frontend Vitest suites exist; Playwright/accessibility evidence pending (RR-011).
- Backlog phases 999.1–999.4: wiki synthesis pages, knowledge lint, query-to-wiki promotion, llmwiki import/export bridge.

## 2. Core gap: the product's central claim is unmeasured

Recalium claims: "future AI session retrieves relevant, source-backed context." Nothing measures *relevant*:

- ROADMAP research flags still open: "RRF recall empirical validation" (k=60, ef_search=100 never validated), "sentence-transformers model quality" (all-MiniLM-L6-v2, 384-dim, never validated on AI-conversation content).
- STATE.md Performance Metrics table: ingest P95 ≤1s, search P95 ≤2s, restore ≤15min — all "Not yet measured".
- Tests assert plumbing (result count > 0, fields present), never ranking quality, extraction precision/recall, or span fidelity.
- Sensitivity gate (keyword heuristics + CrossEncoder NLI fallback) — "domain validation against real exports deferred to beta"; a false-negative here leaks personal content to external providers, the worst failure mode the product has.

## 3. Verified implementation findings (file:line anchors)

### Pipeline / providers (`backend/app/worker/dispatcher.py`)
- F1. Model names hardcoded: `gpt-4o-mini` (line ~82), `claude-3-haiku-20240307` (line ~96 — a deprecated 2024 model). Should come from `.env` via `pydantic-settings` (violates project's own configuration principle; CLAUDE.md says "GPT-4o-mini *or configured model*").
- F2. Provider selection is fixed if/elif priority (openai → anthropic → ollama). Requirement BYOK-08 says "switch providers per function" — not expressible today. Needs per-function setting: `SUMMARIZE_PROVIDER`, `EXTRACT_PROVIDER`, `EMBED_PROVIDER`.
- F3. Whole conversation is sent in a single LLM call, `max_tokens=512` for summaries; no chunking/map-reduce for long conversations → silent truncation of facts on large ChatGPT exports (the primary import source).
- F4. Fact extraction is one-shot JSON prompt (FACT_EXTRACTION_SYSTEM_PROMPT, lines 45–65). No verification that `source_span` is a verbatim substring of the source; hallucinated spans would poison provenance — the product's differentiator.
- F5. Link detection Pass B classifies only top-5 semantic pairs via LLM; errors swallowed with `logger.debug` (non-fatal, fine, but unobservable).

### Retrieval (`backend/app/domain/retrieval/service.py`)
- F6. RRF merge implemented correctly (k=60, top-50/mode, top-20). `RRF_MIN_THRESHOLD = 1/(k+25)` filters single-mode low-rank items — undocumented behavior worth flagging.
- F7. `DEFAULT_BUDGET: int = 2000` — unit ambiguity (chars vs tokens); budget trimming is char-based while MCP consumers think in tokens.
- F8. Module-level `TTLCache(256, ttl=60)` — process-global; invalidation must be called manually after writes (E2E test had to invalidate manually — see commit 59003ab).
- F9. Prior E2E bug (commit 132696d): FTS query with tag parsed as scientific notation — indicates keyword-search input sanitization is fragile; eval should include adversarial query cases.

### MCP (`backend/app/mcp_server/server.py`)
- F10. Four tools: `retrieve_memory`, `ingest_memory`, `get_fact_links`, `list_tags`. SSE transport, bound 127.0.0.1. Error envelope recently standardized (RR-009) but only partially evidenced.
- F11. `mcp>=1.26,<2` pin: SDK v2 lands with breaking transport changes (Q1 2026 per tech-stack doc). SSE is already legacy in the MCP spec (Streamable HTTP is the current transport). Migration risk should be on the roadmap.

### Ops/other
- F12. Restore SLA (≤15 min) never measured (RR-007); no timing evidence exists.
- F13. Uncommitted release-readiness work on `main` is itself a release risk — recommend committing in reviewable slices first.
- F14. Embeddings record model_name+dim per row (good); provider-switch stale-embedding fallback exists per Phase 2 criteria.

## 4. Recommendations doc — required structure and content

Deliverable: `docs/recommendations.md`. It must cover, in this order:

1. **Executive summary** — v1 is functionally complete but quality-unproven; top 5 actions.
2. **Idea/positioning level** — the moat is provenance-backed memory portability; recommend: publish the memory-bundle JSON schema as a versioned spec (open format claim currently unsubstantiated — no formal schema doc exists, only export code); pick ONE flagship claim ("source-backed retrieval that you can audit") and build evidence for it.
3. **Roadmap level** — proposed next milestone (v1.1 "Prove it"): (a) commit + ship pending RR work, (b) eval suite + quality baselines (this task delivers the harness), (c) performance/restore SLA evidence, (d) Playwright keyboard/a11y evidence, (e) MCP v2/Streamable-HTTP migration spike. Then v1.2: retrieval quality improvements informed by eval results (chunking, span verification, per-function providers). Position backlog 999.x (wiki synthesis etc.) AFTER quality baseline exists — synthesis on top of unvalidated extraction compounds errors.
4. **Architecture level** — keep two-container topology; document RRF threshold behavior (F6); define budget units as tokens with an explicit tokenizer or rename to `char_budget` (F7); plan MCP transport migration (F11); event-driven cache invalidation instead of manual (F8).
5. **Implementation level (specific)** — F1–F5 fixes with concrete code-level guidance: settings-driven model names + per-function provider routing; conversation chunking with map-reduce summarization; verbatim source-span validation at write time (reject/downgrade facts whose span isn't a substring — cheap, no LLM needed); adversarial input sanitization tests for FTS (F9).
6. **Testing/evidence level** — map each RR gap to the missing evidence artifact; describe the new eval suite and how it closes the ROADMAP research flags.
7. **Prioritized action table** — impact × effort, P0/P1/P2.

## 5. Eval suite — design (deliverable: `evals/` at repo root)

Purpose: measure how well Recalium does what it claims. Must run against the live local stack (docker compose up, port 8000), degrade gracefully (skip with clear message when stack down), and write evidence artifacts.

Structure:
```
evals/
  README.md                  # how to run, metric definitions, thresholds rationale
  pyproject.toml OR reuse backend deps via uv --project backend
  datasets/
    conversations/           # 8–12 synthetic conversations as generic JSON (importable via existing ingest API)
    golden.json              # labeled ground truth: expected facts (text + verbatim span + confidence),
                             # retrieval queries with relevant-item labels, sensitivity labels
  runner.py                  # CLI: uv run python evals/runner.py --base-url http://localhost:8000
  metrics.py                 # recall@k, precision@k, MRR, nDCG@10, span-fidelity, latency percentiles
  checks/
    eval_ingest.py           # ingest each dataset conversation; measure ingest latency P95 (claim: ≤1s)
    eval_extraction.py       # after pipeline completes: fact precision/recall vs golden (fuzzy match),
                             # span fidelity = % of stored source_spans that are verbatim substrings of raw source
    eval_retrieval.py        # per mode (keyword/semantic/hybrid): recall@5/@10, MRR, nDCG@10 vs golden query labels;
                             # hybrid must beat or match best single mode; latency P95 (claim: ≤2s);
                             # adversarial queries (numbers, '1e5'-like tokens, punctuation) must not 500
    eval_sensitivity.py      # personal/relationship-labeled conversations must be BLOCKED from external dispatch
                             # (verify via job states/audit, no provider key needed — assert gate decision)
    eval_mcp.py              # retrieve_memory returns provenance fields, conflict labels, budget metadata;
                             # malformed ingest gets structured error envelope
  report.py                  # emits evals/results/<timestamp>/report.md + results.json;
                             # compares against thresholds.json → exit code 0/1
  thresholds.json            # initial thresholds (recall@10 ≥ 0.7 hybrid, span fidelity ≥ 0.95,
                             # extraction recall ≥ 0.6/precision ≥ 0.7, latency per claims, sensitivity block rate = 1.0)
```

Design constraints (locked):
- No-key mode must work: extraction evals SKIP (with reason) when no LLM provider configured; retrieval keyword-mode evals still run; semantic evals run when EMBED_BACKEND=cpu.
- Use only committed stack deps (httpx, pytest optional); runner is a plain asyncio CLI, not pytest, so it can emit a report file; keep it runnable via `make eval` (add Makefile target).
- Datasets are synthetic (no real personal data) but shaped like real ChatGPT/Claude exports, including one long conversation (>8k tokens) to expose F3 truncation, and personal-content cases for the sensitivity gate.
- Golden labels live in ONE file with a documented schema so users can extend.
- Evidence output path convention: `docs/operational/tests/` already exists — report copy or pointer goes there per gap-register evidence rules.
- Follow `.env` conventions: base URL etc. via env with defaults, never hardcode secrets. Update `.env.sample` if new vars are introduced.

## 6. Explicit non-goals for this quick task

- No production code changes (F1–F5 fixes are recommendations, not to be implemented now).
- No new backend endpoints; evals use existing API/MCP surface only.
- No real provider keys required to run the baseline eval.
