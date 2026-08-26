# M2 Run-2 Extraction Variance Investigation

**Date**: 2026-08-26  
**Trigger**: M2 baseline `--strict --n-runs 3` — run 2 extraction failed (precision 62.5%, 1 conversation) while runs 1 and 3 passed (2 conversations).

**Artifacts**: [M2 baseline](../tests/artifacts/eval-m2-baseline-2026-08-26/2026-08-26T19-22-52.282640/results.json)

## Question

Was run-2 failure model non-determinism (contradicting 2026-07-23 Ollama bit-for-bit determinism evidence), or a harness / pipeline measurement defect?

## Findings

### Expected extraction corpus

The golden fixture has four conversations. Extraction scoring includes control conversations with golden facts and **no** `personal`/`relationship` labels on any fact:

| Conversation | Golden facts | In extraction eval? |
|--------------|--------------|-------------------|
| conv-001 (Python async) | 7 | Yes |
| conv-002 (PostgreSQL indexing) | 12 | Yes |
| conv-003 (sensitive health) | mixed | No — entire conv skipped (sensitivity gate) |
| conv-004 (Rust ownership) | 7 | Yes |

**Expected:** 3 conversations per run.

### What the baseline actually measured

| Run | `count_conversations` | `count_facts` | Extraction result |
|-----|----------------------|---------------|-------------------|
| 1/3 | 2 | 18 | PASS |
| 2/3 | 1 | 8 | FAIL (precision 62.5%) |
| 3/3 | 2 | 18 | PASS |

Even “passing” runs 1 and 3 only scored **2 of 3** expected conversations. conv-004 (Rust) never contributed facts within the per-conversation poll window.

### Root cause (primary)

**Harness defect:** `eval_extraction.py` averaged metrics only over conversations that produced facts within `EVAL_PIPELINE_TIMEOUT_S` (default 300s). Conversations that timed out were **silently omitted** from the average instead of failing the check.

Effects:

1. **False passes** — runs 1/3 passed despite incomplete coverage (2/3 conversations).
2. **False variance** — run 2 failed precision on a **single-conversation subset** (likely conv-001 only: 8 extracted facts vs 7 golden) while conv-002 did not finish within its poll window after backlog from the prior run.
3. **Misattribution** — looks like model non-determinism on precision; actually **subset scoring** under pipeline backlog.

This does **not** refute 2026-07-17/07-23 determinism evidence for a **fully extracted** corpus on a given model. It shows the eval can report unstable subset metrics when the pipeline does not finish for all conversations.

### Contributing factor (secondary)

**Pipeline backlog across N-run evals:** Each conversation polls independently for up to 300s. Under local Ollama (`qwen3.8:27b`), sequential extraction across multiple ingested conversations plus three full eval runs queues `pending_pipeline` jobs. Later conversations (and later runs) are more likely to miss the timeout.

### Exit code note

`run.log` showed `EXIT_CODE:0` after Overall FAILED because the shell used `| tee` without `pipefail`. The runner itself calls `sys.exit(1)` on failure.

## Decision (engineering)

1. **Fail extraction when coverage is incomplete** — require all expected control conversations to produce facts; report `INCOMPLETE COVERAGE` with missing conv IDs (PR: `fix/m2-extraction-partial-coverage`).
2. **Isolate N-run settings** — fresh `settings` dict per run so `ingested_archive_ids` does not leak across iterations.
3. **Do not rerun** the M2 baseline artifact to replace numbers (PO: record as measured).
4. **Future baselines** — after harness fix, expect extraction to fail until pipeline timeout/capacity is addressed or timeout is raised for local Ollama profiles.

## Still open

- Closed-model control experiment — blocked on `OPENAI_API_KEY` (BYOK).
- Whether `EVAL_PIPELINE_TIMEOUT_S` or pipeline drain/wait should be raised for local Ollama — product/ops tuning, not a threshold change.

## References

- [2026-07-17 determinism audit](../tests/2026-07-17-determinism-and-golden-coverage-audit.md)
- [M2 baseline evidence](./2026-08-26-m2-baseline-eval-evidence.md)
- `docs/roadmap.md` — N-run averaging + determinism notes
