# Feature Research

**Domain:** Local-first MCP-native personal memory platform / AI conversation archive
**Researched:** 2026-03-22
**Confidence:** HIGH (based on direct competitor analysis, official documentation, and deep project context)

---

## Competitive Landscape Summary

Before categorizing features, here is what the field looks like as of March 2026:

| Tool | Approach | Local-first? | MCP? | Source-attribution? | Multi-vendor import? |
|------|----------|-------------|------|---------------------|----------------------|
| **Mem0 (OpenMemory)** | Agent memory library + hosted MCP service | Partial (OpenMemory OSS) | Yes | No | No |
| **basic-memory** | Markdown file knowledge graph via MCP | Yes | Yes | No (file-level only) | No |
| **MCP Reference Memory** | JSONL knowledge graph (flat), entities+relations | Yes | Yes | No | No |
| **ChatGPT Memory** | Vendor silo, auto-extracted preferences | No | No | No | No |
| **Claude Projects** | Vendor silo, user-uploaded docs | No | No | No | No |
| **Obsidian** | Local Markdown PKM (note-taking) | Yes | Via plugin | No | No |
| **Notion AI** | Cloud, structured notes + AI | No | No | No | No |
| **Rewind.ai** | Local screen/audio recording + search | Yes | No | No | No |

**Critical gap Recalium fills:** No tool in the field combines (a) multi-vendor conversation import, (b) structured extraction with provenance, (c) layered memory (raw → facts → canonical), and (d) native MCP retrieval with context budgeting. This is the unoccupied position.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that must exist or the product feels unfinished. Missing any of these causes users to abandon during onboarding.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Conversation import from major vendors** | The entire value prop starts here — ChatGPT exports, Claude exports are what users have | MEDIUM | ChatGPT and Claude JSON formats are well-documented; generic JSON + plain text also needed |
| **Durable local storage** | "Local-first" is the trust promise; if data is not on disk, the product is just another cloud app | LOW | Docker volumes; PostgreSQL; must survive container restart |
| **Keyword search** | Every search-capable tool has this; users will try it first | LOW | PostgreSQL FTS; immediate expectation |
| **Basic web UI for browsing** | Users need to verify what was imported; without it the system is a black box | MEDIUM | Ingest, Archive, Search views are minimum |
| **Delete / redact with cascade** | Privacy-first users expect to be able to remove data fully; anything less is unacceptable | HIGH | Must cascade to derived summaries, facts, embeddings, FTS entries |
| **BYOK provider configuration** | Target audience already has API keys; no managed tier means BYOK must work on day one | LOW | Settings UI + key validation + error handling |
| **First-run wizard / onboarding** | Empty system → no value; users need to be guided to their first result fast | MEDIUM | Cold-start problem is existential; 30-min-to-value target |
| **Backup and restore** | "Local-first" means users own their data; they expect to be able to back it up | MEDIUM | Scheduled daily backups, 30-day retention, 15-min restore SLA |
| **MCP `retrieve` tool** | This is the primary consumption surface for the target audience (AI power users) | HIGH | Context budgeting, source links, rank scores, conflict labels |
| **Basic fact extraction** | Users expect the system to do something intelligent with their conversations, not just archive them | HIGH | Extraction quality is a key risk area; must be good enough on first use |
| **Processing pipeline status** | Users need to know when processing is done before they can search effectively | LOW | Async with status indicators; job failure surfacing |

### Differentiators (Competitive Advantage)

Features that set Recalium apart. Competitors either don't have these at all or implement them weakly.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Layered memory (raw → facts → canonical)** | No competitor preserves raw archive + extracted structure + curated canonical as distinct, navigable layers; users can always see where a fact came from | HIGH | The whole architecture is organized around this; raw is immutable, facts are extracted, canonical requires explicit user action |
| **Source span provenance on every fact** | Users can verify exactly what text a fact was extracted from; this is the "trust anchor" that makes memory credible | HIGH | Every extracted fact carries source span, confidence tier, derivation method, model version; navigable from any derived item |
| **Multi-vendor import with unified memory** | Memory that spans ChatGPT history + Claude history + other tools; competitors only handle their own vendor's data | MEDIUM | ChatGPT JSON, Claude JSON, generic JSON, plain text/Markdown; watched folder for ongoing ingestion |
| **Hybrid search (RRF)** | Better retrieval than keyword-only (what MCP reference memory does) or semantic-only (what Mem0 does) | HIGH | Reciprocal Rank Fusion merging FTS + pgvector results; k=60, top-50 per mode, top-20 merged |
| **Explicit conflict detection and labeling** | No competitor surfaces contradictory facts to users; Recalium shows them in retrieval results with explicit labels | MEDIUM | Conflict detection at extraction time; conflict labels in MCP responses; lower-ranked in results |
| **Canonical memory with explicit promotion** | User-curated ground truth that overrides extracted memory in retrieval; no auto-promotion without user action | MEDIUM | Source of truth for what the user has validated; prioritized in context budgeting |
| **Context budgeting in retrieval** | MCP clients get a result that fits their context window; no competitor does strict priority trimming (canonical → facts → summaries → raw) | MEDIUM | Essential for real-world agent use; without it, retrieval results are noisy and expensive |
| **Comprehensive audit trail** | Every MCP access event logged with client identity, operation metadata, 90-day retention; no competitor has this for personal use | MEDIUM | Answers "what has my AI agent seen?"; privacy-conscious users care deeply |
| **Sensitivity-aware processing** | Personal profile and relationship content blocked from external processing by default; unknown content blocked until explicitly allowed | MEDIUM | Conservative by default is the differentiator; other tools have no privacy classification |
| **Open memory bundle format (portability)** | JSON export/import re-importable without bespoke conversion; positions Recalium as infrastructure, not a silo | MEDIUM | The format is the protocol play; Recalium is the reference implementation |
| **Degraded-mode operation** | System remains usable for ingestion, local storage, browsing, and keyword search without any API keys or embeddings | LOW | Graceful degradation matters for offline/privacy users; most competitors require internet access |
| **Duplicate / overlap detection + review queue** | Keeps the memory clean over time without user effort; competitors leave deduplication entirely to the user | HIGH | Groups similar facts for manageable cleanup; critical for bulk-imported datasets |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem like good ideas but should not be built in v1. Explicitly out of scope to avoid scope creep and premature complexity.

| Feature | Why Requested | Why Problematic for v1 | Alternative |
|---------|---------------|----------------------|-------------|
| **Browser extension ("Recalium Capture")** | "I want it to capture conversations automatically" | Separate release lifecycle; Chrome CSP complexity; adds a whole new surface area before core pipeline is proven | Manual import + watched folder covers the immediate need; extension is v2 |
| **Automatic cloud sync** | "I want my memory on all my devices" | Requires E2E encryption design, cloud backend, auth, and billing before core value is validated | Hosted sync tier is a post-v1 paid feature; local backup/restore is the v1 answer |
| **Auto-promotion to canonical memory** | "Just learn what I care about automatically" | Cannot be tuned without real usage data; false positives erode trust faster than any other failure | Explicit user-promoted canonical is safer; confidence-based auto-curation is v2 after extraction quality data exists |
| **Temporal decay / relevance weighting** | "Old memories should matter less" | Decay tuning requires real usage data; wrong decay silently degrades retrieval quality | Manual stale/disputed marking is the v1 mechanism; decay is v2 |
| **Knowledge graph visualization** | "I want to see how my memories connect" | Looks impressive in demos, adds significant front-end complexity, and is not on the user's critical path to value | Graph can be added post-validation; provenance navigation in the UI is the v1 equivalent |
| **Multi-user / team support** | "Share my memory with my team" | Premature multi-tenant architecture creates massive complexity before a second user exists | Clean module boundaries are preserved for future; add when a second tenant exists |
| **Advanced per-agent permissions** | "I want agent X to see only topic Y" | Policy engine complexity; not needed until multiple agents are in active use | Simple client-identity audit logging covers v1; scoping is a v2 enterprise feature |
| **Automated vendor-specific connectors** | "Connect directly to my ChatGPT account" | Requires OAuth and vendor cooperation; brittle against API changes | Manual export-and-import is more reliable; capture flow is validated before building live connectors |
| **Auto-conflict resolution** | "Just pick the most recent / most confident fact" | Wrong resolutions are worse than surfaced conflicts; users must be in the loop | Surface conflicts explicitly with labels; let the user decide |
| **Real-time conversation capture from running AI sessions** | "Capture everything as I type" | Screen scraping / hooking into running apps is brittle; privacy surface area explodes | Watched folder + manual import covers the immediate need well |

---

## Feature Dependencies

```
[Multi-vendor import]
    └──requires──> [Raw archive storage]
                       └──requires──> [PostgreSQL persistence]
                       └──enables──> [Processing pipeline]
                                        └──produces──> [Summaries]
                                        └──produces──> [Extracted facts]
                                                           └──requires──> [Source span extraction]
                                                           └──enables──> [Canonical memory promotion]
                                                           └──enables──> [Duplicate detection]
                                                           └──enables──> [Conflict detection]
                                        └──produces──> [Embeddings]
                                                           └──enables──> [Semantic search]

[Keyword search]
    └──requires──> [PostgreSQL FTS index]
    └──requires──> [Raw archive storage]

[Semantic search]
    └──requires──> [Embeddings]
    └──requires──> [pgvector]

[Hybrid search (RRF)]
    └──requires──> [Keyword search]
    └──requires──> [Semantic search]

[MCP retrieve]
    └──requires──> [Hybrid search (RRF)]
    └──requires──> [Context budgeting]
    └──requires──> [Canonical memory]
    └──requires──> [Conflict detection labels]

[Context budgeting]
    └──requires──> [Canonical memory]
    └──requires──> [Extracted facts]
    └──requires──> [Summaries]
    └──requires──> [Raw archive]

[Canonical memory]
    └──requires──> [Extracted facts]
    └──requires──> [Provenance navigation]

[Delete/redact with cascade]
    └──requires──> [Raw archive storage]
    └──cascades──> [Summaries]
    └──cascades──> [Extracted facts]
    └──cascades──> [Embeddings]
    └──cascades──> [FTS entries]
    └──marks──> [Canonical memory with source-removed state]

[Audit trail]
    └──requires──> [MCP retrieve]
    └──requires──> [MCP ingest]

[Open memory bundle export]
    └──requires──> [Raw archive]
    └──requires──> [Extracted facts]
    └──requires──> [Canonical memory]
    └──requires──> [Provenance metadata]

[First-run wizard]
    └──requires──> [Multi-vendor import]
    └──requires──> [BYOK configuration]
    └──leads-to──> [First search result within 30 min]

[Backup/restore]
    └──requires──> [Raw archive]
    └──requires──> [PostgreSQL]
    └──restores──> [Summaries, facts, canonical, provenance, audit events]

[Sensitivity-aware processing]
    └──requires──> [Processing pipeline]
    └──blocks──> [External LLM calls for classified content]

[Degraded-mode operation]
    └──requires──> [Keyword search] (always available)
    └──requires──> [Raw archive storage]
    └──gracefully-degrades-from──> [Semantic search]
```

### Dependency Notes

- **Semantic search requires embeddings:** Embeddings require either a local model (sentence-transformers, no API key) or an external provider (OpenAI, Anthropic). The system must degrade gracefully when neither is available — keyword search always works.
- **MCP retrieve requires almost everything:** It sits at the top of the dependency tree and requires hybrid search, canonical memory, conflict detection, and context budgeting all to be in place. This is why MCP retrieve should be in a later phase than basic ingestion and search.
- **Canonical memory requires extracted facts:** Users cannot promote to canonical if no facts have been extracted. The extraction pipeline is a gate for the canonical memory feature.
- **Duplicate detection enhances but does not block retrieval:** Deduplication improves memory quality but is not required for search or retrieval to function. It can ship after the core pipeline.
- **Sensitivity classification can be additive:** Basic privacy protection (blocking personal profile content from external processing) is a safety gate in the pipeline, not a retrieval feature. It should be in the processing pipeline phase, not retrieval.
- **Audit trail is a monitoring layer:** Access events are recorded by MCP tooling; the UI to view them can follow after MCP is working.

---

## MVP Definition

### Launch With (v1)

The minimum viable product — what must exist to validate the core bet: "a user can retrieve relevant context from prior AI conversations across vendors."

- [x] **Multi-vendor import (paste + file upload)** — Without this, users cannot populate the system; the value prop cannot be demonstrated
- [x] **Bulk import from ChatGPT and Claude JSON exports** — These are the two largest AI tool user bases; these formats must work on day one
- [x] **Raw archive with source metadata** — Foundation for everything; without durable raw storage, nothing else works
- [x] **Async processing pipeline** (summarization, fact extraction, embeddings, FTS indexing) — Without extraction, the system is just a document store with no intelligence
- [x] **Source span and confidence tier on every extracted fact** — The provenance feature is the trust differentiator; it should be in place from the first extraction
- [x] **Keyword search** — Table stakes; needed before semantic search is available
- [x] **Semantic + hybrid search (RRF)** — Core retrieval quality; differentiates from plain keyword tools
- [x] **MCP `retrieve` tool with context budgeting** — The primary consumption surface; the "aha moment" requires this to be working
- [x] **Web UI: Ingest, Archive, Facts, Search, Settings** — Minimum navigation to let users see and verify what was imported and processed
- [x] **Delete/redact with cascade** — Privacy is non-negotiable; users must be able to remove data completely
- [x] **BYOK configuration (OpenAI, Anthropic, Ollama)** — Target audience has API keys; BYOK is the launch model
- [x] **Degraded-mode operation** — System must work without any API keys (keyword search + local storage always available)
- [x] **Scheduled local backups + restore UI** — "Local-first" requires users to be able to recover their data
- [x] **First-run wizard with cold-start import** — Empty system = zero value; 30-minutes-to-first-result target drives retention
- [x] **Keyboard-only operability for core workflows** — Accessibility baseline; power users live on keyboards

### Add After Validation (v1.x)

Features expected in v1 but deferrable under delivery pressure. Add once core is working and gate 1 is passed.

- [ ] **Canonical memory with explicit promotion** — High value but not required for first search; add after users have experienced extraction quality
- [ ] **Duplicate/overlap detection + review queue** — Important for data quality at scale; not needed until users have imported thousands of items
- [ ] **Conflict detection and labeling** — Adds significant complexity to extraction; add after basic extraction quality is validated
- [ ] **MCP `ingest` tool** (agent-driven ingestion) — Useful for power users but not required to validate core retrieval value
- [ ] **Watched folder import** — Low-friction ingestion; add after manual import is validated
- [ ] **Audit view** (access event list + detail drawer) — Important for trust; add once MCP retrieval is working and logged
- [ ] **Sensitivity-aware processing** (block personal/relationship/unknown content from external processing) — Privacy feature; add before production release, after core pipeline is stable
- [ ] **Processing cost estimation** — Important for transparency; add before bulk import is heavily used
- [ ] **Provenance full navigation UI** — Navigating from canonical → facts → raw is the trust feature; add with or after canonical memory

### Future Consideration (v2+)

Features to defer until product-market fit is established and usage data exists.

- [ ] **Browser extension ("Recalium Capture")** — Separate release lifecycle; build after core platform is validated and stable
- [ ] **Temporal decay / relevance weighting** — Needs real usage data to tune; wrong decay erodes trust silently
- [ ] **Confidence-based auto-curation** — Needs extraction quality data from real use; premature auto-promotion breaks trust
- [ ] **Cloud sync / hosted sync tier** — Post-v1 paid feature; add when multi-device users are a validated segment
- [ ] **Multi-user / team memory** — Add when a second tenant actually exists
- [ ] **Knowledge graph visualization** — Nice-to-have; add after core retrieval value is validated and users ask for it
- [ ] **Advanced per-agent permissions** — Enterprise feature; add when scoped retrieval is a real use case
- [ ] **Advanced automatic conflict resolution** — Needs conflict detection data from real use; manual resolution is safer first
- [ ] **Managed processing tier** (Recalium-operated API keys) — Can ship shortly after v1; revenue comes from convenience, not data
- [ ] **Markdown-plus-assets export** — Lower priority than JSON bundle; add when users request rich export

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Multi-vendor import (paste + file) | HIGH | MEDIUM | P1 |
| ChatGPT / Claude JSON bulk import | HIGH | MEDIUM | P1 |
| Raw archive with metadata | HIGH | LOW | P1 |
| Async processing pipeline | HIGH | HIGH | P1 |
| Source span provenance on facts | HIGH | HIGH | P1 |
| Keyword search | HIGH | LOW | P1 |
| Hybrid search (RRF) | HIGH | HIGH | P1 |
| MCP retrieve with context budgeting | HIGH | HIGH | P1 |
| Web UI (Ingest, Archive, Facts, Search) | HIGH | MEDIUM | P1 |
| Delete/redact with cascade | HIGH | HIGH | P1 |
| BYOK configuration | HIGH | LOW | P1 |
| Degraded-mode operation | MEDIUM | LOW | P1 |
| Local backup + restore UI | HIGH | MEDIUM | P1 |
| First-run wizard | HIGH | MEDIUM | P1 |
| Keyboard accessibility | MEDIUM | LOW | P1 |
| Canonical memory + promotion | HIGH | MEDIUM | P2 |
| Duplicate/overlap detection | MEDIUM | HIGH | P2 |
| Conflict detection + labeling | MEDIUM | HIGH | P2 |
| MCP ingest tool | MEDIUM | MEDIUM | P2 |
| Watched folder import | MEDIUM | LOW | P2 |
| Audit view | MEDIUM | MEDIUM | P2 |
| Sensitivity-aware processing | HIGH | MEDIUM | P2 |
| Processing cost estimation | MEDIUM | LOW | P2 |
| Full provenance navigation UI | HIGH | MEDIUM | P2 |
| Browser extension | HIGH | HIGH | P3 |
| Cloud sync | MEDIUM | HIGH | P3 |
| Temporal decay | MEDIUM | HIGH | P3 |
| Knowledge graph visualization | LOW | HIGH | P3 |
| Multi-user support | LOW | HIGH | P3 |
| Advanced per-agent permissions | LOW | HIGH | P3 |
| Auto-curation | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for v1 launch — core value proposition gates on these
- P2: Should have in v1 — expected, deferrable only under serious delivery pressure
- P3: Future consideration — do not build in v1

---

## Competitor Feature Analysis

| Feature | Mem0 (OpenMemory) | basic-memory | MCP Reference Memory | Recalium Approach |
|---------|-------------------|--------------|----------------------|-------------------|
| **Multi-vendor import** | No (API only) | No (manual note creation) | No | ChatGPT + Claude JSON + generic + paste |
| **Local-first storage** | Partial (OSS Docker) | Yes (files) | Yes (JSONL) | Yes (Docker + PostgreSQL) |
| **Raw archive** | No | Markdown files | No | Yes (immutable raw archive) |
| **Source span provenance** | No | File-level only | No | Yes (span, confidence tier, derivation method, model version) |
| **Layered memory** | No (flat memories) | No (flat notes) | No (entities + observations) | Yes (raw → summaries → facts → canonical) |
| **Hybrid search** | No (vector only) | Yes (FTS + vector via FastEmbed) | No (text search) | Yes (RRF: FTS + pgvector) |
| **MCP retrieval** | Yes (hosted) | Yes (local) | Yes (local, JSONL) | Yes (local, with context budgeting) |
| **Context budgeting** | No | No | No | Yes (strict priority trimming: canonical → facts → summaries → raw) |
| **Canonical memory** | No | No | No | Yes (user-curated, requires explicit promotion) |
| **Conflict detection** | No | No | No | Yes (with explicit labels in retrieval) |
| **Duplicate detection** | No | No | No | Yes (review queue grouping) |
| **Audit trail** | No | No | No | Yes (90-day access log, client identity) |
| **Sensitivity-aware processing** | No | No | No | Yes (personal profile / relationships blocked by default) |
| **Delete with full cascade** | Yes (basic) | Yes (file delete) | No | Yes (cascade to all derived artifacts) |
| **BYOK + Ollama local processing** | Yes | Yes (Ollama) | No | Yes (OpenAI, Anthropic, Ollama; sentence-transformers default) |
| **Backup/restore** | No | No | No | Yes (daily, 30-day retention, 15-min restore) |
| **Open export format** | No | Markdown (Obsidian-compatible) | JSONL | Yes (open memory bundle JSON spec) |
| **Cost estimation before bulk processing** | No | N/A | N/A | Yes (token heuristics, order-of-magnitude) |

**Recalium's unique position:** It is the only tool that combines multi-vendor history import, layered memory with source-span provenance, hybrid retrieval with context budgeting, canonical curation, conflict detection, and a comprehensive audit trail — while being local-first and BYOK.

---

## Critical Observations from Research

### What the ecosystem actually uses as "memory"
- Mem0 (50k GitHub stars, $24M funded): flat extracted preferences, no raw archive, no provenance, cloud-first
- basic-memory (2.7k stars): Markdown files, knowledge graph via wiki-links, no extraction quality signal
- MCP reference memory: JSONL knowledge graph, entities + observations, no semantic search
- None preserve the original conversation text in a queryable archive with source links on every derived fact

### User needs vs. what sounds cool
**Actually needed (validated by competitor traction):**
1. Quick path from import to first useful retrieval (cold-start is the biggest failure mode)
2. Trustworthy extraction (bad facts are worse than no facts; provenance is the trust mechanism)
3. Deletion that actually works (privacy is a first-class concern for the target audience)
4. Works without internet / full offline capability (Ollama + sentence-transformers path)
5. Doesn't require re-configuration every time a new AI tool is used (MCP makes this automatic once configured)

**Sounds cool but isn't critical yet:**
1. Real-time conversation capture (manual import is more reliable until capture is validated)
2. Graph visualization (pretty but not on the critical path to value)
3. Temporal decay (can't be tuned without data; wrong decay silently breaks things)
4. Auto-curation (same as decay — requires data that doesn't exist yet)

### The cold-start problem is the #1 product risk
Every memory tool that fails does so because the system is empty and provides no value until populated. Recalium's answer — bulk ChatGPT/Claude export import as the primary first-run action — is the right approach. The first-run wizard must be the first thing a new user sees, and it must get them to a successful search result within 30 minutes.

### Extraction quality is the #2 product risk
If more than 50% of extracted facts are trivial or wrong, users will stop trusting the system and abandon it. The conservative extraction principle (under-extract rather than over-assert) plus source span provenance (users can verify any fact) are the risk mitigations. Confidence tiers (high/medium/low) allow the UI to surface low-confidence facts prominently for user review.

---

## Sources

- Mem0 (mem0ai/mem0): https://github.com/mem0ai/mem0 — 50.7k stars, production-scale AI memory library
- OpenMemory (mem0ai/mem0/openmemory): https://github.com/mem0ai/mem0/tree/main/openmemory — local Docker MCP server
- basic-memory: https://github.com/basicmachines-co/basic-memory — 2.7k stars, Markdown knowledge graph via MCP
- MCP Reference Memory Server: https://github.com/modelcontextprotocol/servers/tree/main/src/memory — official MCP knowledge graph
- Mem0 Platform Docs: https://docs.mem0.ai/overview — managed memory layer feature list
- OpenMemory Product: https://mem0.ai/openmemory — MCP memory for coding agents
- Obsidian: https://obsidian.md — local-first PKM, established UX patterns for knowledge management
- Recalium PROJECT.md, product-overview.md, acceptance-criteria.md — deep project context informing all categorizations

---
*Feature research for: local-first MCP-native personal memory platform (Recalium)*
*Researched: 2026-03-22*
