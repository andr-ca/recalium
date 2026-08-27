# M2 Closed-Model Control Experiment — Runbook

**Purpose:** Answer whether extraction precision gap is the **local model** (Ollama) or the **method** (prompt/pipeline). Required before chunk-metadata or other architecture changes (roadmap: measurement → closed-model control → architecture last).

**999.x unlock bar (not this experiment's pass/fail gate):** recall ≥0.75, precision ≥0.80.

**Release gates (frozen in `evals/thresholds.json`):** recall ≥0.60, precision ≥0.70.

## Prerequisites

1. **Repo root `.env`** (used by `docker compose` — not `backend/.env` alone):
   ```bash
   OPENAI_API_KEY=sk-...          # required for this experiment
   EXTRACT_PROVIDER=openai        # pin extraction to OpenAI (not auto/Ollama)
   EXTRACT_MODEL=gpt-4o-mini      # or gpt-4o for GPT-4-class ceiling
   ```
2. Restart stack after editing `.env`:
   ```bash
   docker compose down && docker compose up -d
   ```
3. Verify provider:
   ```bash
   curl -s http://localhost:8000/api/settings/keys | python3 -m json.tool
   # openai.configured must be true
   ```
4. Eval preflight (from repo root):
   ```bash
   python3 -c "
   import asyncio, httpx
   from evals.preflight import preflight_extraction_provider
   async def main():
       async with httpx.AsyncClient() as c:
           ok, msg = await preflight_extraction_provider(c, 'http://localhost:8000')
           print(ok, msg)
   asyncio.run(main())
   "
   ```

## Run

Closed models are faster than local Ollama; default 300s pipeline drain is usually sufficient. Local Ollama baselines used `EVAL_PIPELINE_TIMEOUT_S=900`.

```bash
export EVAL_PIPELINE_TIMEOUT_S=300   # override only if needed

python3 evals/runner.py --strict --n-runs 3 \
  --base-url http://localhost:8000 \
  --output-dir docs/operational/tests/artifacts/eval-m2-closed-model-control-YYYY-MM-DD
```

**Success criteria for the experiment (measurement quality, not release gate):**

- Every run: `count_conversations` = `count_conversations_expected` = **3** (no `INCOMPLETE COVERAGE`)
- Record recall/precision mean + stdev from the artifact
- Write evidence doc under `docs/operational/validations/` linking the artifact

## Interpret results

| Outcome | Conclusion | Next step (PO) |
|---------|------------|----------------|
| Precision ≥0.80, recall ≥0.75 | Method viable; local model was the ceiling | Local tuning or accept BYOK path for quality |
| Precision ≥0.70 but <0.80 | Method better than Ollama; below 999.x bar | Prompt/golden review before architecture spike |
| Precision still ~64% (similar to Ollama) | Likely **method/prompt/golden** limit, not model | Chunk-metadata spike only after PO review |
| INCOMPLETE COVERAGE on closed model | **Harness/pipeline defect** — investigate before interpreting | Do not record as model ceiling |

Compare against local baseline: `docs/operational/validations/2026-08-27-m2-archive-fix-baseline-evidence.md` (Ollama qwen3.8:27b, precision ~64%, 3/3 on runs 2–3).

## After the run

1. Commit artifact + evidence doc via PR (do not commit `.env` or keys).
2. Optionally restore local profile in root `.env`:
   ```bash
   EXTRACT_PROVIDER=auto   # or ollama
   # clear or comment OPENAI_API_KEY if returning to local-only
   docker compose up -d --force-recreate recalium-app
   ```
3. Report to PO with the model-vs-method conclusion.

## Anthropic follow-on (optional)

If `ANTHROPIC_API_KEY` is also set, roadmap M2 still needs an Anthropic `temperature=0` determinism A/B — separate from this OpenAI control experiment; run only after OpenAI control is recorded.

## References

- `docs/roadmap.md` — M2 sequencing
- `evals/thresholds.json` — frozen release gates
- `docs/operational/validations/2026-08-26-m2-run2-variance-investigation.md` — harness history
