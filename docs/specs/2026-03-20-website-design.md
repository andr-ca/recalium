# Recalium Website Design

## What we're building

A product marketing website for Recalium that ships alongside v1. It explains what Recalium does, who it's for, and how to get started. The site targets developers and technical AI power users — the people who can actually use the Docker-based product at launch.

## Decisions made

- **Audience:** Developer-first. Lead with the problem in human terms, then prove technical credibility immediately. The getting-started page should remain approachable enough for technically comfortable non-developers (Persona 2 — research power users who can follow Docker instructions).
- **Pages:** Home, Features, Pricing, Docs (getting started), 404, plus prominent GitHub link.
- **Tech:** Astro static site in a `/website` directory inside the main repo. Deployed to Cloudflare Pages.
- **Design:** Dark slate background with cyan-to-indigo gradient accents. Supabase/Railway aesthetic — premium open-source energy.
- **Analytics:** Cloudflare Web Analytics only (server-side, zero client JS). No third-party tracking scripts.

## Home page

### Hero

- Headline: "Your AI memory. Portable. Private. Yours."
- Subhead: "Every AI vendor locks your context inside their platform. Recalium is a local-first memory layer that works across all of them."
- Two CTAs: "Get Started" (links to docs/install) and "View on GitHub".
- Below CTAs: a terminal-style snippet showing `docker compose up` to signal real, installable software.

### Problem section — "The memory lock-in problem"

Three columns showing vendor silos:
- ChatGPT remembers → only in ChatGPT
- Claude remembers → only in Claude
- Gemini remembers → only in Gemini

One-liner below: "Switch tools and start over. Recalium fixes this."

### How it works — 4 steps

1. **Import** — "Bring your ChatGPT and Claude exports. Paste text. Drop files in a watched folder."
2. **Process** — "Recalium extracts facts, generates summaries, and indexes everything. BYOK — your API keys, your provider bill."
3. **Search & Retrieve** — "Keyword, semantic, or hybrid search. Context-budgeted retrieval with source attribution."
4. **Use anywhere** — "MCP retrieval injects context into any compatible AI tool. No re-explaining."

### Differentiators — 3 cards

- **Local-first** — "Your data stays on your machine. Docker-based. No cloud required."
- **Source-backed** — "Every fact links back to the exact text it came from. No hallucinated memory."
- **Open format** — "JSON export/import. No lock-in — not even to Recalium."

### Comparison table — "How Recalium compares"

Compact table comparing Recalium vs. ChatGPT Memory vs. Claude Projects vs. mem0 vs. Obsidian+plugins. Rows: Portable, Local-first, Source-backed, MCP-native, User-controlled, Open source. Recalium gets checkmarks across the board. MemGPT/Letta and Rewind are intentionally omitted for brevity — they target different use cases.

### CTA footer

"Ready to own your AI memory?" with "Get Started" and "Star on GitHub" buttons.

## Features page

Page header: "Everything you need to own your AI memory"

Six feature blocks, each with a heading, 2-3 sentence description, and a visual. Visuals for features 1-3 are real code/JSON snippets written as part of implementation. Visuals for features 4-6 are SVG diagrams created during implementation.

1. **Zero-friction ingestion** — paste, upload, watched folder, MCP ingest. All paths feed one durable archive. Visual: real code snippet showing an MCP ingest call with source metadata.

2. **Intelligent extraction** — facts, summaries, embeddings with source spans and confidence tiers. BYOK model. Visual: real JSON snippet showing an extracted fact with source_span, confidence_tier, and derivation_method fields.

3. **Hybrid search & retrieval** — keyword, semantic, hybrid with RRF. Context-budgeted retrieval. Visual: real JSON snippet showing the context assembly response format from the architecture (query, items, budget_used, provenance).

4. **MCP-native** — agents and tools retrieve memory without manual intervention. Visual: SVG diagram showing Agent → MCP → Recalium → context returned flow.

5. **Review & curate** — browse facts, inspect provenance, promote to canonical memory, resolve duplicates. Visual: SVG wireframe mockup of the facts review UI with source span highlight.

6. **Private by default** — localhost-only, sensitivity gate, cascade deletion, audit trail. Visual: SVG diagram showing the sensitivity gate decision flow (user-declared → local pre-classification → block or allow).

## Pricing page

Two-column layout:

**Free (BYOK)** — $0 forever. Self-hosted Docker. Your API keys. Everything included. Open source.

**Managed Processing** — Coming soon. Self-hosted Docker. Recalium-provided keys. Everything + no key management.

Below the table: "Recalium is open source and fully functional at zero cost. Bring your own API keys for OpenAI or Anthropic. The managed processing tier eliminates key management — same product, less setup. Cloud sync and team features are on the roadmap."

CTA: "Get Started Free" and "Star on GitHub."

## Docs page

A single Getting Started page for v1 (not a full docs site):

1. **Prerequisites** — Docker (required). An OpenAI or Anthropic API key (optional — enables AI-powered extraction and semantic search; keyword search and manual ingestion work without one).
2. **Install** — `git clone` + `docker compose up` with copy buttons.
3. **First run** — walkthrough of setup wizard (BYOK provider config → import → first search).
4. **MCP setup** — how to configure MCP retrieval in Claude Code and other clients.
5. **Configuration reference** — `.env` variables table.

This grows into a full docs site later (Starlight or similar). For launch, one solid getting-started page is enough.

## 404 page

Dark-themed, on-brand. Short message ("This page doesn't exist — but your AI memory can."), CTA button back to the home page. Uses the same layout shell as other pages. Implemented as `src/pages/404.astro`.

## Shared layout

- **Nav bar:** Logo left (text-only: "Recalium" in semi-bold with accent gradient applied to text), page links center (Home, Features, Pricing, Docs), GitHub star button right.
- **Footer:** Logo, links to all pages, GitHub link, "Built for developers who use more than one AI" tagline, license note (MIT or similar — match repo license).
- **Mobile:** Hamburger menu, all pages accessible, responsive breakpoints.
- **Skip-to-content link:** Hidden link at top of page for screen reader and keyboard users, visible on focus.

## Metadata and SEO

- **Title pattern:** "Recalium — [page-specific subtitle]" (e.g., "Recalium — Your AI Memory, Portable and Private" for home).
- **Meta descriptions:** Unique per page, 150-160 characters, describing the page content.
- **Open Graph tags:** Title, description, and OG image per page. OG image: 1200x630, dark background with Recalium wordmark and tagline in accent gradient.
- **Favicon:** Simple gradient square (indigo-to-cyan) with "R" lettermark. Generate standard sizes (16x16, 32x32, 180x180 apple-touch-icon, SVG).
- **robots.txt:** Allow all crawlers.
- **sitemap.xml:** Auto-generated via `@astrojs/sitemap`.

## Logo

v1 logo is text-only: "Recalium" rendered in Inter semi-bold (600 weight) with the accent gradient (indigo → cyan) applied via CSS gradient text. No icon or glyph. This avoids blocking implementation on a design asset. A proper logo can replace it later.

## Accessibility

- Target WCAG 2.1 AA for all pages.
- Minimum contrast ratio: 4.5:1 for body text, 3:1 for large text and UI elements.
- All images and diagrams require descriptive alt text.
- Skip-to-content link on every page.
- Interactive elements (nav, buttons, links) must be keyboard accessible with visible focus indicators.
- Verify: secondary text color #94a3b8 on #0f172a background meets 4.5:1 (computed ~7.0:1 — passes; verify after implementation).
- The indigo end of the accent gradient (#6366f1) achieves only 4.0:1 on the primary background. Do not use it as a solid color for normal-sized text or small UI labels. Gradient text and large-text usage (3:1 threshold) are acceptable.

## Performance

- Target Lighthouse score: 95+ on Performance, Accessibility, Best Practices, and SEO for all pages.
- No client-side JavaScript beyond Astro's minimal island hydration (none needed for a marketing site).
- Images optimized via Astro's built-in image optimization.

## Tech stack

- **Framework:** Astro 5.x with static output (`output: 'static'`)
- **Integrations:** `@astrojs/tailwind`, `@astrojs/mdx`, `@astrojs/sitemap`
- **Styling:** Tailwind CSS
- **Font:** Inter via `@fontsource/inter` (self-hosted, no Google Fonts dependency) with system font stack fallback
- **Package manager:** pnpm (consistent with the main repo per tech-stack.md)
- **Location:** `/website` directory in the main repo
- **Deployment:** Cloudflare Pages via Git integration (auto-deploy on push to main). Build command: `pnpm build`, output directory: `dist`.
- **Content:** Markdown/MDX for docs page, Astro components for marketing pages

## Design tokens

- **Background:** Dark slate (#0f172a to #1e293b gradient)
- **Text:** Light (#e2e8f0 primary, #94a3b8 secondary)
- **Accent gradient:** Indigo to cyan (#6366f1 → #22d3ee)
- **Cards/surfaces:** Slightly lighter slate with subtle border (#1e293b background, #334155 border)
- **Code blocks:** Darker background (#0a0f1a) with syntax highlighting
- **Buttons:** Gradient fill for primary CTA, subtle border (#334155) for secondary
- **Font:** Inter 400/600 with system fallback
- **Border radius:** 8px for cards, 6px for buttons
