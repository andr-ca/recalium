# M2 Cold-Start Coverage Baseline Evidence

**Date**: 2026-08-27  
**PR**: #57 — Ollama warmup + pre-ingest drain + 900s Ollama-only default

## Command

```bash
python3 evals/runner.py --strict --n-runs 3 \
  --base-url http://localhost:8000 \
  --output-dir docs/operational/tests/artifacts/eval-m2-cold-start-baseline-2026-08-27
```

**Environment:** Docker stack; Ollama `qwen3.8:27b`. No `OPENAI_API_KEY`. Warmup loaded model before Run 1.

## Result: 3/3 coverage on all three runs — harness goal met

| Run | Coverage | Extraction | Retrieval |
|-----|----------|------------|-----------|
| 1/3 | **3/3** | ✗ precision 64.17% | ✓ |
| 2/3 | **3/3** | ✗ precision 64.17% | ✓ |
| 3/3 | **3/3** | ✗ precision 64.17% | ✓ |

**Aggregate:** recall 69.8%, precision **64.17%** (stdev **0.0**), `count_conversations` = 3.0 (stdev 0.0)

Extraction fails the 70% release gate on quality — not coverage. ingest / retrieval / sensitivity / mcp passed all runs.

**Artifacts:** [report](../tests/artifacts/eval-m2-cold-start-baseline-2026-08-27/2026-08-27T18-38-50.821071/report.md), [results.json](../tests/artifacts/eval-m2-cold-start-baseline-2026-08-27/2026-08-27T18-38-50.821071/results.json)

## Comparison

| Baseline | Run-1 coverage | Precision (full) |
|----------|----------------|------------------|
| Archive-fix (prior) | 2/3 | ~64% on runs 2–3 |
| **Cold-start fix (this)** | **3/3** | **64.17% all runs** |

## Conclusion

Harness cold-start coverage is closed. Ready for closed-model control experiment when `OPENAI_API_KEY` is in repo root `.env` (see runbook).
