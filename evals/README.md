# Recalium Evaluation Suite

This directory contains the evaluation harness for measuring Recalium's core claims: memory capture, transformation, retrieval quality, and security.

## Quick Start

### Prerequisites

- Docker Compose running with `recalium-app` at `http://localhost:8000`
- Python 3.12+ with `uv` package manager
- `.env` file with optional provider keys (OPENAI_API_KEY, ANTHROPIC_API_KEY) for extraction tests

### Run Evals

```bash
# Option 1: Via make target (simplest)
make eval

# Option 2: Direct CLI (with custom base URL)
cd backend && uv run --project . python ../evals/runner.py --base-url http://localhost:8000 --output-dir ../evals/results

# Option 3: Offline syntax check (before stack is running)
cd backend && uv run --project . python -m compileall ../evals
cd backend && uv run --project . python ../evals/runner.py --help
```

### Output

Evals produce:
- `evals/results/<timestamp>/report.md` — human-readable summary with pass/fail per metric
- `evals/results/<timestamp>/results.json` — full numeric payload for automation
- Exit code: 0 if all thresholds met, 1 if any fail

## Metric Definitions

### Retrieval Metrics

**Paraphrase / embedding validation (semantic_only queries):** golden queries
flagged `semantic_only` are paraphrases sharing no content-word stems with
their source conversation, verified programmatically at authoring time.
Keyword/FTS is expected to miss them. When the stack runs with embeddings
(`EMBED_BACKEND=cpu`), the check scores them per mode and requires:

- `semantic`/`hybrid` paraphrase recall@10 ≥ 0.66 (embeddings find what FTS can't)
- `semantic_lift` > 0 (semantic paraphrase recall exceeds keyword's)

These queries are excluded from the standard per-mode averages. When embeddings
are unavailable (degraded mode), paraphrase scoring is skipped and reported.

**Extraction also reports `provenance_completeness`** (PIPE-02): the fraction
of extracted facts carrying all of source_span, confidence_tier,
derivation_method, and derivation_model — threshold 1.0 (absolute).


**recall@k:** Fraction of the top-k retrieved results that are in the golden set of relevant items.
- Formula: `|retrieved[:k] ∩ relevant| / |relevant|`
- Range: 0.0–1.0
- Higher is better
- Example: If top-10 results contain 7 of 10 relevant facts, recall@10 = 0.7

**precision@k:** Fraction of the top-k retrieved results that are relevant.
- Formula: `|retrieved[:k] ∩ relevant| / k`
- Range: 0.0–1.0
- Higher is better
- Example: If top-5 results contain 4 relevant facts, precision@5 = 0.8

**MRR (Mean Reciprocal Rank):** Position of the first relevant result, averaged across queries.
- Formula: `mean(1 / rank_of_first_relevant_item for each query)`
- Range: 0.0–1.0
- Higher is better
- Example: If first relevant item is at rank 3, MRR contribution = 1/3 ≈ 0.33

**nDCG@k (Normalized Discounted Cumulative Gain):** Ranking quality metric accounting for relevance gradation.
- Formula: `DCG@k / IDCG@k` (see https://en.wikipedia.org/wiki/Discounted_cumulative_gain)
- Range: 0.0–1.0
- Higher is better
- Penalizes irrelevant items early in the ranking

### Extraction Metrics

**recall:** Fraction of golden facts that are extracted.
- Formula: `|extracted ∩ golden| / |golden|` (after fuzzy matching)
- Range: 0.0–1.0
- Higher is better
- Fuzzy match: extracted text contains ≥80% of expected text or vice versa

**precision:** Fraction of extracted facts that are correct.
- Formula: `|extracted ∩ golden| / |extracted|` (after fuzzy matching)
- Range: 0.0–1.0
- Higher is better

**span_fidelity:** Fraction of extracted facts where `source_span` is a verbatim substring of the raw source text.
- Formula: `|facts_with_valid_span| / |extracted_facts|`
- Range: 0.0–1.0
- Higher is better
- Directly measures hallucinated spans

### Performance Metrics

**latency_percentiles:** Response time distribution (P50, P95, P99) in milliseconds.
- P50: 50th percentile (median)
- P95: 95th percentile (acceptable for SLA)
- P99: 99th percentile (tail latency)
- Example: P95=1500ms means 95% of requests complete within 1.5 seconds

### Sensitivity Metrics

**Differential gate test (requires a configured provider):** sensitive
(personal/relationship) conversations are ingested through the same pipeline as
the control conversations. The gate must prevent LLM extraction for them:

- **block_verified:** 1.0 when zero facts are attributed to sensitive archive
  items *while* control conversations produced facts through the same provider
  (the control comes from the extraction check). 0.0 = LEAK — sensitive content
  reached the LLM extraction path.
- **leaked_fact_count:** number of facts derived from sensitive conversations
  (must be 0).

**Skipped in no-key mode:** without a provider, blocking is indistinguishable
from idling. Direct gate observability (an audit event / job field — F15 in
`docs/recommendations.md`) would make this check exact instead of differential
and runnable without a provider.

### MCP Metrics

Exercised over the real MCP protocol (SSE transport via `mcp.client.sse`),
mirroring `backend/tests/e2e/test_live_stack.py`:

- **ingest_accepted:** well-formed `ingest_memory` request is accepted (1.0 required)
- **retrieve_memory_provenance:** retrieved items carry `provenance`, `source_id`, `type`, `conflict_label` (1.0 required)
- **retrieve_budget_metadata:** response carries `budget_used`, `budget_limit`, `trimming_reason`, `retrieval_mode` (1.0 required)
- **structured_error_correctness:** malformed `ingest_memory` returns a structured error envelope with `type`/`code` (1.0 required)

## Thresholds

Baseline thresholds are defined in `thresholds.json`:

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| ingest_latency_p95_ms | 1000 (≤1s) | Product claim: fast ingest |
| extraction_recall | 0.6 (≥60%) | Baseline: must capture majority of facts |
| extraction_precision | 0.7 (≥70%) | Baseline: must be mostly correct |
| extraction_span_fidelity | 0.95 (≥95%) | Stringent: provenance is the differentiator |
| retrieval_recall_at_10_hybrid | 0.7 (≥70%) | Baseline: hybrid must beat keyword (~40%) |
| retrieval_latency_p95_ms | 2000 (≤2s) | Product claim: fast search |
| sensitivity_block_rate | 1.0 (100%) | Critical: zero tolerance for leaks |
| mcp_error_correctness | 1.0 (100%) | Critical: errors must be well-formed |

Thresholds are **frozen for v1.1** (not changed between runs) to enable longitudinal comparison. Baseline is established on initial run against live stack.

## Running with Ollama (fully local provider)

1. In `.env`: set `OLLAMA_BASE_URL` to an address reachable **from the app
   container** (e.g. the compose network gateway, `http://172.23.0.1:11434` —
   Ollama must listen beyond localhost, `OLLAMA_HOST=0.0.0.0`), and set
   `OLLAMA_MODEL` to a pulled model (e.g. `qwen3.5:4b`; the default `llama3.2`
   must be pulled first). Set `EMBED_BACKEND=cpu` for semantic search.
2. Rebuild + restart: `docker compose build recalium-app && docker compose up -d`
   (the `cpu` build installs sentence-transformers).
3. `make eval`. Local models are slow — raise `EVAL_PIPELINE_TIMEOUT_S` if
   extraction/retrieval checks time out waiting for the pipeline.

Note: configuring a provider re-activates any `pending_provider` backlog — the
worker will process previously ingested items through the new provider.

## Idempotency and Cleanup

Eval items are ingested with `source_name` prefixed `eval-` (e.g.
`eval-conv-001`, `eval-sensitivity-conv-003`, `eval-mcp-contract-<tag>`). At
the start of each run, the ingest check **soft-deletes all prior `eval-`
items** via `DELETE /api/archive/{id}` before ingesting fresh copies. This
keeps runs repeatable — without it, identical already-indexed copies from
earlier runs shadow the current run's items and recall collapses to zero — and
prevents eval data from accumulating in your archive. Retrieval relevance is
resolved through the current run's server-assigned `archive_ids`, matched
against each retrieved item's `source_id`.

## No-Key Mode Behavior

The eval suite gracefully degrades when provider keys are missing:

- **No OPENAI_API_KEY / ANTHROPIC_API_KEY:** Extraction evals skip with reason "No LLM provider configured"
- **No EMBED_BACKEND (or EMBED_BACKEND=none):** Semantic retrieval evals skip with reason "Embeddings not configured"; keyword evals still run
- **Stack is down (health check fails):** All evals skip with reason "Stack down; cannot connect to http://localhost:8000"

Each skipped eval logs clearly so users know why results are incomplete.

## Dataset Schema

Golden labels are stored in `datasets/golden.json` with this schema:

```json
{
  "schema_version": "1.0",
  "conversations": [
    {
      "id": "conv-001",
      "source": "ChatGPT export",
      "raw_text": "User: What's the capital of France?\nAssistant: The capital of France is Paris...",
      "facts": [
        {
          "id": "fact-001",
          "text": "Paris is the capital of France",
          "source_span": "capital of France is Paris",
          "confidence": 0.9,
          "tags": ["geography", "capitals"]
        }
      ],
      "metadata": {
        "import_method": "web_export",
        "conversation_length_tokens": 250,
        "has_code": false
      }
    }
  ],
  "queries": [
    {
      "id": "q-001",
      "text": "What is the capital of France?",
      "relevant_fact_ids": ["fact-001"],
      "sensitivity_level": "public"
    },
    {
      "id": "q-002",
      "text": "1e5",
      "relevant_fact_ids": [],
      "sensitivity_level": "public",
      "is_adversarial": true,
      "adversarial_reason": "scientific notation parsing"
    }
  ]
}
```

**Extending the schema:** Users can add custom fields to `facts` and `queries` objects; the eval runner only consumes standard fields.

## Extending Evals

To add a new check:

1. Create `evals/checks/eval_mycheck.py` with:
   ```python
   async def run_check(client, golden, settings):
       """Run custom check against live stack.
       
       Args:
           client: httpx.AsyncClient authenticated to stack
           golden: Parsed golden.json dataset
           settings: Environment settings (base_url, etc.)
       
       Returns:
           CheckResult(name="my_check", passed=True/False, metrics={"key": value}, details="...")
       """
       # Your implementation
       return CheckResult(...)
   ```

2. Register in `runner.py`:
   ```python
   from evals.checks.eval_mycheck import run_check as run_mycheck
   # Add to checks list in main()
   ```

3. Add threshold to `thresholds.json` if needed.

## Known Limitations

- **Synthetic data:** Golden labels are synthetic AI conversations, not real production data. Actual extraction/retrieval quality may differ.
- **No multi-turn reasoning:** Queries are single-turn; multi-turn conversation context not modeled.
- **Local embedding model:** All semantic search uses local all-MiniLM-L6-v2 model (384 dims). OpenAI or other remote embeddings may perform differently.
- **No backup/restore timing:** RR-007 (restore SLA) is not measured; backup/restore UI validation deferred to separate Playwright suite.

## Performance Baseline

Initial baseline established on [DATE—filled by first run]:

| Check | Status | Metric | Value | Threshold | Pass? |
|-------|--------|--------|-------|-----------|-------|
| ingest | ✓ | P95 latency | — ms | ≤1000 ms | — |
| extraction | ✓ | recall | — | ≥0.6 | — |
| extraction | ✓ | precision | — | ≥0.7 | — |
| extraction | ✓ | span_fidelity | — | ≥0.95 | — |
| retrieval | ✓ | recall@10 (hybrid) | — | ≥0.7 | — |
| retrieval | ✓ | latency P95 | — ms | ≤2000 ms | — |
| sensitivity | ✓ | block_rate | — | 1.0 | — |
| mcp | ✓ | error_correctness | — | 1.0 | — |

*To be filled after initial run.*

## Troubleshooting

**"Stack down; cannot connect to http://localhost:8000"**
- Ensure Docker Compose is running: `docker compose up -d`
- Verify health: `curl http://localhost:8000/api/health`

**"No LLM provider configured"** (extraction evals skipped)
- Set OPENAI_API_KEY or ANTHROPIC_API_KEY in `.env` to enable extraction evals
- Verify: `cd backend && uv run --project . python -c "from app.worker.dispatcher import settings; print(settings.OPENAI_API_KEY[:10])"`

**"Embeddings not configured"** (semantic evals skipped)
- Set EMBED_BACKEND=cpu (or leave as default) to enable local embeddings
- Verify: `cd backend && uv run --project . python -c "from app.domain.embedding.service import EmbeddingService; print(EmbeddingService().model_name)"`

**"Extraction recall 0.58 < 0.6 threshold"**
- This may indicate F3 (truncation on long conversations) or F4 (hallucinated spans filtering).
- Check detailed findings in report.md and compare with eval dataset (check if long conversations are included).

## References

- Product claims: `docs/recommendations.md` (section 1–3)
- Analysis findings: `.planning/quick/260707-jlg-in-depth-project-analysis-recommendation/260707-jlg-ANALYSIS.md`
- Release readiness gaps: `docs/operational/validations/recalium-v1-release-readiness-gap-register.md`
- API reference: `docs/architecture/api-and-mcp.md`
- MCP tools: `backend/app/mcp_server/server.py`

---

*Eval suite v1.0, established 2026-07-07. Baseline thresholds frozen for v1.1.*
