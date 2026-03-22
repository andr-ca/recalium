# Agent Handoff Templates

This is the canonical shared handoff template for the global custom agents.

Use these templates when a package moves between agents so the next agent does not have to reconstruct missing context.

## 1. Requirements Manager → Requirements Reviewer

```md
# Requirements Reviewer Handoff

## Handoff status
- Ready for review: Yes / No
- Open questions remaining: Yes / No

## Request classification
- <new product | feature add | refinement | other>

## Problem statement
<concise statement>

## Intended outcome
<desired business or user outcome>

## Scope summary
### In scope
- ...

### Out of scope
- ...

## Actors and roles
- ...

## Functional requirements summary
- ...

## Non-functional requirements summary
- ...

## Edge cases and exception handling
- ...

## Dependencies, assumptions, and risks
- Dependencies: ...
- Assumptions: ...
- Risks: ...

## Open questions
- None

or

- ...

## Acceptance criteria
- ...

## Files created or updated
- path/to/file.md — purpose

## Validation result
- 15-point checklist passed: Yes / No
- Notes: ...

## Reviewer ask
Please review these requirements for completeness, consistency, ambiguity, missing edge cases, traceability, and implementation readiness.
```

## 2. Requirements Reviewer → Architect

Use only when the requirements outcome is fully approved.

```md
# Architect Handoff

## Approval status
- Fully approved: Yes

## Source requirements summary
- ...

## Key business goals
- ...

## Key functional requirements
- ...

## Key non-functional requirements
- ...

## Constraints and dependencies
- ...

## Known assumptions
- ...

## Remaining open questions
- None

or

- ...

## Files to use as source of truth
- path/to/file.md

## Architect ask
Convert these approved requirements into practical, implementation-oriented solution architecture with explicit assumptions, options where needed, and a preferred recommendation.
```

## 3. Architect → Architecture Reviewer

```md
# Architecture Reviewer Handoff

## Review readiness
- Ready for architecture review: Yes / No

## Source input summary
- ...

## Interpreted requirements summary
- ...

## Assumptions and open questions
- ...

## Architecture drivers
- ...

## Options considered
- ...

## Recommended architecture and rationale
- ...

## Component and integration summary
- ...

## Data, security, and NFR considerations
- ...

## Operations, support, capacity, and deployment summary
- ...

## Risks and tradeoffs
- ...

## Files created or updated
- path/to/file.md — purpose

## Checklist status
- Architecture readiness checklist passed: Yes / No
- Notes: ...

## Reviewer ask
Review this architecture for correctness, completeness, realism, tradeoffs, risk handling, requirement traceability, and implementation readiness.
```

## 4. Architecture Reviewer → Planner

Use only when the architecture outcome is fully approved.

```md
# Planner Handoff

## Approval status
- Architecture fully approved: Yes

## Source requirements
- path/to/requirements-file.md

## Source architecture
- path/to/architecture-file.md

## Scope and architecture summary
- ...

## Important constraints
- ...

## Important assumptions
- ...

## Quality gates already established
- ...

## Open items that are non-blocking
- None

or

- ...

## Planner ask
Create a super-detailed execution plan with role-based tasks, dependency mapping, parallelization guidance, TDD work, QA automation, QA execution, validation tasks, and explicit coverage/standards gates.
```

## 5. Planner → Plan Reviewer

```md
# Plan Reviewer Handoff

## Review readiness
- Ready for plan review: Yes / No

## Source requirements
- path/to/requirements-file.md

## Source architecture
- path/to/architecture-file.md

## Plan summary
- ...

## Assumptions
- ...

## Scope coverage summary
- ...

## Workstreams
- ...

## Role assignments
- ...

## Dependency and sequencing summary
- ...

## Parallelization summary
- ...

## TDD and test strategy summary
- ...

## QA automation summary
- ...

## QA execution summary
- ...

## Validator and signoff summary
- ...

## Quality gates and coverage targets
- ...

## Files created or updated
- path/to/plan.md — purpose

## Reviewer ask
Review this plan for requirements coverage, architecture coverage, task specificity, role ownership, sequencing realism, TDD/test completeness, QA coverage, validation coverage, and execution readiness.
```

## 6. Plan Reviewer → Dev Manager

Use only when the plan outcome is fully approved.

```md
# Dev Manager Handoff

## Approval status
- Plan fully approved: Yes

## Source requirements
- path/to/requirements-file.md

## Source architecture
- path/to/architecture-file.md

## Source plan
- path/to/plan-file.md

## Execution summary
- ...

## Key workstreams
- ...

## Role expectations
- ...

## Dependency and sequencing constraints
- ...

## Parallel work opportunities
- ...

## Quality gates and coverage targets
- ...

## Non-blocking notes
- None

or

- ...

## Dev manager ask
Execute the approved plan fully by orchestrating the allowed role agents, preserving sequencing, quality gates, validation tasks, QA tasks, and coverage expectations.
```

## 7. Reviewer return package

When a reviewer sends work back for rework, use this minimal structure:

```md
# Review Rework Request

## Outcome
- Approved with minor issues | Changes required

## Summary
- ...

## Blocking findings
- ...

## Major findings
- ...

## Minor findings
- ...

## Required next step
- Return to <requirements-manager | architect>

## Files that need updates
- path/to/file.md
```
