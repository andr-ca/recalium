# M2 Post-Archive-Fix Baseline Evidence

**Date**: 2026-08-27  
**PO context**: Re-baseline after PR #53 scoped archive fetch + `EVAL_PIPELINE_TIMEOUT_S=900`.

## Command

```bash
export EVAL_PIPELINE_TIMEOUT_S=900
python3 evals/runner.py --strict --n-runs 3 \
  --base-url http://localhost:8000 \
  --output-dir docs/operational/tests/artifacts/eval-m2-archive-fix-baseline-2026-08-27
```

**Environment:** Docker stack; Ollama `qwen3.8:27b` (root `.env`). No `OPENAI_API_KEY`.

## Result: extraction FAILED (precision), 4/5 checks passed

| Run | Extraction coverage | Extraction pass? | Retrieval |
|-----|---------------------|------------------|-----------|
| 1/3 | 2/3 (missing conv-004) | ✓ (71.25% precision on subset) | ✓ |
| 2/3 | **3/3** | ✗ (64.17% precision) | ✓ |
| 3/3 | **3/3** | ✗ (64.17% precision) | ✓ |

**Aggregate extraction:** recall 69.8%, precision **66.5%** (threshold 70%) — **FAILED**  
**Aggregate coverage:** 2.67/3 conversations (run 1 incomplete on conv-004)

Other checks passed all three runs. Retrieval strong (hybrid R@10 100% on runs 2–3).

**Artifacts:** [report](../tests/artifacts/eval-m2-archive-fix-baseline-2026-08-27/2026-08-27T01-56-27.691259/report.md), [results.json](../tests/artifacts/eval-m2-archive-fix-baseline-2026-08-27/2026-08-27T01-56-27.691259/results.json)

## Interpretation (for PO)

1. **Harness trustworthiness:** Archive-scoped drain + 900s timeout achieves **full 3/3 coverage** once pipeline backlog clears (runs 2–3). Run 1 conv-004 lag is cold-start/backlog, not subset-scoring regression.
2. **Product signal:** With honest full-corpus measurement, local Ollama precision **~64%** — below the 70% release gate and far from the 999.x unlock bar (≥80%). Supports roadmap sequencing: closed-model control experiment next to answer model vs method.
3. **Closed-model control:** Still blocked — `OPENAI_API_KEY` empty in repo root `.env`.

## Comparison to prior baselines

| Baseline | Coverage | Precision | Harness issue? |
|----------|----------|-----------|----------------|
| M2 initial (2026-08-26) | 2/3 or 1/3 | 68.3% agg | Subset scoring + drain |
| Post-drain (2026-08-27 00:24) | 1/3 all runs | 62.5% subset | Archive list pagination |
| **Archive-fix (this run)** | **3/3 on runs 2–3** | **64.2% full corpus** | None — real model gate |
