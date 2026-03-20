# Recalium v1 Plan Review

## Review status
- Verdict: Not ready
- Review date: 2026-03-14
- Review scope: implementation planning package

## Blocking issues
1. Dependency cycles existed in the work breakdown:
   - `WS4-E6` depended on `WS6-E3` while `WS6-E3` depended on `WS4-E6`.
   - `WS5-E5` depended on `WS6-E5` while `WS6-E5` depended on `WS5-E5`.
2. Milestones and slices violated prerequisites:
   - early UI delivery depended on later operations work,
   - canonical workflows depended on later deletion behaviors,
   - deleted-data warnings were placed before export capabilities existed.
3. Early non-functional control points were not explicit enough for ingest, queue recovery, retrieval latency, and restore timing.

## Minor issues
- Batch 1 user-facing and operator-facing surfaces were not named precisely enough for implementation assignment.
- API and MCP contract hardening was only partially reflected in the plan.
- Early UI shell expectations from architecture were only loosely mapped.

## Required changes
- remove dependency cycles
- rebuild milestone and slice composition to respect prerequisites
- split early UI from later operations and recovery UI
- move or split deleted-data warning work so it follows backup/export capability delivery
- add explicit early NFR control points
- tighten Batch 1 to exact surfaces and evidence

## Outcome
The plan package required revision before implementation could start safely.
