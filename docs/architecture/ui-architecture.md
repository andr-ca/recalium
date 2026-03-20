# UI Architecture

## Purpose
Define the architectural expectations for the localhost web UI as the primary review and curation surface.

## Core workflow coverage
The UI architecture must explicitly support keyboard-only operation and accessible interaction patterns for:
- ingest
- search
- fact review
- canonical memory edit
- duplicate/overlap review queue
- backup inventory review
- restore initiation and cutover confirmation

## Accessibility posture
For core workflows, the UI architecture should preserve:
- predictable focus order
- visible focus state
- keyboard-operable primary actions
- clear navigation between left-nav sections
- readable provenance and audit detail presentation
- low-friction movement from derived memory to source context

## Architecture implications
- route structure and screen composition should align with the left-nav information architecture
- restore and review flows should not assume mouse-only interactions
- evidence, provenance, and audit surfaces should be accessible through structured detail views rather than hover-only affordances
- the UI layer should keep accessibility-critical interaction logic centralized and testable

## Operations-oriented surfaces
The UI architecture should include explicit operational surfaces for:
- processing backlog and failed items
- backup inventory
- deleted-data warnings on prior backups/exports
- restore validation status and cutover confirmation

## QA references
- Architecture QA index: [../operational/architecture-reviews/README.md](../operational/architecture-reviews/README.md)
- Architecture QA tech stack: [../operational/architecture-reviews/tech-stack-qa.md](../operational/architecture-reviews/tech-stack-qa.md)
- Final architecture QA result: [../operational/architecture-reviews/recalium-v1-architecture-review-final.md](../operational/architecture-reviews/recalium-v1-architecture-review-final.md)
