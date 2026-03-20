# Recalium Plans

## Status
- Phase: Implementation planning baseline expanded for execution use
- Based on: approved requirements and approved architecture baseline
- Scope: Recalium v1
- Planning posture: dependency-driven, risk-first, locally deployable, single-user-first

## Document map
- [plan-manager-handoff.md](plan-manager-handoff.md) — explicit handoff into planning work
- [implementation-plan.md](implementation-plan.md) — planning principles, workstreams, sequencing model, and first implementation batch
- [work-breakdown.md](work-breakdown.md) — execution control document for workstreams, epics, prerequisites, and completion evidence
- [milestones.md](milestones.md) — milestone governance, scope boundaries, evidence requirements, and exit criteria
- [release-slices.md](release-slices.md) — demoable delivery increments with included/excluded scope and acceptance evidence
- [risks-and-dependencies.md](risks-and-dependencies.md) — dependency register and risk register for delivery control
- [../operational/plan-reviews/recalium-v1-plan-handoff.md](../operational/plan-reviews/recalium-v1-plan-handoff.md) — explicit planning handoff package
- [../operational/plan-reviews/recalium-v1-plan-review.md](../operational/plan-reviews/recalium-v1-plan-review.md) — initial plan review identifying sequencing and dependency issues
- [../operational/plan-reviews/recalium-v1-plan-review-final.md](../operational/plan-reviews/recalium-v1-plan-review-final.md) — final plan review with readiness approval

## Purpose of this package
This planning package translates approved requirements and architecture into implementation-ready delivery structure. It is intended to let engineering start execution without rediscovering sequencing, dependency rules, trust constraints, or milestone evidence.

## Planning principles
1. Retire durability and recovery risk before feature breadth.
2. Treat audit, provenance, and policy as foundation work, not late hardening.
3. Deliver coherent, testable slices instead of disconnected technical tasks.
4. Keep synchronous ingest minimal and move heavy work to durable async jobs.
5. Validate measurable non-functional commitments incrementally, not only at release end.

## Primary plan artifacts by role
- Engineering leads should start with [implementation-plan.md](implementation-plan.md).
- Delivery managers should control execution from [work-breakdown.md](work-breakdown.md) and [milestones.md](milestones.md).
- Reviewers should evaluate release readiness from [release-slices.md](release-slices.md) and [risks-and-dependencies.md](risks-and-dependencies.md).

## Current planning baseline
The first execution target is a durable ingest spine that proves the architectural contract: accepted ingest is persisted synchronously to the raw archive, acknowledged only after durable commit, and followed by asynchronous job processing.
