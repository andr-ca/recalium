# Assumptions, Dependencies, Risks, and Open Questions

## Assumptions
- v1 is a single-user local-first product.
- v1 must avoid design choices that block a future sellable service, but must not build multi-tenant complexity before it is needed. No tenant-aware columns, policy engines, or multi-user auth in v1.
- v1 is deployed primarily as a local Docker-based service with two containers: `recalium-app` and `recalium-postgres`.
- Tech stack is committed: Python/FastAPI, React/TypeScript, PostgreSQL/pgvector. See docs/architecture/tech-stack.md.
- Cold-start is a first-class requirement. Users must be able to import ChatGPT and Claude exports at launch. An empty memory system has no value.
- v1 should preserve service-ready boundaries without introducing full tenant-aware runtime complexity into the first release.
- v1 may use external providers for parts of the processing pipeline.
- v1 should remain partially useful without external providers through keyword search and basic local processing.
- v1 portability should use a JSON bundle as the first structured re-importable export format.
- v1 should also provide a human-browsable zip archive containing Markdown plus assets.
- Personal profile and relationship data are treated as sensitive by default in v1.
- Sensitive categories are blocked from external processing by default unless the user explicitly overrides the protection.
- Sensitive content identification should combine user declaration with local rule-based pre-classification before any external processing.
- Unknown or low-confidence content classification should default to blocking external processing.
- Heavy processing steps should run asynchronously after raw archive persistence and lightweight metadata extraction.
- v1 should standardize on PostgreSQL, PostgreSQL full-text search, and `pgvector`.
- v1 should provide a watched import folder as the first low-friction local ingestion workflow.
- v1 duplicate and overlap cleanup should use a dedicated review queue.
- v1 should use a left-nav web UI with top-level sections for Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, and Settings.
- v1 audit visibility should be driven by configuration, with a standard default matching a basic list plus per-event detail drawer and optional expansion to fuller audit detail.
- v1 ingestion acknowledgement target is $P95 \le 1\text{ s}$ for paste import and file upload up to 5 MB under normal local conditions.
- v1 search and retrieval target is $P95 \le 2\text{ s}$ on datasets up to 100k stored items.
- v1 raw archive durability target is zero loss for acknowledged items across container restart or host reboot when persisted Docker volumes are intact.
- v1 processing failures should use bounded automatic retries before manual retry is required.
- v1 should provide built-in scheduled local backups and a restore UI.
- v1 backup baseline is daily backups, 30-day retention, and restore within 15 minutes.
- v1 browser support target is the latest Chrome/Chromium only.
- v1 requires keyboard-only operation for core UI workflows.
- v1 accessibility target is no critical accessibility failures (missing labels, keyboard traps, unannounced state changes) plus keyboard operability for core workflows. Full WCAG 2.1 AA compliance is a v2 target.
- v1 first-run setup should offer provider configuration without making providers mandatory for initial usability.
- v1 should retain access-event history for at least 90 days.
- v1 human-readable export zip should use a hybrid structure with a top-level index, type-based folders, and manifest metadata linking items back to source and session context.
- Manual ingestion flows are the primary import path for v1.
- A localhost web UI is the primary review and curation surface.
- MCP-compatible clients and agents are important first-class consumers.
- Canonical memory requires explicit user action.
- Fully automated vendor-specific connectors are deferred beyond v1.

## Dependencies
- PostgreSQL with support for full-text search and `pgvector`
- At least one summarization and extraction pipeline implementation
- At least one embedding and search implementation suitable for personal-scale use
- A local web application stack for review and curation
- An MCP-compatible interface for agent and tool access

## Key risks
### False memories or wrong summaries
Implication: all derived memory must link back to source span, remain editable, and stay distinct from canonical memory. Extraction quality must be measurable against a labeled test corpus.

### Platform resistance
Implication: AI vendors have incentive to block external MCP memory retrieval. Recalium must deliver value even if no vendor actively supports outbound MCP calls. The local-first posture and manual/system-prompt retrieval paths are the fallback. Do not build on the assumption of vendor cooperation.

### Cold-start abandonment
Implication: users who set up Recalium but have no prior memory to import will not experience value. Bulk import from major vendor exports must be available at launch and must be the primary onboarding flow.

### Extraction quality drift
Implication: if extraction quality is not measured against a labeled corpus, degraded extraction will go undetected. The 200-item hand-labeled test corpus and precision target must be maintained as a required artifact, not optional.

### Sensitive data over-capture
Implication: conservative defaults, redaction, deletion, exclusion from indexing or embedding, and explicit provider visibility are required.

### Context overload
Implication: retrieval must enforce context budgets and default to compact, high-signal output.

### Staleness and contradiction
Implication: lifecycle statuses, timestamps, provenance, and user-editable canonical memory are required.

### User trust erosion
Implication: provenance, portability, local-first behavior, and reviewability are essential.

### Tool overload or agent spam
Implication: access must be auditable and retrieval behavior should favor relevance and restraint.

### Redundant memory pollution
Implication: duplicate and overlap detection plus cleanup workflows are required.

### Provider key abuse or leakage
Implication: if Recalium stores user API keys insecurely (even locally), or if a future managed tier leaks keys, user trust collapses. Keys must be stored in local-only config, never in database, never in backups, never in exports. A future managed tier must use Recalium's own keys, never store user keys.

## Competitive response scenarios

### Scenario A — OpenAI ships memory export and import
- Impact: reduces Recalium's cold-start advantage and portability narrative.
- Response: emphasize structured extraction, source-backed provenance, and MCP retrieval — features OpenAI is unlikely to offer for competitor tools.
- Required preparation: none. Recalium's value is in the processing and cross-tool retrieval, not just the storage.

### Scenario B — MCP adoption stalls or a competing protocol wins
- Impact: core retrieval story weakens significantly.
- Response: ensure REST API is a first-class retrieval path, not just MCP. Add a system-prompt injector that works with any API-based AI tool regardless of protocol support.
- Required preparation: v1 must not couple retrieval exclusively to MCP transport. The REST API must provide equivalent retrieval capabilities.

### Scenario C — mem0 or Letta ships a local-first mode
- Impact: direct competitive overlap with funded competitors.
- Response: differentiate on provenance, user control, and open format. Accelerate the protocol and format play.
- Required preparation: publish memory bundle format spec before competitors can define the interchange format.

### Scenario D — Apple or Google ships OS-level AI memory
- Impact: mainstream users have no reason to use Recalium.
- Response: target developer and power-user niche explicitly. OS-level memory will be general-purpose; Recalium can be the precision tool for structured, source-backed, cross-tool context.
- Required preparation: none. Different market segments.

## Open questions
- None currently tracked at the product-scope level.
