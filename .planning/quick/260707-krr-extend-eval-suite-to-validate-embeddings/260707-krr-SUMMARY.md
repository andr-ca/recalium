# Quick Task 260707-krr Summary — Embeddings/provider eval validation + Ollama run

**Completed:** 2026-07-08
**Commits:** ee80112 (pipeline fixes), 835d0df (eval suite), 88a1166 (.env.sample)

## What was asked

Improve the eval suite to validate embeddings and other claims; test with Ollama.

## What happened

Enabling the first-ever real configuration (Ollama provider + `EMBED_BACKEND=cpu`)
exposed three product bugs that had to be fixed before any embedding claim was
measurable, plus one P0 product finding:

- **F19 (fixed)**: worker loop lost ALL job status transitions (detached ORM
  session) — jobs reprocessed forever; regression test added.
- **F20 (fixed)**: numpy `str()` bound as pgvector literal — conflict/link
  detection never worked with real embeddings.
- **F21 (fixed)**: aborted transaction from any "non-fatal" step wedged status
  writes.
- **F22 (open, P0)**: the sensitivity gate's NLI classifier blocks essentially
  all real content (tech Q&A → `personal_profile` @0.99) — no summaries or
  facts are ever produced. Documented in docs/recommendations.md with a
  calibration plan using the eval dataset.
- **F18 (open)**: stale-claim recovery only runs at worker startup.

## Eval improvements

- Paraphrase (`semantic_only`) golden queries with verified zero lexical
  overlap → `semantic_lift` metric proves embeddings add recall beyond FTS.
- Provenance-completeness metric (PIPE-02), server-side provider detection,
  differential sensitivity gate test, per-mode search error capture, correct
  nDCG (was crashing on ≥2 results), embedding-readiness wait,
  `EVAL_PIPELINE_TIMEOUT_S`.

## Baseline (run 2, Ollama qwen3.5:4b + embeddings, 2026-07-08)

- Keyword R@5 87.5% / MRR 0.88 / P95 26ms
- Semantic R@10 100% / MRR 1.00 / P95 116ms; Hybrid 100% / 122ms (≥ best single)
- Paraphrase: semantic 100% vs keyword 0% (lift +100%)
- MCP contract 4/4; ingest ✓; extraction+sensitivity SKIP (cause: F22)
- Evidence: docs/operational/tests/artifacts/eval-baseline-2026-07-08-ollama/

## Environment changes

`.env`: `EMBED_BACKEND=cpu`, `OLLAMA_BASE_URL=http://172.23.0.1:11434`,
`OLLAMA_MODEL=qwen3.5:4b`; compose passes `OLLAMA_MODEL` through; app image
rebuilt with sentence-transformers. Note: configuring the provider reactivated
the pending backlog — 20 live jobs processed to `completed` (first completed
statuses in this DB's history); 152 jobs referencing deleted sources
terminal-failed correctly.
