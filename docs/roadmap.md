# Recalium Product Roadmap

**Status:** Living document — reviewed at each milestone close, changed via PR
**Last updated:** 2026-07-17
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

## Where we are (2026-07-17)

The v1 feature build-out (planning phases 1–5) is complete: ingest (paste, file upload, watched folder, MCP), async pipeline (summaries, span-validated facts, embeddings, sensitivity gate), hybrid retrieval (FTS + pgvector + RRF), canonical memory and review queue, deletion cascade with crypto-erase, backup/restore, first-run wizard, audit trail, and bundle v2 export/import with UI.

Quality and evidence state:

- **Eval suite** (`evals/`): 5 checks (ingest, extraction, retrieval, sensitivity, mcp) against frozen thresholds. Ingest/retrieval/sensitivity/mcp pass; **extraction is borderline** — the latest fresh measurements (2026-07-17, two identical back-to-back runs) show recall 0.583 (gate ≥0.60, failing) / precision 0.717 (gate ≥0.70, passing), while the best historical run (prompt-iteration 7 in the [extraction failure analysis](operational/tests/2026-07-17-extraction-failure-analysis.md)) measured recall 0.774 / precision 0.617. The [determinism audit](operational/tests/2026-07-17-determinism-and-golden-coverage-audit.md) attributes that gap to prompt/model-state drift between measurement dates, not eval noise — which is itself part of why M2 exists. Tracked in issue #13.
- **Performance:** ingest P95 ~18 ms (SLA ≤1 s), hybrid search P95 ~175 ms (SLA ≤2 s), restore worst case 3.11 s (SLA ≤15 min).
- **Accessibility:** all 9 routes WCAG 2.2 AA, core workflows keyboard-operable (RR-011 evidence doc).
- **Release readiness:** 7 of 14 gap-register rows closed with cited evidence (RR-006, 007, 008, 009, 011, 012, 013); 7 remain open (RR-001, 002, 003, 004, 005, 010, 014).

Note on `recommendations.md` §3: its "v1.2 Quality Improvements" list (F1, F2, F4, F7, F8) was pulled forward and already shipped — see `recommendations-update.md`. The v1.2 milestone below is therefore *not* that list; it is the MCP-evolution work from ADR 0001.

---

## Milestones

### M1 — v1.0 GA: close the release register *(Now)*

**Goal:** every gap-register row closed with cited evidence; a strict eval run green; a release evidence matrix published. No new features.

| Item | What "done" means |
| --- | --- |
| RR-001 startup docs | Verify `docs/guides/local-use-and-test.md` + README cover clean-checkout start/use/test/troubleshoot end to end, then close the row with evidence (the guide exists; the row predates it) |
| RR-002 / RR-005 UI evidence | Expand keyboard/E2E evidence for nav and review-queue workflows to the same standard RR-011 set for the rest of the UI |
| RR-003 / RR-004 facts lifecycle | Audit rows against current code — substantial functionality landed after the rows were written (editing, statuses, archive/delete, promotion). Close what's evidenced; finish and test any genuine remainder |
| RR-010 MCP resources & live coverage | Decide whether MCP resources ship in v1 or move to M3 (record the decision); add live-client tests for schemas, invalid inputs, audit metadata, concurrent SSE clients |
| RR-014 evidence matrix | Publish the acceptance-criteria → evidence mapping so release readiness is auditable in one place |
| Extraction gate (#13) | ✅ Root cause found and fixed 2026-07-21: the commit that claimed "77.38% recall achieved" (785d40d) never actually shipped that prompt — it shipped a stricter-scope variant the same analysis had already measured as a regression. Restoring the minimal, scan-all-text prompt (dropping the `SCOPE:`/`STRATEGY:` guardrail block) re-measured at recall 0.6706 (gate ≥0.60, **passing**), precision 0.75 (gate ≥0.70, **passing**), no cross-conversation contamination observed. Gate is green |
| Known code-health items | ✅ Anthropic `temperature=0` pin landed 2026-07-20 (all 3 call sites: summarize/extract/link-classify). Still open: wrap unexpected exceptions in the MCP error envelope for `retrieve_memory`/`get_fact_links`/`list_tags`; fix the 3 stale phase-5 MCP tests (pre-envelope assertions + test isolation) |

**Exit criteria:** gap register all-closed · `evals/runner.py --strict` 5/5 · evidence matrix published.

### M2 — v1.1: extraction quality & eval trustworthiness *(Next)*

**Goal:** make the extraction number one we believe, then reach the **backlog-unlock bar: recall ≥0.75 and precision ≥0.80** (a deliberately higher bar than the ≥0.60/≥0.70 release gates — it gates the 999.x synthesis features, which compound extraction errors if built on a weak base).

- **Golden-set completeness:** ✅ Resolved 2026-07-23: re-enumerated all 4 conversations against their raw text — conv-001 ~100%, conv-002 ~92–100%, conv-004 ~100%, all comfortably above the ≥85% target. conv-003 sits at ~80%; **policy decision:** don't pad it further, since it carries personal/relationship-tagged facts and is entirely excluded from extraction scoring (`evals/checks/eval_extraction.py` skips any conversation with a personal/relationship golden fact) — its coverage percentage has zero effect on gate reliability, so chasing 85% there would just mean cataloging more synthetic personal-health detail for no measurable benefit. Golden facts are authored by exhaustive manual enumeration of the source, never from model output.
- **Eval methodology hardening:** ✅ N-run averaged mode with variance reporting landed 2026-07-23 (`evals/runner.py --n-runs N`, mean + stdev per metric, "passed" requires every run to sustain the gate). Smoke-tested with `--n-runs 2` against the post-fix extraction prompt: stdev 0.0 across every metric, reconfirming Ollama determinism through the tool itself. Determinism is confirmed for the OpenAI/Ollama paths (bit-for-bit identical A/B runs, 2026-07-17); Anthropic's `temperature=0` pin landed 2026-07-20 (all 3 call sites) — still needs its own A/B determinism confirmation run (blocked: no `ANTHROPIC_API_KEY` configured locally).
- **Closed-model control experiment:** one measured run with a GPT-4-class `EXTRACT_PROVIDER` to locate the quality ceiling — answers whether the gap is the local model or the method.
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
