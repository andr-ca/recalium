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

## Post-fix baseline

After merge, run and record:

```bash
python3 evals/runner.py --strict --n-runs 3 \
  --base-url http://localhost:8000 \
  --output-dir docs/operational/tests/artifacts/eval-m2-post-drain-baseline-2026-08-26
```

Success criterion: **3/3 control conversations** on every run (`count_conversations` = `count_conversations_expected` = 3).

Artifact path will be linked here when the run completes.

## Anthropic determinism A/B

Still blocked (no `ANTHROPIC_API_KEY` in root `.env`).
