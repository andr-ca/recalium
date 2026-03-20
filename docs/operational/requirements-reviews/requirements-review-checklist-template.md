# Requirements Review Checklist Template

Use this template for completed requirements reviews.

## Naming
- Save completed reviews as `docs/operational/requirements-reviews/<task-name>-requirements-review-checklist.<YYYYMMDD>T<HHMMSS>Z.md`.

## Usage rules
- Mark each checklist item as `PASS`, `FAIL`, or `N/A`.
- Add direct evidence for each item, including file links where possible.
- For every `FAIL`, add a concrete follow-up action.
- Keep the checklist focused on requirement quality, traceability, and implementation readiness.

---

# Requirements Review Checklist: <task-name>

## Metadata
- Timestamp: <YYYY-MM-DDTHH:MM:SSZ>
- Reviewer: <name>
- Scope: <short summary>
- Review request: <link or description>
- Outcome: <Approved | Approved with minor issues | Changes required>

## Files reviewed
- [docs/requirements/README.md](../../requirements/README.md)
- <add reviewed file links>

## Checklist

### Problem, intent, and classification
- [ ] **RR-01 — Problem or opportunity is stated clearly and correctly.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-02 — Requirements reflect the actual user or business intent, not an unverified assumption or proposed solution that hides the real goal.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-03 — The request is correctly classified as a new product, feature add, or refinement.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

### Scope, actors, and ownership
- [ ] **RR-04 — In-scope and out-of-scope items are explicit and coherent.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-05 — All relevant roles, permissions, ownership boundaries, and affected parties are defined.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

### Functional completeness
- [ ] **RR-06 — Primary, alternate, and system-response workflows are adequately described.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-07 — Business rules, triggers, constraints, and validations are explicit.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-08 — Failure modes, exceptions, invalid inputs, and recovery paths are covered.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-09 — Important data concepts, sources, destinations, and external system interactions are covered.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

### Non-functional requirements
- [ ] **RR-10 — All relevant NFRs are captured and made measurable (performance, security, reliability, availability, accessibility, compliance, observability, compatibility, etc.).**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

### Quality and consistency
- [ ] **RR-11 — Acceptance criteria are testable, unambiguous, and expressible in Given/When/Then form where appropriate.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-12 — Requirements are specific enough for task breakdown and QA validation without guesswork.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-13 — Terminology is consistent across the requirements package and aligned with the glossary when present.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-14 — The requirements package is internally consistent and free of contradictions or stale statements.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-15 — Assumptions, dependencies, risks, and open questions are tracked explicitly.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

### Requirement identifiers and traceability
- [ ] **RR-16 — Every atomic requirement statement has a unique identifier in the form `<FEATURE-SHORT>-NNN`.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-17 — Requirement identifiers are unique across the reviewed requirements package.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-18 — Identifier prefixes are concise, stable, and consistently applied across related files.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-19 — High-level goals trace cleanly to detailed requirement files and requirement IDs; every requirement carries a source annotation (`→ DECISION-NNN` or `→ original request`); every cited `DECISION-NNN` exists in `decisions.md`.**
  - Status: <PASS|FAIL|N/A>
  - Evidence: <list any requirements missing annotations or citing decisions absent from the log>
  - Notes:
  - Follow-up:

### Document structure and indexing
- [ ] **RR-20 — A canonical high-level index document exists when multiple requirements files are present.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-21 — The index document explains what the product or feature does at a high level.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-22 — Every created or updated requirements file is linked from the high-level index document.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-23 — Feature-level overview or local index files exist when a feature is split across multiple files.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-24 — Requirements are stored in the correct project location and follow the existing documentation convention.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

### Decision log
- [ ] **RR-25 — A standalone `decisions.md` file exists at the root of the requirements area and is non-empty.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-26 — Every decision entry contains a decision number, statement, author name (real name — not a placeholder or role label), ISO 8601 UTC timestamp, and rationale.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-27 — The `decisions.md` file is linked from the high-level index document.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

- [ ] **RR-28 — Every significant decision visible in the requirements package (scope boundaries, constraints, technology choices, NFR targets, deferrals, reversals) has a corresponding entry in `decisions.md`.**
  - Status: <PASS|FAIL|N/A>
  - Evidence: <list any decisions found in requirement files that are absent from the log>
  - Notes:
  - Follow-up:

### Implementation readiness
- [ ] **RR-29 — Architecture and development could proceed without inventing missing meaning or guessing about behavior, scope, permissions, rules, or quality constraints.**
  - Status: <PASS|FAIL|N/A>
  - Evidence:
  - Notes:
  - Follow-up:

## Findings

Use the format below for every `FAIL` item. Copy the block as many times as needed.

```
- Severity: <Blocking | Major | Minor>
  Category: <scope | actors and permissions | workflow | business rules | edge cases | data and integrations | NFR | acceptance criteria | consistency | ambiguity | document structure | assumptions and risks | identifiers | index>
  Location: <path/to/file.md>
  Issue: <what is wrong>
  Why it matters: <impact on architect, developer, or QA>
  Required fix: <concrete action the requirements manager must take>
```

## Overall verdict
- Outcome: <Approved | Approved with minor issues | Changes required>
- 29-point checklist passed fully: <Yes | No>
- Failed or partial items:
  - <RR-NN — brief description>

## Recommendation
- Next step: <hand off to architect agent | return to requirements manager with findings>
- Notes: <anything the receiving agent should know>

## Required follow-ups
- <action — owner — priority>

## Optional notes
- <anything else>