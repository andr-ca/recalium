# M1 Strict Eval Evidence — v1.0 GA Gate

**Date**: 2026-08-26  
**PO decision**: Run `evals/runner.py --strict` as final M1 exit criterion before `v1.0.0` tag.

## Green run (authoritative)

**Command:**
```bash
python3 evals/runner.py --strict --base-url http://localhost:8000 \
  --output-dir docs/operational/tests/artifacts/eval-strict-m1-rerun-2026-08-26
```

**Result:** ✓ PASSED — 5/5 checks, 0 skipped

| Check | Status | Key metrics |
|-------|--------|-------------|
| ingest | ✓ | P95 42ms |
| extraction | ✓ | recall 0.69, precision 0.71, span fidelity 1.00 |
| retrieval | ✓ | hybrid R@10 passes thresholds |
| sensitivity | ✓ | block verified, 0 leaks |
| mcp | ✓ | contract + provenance |

**Artifacts:** [eval-strict-m1-rerun-2026-08-26](../tests/artifacts/eval-strict-m1-rerun-2026-08-26/2026-08-26T13-39-40.902250/report.md)

## Failed run + diagnosis (same day)

Initial strict run failed because `OLLAMA_MODEL=qwen3.5:4b` was configured but not installed locally (Ollama 404 on `/api/chat`). Environment fix: point model at installed `qwen3.8:27b`, restart stack, single authorized rerun.

**Artifacts:** [diagnosis.md](../tests/artifacts/eval-strict-m1-2026-08-26/diagnosis.md), [failed report](../tests/artifacts/eval-strict-m1-2026-08-26/2026-08-26T13-09-47.819402/report.md)

## M2 backlog note (PO)

Eval skip-reason misattributed extraction failure as "gate-blocked"; sensitivity can pass vacuously when zero facts extracted — track under M2 eval-trustworthiness.
