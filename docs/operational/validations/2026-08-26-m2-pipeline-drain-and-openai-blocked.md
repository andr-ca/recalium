# M2 Pipeline Drain + Closed-Model Control Status

**Date**: 2026-08-26  
**PO decision**: OpenAI key present → closed-model control first; absent → local Ollama pipeline drain + post-fix baseline.

## BYOK key presence (values not recorded)

| Key | Repo root `.env` | `backend/.env` | Server API `configured` |
|-----|------------------|----------------|-------------------------|
| `OPENAI_API_KEY` | empty | empty | `false` |
| `ANTHROPIC_API_KEY` | empty | empty | `false` |
| `OLLAMA_BASE_URL` | set | — | `true` |

**Closed-model control experiment:** **blocked** — add `OPENAI_API_KEY` to repo root `.env` and restart `docker compose` before running with `EXTRACT_PROVIDER=openai`.

## Engineering delivered (PR pending)

**Pipeline drain for extraction eval** (`fix/m2-eval-pipeline-drain`):

- `wait_for_archive_pipeline_drain()` — poll archive `status_badge` until all control IDs leave `Processing`
- Extraction check waits for **all** control archives once, then scores facts (replaces per-conversation sequential poll)
- `resolve_pipeline_timeout_s()` — honors `EVAL_PIPELINE_TIMEOUT_S` when set; otherwise 300s default, **600s when only Ollama is configured**

## Post-fix baseline (completed 2026-08-27)

**Artifact:** [report](../tests/artifacts/eval-m2-post-drain-baseline-2026-08-26/2026-08-27T00-24-36.812702/report.md)

**Result:** FAILED — extraction and retrieval failed all 3 runs.

| Metric | Value |
|--------|-------|
| `count_conversations` | 1/3 every run (conv-001 only) |
| Missing | conv-002, conv-004 |
| Drain timeout | 600s (Ollama-only profile) |
| Precision (subset) | 62.5% on 8 facts |

**Interpretation:** Harness correctly reported `INCOMPLETE COVERAGE` (no silent subset pass). conv-002/004 still `Processing` after 600s — archive list pagination missed eval IDs during drain (fixed in PR #53).

## Archive-fix re-baseline (2026-08-27)

After PR #53 + `EVAL_PIPELINE_TIMEOUT_S=900`: runs 2–3 achieved **3/3 coverage**; extraction still failed on **precision ~64%** (honest local-Ollama measurement). See [archive-fix evidence](./2026-08-27-m2-archive-fix-baseline-evidence.md).

Closed-model control remains blocked until `OPENAI_API_KEY` is set in repo root `.env`.

## Anthropic determinism A/B

Still blocked (no `ANTHROPIC_API_KEY` in root `.env`).
