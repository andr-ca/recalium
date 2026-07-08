# Recalium Codex Instructions

Use [AGENTS.md](AGENTS.md) as the primary repository instruction file.

When starting the app, testing, validating MCP, exercising UI UAT, or collecting release evidence, read the Codex skill first:

- [.codex/skills/recalium-use-and-test/SKILL.md](.codex/skills/recalium-use-and-test/SKILL.md)

Also read:

- [agents/project.instructions.md](agents/project.instructions.md)
- [docs/guides/local-use-and-test.md](docs/guides/local-use-and-test.md)
- [docs/operational/validations/recalium-v1-release-readiness-gap-register.md](docs/operational/validations/recalium-v1-release-readiness-gap-register.md)

Rules:

- Never hardcode secrets; use `.env` and keep `.env.sample` sanitized.
- Keep v1 to two containers only: `recalium-app` and `recalium-postgres`.
- Use `uv` for Python and `pnpm` for frontend work.
- Do not claim release readiness without evidence under [docs/operational](docs/operational).
