# Product Overview

## Product name
Recalium

## Classification
New product

## The core insight
Every major AI vendor offers memory. None of them solve the actual problem.

Memory stored in ChatGPT keeps you on ChatGPT. Memory stored in Claude Projects keeps you on Anthropic. Memory stored in Gemini keeps you on Google. Vendor memory is a retention mechanism dressed as a user feature. When you switch tools — or use more than one simultaneously — your context stays behind.

Recalium's position: **your memory should not belong to any AI vendor.** It should live somewhere you control, be portable across any tool, and be retrievable by any client that speaks MCP.

## Purpose
Recalium is a local-first, MCP-native personal memory platform that captures user interactions across LLMs, agents, and tools, then transforms them into durable, searchable, portable context that works with any AI system.

It is designed as infrastructure, not a feature. The app is the reference implementation of an open memory portability format.

## Problem statement
Users do not use one AI tool. They use several — for different tasks, different modalities, different strengths. Their context is fragmented not because they want it to be, but because no neutral memory layer exists. This causes repeated re-explanation, context loss, and degraded continuity every time a user switches tools or starts a new session.

Vendor memory makes this worse, not better: each vendor's memory silo deepens lock-in rather than solving portability.

Recalium addresses this by ingesting conversations and artifacts, preserving the raw archive, extracting structured and unstructured memory, organizing memory into useful layers, and enabling governed retrieval for any MCP-compatible client or agent — regardless of vendor.

## Intended outcome
A user's future AI session — on any tool, with any model — can retrieve relevant, source-backed context from prior conversations that happened anywhere. The user inspects, corrects, suppresses, promotes, or deletes memory at any time, with full provenance visibility.

The "aha" moment: a user tells a new Claude session something it retrieves from a ChatGPT conversation they had six months ago, without re-explaining anything. This moment should be achievable within 30 minutes of setup.

## Target users
### Primary users
- AI power users who use more than one AI tool
- Developers building with multiple LLMs and agents
- Technically sophisticated users with ongoing projects and recurring context needs

## Primary goals
1. Capture conversations and related artifacts from multiple AI systems and tools.
2. Store both raw and processed memory durably under user control.
3. Categorize, summarize, vectorize, and index captured information.
4. Support retrieval of relevant context for future interactions via MCP and direct API.
5. Expose retrieval through MCP so any compatible agent or tool can use it.
6. Allow user review, correction, and deletion of stored memory.
7. Preserve user trust through source attribution, conservative extraction, and explicit user control.
8. Be the first and best implementation of an open memory portability format.

## Secondary goals
1. Preserve source attribution for all stored memory.
2. Track timestamps and memory status.
3. Distinguish durable memory from temporary or low-value information.
4. Support layered retrieval rather than a single undifferentiated dump.
5. Ensure exported memory can be re-imported without bespoke conversion — and imported into other tools that adopt the format.
6. Provide a strong local review experience through a web UI.

## Core principles
1. Model-agnostic — the system must not depend on a single LLM vendor.
2. Local-first and user-controlled — storage defaults to user-controlled local storage.
3. Layered memory — raw, extracted, embedded, and curated memory remain distinct.
4. Explainable retrieval — returned memory must remain source-backed and explainable.
5. User override — the user can inspect, correct, delete, suppress, and promote memory.
6. Conservative by default — the system should under-extract rather than over-assert.
7. Protocol-first — the memory bundle format is an open spec; Recalium is its reference implementation.

## Business model
- **Free tier (BYOK):** full functionality, self-hosted Docker deployment. User provides their own provider API keys (OpenAI, Anthropic, Ollama). Processing costs are borne by the user through their own provider accounts. No user data leaves the machine except to the user's own configured providers. Always free and open source.
- **Managed processing tier (paid):** Recalium-provided API access with pre-configured providers, no key management required, usage-based or flat-rate billing. Revenue comes from processing convenience, not from user data. Can ship at or shortly after v1 launch.
- **Hosted sync tier (paid, post-v1):** end-to-end encrypted sync across devices, managed backup, mobile companion.
- **Team tier (future):** shared canonical memory for teams, scoped retrieval, access policy.

The BYOK model is the default. Users who already have provider API keys (the primary target audience) experience full functionality at zero cost. The managed processing tier converts users who prefer convenience over key management.

## Future-service compatibility baseline
v1 must not introduce premature multi-tenant runtime complexity. Do not add tenant-aware data model columns, policy engines, or multi-user auth in v1. The correct time to add these is when a second user or tenant exists. Preserve clean module boundaries that would allow these additions without a full rewrite — but do not build them yet.

## Deployment baseline
v1 is delivered as a local Docker-based service with two containers: `recalium-app` and `recalium-postgres`. The default operator experience is a user running Recalium locally with a localhost web UI. See [../architecture/container-topology.md](../architecture/container-topology.md).

## Tech stack baseline
See [../architecture/tech-stack.md](../architecture/tech-stack.md) for committed stack decisions (Python/FastAPI, React/TypeScript, PostgreSQL/pgvector, MCP Python SDK).

## Processing provider baseline
v1 may use external providers for summarization, extraction, and embeddings from day one. Local-first storage remains the default; processing is not required to be fully local in v1. Local-only processing via Ollama and `sentence-transformers` is supported for high-privacy scenarios.

If external providers are unavailable or unconfigured, the system remains usable for ingestion, local storage, browsing, and keyword search. First-run setup offers provider configuration but does not require it.

## Cold-start strategy
An empty memory system has no value. The first-run experience must address this directly.

v1 must support bulk import from the major AI vendor export formats at launch:
- ChatGPT conversation export (JSON)
- Claude conversation export (JSON)
- Generic conversation JSON (open format)
- Plain text / Markdown paste

The first-run wizard must offer "import your history" as the primary onboarding action. Users who complete an import and run their first search within the same session experience the product's core value before leaving.

## In scope for v1
- Manual import via text paste and file upload
- Bulk import from ChatGPT export and Claude export formats
- JSON file upload
- Direct text submission into Recalium
- MCP-accessible ingestion for agents and tools
- A watched import folder as a low-friction local ingestion workflow
- Immutable raw archive with deletion and redaction workflows
- Summarization, chunking, classification, extraction, embeddings, and indexing
- Source span and confidence tier for every extracted fact
- Duplicate and overlap detection for extracted facts
- Conflict detection for contradictory facts
- Search by keyword, semantic, and hybrid modes (RRF)
- Retrieval with context budgeting and source attribution
- Curated canonical memory
- Local web-based review, correction, deletion, and promotion workflows
- Machine-consumable APIs and MCP-compatible capabilities
- Audit visibility for provenance and machine-client access events
- JSON export/import (open memory bundle format — v1 spec)
- Scheduled local backups and restore UI

## Out of scope for v1
- "Recalium Capture" browser extension (v2 — separate release lifecycle, Chrome CSP complexity)
- Temporal decay and relevance weighting (v2 — requires data to tune; ship after usage data exists)
- Confidence-based auto-curation (v2 — depends on extraction quality data from real use)
- Automated native integration with every LLM platform
- Screen scraping as a core ingestion assumption
- Enterprise-grade multi-tenant SaaS
- Advanced permissions and per-agent scoping
- Knowledge graph visualization
- Advanced automatic conflict resolution
- Multi-user support
- Cloud sync (hosted sync tier is post-v1)
- Tenant-aware data model seams (premature; add when a second tenant exists)

## Ingestion and processing baseline
Synchronous path: persist raw archive entry and extract lightweight metadata only.
Asynchronous path: summarization, fact extraction, embeddings, FTS indexing. See [../architecture/processing-pipeline.md](../architecture/processing-pipeline.md).

## Storage and search baseline
PostgreSQL as the primary local database. PostgreSQL full-text search for keyword search. `pgvector` for semantic search. Hybrid retrieval via Reciprocal Rank Fusion in the application layer. See [../architecture/retrieval-and-ranking.md](../architecture/retrieval-and-ranking.md) for the exact algorithm.

## UI information architecture baseline
Left-navigation application layout: Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, Settings.

## Feature priority (MoSCoW)

### Must have (v1 cannot ship without)
- Manual import via paste and file upload
- Bulk import from ChatGPT and Claude export formats
- Raw archive with source metadata
- Basic extraction (summarization and fact extraction)
- Keyword search
- MCP retrieval with context budgeting
- Web UI: Ingest, Search, Facts views
- Deletion workflow
- BYOK provider configuration

### Should have (expected in v1, deferrable under pressure)
- Semantic and hybrid search
- Canonical memory with promotion
- Duplicate and overlap detection and review queue
- Watched folder import
- Audit visibility
- Provenance on every derived item
- Processing cost estimation and display

### Could have (valuable if time permits)
- Markdown-plus-assets export
- Backup and restore with scheduled retention
- Degraded-mode handling (keyword-only fallback)
- Full operations dashboard
- Keyboard-only accessibility for all core workflows

### Won't have (explicitly v2)
- Browser extension
- Temporal decay
- Auto-curation
- Cloud sync
- Multi-user
- Managed processing tier backend (can be added shortly after v1)

## Success criteria
Recalium v1 is successful when:
1. A user can go from zero to their first retrieved result within 30 minutes using a ChatGPT or Claude conversation export.
2. A user can import prior AI conversations, archive and process them, search them, and retrieve concise relevant context within a bounded context budget.
3. A user can inspect provenance, correct or remove incorrect memory, and promote selected memory into canonical memory.
4. An MCP-compatible agent or tool can retrieve relevant context from Recalium without any user intervention after initial setup.
5. Every retrieved fact links back to its source conversation and the exact text span it was derived from.

## Validation gates
Recalium v1 development should include explicit validation checkpoints that can adjust scope before full delivery.

### Gate 1 — Core value signal (after Slice A plus basic extraction)
- 10 or more external users have installed and imported conversations.
- At least 3 users have performed unprompted retrieval (not prompted by a walkthrough).
- Qualitative feedback collected on: import friction, extraction quality, retrieval relevance.
- Decision: proceed with full plan, adjust scope, or pivot.

### Gate 2 — MCP value signal (after Slice B plus MCP ingest)
- At least 3 users have configured MCP retrieval in an AI client.
- At least 1 user has used MCP retrieval without manual intervention for more than 1 week.
- Decision: MCP-first strategy validated or adjust retrieval distribution.

### Gate 3 — Retention signal (4 weeks after first external users)
- Weekly active users returning to search or review.
- Import volume trending up (users adding more conversations over time).
- Decision: proceed to release hardening or reassess scope.

## Key bets
1. Users who try cross-tool memory retrieval will find it valuable enough to maintain the system. (Validated by: Gate 1)
2. MCP retrieval by agents will be the primary consumption mode, not manual UI search. (Validated by: Gate 2)
3. Source-backed provenance is a meaningful differentiator users notice, not just a technical feature. (Validated by: user feedback)
4. The cold-start import experience is good enough to demonstrate value before the user gives up. (Validated by: completion rate of first-run wizard)
5. BYOK is the natural model for the target audience and does not create meaningful onboarding friction. (Validated by: Gate 1 setup completion rate)

## Competitive differentiation
See [competitive-differentiation.md](competitive-differentiation.md).

## Personas
See [personas.md](personas.md).

## Open areas still needing clarification
- None currently tracked at the product-scope level.
