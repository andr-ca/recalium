# Architecture Review Report

## Overall verdict
Not ready

## Blocking issues
1. Component and runtime boundaries are still too abstract.
   - The package does not yet define implementable module ownership, internal contracts, durable job orchestration, or dependency rules across ingest, policy, retrieval, audit, and reprocessing.
   - Relevant docs: [../../architecture/README.md](../../architecture/README.md), [../../architecture/system-context.md](../../architecture/system-context.md), [../../architecture/processing-pipeline.md](../../architecture/processing-pipeline.md), [../../architecture/architect-handoff.md](../../architecture/architect-handoff.md)

2. Security architecture for non-`localhost` exposure and MCP identity is missing.
   - The docs require authentication, session handling, and transport protection for broader exposure, but do not define how UI/API/MCP authentication works or how client identity propagates into audit.
   - Relevant docs: [../../architecture/container-topology.md](../../architecture/container-topology.md), [../../architecture/api-and-mcp.md](../../architecture/api-and-mcp.md), [../../requirements/nfr.md](../../requirements/nfr.md)

3. Portability/export architecture is not covered.
   - Export/import flow, format versioning, and ownership boundaries are not architected despite explicit requirements.
   - Relevant docs: [../../architecture/container-topology.md](../../architecture/container-topology.md), [../../architecture/privacy-and-policy.md](../../architecture/privacy-and-policy.md), [../../requirements/nfr.md](../../requirements/nfr.md)

4. Performance architecture does not yet trace to the stated targets.
   - There is no benchmark strategy, indexing/query tactic detail, backpressure model, or capacity assumption package tied to the published $P95$ requirements.
   - Relevant docs: [../../architecture/storage-and-indexing.md](../../architecture/storage-and-indexing.md), [../../architecture/processing-pipeline.md](../../architecture/processing-pipeline.md), [../../architecture/retrieval-and-ranking.md](../../architecture/retrieval-and-ranking.md), [../../requirements/nfr.md](../../requirements/nfr.md)

## Minor issues
- `import-watcher` appears in [../../architecture/system-context.md](../../architecture/system-context.md) but is not represented in [../../architecture/container-topology.md](../../architecture/container-topology.md).
- Backup/restore architecture remains high-level and does not define consistency method or restore cutover behavior.
- UI architecture is still thin for keyboard-critical and restore workflows.

## Recommended next actions
1. Add concrete component boundaries, module ownership, and sequence flows.
2. Add a security appendix covering localhost-only and exposed modes, authentication, session handling, transport protection, and MCP identity propagation.
3. Add a portability appendix covering export/import architecture and format versioning.
4. Add a performance appendix covering queue durability, indexing strategy, benchmark approach, and capacity assumptions.
