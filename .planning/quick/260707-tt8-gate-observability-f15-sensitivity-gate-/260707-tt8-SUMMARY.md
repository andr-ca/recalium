# Quick Task 260707-tt8 Summary — Gate observability (F15) + calibration (F22)

**Completed:** 2026-07-08
**Commits:** 13d188a (gate + F15 + Ollama fixes), 0a8c89f (evals + docs), 86eb9d8 (plan)

## Outcome

- **F15 FIXED**: `sensitivity_gate` AuditEvent per job (category/confidence/
  blocked/method); audit API exposes `raw_archive_id`. The privacy promise is
  now externally verifiable.
- **F22 FIXED**: NLI classifier proven unusable empirically (tech → personal
  @0.93 even with softmax + better hypotheses); replaced with embedding-
  prototype classification (MiniLM cosine vs prototypes, unit-tested pure
  decision rule, privacy-first asymmetric thresholds). PRIV-05 default-block
  preserved. Tech convs now allowed (0.71–0.80), personal/health blocked.
- **Bonus fixes**: Ollama thinking models returned empty content via
  OpenAI-compat (budget eaten by reasoning) → native /api/chat with
  think:false + format:json; robust first-JSON-object parsing; eval matcher
  recalibrated (content-word overlap); golden labels made exhaustive.

## Final eval (run 3, all 5 checks live, zero skips)

- ingest ✓, retrieval ✓ (semantic/hybrid R@10 100%), MCP ✓
- **sensitivity ✓ — audit-verified**: sensitive blocked, controls allowed,
  zero leaked facts
- extraction ✗ (measured, honest): recall 57.7% (need 60%), precision 65.6%
  (need 70%), span fidelity 100%, provenance 100% — qwen3.5:4b extracts
  accurately but mainly from the FIRST turn of multi-turn conversations.
  Remedies: chunked/per-turn extraction (F3) or a larger local model.

## Notes

- Pre-existing test flakiness (not mine): `tests/api/test_facts_api.py::
  test_list_facts_returns_active_facts` asserts absolute count and fails when
  combined with tests/domain (facts leak across suites via committed fixtures).
