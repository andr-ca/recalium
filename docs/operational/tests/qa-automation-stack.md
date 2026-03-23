# QA Automation Stack

## Status
- Decision status: working baseline
- Applies to: Recalium v1 implementation and release validation
- Constraint: implementation stack is committed for v1 (Python/FastAPI, React/TypeScript, PostgreSQL/pgvector — see docs/architecture/tech-stack.md); this QA stack is locked to match

## QA automation goals
Recalium QA automation must prove:
- durable ingest and queue recovery
- retrieval correctness and API contract stability
- policy enforcement for sensitive-content and deletion behavior
- backup, restore, and portability correctness
- keyboard-only and accessibility compliance for core workflows
- published performance targets under the documented local profile

## Selected QA tools

### 1. CI orchestration
- GitHub Actions

Use for:
- pull request checks
- main-branch validation
- scheduled nightly validations
- artifact upload for reports and benchmark evidence

### 2. Backend and domain test runner
- `pytest`
- `pytest-xdist`
- `pytest-cov`

Use for:
- unit tests
- service-layer tests
- integration tests against PostgreSQL and local artifact storage
- queue recovery and deletion suppression scenarios
- coverage reporting

Reason:
- the repository already carries Python-oriented agent instructions and no competing backend stack has been fixed yet
- `pytest` is the simplest baseline for API, worker, and operations automation if backend delivery proceeds in Python

### 3. Property and edge-case testing
- `hypothesis`

Use for:
- idempotency key behavior
- ranking and trimming edge cases
- import/export manifest validation
- deletion and suppression invariants

### 4. UI end-to-end automation
- Playwright

Use for:
- localhost UI smoke tests
- ingest, search, review queue, canonical edit, and restore flows
- Chrome/Chromium-only workflow coverage matching the v1 browser target
- keyboard-only navigation checks

### 5. Accessibility automation
- `axe-core` through Playwright

Use for:
- automated accessibility checks on core workflows
- WCAG 2.1 AA regression detection for the supported browser target

### 6. API contract validation
- OpenAPI-based contract checks once API schemas exist
- `schemathesis` for API fuzzing and contract validation

Use for:
- validation, policy-denial, unavailable-capability, and internal-failure response classes
- request and response contract drift detection
- bounded result envelope and pagination behavior

### 7. Performance and load validation
- `k6`

Use for:
- ingest acknowledgment benchmarking
- retrieval latency benchmarking
- queue backlog impact checks on foreground APIs
- degraded-mode performance checks

### 8. Security and dependency scanning
- `bandit`
- `pip-audit`
- Trivy

Use for:
- Python security linting
- dependency vulnerability scanning
- container image and filesystem scanning

### 9. Code quality gates
- Ruff
- mypy

Use for:
- linting
- import/order/style enforcement
- static type checks for backend code

### 10. Documentation and Markdown checks
- `markdownlint-cli2`

Use for:
- documentation quality gates for requirements, architecture, plans, and operational docs

## Automation layers

### Pull request gate
Required on every change:
- Ruff
- mypy
- fast `pytest` unit and service tests
- Playwright smoke suite for affected core UI flows
- `axe-core` accessibility smoke checks for affected UI flows
- OpenAPI / `schemathesis` contract checks when API surfaces change
- `markdownlint-cli2` for docs changes

### Merge-to-main gate
Required on main branch:
- full `pytest` suite
- full Playwright end-to-end suite
- full API contract suite
- coverage report generation
- Trivy, `bandit`, and `pip-audit`

### Nightly or scheduled gate
Required on schedule:
- `k6` ingest and retrieval benchmark suite
- queue backlog impact validation
- backup creation and restore validation run
- export/import round-trip validation
- larger dataset regression suite

## Minimum automated evidence by requirement area

### Reliability
Tools:
- `pytest`
- `hypothesis`
- Playwright

Evidence:
- no acknowledged raw item lost after restart
- queue retry and terminal failure behavior
- restore validation before cutover

### Privacy and deletion safety
Tools:
- `pytest`
- `hypothesis`
- `schemathesis`

Evidence:
- policy gate blocks sensitive or unknown content from external processing
- deleted or redacted content is suppressed from retrieval
- tombstone behavior survives restore and import paths where required

### Performance
Tools:
- `k6`
- `pytest` benchmark-style integration scenarios where useful

Evidence:
- ingest $P95 \le 1\text{ s}$ for supported ingest profile
- retrieval $P95 \le 2\text{ s}$ for the documented dataset profile
- queue backlog impact on foreground APIs is measured
- restore timing meets the published target

### Accessibility and compatibility
Tools:
- Playwright
- `axe-core`

Evidence:
- keyboard-only operation for core workflows
- WCAG 2.1 AA automated checks for core screens in latest Chrome/Chromium

## Initial adoption order
1. GitHub Actions
2. Ruff, mypy, `pytest`, `pytest-cov`
3. Playwright plus `axe-core`
4. Trivy, `bandit`, `pip-audit`
5. OpenAPI contract checks and `schemathesis`
6. `k6` nightly performance and restore validation
7. `hypothesis` for deeper invariants and edge-case automation

## Implementation note
The backend stack is committed as Python for v1. `pytest`, Ruff, mypy, `bandit`, and `pip-audit` are the correct tools for that runtime. If a future version migrates to a different backend runtime, replace these tools with equivalents for that runtime while preserving the same gate structure and evidence model.
