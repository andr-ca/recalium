# Return to Architect

## Status
- Returned to architect: Yes
- Trigger: architecture review found blocking issues
- Review source: [recalium-v1-architecture-review.md](recalium-v1-architecture-review.md)
- Return loop completed: Yes

## Return reason
The current architecture package is not yet ready. The architecture reviewer identified blocking issues that must be addressed before the architecture package can be approved.

## Blocking issues to resolve
1. Component and runtime boundaries are too abstract.
2. Security architecture for non-`localhost` exposure and MCP identity is missing.
3. Portability/export architecture is not covered.
4. Performance architecture does not yet trace to the stated $P95$ targets.

## Required architect actions
1. Add concrete component boundaries, module ownership, and internal interface expectations.
2. Add a security appendix for localhost-only and exposed modes, including authentication, session handling, transport protection, and MCP/client identity propagation.
3. Add a portability appendix covering export/import architecture, format versioning, and ownership boundaries.
4. Add a performance/operability appendix covering queue durability, indexing/query strategy, benchmark approach, and capacity assumptions.

## Review references
- [../../architecture/README.md](../../architecture/README.md)
- [../../architecture/architect-handoff.md](../../architecture/architect-handoff.md)
- [recalium-v1-architecture-review.md](recalium-v1-architecture-review.md)

## Handoff note
This document is the explicit return path from architecture review back to architecture authoring. The next architecture revision should address the blocking issues above and then be resubmitted for review.

Architect response: [recalium-v1-architect-response.md](recalium-v1-architect-response.md)

Final re-review result: [recalium-v1-architecture-review-final.md](recalium-v1-architecture-review-final.md)
