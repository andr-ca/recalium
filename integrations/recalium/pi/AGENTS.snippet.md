<!-- Recalium memory — append to AGENTS.md (project) or ~/.pi/agent/AGENTS.md -->

## Recalium memory (REST)

pi has no MCP — use Recalium's local REST API.

- Recall before a task:
  `curl -s "http://localhost:8000/api/search?q=<query>&mode=hybrid"`
- Store durable notes after:
  `curl -s -X POST http://localhost:8000/api/ingest -H 'Content-Type: application/json' -d '{"content":"<note>","source_name":"pi-cli"}'`
- Check provenance and `conflict_label` before trusting results. Never ingest
  secrets — redact first. Full guidance: skills/recalium-memory/SKILL.md.
