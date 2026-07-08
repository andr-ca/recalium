# Quick Task 260707-krr: Validate embeddings + provider claims; test with Ollama

**Mode:** quick (executed inline by orchestrator — prior task showed live-stack
iteration is required; planner/executor artifacts consolidated here)
**Created:** 2026-07-07

## Goal

Extend the eval suite so the previously unmeasured claims become measured:
semantic/hybrid retrieval (embeddings), extraction quality + span fidelity +
provenance completeness (PIPE-02), summary production — then run the full
suite against the live stack backed by local Ollama and record the baseline.

## Tasks

1. **Stack enablement**
   - `.env`: `EMBED_BACKEND=cpu`, `OLLAMA_BASE_URL=http://172.23.0.1:11434`
     (compose network gateway; Ollama binds `*:11434`), `OLLAMA_MODEL=qwen3.6:latest`
   - `docker-compose.yml`: pass `OLLAMA_MODEL` through to the app container
     (settings default `llama3.2` is not installed)
   - `.env.sample`: document `OLLAMA_MODEL`
   - Rebuild image (`EMBED_BACKEND=cpu` installs sentence-transformers), restart stack
   - Verify: `/api/settings/keys` shows ollama configured; semantic search not degraded

2. **Eval improvements**
   - Provider detection via `GET /api/settings/keys` (server truth) instead of local env vars
   - `golden.json`: add `semantic_only` paraphrase queries (no lexical overlap with
     source text) so embeddings are validated as adding recall beyond FTS
   - `eval_retrieval.py`: score paraphrase queries per mode (`semantic_lift`);
     assert semantic not degraded when embeddings enabled; keep hybrid ≥ best single mode
   - `eval_extraction.py`: add provenance completeness metric (fraction of extracted
     facts with confidence_tier + derivation_method + derivation_model + source_span)
     and summary-presence check (search returns type=summary/fact items post-processing)
   - `thresholds.json` + `README.md` updated accordingly

3. **Run + evidence**
   - `make eval` green (or failures analyzed as product findings, not harness bugs)
   - Copy report to `docs/operational/tests/artifacts/eval-baseline-<date>-ollama/`
   - Update `docs/recommendations.md` §8 baseline table; STATE.md quick-task row

## Verify

- `make eval` exit 0 with semantic+hybrid+extraction sections populated
- Evidence artifacts committed; no secrets in any committed file
