# Competitive Differentiation

## The core problem with vendor memory

Every major AI vendor — OpenAI, Anthropic, Google — offers some form of memory. None of them solve the real problem: **vendor memory is a retention mechanism, not a user feature.** Memory stored in ChatGPT keeps you on ChatGPT. Memory stored in Claude Projects keeps you on Anthropic. Switching vendors means starting over.

Users do not have one AI tool. They use several, for different tasks, with different strengths. Their context is fragmented not because they want it to be, but because no neutral layer exists.

## Why Recalium wins even if vendors resist

Vendors have incentive not to implement MCP memory retrieval from external sources. Recalium's answer: local-first means value exists regardless of vendor cooperation.

Even without active MCP integration in the AI client:
- Users can retrieve context manually and paste it into any session
- A system prompt injector can prepend retrieved memory to any API call
- Any AI tool that supports MCP tools gains full retrieval automatically

The value exists in all three scenarios. Vendor resistance slows adoption; it does not eliminate the value.

## Competitor comparison

### OpenAI memory (ChatGPT)
- Siloed: only available inside ChatGPT
- User cannot inspect what was remembered or why
- No portability: memory cannot be exported or used elsewhere
- No source attribution: remembered facts have no provenance
- **Recalium differentiator:** portable, inspectable, source-backed, works with any tool

### Claude Projects (Anthropic)
- Siloed: only available inside Claude.ai
- User uploads context manually but it is not structured or searchable
- No cross-session memory extraction
- No MCP retrieval interface
- **Recalium differentiator:** extracted, searchable, vendor-neutral, MCP-first

### mem0.ai
- API-only, cloud-hosted, no local-first option
- No user-visible storage; opaque extraction
- No audit or provenance trail
- Requires trusting a third party with all AI context
- **Recalium differentiator:** local-first, user-controlled, source-backed, fully auditable

### MemGPT / Letta
- Designed around a single managed-context LLM architecture
- Not portable across AI systems
- High operational complexity
- **Recalium differentiator:** model-agnostic, simple Docker deployment, no managed-LLM dependency

### Rewind.ai
- Screen recording based; captures everything indiscriminately
- Not structured memory; not suitable for AI context injection
- Privacy concerns from always-on recording
- **Recalium differentiator:** explicit ingestion, structured extraction, conservative defaults

### Obsidian + plugins
- General note-taking; not designed for AI context retrieval
- No MCP interface
- No structured fact extraction
- **Recalium differentiator:** purpose-built for AI context, MCP-native retrieval, automatic extraction

## The protocol play

Recalium's strongest long-term differentiator is owning the format, not just the app.

The Recalium Memory Bundle (JSON export/import format) should be published as an open specification. If Recalium defines what a portable memory bundle looks like, any AI tool that wants to import user memory has to speak the format. This is the same dynamic that made RSS a standard rather than a single vendor's feature.

This means:
1. Publish the memory bundle schema as a versioned open spec
2. Make the import/export format the canonical interchange format for AI memory portability
3. Position Recalium as the reference implementation of the open spec

## Business model

Open source core with BYOK default and tiered convenience upsells.

- **Free tier (BYOK):** full functionality, self-hosted, Docker-based. User provides their own provider API keys. No data leaves the user's machine except to the user's own configured providers. Always free.
- **Managed processing tier (paid):** Recalium-provided API access, no key management, usage-based or flat-rate billing. Revenue comes from processing convenience. Can ship at or shortly after v1.
- **Hosted sync tier (paid, post-v1):** end-to-end encrypted sync across devices, mobile companion, managed backup. No plaintext user data on servers.
- **Team/org tier (future):** shared canonical memory for teams, scoped retrieval, access policy.

This is the Obsidian/Standard Notes model adapted for AI tooling. BYOK is the default because the target audience already has provider API keys. The managed processing tier converts users who prefer convenience over key management, providing an earlier revenue path than cloud sync alone.
