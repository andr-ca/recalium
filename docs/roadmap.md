# Recalium Product Roadmap

**Status:** Living document — reviewed at each milestone close, changed via PR
**Last updated:** 2026-08-26 (M1 closed)
**Audience:** Contributors and users deciding what Recalium is, what works today, and what comes next

This is the forward-looking product view. It does not replace the sources of truth it is built from:

| Document | Role |
| --- | --- |
| [.planning/ROADMAP.md](../.planning/ROADMAP.md) | Execution history of the v1 build-out (phases 1–5, all complete) and the 999.x backlog definitions |
| [operational/validations/recalium-v1-release-readiness-gap-register.md](operational/validations/recalium-v1-release-readiness-gap-register.md) | Release control surface — a milestone here is done only when its register rows are closed with cited evidence |
| [recommendations.md](recommendations.md) / [recommendations-update.md](recommendations-update.md) | v1.1 strategic recommendations and their implementation status |
| [architecture/decisions/0001-mcp-transport.md](architecture/decisions/0001-mcp-transport.md) | ADR governing the MCP transport timeline referenced by M3/M4 |
| [evals/thresholds.json](../evals/thresholds.json) | Frozen quality gates — release criteria, not aspirations |

---

## Vision

**A user's future AI session — on any tool, with any model — can retrieve relevant, source-backed context from prior conversations that happened anywhere, without re-explaining anything.**

Recalium is infrastructure, not a feature. The app is the reference implementation of an open memory portability format (memory-bundle, currently v2 with canonical memory and a tombstone deletion ledger). Local-first, MCP-native, bring-your-own-keys.

## Standing constraints (v1 era)

These are commitments, not preferences. Changing any of them requires explicit approval plus a doc update (see `CLAUDE.md` Constraints):

- **Stack:** Python/FastAPI + React/TypeScript + PostgreSQL/pgvector
- **Topology:** exactly two containers (`recalium-app`, `recalium-postgres`)
- **Single-user, local-first** — no multi-tenant columns, auth systems, or policy engines in v1
- **BYOK by default** — no Recalium-operated processing services; user's own provider keys; fully usable with no keys at all (degraded mode)
- **Service-ready boundaries** — module seams (domain logic / deployment profile / policy hooks) kept clean so a future hosted option needs no rewrite
- **Secrets** only in `.env`; sanitized `.env.sample` always maintained

---

## Where we are (2026-08-26)

**M1 — v1.0 GA is complete.** All three exit criteria are met:

- Gap register: all 14 rows closed (RR-001–RR-014) with cited evidence.
- Strict eval: `evals/runner.py --strict` **5/5 passed** on 2026-08-26 — see [2026-08-26-m1-strict-eval-evidence.md](operational/validations/2026-08-26-m1-strict-eval-evidence.md).
- Evidence matrix: published (RR-014, 2026-07-24).

The v1 feature build-out (planning phases 1–5) remains complete: ingest, async pipeline, hybrid retrieval, canonical memory, review queue, deletion cascade, backup/restore, wizard, audit, bundle v2, MCP tools.

Current quality snapshot (2026-08-27 M2 cold-start baseline, Ollama `qwen3.8:27b`):

- **Eval suite:** `--strict --n-runs 3` — extraction recall ~0.70 / precision **0.6417** (stdev 0.0); **3/3** conversation coverage on all runs; retrieval/MCP/sensitivity pass. Evidence: [2026-08-27-m2-cold-start-baseline-evidence.md](operational/validations/2026-08-27-m2-cold-start-baseline-evidence.md).
- **M1 GA snapshot (historical):** 2026-08-26 single-run strict 5/5 at recall 0.69 / precision 0.71 — measured before harness hardening; superseded for M2 quality claims.
- **Accessibility:** 9 routes axe-clean after destructive-token fix (PR #48).

**Next milestone:** M2 — extraction quality & eval trustworthiness (999.x unlock bar: recall ≥0.75, precision ≥0.80). Harness trustworthiness closed 2026-08-27 (PRs #50–57); **sole remaining M2 step:** closed-model control experiment (blocked: `OPENAI_API_KEY` in repo root `.env`).

---

## Milestones

### M1 — v1.0 GA: close the release register *(Complete — 2026-08-26)*

**Goal:** every gap-register row closed with cited evidence; a strict eval run green; a release evidence matrix published. No new features.

**Status:** ✅ All exit criteria met. Tagged `v1.0.0`.

| Item | What "done" means |
| --- | --- |
| RR-001 startup docs | ✅ Closed 2026-08-26 — verified in `docs/operational/validations/2026-08-26-rr001-startup-docs-verification.md` |
| RR-002 / RR-005 UI evidence | ✅ Closed 2026-08-26 — audit mapped nav + review-queue coverage to RR-011 suite; evidence in `docs/operational/validations/2026-08-26-rr002-rr005-ui-evidence-audit.md` |
| RR-003 / RR-004 facts lifecycle | ✅ Closed 2026-08-26 — audit confirmed API, UI, audit events, and retrieval filtering; evidence in `docs/operational/validations/2026-08-26-rr003-rr004-facts-lifecycle-audit.md` |
| RR-010 MCP resources & live coverage | ✅ M1 live-client evidence closed 2026-08-26 (`test_mcp_live_client.py`, 7 tests). MCP *resources* remain M3. |
| RR-014 evidence matrix | ✅ Published 2026-07-24: all 47 acceptance criteria mapped to verified test/code evidence (40 evidenced, 4 partial, 3 gaps, none release-blocking) — see `docs/operational/validations/recalium-v1-acceptance-criteria-evidence-matrix.md` |
| Extraction gate (#13) | ✅ Root cause found and fixed 2026-07-21: the commit that claimed "77.38% recall achieved" (785d40d) never actually shipped that prompt — it shipped a stricter-scope variant the same analysis had already measured as a regression. Restoring the minimal, scan-all-text prompt (dropping the `SCOPE:`/`STRATEGY:` guardrail block) re-measured at recall 0.6706 (gate ≥0.60, **passing**), precision 0.75 (gate ≥0.70, **passing**), no cross-conversation contamination observed. Gate is green |
| Strict eval gate | ✅ Closed 2026-08-26 — `evals/runner.py --strict` 5/5; evidence in `docs/operational/validations/2026-08-26-m1-strict-eval-evidence.md` |

### M2 — v1.1: extraction quality & eval trustworthiness *(In progress)*

**Goal:** make the extraction number one we believe, then reach the **backlog-unlock bar: recall ≥0.75 and precision ≥0.80** (a deliberately higher bar than the ≥0.60/≥0.70 release gates — it gates the 999.x synthesis features, which compound extraction errors if built on a weak base).

**Current quality snapshot (honest measurement, 2026-08-27):** local Ollama `qwen3.8:27b`, 3/3 control-conversation coverage on runs 2–3 of `--strict --n-runs 3` — extraction precision **~64%** (fails 70% release gate); recall ~70%; retrieval/MCP/sensitivity pass. Evidence: `docs/operational/validations/2026-08-27-m2-archive-fix-baseline-evidence.md`. M1 strict snapshot (0.71 precision) was measured before harness hardening exposed subset-scoring bias.

- **Eval-trustworthiness (from M1 strict run):** ✅ Closed 2026-08-27 — skip-reason classification, sensitivity vacuous-pass guard, Ollama preflight, incomplete-coverage failure, pipeline drain, scoped archive fetch (PRs #50–54). Baselines recorded as measured; no reruns to chase green.
- **Golden-set completeness:** ✅ Resolved 2026-07-23: re-enumerated all 4 conversations against their raw text — conv-001 ~100%, conv-002 ~92–100%, conv-004 ~100%, all comfortably above the ≥85% target. conv-003 sits at ~80%; **policy decision:** don't pad it further, since it carries personal/relationship-tagged facts and is entirely excluded from extraction scoring (`evals/checks/eval_extraction.py` skips any conversation with a personal/relationship golden fact) — its coverage percentage has zero effect on gate reliability, so chasing 85% there would just mean cataloging more synthetic personal-health detail for no measurable benefit. Golden facts are authored by exhaustive manual enumeration of the source, never from model output.
- **Eval methodology hardening:** ✅ N-run averaged mode with variance reporting landed 2026-07-23 (`evals/runner.py --n-runs N`, mean + stdev per metric, "passed" requires every run to sustain the gate). Smoke-tested with `--n-runs 2` against the post-fix extraction prompt: stdev 0.0 across every metric, reconfirming Ollama determinism through the tool itself. Determinism is confirmed for the OpenAI/Ollama paths (bit-for-bit identical A/B runs, 2026-07-17); Anthropic's `temperature=0` pin landed 2026-07-20 (all 3 call sites) — still needs its own A/B determinism confirmation run (blocked: no `ANTHROPIC_API_KEY` configured locally).
- **Closed-model control experiment:** **Next, blocked on key** — one measured run with a GPT-4-class `EXTRACT_PROVIDER` to locate the quality ceiling (model vs method). Runbook: `docs/operational/validations/2026-08-27-m2-closed-model-control-runbook.md`. Requires `OPENAI_API_KEY` in **repo root** `.env` + compose restart.
- **Chunk-metadata spike** (conversation title/sequence/speaker headers on chunks): design-first, and only if the gates are still unmet after the above — measurement before architecture.
- **Deduplication stays exact-match** unless a change is proven on the eval. (A fuzzy-paraphrase dedup was tried and rejected 2026-07-17: zero measured improvement, and ≥60% content-word overlap falsely merged genuinely distinct facts.)

**Exit criteria:** documented, reproducible eval methodology · a data-backed go/no-go decision on the 999.x unlock.

### M3 — v1.2: MCP evolution & interop proof *(Later)*

Per ADR 0001 (SSE through v1.1; spike in v1.2; migrate v1.3+):

- **Streamable-HTTP transport spike** — prototype behind the existing 127.0.0.1-only bind; SSE remains the default; record the outcome as an ADR update.
- **MCP Python SDK v2 assessment** — upstream v2 carries breaking transport changes; the `mcp>=1.26,<2` pin holds until the spike concludes.
- **Cross-client interop matrix** — the repo ships client configs for Claude Code, Cursor, GitHub Copilot, and opencode (`integrations/recalium/`); prove each against a live checklist (connect, ingest, retrieve, error envelope) and publish the evidence. Carries forward any RR-010 scope M1 deferred.
- **Tool-surface candidates** (each must respect audit events and the crypto-erase delete path): fact correction/feedback via MCP, delete/tombstone via MCP.

**Exit criteria:** transport decision recorded · interop matrix published with evidence per client.

### M4 — v1.3: scale & retrieval depth *(Later)*

- **Transport migration** to Streamable-HTTP if the M3 spike confirms it (ADR 0001 timeline), preserving the localhost bind and stable tool contract.
- **pgvector HNSW option** for large libraries — in-place IVFFlat→HNSW upgrade path (pgvector 0.8.2 already required); publish tuning guidance. Still no third container.
- **Scale evidence at 100k items** — the harness's `--scale` check exists (default 150 synthetic conversations); extend it to validate the 2 s search SLA at the 100k design point.
- **Retrieval-quality deepening:** larger golden query set, sensitivity-aware ranking checks, re-validated latency budgets.
- **Bundle v2.x:** incremental/delta export and a size/perf profile for large archives.

**Exit criteria:** SLAs re-proven at 100k items · HNSW guidance published.

### M5 — 999.x: the synthesis layer *(Gated — enters planning only when M2's unlock bar is met)*

From the `.planning/ROADMAP.md` backlog, in likely order:

1. **999.1 Wiki synthesis pages** — LLM-generated entity/concept pages as a derived type alongside facts and summaries.
2. **999.2 Knowledge lint** — periodic job surfacing superseded/contradicted facts, orphaned derived items, and knowledge gaps.
3. **999.3 Query-to-knowledge** — file MCP query answers back into canonical memory so exploratory analysis compounds.
4. **999.4 llmwiki bridge** — import/export between Recalium and LLM-maintained markdown wiki directories (Obsidian-style workflows).

**Why gated:** synthesis built on unvalidated extraction compounds errors. The gate is the point.

### Horizon — v2 *(Directional, not committed)*

Each of these requires changing a standing constraint, so each enters planning only through an ADR plus a constraints-doc update:

- **Hosted/multi-device option** built on the service-ready seams — local-first stays the default; BYOK is preserved.
- **Encrypted bundle sync** between a user's own devices via user-owned storage.
- **Multi-user** — explicitly out of v1 schema; a v2-scale decision.
- **Memory-bundle v3 & format governance** — broader cross-tool importers (ChatGPT/Claude/generic JSON exports already parse at ingest; v3 targets more sources and round-trip fidelity), a versioned public spec, and adoption beyond the reference implementation.

---

## Cross-cutting tracks (apply to every milestone)

- **Quality gates as merge criteria.** `evals/thresholds.json` is frozen; a threshold change is a reviewed contract change, never a convenience edit.
- **Privacy invariants.** Sensitivity labels honored end to end; every delete path goes through suppression + crypto-erase (`_suppress_derived`/`_erase_plaintext`), including bundle tombstone import; keys never leave `.env`.
- **Evidence discipline.** Register rows close only with cited evidence; architecture shifts get ADRs; harness friction gets dual-logged (local `docs/operational/harness-feedback.md` entry + upstream `agentharness` issue).
- **Agent DX.** Platform skills (Copilot/Claude/Codex) and `docs/guides/local-use-and-test.md` stay current as features land.

## Risks & dependencies

| Risk | Impact | Mitigation |
| --- | --- | --- |
| MCP SDK v2 breaking transport changes (upstream) | Forced rework of the MCP layer | Pin `<2`; phased spike→migrate plan in ADR 0001 (M3/M4) |
| Local-model extraction ceiling (qwen-class) | 999.x stays blocked | M2 sequence: fix measurement first, closed-model control second, architecture change last |
| Eval trust erosion (non-determinism, golden gaps) | Gates stop meaning anything | Anthropic temperature pin landed (M1); N-run averaging + ≥85% golden coverage (M2) |
| Frontend major-version churn (React 19 / Vite 8 / Tailwind 4) | Upgrade breakage | Versions pinned; upgrades only on green E2E + axe suites |
| pnpm v11 (beta, breaking) | CI/dev breakage | Stay on 10.x until stable (see tech-stack doc) |
| Single-user assumptions leaking into schema | Costly v2 rework | Service-ready boundary review in PRs touching domain seams |

## Operating cadence

- The roadmap is reviewed and updated at each milestone close (or when a gate decision lands), via PR like any other doc.
- "Is it done?" is always answered by the gap register and evidence docs — never by this file.
- Direction lives here; decisions live in ADRs; execution detail lives in `.planning/`.
