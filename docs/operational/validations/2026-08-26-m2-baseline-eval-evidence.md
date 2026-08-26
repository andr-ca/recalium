# M2 Baseline Eval Evidence — Harness Trustworthiness

**Date**: 2026-08-26  
**PO decision**: Record the first M2 `--strict --n-runs 3` baseline as measured; do not rerun to chase a green number (PR #50).

## Command

```bash
python3 evals/runner.py --strict --n-runs 3 \
  --base-url http://localhost:8000 \
  --output-dir docs/operational/tests/artifacts/eval-m2-baseline-2026-08-26
```

**Environment:** Local Docker stack; `OLLAMA_MODEL=qwen3.8:27b` (installed on host). No `OPENAI_API_KEY`.

## Result: extraction FAILED (aggregate), 4/5 checks passed

| Run | ingest | extraction | retrieval | sensitivity | mcp |
|-----|--------|------------|-----------|-------------|-----|
| 1/3 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2/3 | ✓ | ✗ (precision 62.5%, 1 conv) | ✓ | ✓ | ✓ |
| 3/3 | ✓ | ✓ | ✓ | ✓ | ✓ |

**Aggregated extraction:** recall 69.8%, precision 68.3% (threshold 70%) — **FAILED**

Other checks passed across all three runs.

**Artifacts:** [report](../tests/artifacts/eval-m2-baseline-2026-08-26/2026-08-26T19-22-52.282640/report.md), [results.json](../tests/artifacts/eval-m2-baseline-2026-08-26/2026-08-26T19-22-52.282640/results.json), [run.log](../tests/artifacts/eval-m2-baseline-2026-08-26/run.log)

## Notes

- Run 2 evaluated only one conversation (8 facts) vs two in runs 1 and 3 — variance under investigation (M2 follow-up).
- `run.log` shows `EXIT_CODE:0` after Overall FAILED because the log was captured via `| tee`; without `pipefail`, shell `$?` reflects `tee`, not the runner. Runner sets `sys.exit(1)` when overall fails (`evals/runner.py`).
- Closed-model control experiment remains blocked until `OPENAI_API_KEY` is available locally (BYOK; not committed).

## PR #50 scope delivered

- Skip-reason classification (provider/pipeline vs gate-blocked)
- Sensitivity vacuous-pass guard when zero facts in corpus
- Ollama model preflight before checks
- `.env.sample` and local-use guide updates for `OLLAMA_MODEL`
