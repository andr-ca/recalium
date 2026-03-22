# Recalium Website — Implementation Spec

Date: 2026-03-21

## What we're building

A five-page static marketing website for Recalium, a local-first AI memory layer. Targets developers and technical AI power users. Ships alongside v1.

**Pages:** Home, Features, Pricing, Docs (getting started), 404

**Stack:** Astro 5.x, Tailwind CSS, pnpm, Cloudflare Pages. Lives in `/website` inside the main repo.

---

## Visual direction

Decisions confirmed during design session:

### Hero (Home page)
- **Style:** Centered layout, film-grain noise texture overlay, large bold headline, indigo→cyan gradient on key phrase, top radial glow
- **Tag pill** above headline: `Open source · BYOK · Docker-based`
- **Headline:** "AI memory that's *actually yours*" — gradient on "actually yours"
- **Subhead:** "Every AI tool locks your context in its own silo. Recalium is a local-first memory layer — portable, private, and open."
- **CTAs:** "Get Started →" (indigo fill, rounded-full) + "View on GitHub" (border, rounded-full)
- **No terminal snippet in hero** — the centered layout carries the message without it

### Nav
- **Style:** Frosted glass — `backdrop-filter: blur(12px)`, semi-transparent dark background, 1px hairline border bottom
- **Layout:** Logo left, links center (Home, Features, Pricing, Docs), GitHub star button + "Get Started" CTA right
- **Logo:** "Recalium" in Inter 700, indigo→cyan gradient text
- **Scroll behavior:** Nav starts transparent over hero, border appears on scroll (CSS scroll-driven or JS class toggle)
- **Mobile:** Hamburger menu, full-screen overlay

### Features page layout
- **Style:** Alternating full-width rows — text left / visual right, then text right / visual left
- **Each row:** Icon, feature number label (01–06), heading, 2–3 sentence description on one side; code snippet or SVG diagram on the other
- **Visuals for features 1–3:** Real code/JSON snippets (written during implementation)
- **Visuals for features 4–6:** SVG diagrams (created during implementation)

### Design tokens
| Token | Value |
|---|---|
| Page background | `#06090f` (near-black with slight blue tint) |
| Nav background | `rgba(6,9,15,0.7)` + `backdrop-filter:blur(12px)` |
| Surface / card | `#0d1520` |
| Border | `#1a2640` |
| Text primary | `#f8fafc` |
| Text secondary | `#94a3b8` |
| Text muted | `#475569` |
| Accent gradient | `#818cf8` → `#22d3ee` |
| Accent solid | `#6366f1` |
| Success / terminal green | `#4ade80` |
| Code background | `#040810` |
| Border radius — cards | `10px` |
| Border radius — buttons | `100px` (pill) |
| Border radius — code blocks | `6px` |
| Font | Inter 400/700/800 via `@fontsource/inter` |
| Noise texture | SVG fractalNoise, opacity ~0.04, 200px tile |

---

## Pages

### Home (`/`)

**Sections in order:**

1. **Hero** — tag pill, gradient headline, subhead, two CTAs
2. **Problem** — "The memory lock-in problem". Three columns: ChatGPT / Claude / Gemini each remember only within their own silo. One-liner below: "Switch tools and start over. Recalium fixes this."
3. **How it works** — 4-step horizontal flow: Import → Process → Search & Retrieve → Use anywhere. Each step has a number, bold title, one-sentence description.
4. **Differentiators** — 3 cards: Local-first / Source-backed / Open format. Cards use `#0d1520` background, `#1a2640` border, 10px radius.
5. **Comparison table** — "How Recalium compares". Rows: Portable, Local-first, Source-backed, MCP-native, User-controlled, Open source. Columns: Recalium, ChatGPT Memory, Claude Projects, mem0, Obsidian+plugins. Recalium checkmarks all rows.
6. **CTA footer** — "Ready to own your AI memory?" with "Get Started" and "Star on GitHub".

### Features (`/features`)

**Header:** "Everything you need to own your AI memory"

**Six alternating rows:**

| # | Title | Visual type |
|---|---|---|
| 01 | Zero-friction ingestion | Code snippet: MCP ingest call with source metadata |
| 02 | Intelligent extraction | JSON snippet: extracted fact with source_span, confidence_tier, derivation_method |
| 03 | Hybrid search & retrieval | JSON snippet: context assembly response (query, items, budget_used, provenance) |
| 04 | MCP-native retrieval | SVG diagram: Agent → MCP → Recalium → context returned |
| 05 | Review & curate | SVG wireframe: facts review UI with source span highlight |
| 06 | Private by default | SVG diagram: sensitivity gate decision flow |

Odd rows (01, 03, 05): text left, visual right.
Even rows (02, 04, 06): text right, visual left.

### Pricing (`/pricing`)

Two-column layout:

**Free (BYOK)** — $0 forever. Self-hosted Docker. Your API keys. Everything included. Open source. Checkmark list of all features.

**Managed Processing** — "Coming soon" badge. Self-hosted Docker. Recalium-provided keys. Everything + no key management.

Below table: one paragraph explaining the model.

CTA: "Get Started Free" + "Star on GitHub".

### Docs (`/docs`)

Single getting-started page (not a full docs site at v1).

Five sections with anchors:
1. **Prerequisites** — Docker required. API key optional (enables AI extraction + semantic search; keyword search + manual ingestion work without one).
2. **Install** — `git clone` + `docker compose up`. Copy buttons on code blocks.
3. **First run** — walkthrough: BYOK provider config → import → first search.
4. **MCP setup** — configure MCP retrieval in Claude Code and other clients. Code block with MCP config JSON.
5. **Configuration reference** — `.env` variables table (name, default, description).

Content written in MDX. Page uses a slightly different layout: left sidebar with anchor nav on desktop, prose content area on right.

### 404 (`/404`)

Dark-themed, on-brand. Short message: "This page doesn't exist — but your AI memory can." CTA button back to home. Uses the same shared layout shell.

---

## Shared layout

**`BaseLayout.astro`** — wraps every page. Contains:
- `<head>` with title, meta description, OG tags, favicon links, font preloads
- Skip-to-content link (hidden, visible on focus)
- `<Nav />` component
- `<slot />`
- `<Footer />` component

**`<Nav />`** — frosted glass, scroll-aware. Links: Home, Features, Pricing, Docs. Right side: GitHub star button + "Get Started" CTA. Hamburger on mobile.

**`<Footer />`** — Logo, page links, GitHub link, tagline "Built for developers who use more than one AI", MIT license note.

---

## SEO & metadata

- Title pattern: `"Recalium — [page subtitle]"`
- Unique meta description per page (150–160 chars)
- Open Graph tags per page (title, description, og:image)
- OG image: 1200×630, dark background, Recalium wordmark + tagline in accent gradient. Generated as a static asset (not dynamic).
- Favicon: gradient square (indigo→cyan) with "R" lettermark. Sizes: 16×16, 32×32, 180×180 apple-touch-icon, SVG.
- `robots.txt`: allow all
- `sitemap.xml`: auto-generated via `@astrojs/sitemap`

---

## Accessibility

- WCAG 2.1 AA target
- Min contrast: 4.5:1 body text, 3:1 large text/UI elements
- All images and SVG diagrams have descriptive `alt` text
- Skip-to-content link on every page
- All interactive elements keyboard accessible with visible focus indicators
- `#94a3b8` on `#06090f` ≈ 7.2:1 — passes
- `#818cf8` (indigo end of gradient) on `#06090f` ≈ 4.2:1 — do not use as solid color for normal body text; gradient text and large headings (3:1 threshold) are fine

---

## Performance

- Lighthouse target: 95+ on Performance, Accessibility, Best Practices, SEO
- Zero client-side JS (no islands needed for a static marketing site)
- Images via Astro's built-in `<Image />` optimization
- Inter font self-hosted via `@fontsource/inter` — no Google Fonts
- Cloudflare Analytics via server-side snippet only (no client tracking JS)

---

## Project structure

```
/website
├── astro.config.mjs
├── tailwind.config.mjs
├── tsconfig.json
├── package.json
├── .env.sample
├── public/
│   ├── favicon.svg
│   ├── favicon-16.png
│   ├── favicon-32.png
│   ├── apple-touch-icon.png
│   ├── robots.txt
│   └── og/
│       └── default.png        # 1200×630 OG image
├── src/
│   ├── layouts/
│   │   ├── BaseLayout.astro
│   │   └── DocsLayout.astro
│   ├── components/
│   │   ├── Nav.astro
│   │   ├── Footer.astro
│   │   ├── HeroSection.astro
│   │   ├── ProblemSection.astro
│   │   ├── HowItWorksSection.astro
│   │   ├── DifferentiatorsSection.astro
│   │   ├── ComparisonTable.astro
│   │   ├── FeatureRow.astro
│   │   └── diagrams/
│   │       ├── McpFlow.astro
│   │       ├── FactsReview.astro
│   │       └── SensitivityGate.astro
│   ├── pages/
│   │   ├── index.astro
│   │   ├── features.astro
│   │   ├── pricing.astro
│   │   ├── docs.mdx
│   │   └── 404.astro
│   └── styles/
│       └── global.css
```

---

## Deployment

- Cloudflare Pages, Git integration, auto-deploy on push to `main`
- Build command: `pnpm build`
- Output directory: `dist`
- Root directory: `website`
- Environment variables: none required for the static site itself (analytics token injected via Cloudflare dashboard)

---

## Out of scope for v1

- Full docs site (Starlight or similar) — referenced in the original spec as future work
- GitHub star count (live API) — static "★ GitHub" link is sufficient at launch
- Blog
- Search within docs
- Dark/light mode toggle
- Animations / scroll-triggered reveals (keep it simple, fast, and accessible)
