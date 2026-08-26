# M1 Strict Eval Failure — Diagnosis (2026-08-26)

## Symptom
Strict eval failed: extraction **skipped** (zero facts), retrieval collapsed (12.5% R@10).

## Root cause
**Environment misconfiguration:** `.env` sets `OLLAMA_MODEL=qwen3.5:4b`, but that model is **not installed** in local Ollama.

Evidence:
- Container env: `OLLAMA_MODEL=qwen3.5:4b`, `OLLAMA_BASE_URL=http://172.23.0.1:11434`
- `curl http://localhost:11434/api/show -d '{"name":"qwen3.5:4b"}'` → `model 'qwen3.5:4b' not found`
- Postgres jobs: 178 `pending_pipeline` jobs in `failed` state; sample error:
  `HTTPStatusError: Client error '404 Not Found' for url 'http://172.23.0.1:11434/api/chat'`
- Available models include `qwen3.8:27b`, `gemma4:e2b` (via `GET /api/tags`)

Ingest, embeddings (sentence-transformers), MCP, and sensitivity gate checks passed independently; failure is isolated to the Ollama completion path used for extraction/summarization.

## Remediation (PO-authorized, env-only)
Point `OLLAMA_MODEL` at an installed model (`qwen3.8:27b`) and restart the app container so pipeline jobs can complete.

## Not in scope
- No threshold, prompt, or product code changes.
- Eval skip-reason misattribution logged for M2 eval-trustworthiness backlog.
