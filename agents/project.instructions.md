# Project Instructions Template

Use this file as the repository-specific companion to `core.instructions.md`, `python.instructions.md`, and `tdd.instructions.md`.

Before relying on it in a target repository:

1. replace placeholder text with project-specific guidance
2. delete sections that do not apply
3. add project constraints, workflows, and domain language that agents must know

## Project Summary

- Project name: `<replace-with-project-name>`
- Primary purpose: `<replace-with-project-purpose>`
- Primary users or stakeholders: `<replace-with-users-or-stakeholders>`
- Current phase: `<bootstrap | MVP | active development | maintenance>`

## In Scope

- `<replace-with-core-scope-item>`
- `<replace-with-core-scope-item>`

## Out Of Scope

- `<replace-with-explicit-non-goal>`
- `<replace-with-explicit-non-goal>`

## Key Folders

- `src/` or equivalent application code folder: `<describe-purpose>`
- `tests/`: `<describe-test-layout>`
- `docs/`: `<describe-documentation-layout>`
- `agents/`: `<describe-agent instructions, prompts, or operational artifacts if used>`

Add any project-specific folders that agents should recognize immediately.

## Key Files

- `README.md`: project overview, setup, and usage guidance
- `AGENTS.md`: repository-level agent workflow and safety rules
- `agents/project.instructions.md`: this file after it is copied into a target repository
- `<replace-with-important-config-file>`: `<describe-why-it-matters>`
- `<replace-with-important-entrypoint>`: `<describe-why-it-matters>`

## Technology And Runtime Notes

- Primary language or stack: `<replace>`
- Build or package tool: `<replace>`
- Test command: `<replace>`
- Lint or format command: `<replace>`
- Run command: `<replace>`
- Deployment target: `<replace>`

## Workflow Requirements

- Branch naming convention: `<replace>`
- Required review flow: `<replace>`
- Required test evidence before merge: `<replace>`
- Required documentation updates for changes: `<replace>`
- Required artifact folders, if any: `<replace>`

## Standards And Constraints

- Architecture or design constraints: `<replace>`
- Security or compliance constraints: `<replace>`
- Performance or scalability constraints: `<replace>`
- Data handling rules: `<replace>`
- Third-party dependency or integration constraints: `<replace>`

## Domain Context

- Important domain terms: `<replace>`
- Critical business rules: `<replace>`
- Edge cases agents must remember: `<replace>`

## Maintenance Guidance

- Keep this file aligned with the actual repository structure.
- Update it whenever project intent, key folders, workflows, or constraints change.
- Prefer concrete examples and repo-relative paths over vague statements.
