# Quick Task 260708-0kx Summary — Chunked extraction (F3): first fully green eval

**Completed:** 2026-07-08 · **Commit:** 35f5b89

Implemented turn-boundary chunked fact extraction (verbatim-slice chunks,
greedy packing, oversized-turn hard split, fact dedupe; 4 unit tests, TDD).
Applied to all providers in `_run_extract_job`.

**Eval: 5/5 PASSED, zero skips — the first fully green run.**
Extraction: recall 62.5% (≥60), precision 76.7% (≥70), span fidelity 100%,
provenance 100%. Retrieval semantic/hybrid R@10 100%; sensitivity
audit-verified; ingest + MCP green.
Evidence: docs/operational/tests/artifacts/eval-green-2026-07-08/
