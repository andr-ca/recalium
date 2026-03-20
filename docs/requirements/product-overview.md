# Product Overview

## Product name
Recalium

## Classification
New product

## Purpose
Recalium is a local-first, MCP-enabled personal memory platform that captures user interactions across LLMs, agents, and tools, then transforms them into durable, searchable, retrievable context for future interactions.

Its purpose is to provide a portable memory layer that persists across models, sessions, and applications while remaining inspectable, user-controlled, and source-backed.

## Problem statement
User context is fragmented across chats with different LLMs, local notes and documents, code repositories, agent interactions, and tool-specific memory systems. This fragmentation causes repeated re-explanation, context loss, inconsistent outputs, and weak continuity across AI systems.

Recalium addresses this by ingesting conversations and artifacts, preserving the raw archive, extracting structured and unstructured memory, organizing memory into useful layers, and enabling governed retrieval for future conversations.

## Intended outcome
A future agent or LLM can retrieve relevant, source-backed user, project, preference, and decision context even when that context was originally captured in a different tool or session. The user can inspect, correct, suppress, promote, or delete memory at any time.

## Target users
### Primary users
- AI power users
- Developers using multiple LLMs and agents
- Technically sophisticated users with ongoing projects and recurring context

## Primary goals
1. Capture conversations and related artifacts from multiple AI systems and tools.
2. Store both raw and processed memory durably.
3. Categorize, summarize, vectorize, and index captured information.
4. Support retrieval of relevant context for future interactions.
5. Expose this capability through MCP so compatible agents and tools can use it.
6. Allow user review, correction, and deletion of stored memory.
7. Preserve user trust through source attribution, conservative extraction, and explicit user control.

## Secondary goals
1. Preserve source attribution for all stored memory.
2. Track timestamps and memory status.
3. Distinguish durable memory from temporary or low-value information.
4. Support layered retrieval rather than a single undifferentiated dump.
5. Ensure exported memory can be re-imported without bespoke conversion.
6. Provide a strong local review experience through a web UI.

## Core principles
1. Model-agnostic — the system must not depend on a single LLM vendor.
2. Local-first and user-controlled — storage defaults to user-controlled local storage.
3. Layered memory — raw, extracted, embedded, and curated memory remain distinct.
4. Explainable retrieval — returned memory must remain source-backed and explainable.
5. User override — the user can inspect, correct, delete, suppress, and promote memory.
6. Conservative by default — the system should under-extract rather than over-assert.
7. Future-commercializable — v1 implementation choices should preserve a credible path to a future sellable service without forcing a full conceptual rewrite.
8. Intelligence-assisted — use decay, conflict detection, and confidence scoring to maintain relevance and trust.

## Future-service compatibility baseline
v1 should preserve service-ready boundaries in the design, including tenant-aware concepts, policy hooks, and deployment-profile separation, without requiring v1 to ship multi-user or hosted-service capabilities.

## Deployment baseline
v1 should be delivered as a local Docker-based service. The default operator experience is a user running Recalium locally as containers, with a localhost web UI and local backend services under user control.

## Processing provider baseline
v1 may use external providers for summarization, extraction, and embeddings from day one. Local-first storage remains the default, but processing is not required to be fully local in the first release. Support for local-only processing (e.g., via Ollama or Sentence Transformers) should be provided for high-privacy scenarios.

If external providers are unavailable or unconfigured, the system should still support keyword search and some basic local processing. Advanced provider-dependent processing may remain pending until a provider becomes available.

First-run setup should offer provider configuration, but the system must remain usable even if the user skips provider setup.

## In scope for v1
- Manual import via text paste and file upload
- JSON and Markdown file upload
- Direct text submission into Recalium
- MCP-accessible ingestion for agents and tools
- "Recalium Capture" browser extension for low-friction chat ingestion
- A watched import folder as the first low-friction local ingestion workflow
- Immutable raw archive with deletion and redaction workflows
- Summarization, chunking, classification, extraction, embeddings, and indexing
- Duplicate and overlap detection for extracted facts
- Conflict detection for contradictory facts
- Temporal decay and relevance weighting for stored memory
- Auto-curation of high-confidence facts
- Search by keyword, semantic, and hybrid modes
- Retrieval with context budgeting and source attribution
- Curated canonical memory
- Local web-based review, correction, deletion, and promotion workflows
- Machine-consumable APIs and MCP-compatible capabilities
- Audit visibility for provenance and machine-client access events

## Ingestion and processing baseline
During ingestion, the system should synchronously persist the raw archive entry and extract lightweight metadata needed for attribution, visibility, and pipeline tracking. Heavier steps such as summaries, fact extraction, embeddings, and search indexing should run asynchronously.

## Storage and search baseline
v1 should standardize on PostgreSQL as the primary local database, using PostgreSQL full-text search for keyword search and `pgvector` for semantic search. Hybrid retrieval should be assembled in the application layer.

## UI information architecture baseline
The first localhost web UI should use a left-navigation application layout with top-level sections for Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, and Settings.

## Out of scope for v1
- Automated native integration with every LLM platform
- Screen scraping as a core ingestion assumption
- Enterprise-grade multi-tenant SaaS
- Advanced permissions and per-agent scoping
- Knowledge graph visualization
- Advanced automatic conflict resolution
- Automated decay or confidence-driven freshness logic
- Multi-user support
- Complex cloud sync features

## Success criteria baseline
Recalium v1 is useful when a user can import prior AI conversations, archive and process them, search them, retrieve concise relevant context within a bounded context budget, inspect provenance, correct or remove incorrect memory, promote selected memory into canonical memory, and expose retrieved memory to an MCP-compatible tool or agent.

## Open areas still needing clarification
- None currently tracked at the product-scope level.
