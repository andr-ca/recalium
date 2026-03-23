# User Personas

## Purpose
Ground requirements and design decisions in concrete user profiles. Each persona represents a distinct usage pattern, motivation, and value measurement for Recalium.

## Persona 1 — The Multi-Tool Developer

### Profile
Mid-to-senior developer who uses Claude Code for backend work, ChatGPT for architecture brainstorming and code review, and Gemini for documentation and research. Switches between tools daily depending on the task. Has 6+ months of conversation history across multiple providers.

### Technical profile
- Runs Docker daily as part of development workflow
- Has API keys for OpenAI and Anthropic
- Comfortable with CLI tools and MCP configuration
- Would install Recalium via `docker compose up` without hesitation

### Pain point
Loses project context every time they switch tools. Re-explains project setup, coding conventions, and architectural decisions to each new session. Spends 5-10 minutes at the start of each session re-establishing context that already exists in a conversation on another platform.

### Primary use pattern
- Imports ChatGPT and Claude conversation exports on first setup
- Uses MCP retrieval as the primary consumption mode (context auto-injected into AI sessions)
- Occasionally reviews and promotes facts to canonical memory through the web UI
- Values accuracy over comprehensiveness — would rather get 3 correct facts than 10 noisy ones

### Measures value by
"Did I stop re-explaining my project setup and tech decisions to every new AI session?"

### Tolerance for friction
High. Will configure `.env` files, manage API keys, and troubleshoot Docker issues. Low tolerance for incorrect or noisy extraction results.

## Persona 2 — The Research Power User

### Profile
Non-developer knowledge worker who uses AI extensively for analysis, writing, and research. Uses ChatGPT Plus for general work, Claude for long-form writing, and Gemini for web-connected research. Has hundreds of conversations spanning months of work on multiple projects.

### Technical profile
- Can follow Docker installation instructions but does not use Docker regularly
- May or may not have provider API keys — would need guidance to obtain them
- Primarily uses the web UI, not CLI or MCP
- Comfortable with web applications but not terminal-based tools

### Pain point
Cannot find insights, decisions, or analysis from past AI conversations. Knows they discussed a specific topic with an AI tool months ago but cannot locate which tool, which conversation, or what was concluded. Recreates analysis that already exists somewhere in their conversation history.

### Primary use pattern
- Imports large ChatGPT exports during first-run setup
- Uses the web UI search as the primary consumption mode
- Reviews facts and promotes important research conclusions to canonical memory
- Browses the archive to rediscover past conversations
- Values comprehensive retrieval — wants to find everything related to a topic

### Measures value by
"Can I find that analysis I did 3 months ago without remembering which AI tool I used?"

### Tolerance for friction
Moderate. Will follow a setup wizard but will abandon if the first-run experience takes more than 30 minutes or requires terminal commands beyond `docker compose up`. Low tolerance for confusing or overly technical UI.

## Persona 3 — The MCP Agent Builder

### Profile
Developer building AI agents or workflows that need persistent user context. Building tools that interact with multiple AI services and need a shared memory layer. Evaluates Recalium primarily as infrastructure, not as a user-facing product.

### Technical profile
- Deep familiarity with MCP protocol and AI tool APIs
- Has multiple provider API keys and manages them routinely
- Evaluates Recalium's API and MCP interface quality, not its UI
- Would read API docs before opening the web UI

### Pain point
Building agents that lack persistent context across sessions and tools. Each agent invocation starts from zero. Needs a reliable, queryable memory backend that agents can read from and write to via MCP without user intervention.

### Primary use pattern
- Uses MCP ingest to write agent outputs and conversation summaries into Recalium
- Uses MCP retrieval to inject relevant context into agent prompts
- Rarely uses the web UI except for debugging and auditing agent access
- Values API stability, clear error contracts, and predictable retrieval behavior
- Treats Recalium as a dependency in a larger system

### Measures value by
"Can my agents retrieve relevant context from prior sessions without me pre-loading it manually?"

### Tolerance for friction
Very high for setup complexity. Very low for API instability, unclear error messages, or unpredictable retrieval results. Will abandon immediately if the MCP interface is unreliable or poorly documented.

## Usage in requirements

When writing acceptance criteria, workflows, or UI specifications, reference these personas to ground decisions:
- "Given **a multi-tool developer** imports their ChatGPT export..." forces attention to extraction quality and MCP retrieval.
- "Given **a research power user** searches for a topic discussed months ago..." forces attention to search relevance and UI clarity.
- "Given **an MCP agent builder** configures retrieval for their workflow..." forces attention to API contracts and error handling.
