# Recalium Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy a five-page static marketing website for Recalium using Astro 5, Tailwind CSS, and pnpm, deployed to Cloudflare Pages.

**Architecture:** Static Astro site in `/website` subdirectory. Shared `BaseLayout.astro` wraps all pages with nav and footer. Each page is a `.astro` file (or `.mdx` for docs) that composes section components. No client-side JS — pure static output.

**Tech Stack:** Astro 5.x, Tailwind CSS 3.x, `@astrojs/tailwind`, `@astrojs/mdx`, `@astrojs/sitemap`, `@fontsource/inter`, pnpm, Cloudflare Pages.

---

## File Map

**Created from scratch:**

```
website/
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
│       └── default.png
├── src/
│   ├── styles/
│   │   └── global.css
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
│   │   ├── CtaSection.astro
│   │   ├── FeatureRow.astro
│   │   └── diagrams/
│   │       ├── McpFlow.astro
│   │       ├── FactsReview.astro
│   │       └── SensitivityGate.astro
│   └── pages/
│       ├── index.astro
│       ├── features.astro
│       ├── pricing.astro
│       ├── docs.mdx
│       └── 404.astro
```

---

## Task 1: Scaffold the Astro project

**Files:**
- Create: `website/package.json`
- Create: `website/astro.config.mjs`
- Create: `website/tailwind.config.mjs`
- Create: `website/tsconfig.json`
- Create: `website/.env.sample`
- Create: `website/src/styles/global.css`

- [ ] **Step 1: Create the website directory and initialise pnpm**

```bash
mkdir website
cd website
pnpm init
```

- [ ] **Step 2: Install Astro and integrations**

```bash
pnpm add astro@^5 @astrojs/tailwind @astrojs/mdx @astrojs/sitemap tailwindcss @fontsource/inter
pnpm add -D typescript
```

- [ ] **Step 3: Write `astro.config.mjs`**

```js
// website/astro.config.mjs
import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://recalium.com',
  output: 'static',
  integrations: [tailwind(), mdx(), sitemap()],
});
```

- [ ] **Step 4: Write `tailwind.config.mjs`**

```js
// website/tailwind.config.mjs
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        page: '#06090f',
        surface: '#0d1520',
        border: '#1a2640',
        'text-primary': '#f8fafc',
        'text-secondary': '#94a3b8',
        'text-muted': '#475569',
        accent: '#6366f1',
        cyan: '#22d3ee',
        'indigo-light': '#818cf8',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      backgroundImage: {
        'accent-gradient': 'linear-gradient(90deg, #818cf8, #22d3ee)',
      },
      borderRadius: {
        card: '10px',
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 5: Write `tsconfig.json`**

```json
{
  "extends": "astro/tsconfigs/strict",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@components/*": ["src/components/*"],
      "@layouts/*": ["src/layouts/*"]
    }
  }
}
```

- [ ] **Step 6: Write `src/styles/global.css`**

```css
/* website/src/styles/global.css */
@import '@fontsource/inter/400.css';
@import '@fontsource/inter/700.css';
@import '@fontsource/inter/800.css';

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    background-color: #06090f;
    color: #f8fafc;
    scroll-behavior: smooth;
  }

  /* Gradient text utility */
  .gradient-text {
    background: linear-gradient(90deg, #818cf8, #22d3ee 60%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  /* Noise texture overlay — applied via ::before on sections that need it */
  .noise::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
    background-size: 200px;
    pointer-events: none;
    z-index: 0;
  }
}

@layer utilities {
  .gradient-text {
    background: linear-gradient(90deg, #818cf8, #22d3ee 60%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
}
```

- [ ] **Step 7: Write `.env.sample`**

```
# website/.env.sample
# No environment variables required for the static site.
# Cloudflare Web Analytics token is injected via Cloudflare Pages dashboard.
```

- [ ] **Step 8: Add dev and build scripts to `package.json`**

Edit `website/package.json` to include:

```json
{
  "name": "recalium-website",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview",
    "check": "astro check"
  }
}
```

- [ ] **Step 9: Verify dev server starts**

```bash
cd website && pnpm dev
```

Expected: Astro dev server running on `http://localhost:4321` with no errors.

- [ ] **Step 10: Commit**

```bash
git add website/
git commit -m "chore: scaffold Astro website project"
```

---

## Task 2: Static assets — favicon, OG image, robots.txt

**Files:**
- Create: `website/public/favicon.svg`
- Create: `website/public/robots.txt`
- Create: `website/public/og/default.png` (placeholder — see note)

**Note on favicon PNGs and OG image:** These are binary assets. The SVG favicon is generated in this task. PNG sizes (16, 32, 180) and the 1200×630 OG image are produced by running a Node script included below, which uses the `sharp` package to rasterise the SVG. The OG image is a flat dark card with gradient text — also generated via script.

- [ ] **Step 1: Write `public/favicon.svg`**

```svg
<!-- website/public/favicon.svg -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#6366f1"/>
      <stop offset="100%" stop-color="#22d3ee"/>
    </linearGradient>
  </defs>
  <rect width="32" height="32" rx="7" fill="url(#g)"/>
  <text x="16" y="23" font-family="Inter,system-ui,sans-serif" font-size="18"
        font-weight="800" fill="white" text-anchor="middle">R</text>
</svg>
```

- [ ] **Step 2: Install sharp for asset generation (dev dependency)**

```bash
cd website && pnpm add -D sharp
```

- [ ] **Step 3: Write `scripts/generate-assets.mjs`**

```js
// website/scripts/generate-assets.mjs
import sharp from 'sharp';
import { readFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const publicDir = join(__dirname, '../public');
const svgPath = join(publicDir, 'favicon.svg');
const svg = readFileSync(svgPath);

mkdirSync(join(publicDir, 'og'), { recursive: true });

// Favicon PNGs
await sharp(svg).resize(16, 16).png().toFile(join(publicDir, 'favicon-16.png'));
await sharp(svg).resize(32, 32).png().toFile(join(publicDir, 'favicon-32.png'));
await sharp(svg).resize(180, 180).png().toFile(join(publicDir, 'apple-touch-icon.png'));

// OG image — 1200×630 dark card with wordmark
const ogSvg = `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#818cf8"/>
      <stop offset="100%" stop-color="#22d3ee"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="#06090f"/>
  <rect x="0" y="0" width="1200" height="630" fill="url(#g)" opacity="0.04"/>
  <text x="600" y="280" font-family="Inter,system-ui,sans-serif" font-size="80"
        font-weight="800" fill="url(#g)" text-anchor="middle">Recalium</text>
  <text x="600" y="360" font-family="Inter,system-ui,sans-serif" font-size="32"
        fill="#475569" text-anchor="middle">Your AI memory. Portable. Private. Yours.</text>
</svg>`;

await sharp(Buffer.from(ogSvg)).png().toFile(join(publicDir, 'og/default.png'));

console.log('Assets generated.');
```

- [ ] **Step 4: Run the asset generator**

```bash
cd website && node scripts/generate-assets.mjs
```

Expected: `favicon-16.png`, `favicon-32.png`, `apple-touch-icon.png`, `og/default.png` created in `public/`.

- [ ] **Step 5: Write `public/robots.txt`**

```
User-agent: *
Allow: /

Sitemap: https://recalium.com/sitemap-index.xml
```

- [ ] **Step 6: Commit**

```bash
git add website/public/ website/scripts/
git commit -m "chore: add favicon, OG image, and robots.txt"
```

---

## Task 3: BaseLayout and Nav component

**Files:**
- Create: `website/src/layouts/BaseLayout.astro`
- Create: `website/src/components/Nav.astro`

- [ ] **Step 1: Write `Nav.astro`**

```astro
---
// website/src/components/Nav.astro
const links = [
  { href: '/', label: 'Home' },
  { href: '/features', label: 'Features' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/docs', label: 'Docs' },
];
const currentPath = Astro.url.pathname;
---

<header
  id="nav"
  class="fixed top-0 left-0 right-0 z-50 border-b border-transparent transition-all duration-200"
  style="background: rgba(6,9,15,0); backdrop-filter: blur(0px);"
>
  <!-- Skip to content -->
  <a
    href="#main-content"
    class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-accent focus:text-white focus:px-4 focus:py-2 focus:rounded"
  >
    Skip to content
  </a>

  <nav class="max-w-6xl mx-auto px-6 h-14 flex items-center gap-8" aria-label="Main navigation">
    <!-- Logo -->
    <a href="/" class="gradient-text font-extrabold text-base tracking-tight shrink-0">
      Recalium
    </a>

    <!-- Center links (desktop) -->
    <ul class="hidden md:flex gap-6 flex-1 justify-center list-none" role="list">
      {links.map(({ href, label }) => (
        <li>
          <a
            href={href}
            class={`text-sm transition-colors ${
              currentPath === href
                ? 'text-text-secondary'
                : 'text-text-muted hover:text-text-secondary'
            }`}
            aria-current={currentPath === href ? 'page' : undefined}
          >
            {label}
          </a>
        </li>
      ))}
    </ul>

    <!-- Right side -->
    <div class="hidden md:flex items-center gap-3 shrink-0">
      <a
        href="https://github.com/recalium/recalium"
        target="_blank"
        rel="noopener noreferrer"
        class="text-sm text-text-muted hover:text-text-secondary border border-border rounded-full px-4 py-1.5 transition-colors"
      >
        ★ GitHub
      </a>
      <a
        href="/docs"
        class="text-sm font-semibold bg-accent text-white rounded-full px-4 py-1.5 hover:bg-indigo-500 transition-colors"
      >
        Get Started
      </a>
    </div>

    <!-- Hamburger (mobile) -->
    <button
      id="nav-toggle"
      class="md:hidden ml-auto text-text-muted hover:text-text-secondary p-2"
      aria-label="Toggle menu"
      aria-expanded="false"
      aria-controls="mobile-menu"
    >
      <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <rect y="3" width="20" height="2" rx="1"/>
        <rect y="9" width="20" height="2" rx="1"/>
        <rect y="15" width="20" height="2" rx="1"/>
      </svg>
    </button>
  </nav>

  <!-- Mobile menu -->
  <div
    id="mobile-menu"
    class="hidden md:hidden bg-page border-t border-border px-6 py-4"
  >
    <ul class="flex flex-col gap-4 list-none" role="list">
      {links.map(({ href, label }) => (
        <li>
          <a href={href} class="text-sm text-text-secondary">
            {label}
          </a>
        </li>
      ))}
      <li>
        <a
          href="https://github.com/recalium/recalium"
          target="_blank"
          rel="noopener noreferrer"
          class="text-sm text-text-muted"
        >
          ★ GitHub
        </a>
      </li>
      <li>
        <a
          href="/docs"
          class="text-sm font-semibold bg-accent text-white rounded-full px-4 py-2 inline-block"
        >
          Get Started
        </a>
      </li>
    </ul>
  </div>
</header>

<script>
  // Scroll-aware nav: add frosted glass effect after scrolling past hero
  const nav = document.getElementById('nav');
  const toggle = document.getElementById('nav-toggle');
  const menu = document.getElementById('mobile-menu');

  function updateNav() {
    if (window.scrollY > 20) {
      nav?.setAttribute('style',
        'background: rgba(6,9,15,0.85); backdrop-filter: blur(12px);'
      );
      nav?.classList.add('border-border');
      nav?.classList.remove('border-transparent');
    } else {
      nav?.setAttribute('style',
        'background: rgba(6,9,15,0); backdrop-filter: blur(0px);'
      );
      nav?.classList.remove('border-border');
      nav?.classList.add('border-transparent');
    }
  }

  window.addEventListener('scroll', updateNav, { passive: true });
  updateNav();

  toggle?.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!expanded));
    menu?.classList.toggle('hidden');
  });
</script>
```

- [ ] **Step 2: Write `BaseLayout.astro`**

```astro
---
// website/src/layouts/BaseLayout.astro
import Nav from '@components/Nav.astro';
import Footer from '@components/Footer.astro';
import '../styles/global.css';

interface Props {
  title: string;
  description: string;
  ogImage?: string;
}

const {
  title,
  description,
  ogImage = '/og/default.png',
} = Astro.props;

const canonicalURL = new URL(Astro.url.pathname, Astro.site);
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <meta name="description" content={description} />
    <link rel="canonical" href={canonicalURL} />

    <!-- Favicon -->
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png" />
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png" />
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />

    <!-- Open Graph -->
    <meta property="og:type" content="website" />
    <meta property="og:url" content={canonicalURL} />
    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:image" content={new URL(ogImage, Astro.site)} />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content={title} />
    <meta name="twitter:description" content={description} />
    <meta name="twitter:image" content={new URL(ogImage, Astro.site)} />
  </head>
  <body class="bg-page text-text-primary font-sans antialiased">
    <Nav />
    <main id="main-content">
      <slot />
    </main>
    <Footer />
  </body>
</html>
```

- [ ] **Step 3: Create a stub `Footer.astro` (so BaseLayout compiles)**

```astro
---
// website/src/components/Footer.astro
const links = [
  { href: '/', label: 'Home' },
  { href: '/features', label: 'Features' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/docs', label: 'Docs' },
];
---

<footer class="border-t border-border mt-24 py-12 px-6">
  <div class="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
    <div class="flex flex-col items-center md:items-start gap-2">
      <span class="gradient-text font-extrabold text-base tracking-tight">Recalium</span>
      <p class="text-xs text-text-muted">Built for developers who use more than one AI</p>
    </div>
    <nav aria-label="Footer navigation">
      <ul class="flex gap-6 list-none flex-wrap justify-center">
        {links.map(({ href, label }) => (
          <li>
            <a href={href} class="text-sm text-text-muted hover:text-text-secondary transition-colors">
              {label}
            </a>
          </li>
        ))}
        <li>
          <a
            href="https://github.com/recalium/recalium"
            target="_blank"
            rel="noopener noreferrer"
            class="text-sm text-text-muted hover:text-text-secondary transition-colors"
          >
            GitHub
          </a>
        </li>
      </ul>
    </nav>
    <p class="text-xs text-text-muted">MIT License</p>
  </div>
</footer>
```

- [ ] **Step 4: Create a placeholder `index.astro` (so dev server renders something)**

```astro
---
// website/src/pages/index.astro
import BaseLayout from '@layouts/BaseLayout.astro';
---
<BaseLayout
  title="Recalium — Your AI Memory, Portable and Private"
  description="Recalium is a local-first memory layer that works across all your AI tools. Portable, private, and open source."
>
  <div class="h-screen flex items-center justify-center text-text-muted">
    Home page coming soon
  </div>
</BaseLayout>
```

- [ ] **Step 5: Verify build passes**

```bash
cd website && pnpm build
```

Expected: Build succeeds, `dist/` created, no type errors.

- [ ] **Step 6: Commit**

```bash
git add website/src/
git commit -m "feat: add BaseLayout, Nav, and Footer shell"
```

---

## Task 4: Home page — Hero section

**Files:**
- Create: `website/src/components/HeroSection.astro`
- Modify: `website/src/pages/index.astro`

- [ ] **Step 1: Write `HeroSection.astro`**

```astro
---
// website/src/components/HeroSection.astro
---

<section class="relative overflow-hidden pt-32 pb-24 px-6 text-center noise">
  <!-- Radial glow -->
  <div
    class="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] pointer-events-none"
    style="background: radial-gradient(ellipse, rgba(99,102,241,0.10) 0%, transparent 70%);"
    aria-hidden="true"
  ></div>

  <div class="relative z-10 max-w-3xl mx-auto">
    <!-- Tag pill -->
    <div class="inline-block border border-border rounded-full px-4 py-1 text-xs text-text-muted mb-8">
      Open source &middot; BYOK &middot; <strong class="text-indigo-light font-medium">Docker-based</strong>
    </div>

    <!-- Headline -->
    <h1 class="text-5xl md:text-6xl font-extrabold tracking-tighter leading-none mb-5 text-text-primary">
      AI memory that's<br />
      <em class="gradient-text not-italic">actually yours</em>
    </h1>

    <!-- Subhead -->
    <p class="text-base md:text-lg text-text-muted leading-relaxed max-w-xl mx-auto mb-10">
      Every AI tool locks your context in its own silo. Recalium is a local-first
      memory layer — portable, private, and open.
    </p>

    <!-- CTAs -->
    <div class="flex gap-3 justify-center flex-wrap">
      <a
        href="/docs"
        class="bg-accent text-white font-semibold rounded-full px-6 py-3 text-sm hover:bg-indigo-500 transition-colors"
      >
        Get Started &rarr;
      </a>
      <a
        href="https://github.com/recalium/recalium"
        target="_blank"
        rel="noopener noreferrer"
        class="border border-border text-text-muted rounded-full px-6 py-3 text-sm hover:text-text-secondary hover:border-text-muted transition-colors"
      >
        View on GitHub
      </a>
    </div>
  </div>
</section>
```

- [ ] **Step 2: Update `index.astro` to use HeroSection**

```astro
---
// website/src/pages/index.astro
import BaseLayout from '@layouts/BaseLayout.astro';
import HeroSection from '@components/HeroSection.astro';
---
<BaseLayout
  title="Recalium — Your AI Memory, Portable and Private"
  description="Recalium is a local-first memory layer that works across all your AI tools. Portable, private, and open source."
>
  <HeroSection />
</BaseLayout>
```

- [ ] **Step 3: Verify visually**

```bash
cd website && pnpm dev
```

Open `http://localhost:4321`. Check:
- Gradient headline renders correctly
- Radial glow visible above headline
- Noise texture subtle but present
- Nav transparent over hero, frosted on scroll
- Both CTAs visible and correctly styled

- [ ] **Step 4: Commit**

```bash
git add website/src/
git commit -m "feat: add home page hero section"
```

---

## Task 5: Home page — Problem, How It Works, Differentiators sections

**Files:**
- Create: `website/src/components/ProblemSection.astro`
- Create: `website/src/components/HowItWorksSection.astro`
- Create: `website/src/components/DifferentiatorsSection.astro`
- Modify: `website/src/pages/index.astro`

- [ ] **Step 1: Write `ProblemSection.astro`**

```astro
---
// website/src/components/ProblemSection.astro
const silos = [
  { name: 'ChatGPT', detail: 'remembers → only in ChatGPT' },
  { name: 'Claude', detail: 'remembers → only in Claude' },
  { name: 'Gemini', detail: 'remembers → only in Gemini' },
];
---

<section class="py-24 px-6">
  <div class="max-w-4xl mx-auto text-center">
    <h2 class="text-3xl md:text-4xl font-extrabold tracking-tight mb-4 text-text-primary">
      The memory lock-in problem
    </h2>
    <p class="text-text-muted mb-14 max-w-xl mx-auto">
      Each platform keeps your context to itself. Start a new tool and you start over.
    </p>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
      {silos.map(({ name, detail }) => (
        <div class="bg-surface border border-border rounded-card p-6 text-left">
          <p class="font-semibold text-text-secondary mb-1">{name}</p>
          <p class="text-sm text-text-muted">{detail}</p>
        </div>
      ))}
    </div>

    <p class="text-text-secondary font-medium">
      Switch tools and start over. <span class="gradient-text">Recalium fixes this.</span>
    </p>
  </div>
</section>
```

- [ ] **Step 2: Write `HowItWorksSection.astro`**

```astro
---
// website/src/components/HowItWorksSection.astro
const steps = [
  {
    number: '01',
    title: 'Import',
    description: 'Bring your ChatGPT and Claude exports. Paste text. Drop files in a watched folder.',
  },
  {
    number: '02',
    title: 'Process',
    description: 'Recalium extracts facts, generates summaries, and indexes everything. BYOK — your API keys, your provider bill.',
  },
  {
    number: '03',
    title: 'Search & Retrieve',
    description: 'Keyword, semantic, or hybrid search. Context-budgeted retrieval with source attribution.',
  },
  {
    number: '04',
    title: 'Use anywhere',
    description: 'MCP retrieval injects context into any compatible AI tool. No re-explaining.',
  },
];
---

<section class="py-24 px-6 border-t border-border">
  <div class="max-w-5xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-extrabold tracking-tight mb-14 text-center text-text-primary">
      How it works
    </h2>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
      {steps.map(({ number, title, description }) => (
        <div class="flex flex-col">
          <span class="text-xs font-semibold text-accent mb-3 tracking-widest">{number}</span>
          <h3 class="font-bold text-text-primary mb-2">{title}</h3>
          <p class="text-sm text-text-muted leading-relaxed">{description}</p>
        </div>
      ))}
    </div>
  </div>
</section>
```

- [ ] **Step 3: Write `DifferentiatorsSection.astro`**

```astro
---
// website/src/components/DifferentiatorsSection.astro
const cards = [
  {
    title: 'Local-first',
    description: 'Your data stays on your machine. Docker-based. No cloud required.',
    icon: '🏠',
  },
  {
    title: 'Source-backed',
    description: 'Every fact links back to the exact text it came from. No hallucinated memory.',
    icon: '🔗',
  },
  {
    title: 'Open format',
    description: 'JSON export/import. No lock-in — not even to Recalium.',
    icon: '📂',
  },
];
---

<section class="py-24 px-6 border-t border-border">
  <div class="max-w-5xl mx-auto">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      {cards.map(({ title, description, icon }) => (
        <div class="bg-surface border border-border rounded-card p-7">
          <div class="text-2xl mb-4" aria-hidden="true">{icon}</div>
          <h3 class="font-bold text-text-primary mb-2">{title}</h3>
          <p class="text-sm text-text-muted leading-relaxed">{description}</p>
        </div>
      ))}
    </div>
  </div>
</section>
```

- [ ] **Step 4: Add sections to `index.astro`**

```astro
---
import BaseLayout from '@layouts/BaseLayout.astro';
import HeroSection from '@components/HeroSection.astro';
import ProblemSection from '@components/ProblemSection.astro';
import HowItWorksSection from '@components/HowItWorksSection.astro';
import DifferentiatorsSection from '@components/DifferentiatorsSection.astro';
---
<BaseLayout
  title="Recalium — Your AI Memory, Portable and Private"
  description="Recalium is a local-first memory layer that works across all your AI tools. Portable, private, and open source."
>
  <HeroSection />
  <ProblemSection />
  <HowItWorksSection />
  <DifferentiatorsSection />
</BaseLayout>
```

- [ ] **Step 5: Verify visually in dev server, commit**

```bash
cd website && pnpm dev
```

Check all three sections render and are visually coherent. Then:

```bash
git add website/src/
git commit -m "feat: add problem, how it works, and differentiators sections"
```

---

## Task 6: Home page — Comparison table and CTA footer

**Files:**
- Create: `website/src/components/ComparisonTable.astro`
- Create: `website/src/components/CtaSection.astro`
- Modify: `website/src/pages/index.astro`

- [ ] **Step 1: Write `ComparisonTable.astro`**

```astro
---
// website/src/components/ComparisonTable.astro
const rows = [
  'Portable',
  'Local-first',
  'Source-backed',
  'MCP-native',
  'User-controlled',
  'Open source',
];

const cols = [
  { name: 'Recalium', highlight: true },
  { name: 'ChatGPT Memory', highlight: false },
  { name: 'Claude Projects', highlight: false },
  { name: 'mem0', highlight: false },
  { name: 'Obsidian+plugins', highlight: false },
];

// Recalium checks all; others have partial support
const checks: Record<string, boolean[]> = {
  'Portable':        [true,  false, false, false, true ],
  'Local-first':     [true,  false, false, false, true ],
  'Source-backed':   [true,  false, false, false, true ],
  'MCP-native':      [true,  false, false, false, false],
  'User-controlled': [true,  false, false, true,  true ],
  'Open source':     [true,  false, false, true,  true ],
};
---

<section class="py-24 px-6 border-t border-border">
  <div class="max-w-5xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-extrabold tracking-tight mb-12 text-center text-text-primary">
      How Recalium compares
    </h2>

    <div class="overflow-x-auto">
      <table class="w-full text-sm border-collapse">
        <thead>
          <tr>
            <th class="text-left py-3 pr-6 text-text-muted font-medium w-40"></th>
            {cols.map(({ name, highlight }) => (
              <th class={`py-3 px-4 text-center font-semibold ${highlight ? 'text-indigo-light' : 'text-text-muted'}`}>
                {name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr class="border-t border-border">
              <td class="py-3 pr-6 text-text-secondary">{row}</td>
              {checks[row].map((yes, i) => (
                <td class={`py-3 px-4 text-center ${cols[i].highlight ? 'bg-surface/50' : ''}`}>
                  {yes
                    ? <span class="text-green-400 font-bold" aria-label="Yes">✓</span>
                    : <span class="text-text-muted" aria-label="No">—</span>
                  }
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
</section>
```

- [ ] **Step 2: Write `CtaSection.astro`**

```astro
---
// website/src/components/CtaSection.astro
interface Props {
  heading?: string;
  primary?: { label: string; href: string };
  secondary?: { label: string; href: string };
}

const {
  heading = 'Ready to own your AI memory?',
  primary = { label: 'Get Started', href: '/docs' },
  secondary = { label: 'Star on GitHub', href: 'https://github.com/recalium/recalium' },
} = Astro.props;
---

<section class="py-24 px-6 border-t border-border text-center">
  <div class="max-w-xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-extrabold tracking-tight mb-8 text-text-primary">
      {heading}
    </h2>
    <div class="flex gap-3 justify-center flex-wrap">
      <a
        href={primary.href}
        class="bg-accent text-white font-semibold rounded-full px-6 py-3 text-sm hover:bg-indigo-500 transition-colors"
      >
        {primary.label}
      </a>
      <a
        href={secondary.href}
        target={secondary.href.startsWith('http') ? '_blank' : undefined}
        rel={secondary.href.startsWith('http') ? 'noopener noreferrer' : undefined}
        class="border border-border text-text-muted rounded-full px-6 py-3 text-sm hover:text-text-secondary hover:border-text-muted transition-colors"
      >
        {secondary.label}
      </a>
    </div>
  </div>
</section>
```

- [ ] **Step 3: Complete `index.astro`**

```astro
---
import BaseLayout from '@layouts/BaseLayout.astro';
import HeroSection from '@components/HeroSection.astro';
import ProblemSection from '@components/ProblemSection.astro';
import HowItWorksSection from '@components/HowItWorksSection.astro';
import DifferentiatorsSection from '@components/DifferentiatorsSection.astro';
import ComparisonTable from '@components/ComparisonTable.astro';
import CtaSection from '@components/CtaSection.astro';
---
<BaseLayout
  title="Recalium — Your AI Memory, Portable and Private"
  description="Recalium is a local-first memory layer that works across all your AI tools. Portable, private, and open source."
>
  <HeroSection />
  <ProblemSection />
  <HowItWorksSection />
  <DifferentiatorsSection />
  <ComparisonTable />
  <CtaSection />
</BaseLayout>
```

- [ ] **Step 4: Verify and commit**

```bash
cd website && pnpm dev
```

Verify the comparison table is readable on mobile (horizontal scroll). Then:

```bash
git add website/src/
git commit -m "feat: complete home page with comparison table and CTA"
```

---

## Task 7: SVG diagrams for Features page

**Files:**
- Create: `website/src/components/diagrams/McpFlow.astro`
- Create: `website/src/components/diagrams/FactsReview.astro`
- Create: `website/src/components/diagrams/SensitivityGate.astro`

These are inline SVG components — no external files, no rasterisation needed.

- [ ] **Step 1: Write `McpFlow.astro`** — Agent → MCP → Recalium flow

```astro
---
// website/src/components/diagrams/McpFlow.astro
---
<figure class="bg-[#040810] border border-border rounded-[6px] p-6" aria-label="MCP retrieval flow diagram">
  <svg viewBox="0 0 420 80" xmlns="http://www.w3.org/2000/svg" class="w-full" role="img" aria-hidden="true">
    <!-- Nodes -->
    <rect x="0" y="20" width="90" height="36" rx="6" fill="#0d1520" stroke="#1a2640" stroke-width="1"/>
    <text x="45" y="43" text-anchor="middle" font-family="Inter,sans-serif" font-size="11" fill="#94a3b8">Agent</text>

    <rect x="165" y="20" width="90" height="36" rx="6" fill="#0d1520" stroke="#6366f1" stroke-width="1"/>
    <text x="210" y="43" text-anchor="middle" font-family="Inter,sans-serif" font-size="11" fill="#818cf8">MCP Server</text>

    <rect x="330" y="20" width="90" height="36" rx="6" fill="#0d1520" stroke="#1a2640" stroke-width="1"/>
    <text x="375" y="43" text-anchor="middle" font-family="Inter,sans-serif" font-size="11" fill="#94a3b8">Recalium</text>

    <!-- Forward arrows -->
    <line x1="92" y1="38" x2="163" y2="38" stroke="#334155" stroke-width="1" marker-end="url(#arr)"/>
    <line x1="257" y1="38" x2="328" y2="38" stroke="#334155" stroke-width="1" marker-end="url(#arr)"/>

    <!-- Return arrow -->
    <path d="M 328 44 Q 210 72 92 44" stroke="#22d3ee" stroke-width="1" fill="none" stroke-dasharray="4 3" marker-end="url(#arr-c)"/>
    <text x="210" y="76" text-anchor="middle" font-family="Inter,sans-serif" font-size="9" fill="#22d3ee">context returned</text>

    <defs>
      <marker id="arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
        <path d="M0,0 L6,3 L0,6 Z" fill="#334155"/>
      </marker>
      <marker id="arr-c" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
        <path d="M0,0 L6,3 L0,6 Z" fill="#22d3ee"/>
      </marker>
    </defs>
  </svg>
</figure>
```

- [ ] **Step 2: Write `FactsReview.astro`** — Facts UI wireframe

```astro
---
// website/src/components/diagrams/FactsReview.astro
---
<figure class="bg-[#040810] border border-border rounded-[6px] p-4 font-mono text-xs" aria-label="Facts review UI mockup">
  <div class="border border-border rounded mb-2 overflow-hidden">
    <div class="bg-surface px-3 py-2 text-[#475569] border-b border-border flex justify-between">
      <span>Facts</span>
      <span class="text-[#6366f1]">1,247 total</span>
    </div>
    <div class="divide-y divide-border">
      <div class="px-3 py-2">
        <p class="text-[#94a3b8]">Prefers TypeScript over JavaScript for new projects</p>
        <p class="text-[#334155] mt-1">source: <span class="text-[#22d3ee]">chatgpt-export/msg_291</span> · confidence: <span class="text-green-400">high</span></p>
      </div>
      <div class="px-3 py-2 bg-[#0d1520]">
        <p class="text-[#94a3b8]">Uses Tailwind CSS for styling</p>
        <p class="text-[#334155] mt-1">source: <span class="text-[#22d3ee]">claude-export/conv_18</span> · confidence: <span class="text-green-400">high</span></p>
        <div class="mt-2 border-l-2 border-[#6366f1] pl-2 text-[#475569]">
          "I usually reach for Tailwind — it keeps everything colocated..."
        </div>
      </div>
    </div>
  </div>
  <p class="text-[#334155] text-center">↑ source span highlighted on hover</p>
</figure>
```

- [ ] **Step 3: Write `SensitivityGate.astro`** — Sensitivity gate flow

```astro
---
// website/src/components/diagrams/SensitivityGate.astro
---
<figure class="bg-[#040810] border border-border rounded-[6px] p-6" aria-label="Sensitivity gate decision flow diagram">
  <svg viewBox="0 0 320 160" xmlns="http://www.w3.org/2000/svg" class="w-full" role="img" aria-hidden="true">
    <!-- Input -->
    <rect x="110" y="4" width="100" height="30" rx="5" fill="#0d1520" stroke="#1a2640"/>
    <text x="160" y="24" text-anchor="middle" font-family="Inter,sans-serif" font-size="10" fill="#94a3b8">Incoming fact</text>

    <!-- Arrow down -->
    <line x1="160" y1="35" x2="160" y2="55" stroke="#334155" stroke-width="1" marker-end="url(#a2)"/>

    <!-- Decision diamond -->
    <polygon points="160,56 220,86 160,116 100,86" fill="#0d1520" stroke="#6366f1" stroke-width="1"/>
    <text x="160" y="82" text-anchor="middle" font-family="Inter,sans-serif" font-size="9" fill="#818cf8">Sensitivity</text>
    <text x="160" y="94" text-anchor="middle" font-family="Inter,sans-serif" font-size="9" fill="#818cf8">gate</text>

    <!-- Allow path -->
    <line x1="220" y1="86" x2="270" y2="86" stroke="#4ade80" stroke-width="1" marker-end="url(#a-g)"/>
    <rect x="272" y="72" width="44" height="28" rx="5" fill="#0d1520" stroke="#4ade80"/>
    <text x="294" y="90" text-anchor="middle" font-family="Inter,sans-serif" font-size="9" fill="#4ade80">Allow</text>
    <text x="248" y="80" text-anchor="middle" font-family="Inter,sans-serif" font-size="8" fill="#334155">safe</text>

    <!-- Block path -->
    <line x1="100" y1="86" x2="50" y2="86" stroke="#ef4444" stroke-width="1" marker-end="url(#a-r)"/>
    <rect x="4" y="72" width="44" height="28" rx="5" fill="#0d1520" stroke="#ef4444"/>
    <text x="26" y="90" text-anchor="middle" font-family="Inter,sans-serif" font-size="9" fill="#ef4444">Block</text>
    <text x="72" y="80" text-anchor="middle" font-family="Inter,sans-serif" font-size="8" fill="#334155">sensitive</text>

    <!-- Audit trail note -->
    <text x="160" y="148" text-anchor="middle" font-family="Inter,sans-serif" font-size="9" fill="#334155">all decisions logged to audit trail</text>

    <defs>
      <marker id="a2" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#334155"/></marker>
      <marker id="a-g" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#4ade80"/></marker>
      <marker id="a-r" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#ef4444"/></marker>
    </defs>
  </svg>
</figure>
```

- [ ] **Step 4: Commit**

```bash
git add website/src/components/diagrams/
git commit -m "feat: add SVG diagram components for features page"
```

---

## Task 8: Features page

**Files:**
- Create: `website/src/components/FeatureRow.astro`
- Create: `website/src/pages/features.astro`

- [ ] **Step 1: Write `FeatureRow.astro`**

```astro
---
// website/src/components/FeatureRow.astro
interface Props {
  number: string;
  title: string;
  description: string;
  reverse?: boolean;
}
const { number, title, description, reverse = false } = Astro.props;
---

<div class={`flex flex-col ${reverse ? 'md:flex-row-reverse' : 'md:flex-row'} gap-12 md:gap-20 items-center py-16 border-t border-border`}>
  <div class="flex-1">
    <span class="text-xs font-semibold tracking-widest text-accent mb-3 block">{number}</span>
    <h3 class="text-2xl font-extrabold tracking-tight text-text-primary mb-4">{title}</h3>
    <p class="text-text-muted leading-relaxed">{description}</p>
  </div>
  <div class="flex-1 w-full">
    <slot />
  </div>
</div>
```

- [ ] **Step 2: Write `features.astro`**

```astro
---
// website/src/pages/features.astro
import BaseLayout from '@layouts/BaseLayout.astro';
import FeatureRow from '@components/FeatureRow.astro';
import CtaSection from '@components/CtaSection.astro';
import McpFlow from '@components/diagrams/McpFlow.astro';
import FactsReview from '@components/diagrams/FactsReview.astro';
import SensitivityGate from '@components/diagrams/SensitivityGate.astro';
---

<BaseLayout
  title="Recalium — Features"
  description="Zero-friction ingestion, intelligent extraction, hybrid search, MCP-native retrieval, fact curation, and privacy by default."
>
  <div class="pt-28 pb-0 px-6 text-center">
    <div class="max-w-3xl mx-auto">
      <h1 class="text-4xl md:text-5xl font-extrabold tracking-tight text-text-primary mb-4">
        Everything you need to own<br class="hidden md:block" /> your AI memory
      </h1>
    </div>
  </div>

  <div class="max-w-5xl mx-auto px-6">

    <FeatureRow number="01" title="Zero-friction ingestion" description="Paste, upload, watched folder, or MCP ingest. All paths feed one durable archive with full provenance tracking.">
      <figure class="bg-[#040810] border border-border rounded-[6px] p-4 font-mono text-xs leading-relaxed" aria-label="MCP ingest code example">
        <div class="text-[#475569] mb-2">// ingest via MCP</div>
        <div><span class="text-[#818cf8]">ingest</span>({</div>
        <div>&nbsp;&nbsp;source: <span class="text-[#a78bfa]">"chatgpt-export.zip"</span>,</div>
        <div>&nbsp;&nbsp;metadata: {`{`}</div>
        <div>&nbsp;&nbsp;&nbsp;&nbsp;provider: <span class="text-[#a78bfa]">"openai"</span>,</div>
        <div>&nbsp;&nbsp;&nbsp;&nbsp;imported_at: <span class="text-[#f59e0b]">Date.now()</span></div>
        <div>&nbsp;&nbsp;{`}`}</div>
        <div>})</div>
        <div class="mt-2 text-green-400">// ✓ 1,247 memories archived</div>
      </figure>
    </FeatureRow>

    <FeatureRow number="02" title="Intelligent extraction" description="Facts, summaries, and embeddings with source spans and confidence tiers. Bring your own API key — your model, your bill." reverse>
      <figure class="bg-[#040810] border border-border rounded-[6px] p-4 font-mono text-xs leading-relaxed" aria-label="Extracted fact JSON example">
        <div class="text-[#475569] mb-2">// extracted fact</div>
        <div>{`{`}</div>
        <div>&nbsp;&nbsp;<span class="text-[#22d3ee]">fact</span>: <span class="text-[#a78bfa]">"Prefers TypeScript"</span>,</div>
        <div>&nbsp;&nbsp;<span class="text-[#22d3ee]">source_span</span>: <span class="text-[#a78bfa]">"msg_291"</span>,</div>
        <div>&nbsp;&nbsp;<span class="text-[#22d3ee]">confidence_tier</span>: <span class="text-[#a78bfa]">"high"</span>,</div>
        <div>&nbsp;&nbsp;<span class="text-[#22d3ee]">derivation_method</span>: <span class="text-[#a78bfa]">"llm_extract"</span></div>
        <div>{`}`}</div>
      </figure>
    </FeatureRow>

    <FeatureRow number="03" title="Hybrid search & retrieval" description="Keyword, semantic, or hybrid search with Reciprocal Rank Fusion. Context-budgeted retrieval keeps responses within token limits, with source attribution on every result.">
      <figure class="bg-[#040810] border border-border rounded-[6px] p-4 font-mono text-xs leading-relaxed" aria-label="Context assembly response JSON example">
        <div class="text-[#475569] mb-2">// context assembly response</div>
        <div>{`{`}</div>
        <div>&nbsp;&nbsp;<span class="text-[#22d3ee]">query</span>: <span class="text-[#a78bfa]">"typescript patterns"</span>,</div>
        <div>&nbsp;&nbsp;<span class="text-[#22d3ee]">items</span>: [ <span class="text-[#475569]">/* 8 results */</span> ],</div>
        <div>&nbsp;&nbsp;<span class="text-[#22d3ee]">budget_used</span>: <span class="text-[#f59e0b]">2841</span>,</div>
        <div>&nbsp;&nbsp;<span class="text-[#22d3ee]">provenance</span>: [ <span class="text-[#475569]">/* sources */</span> ]</div>
        <div>{`}`}</div>
      </figure>
    </FeatureRow>

    <FeatureRow number="04" title="MCP-native retrieval" description="Agents and tools retrieve memory without manual intervention. Works with Claude Code, Cursor, and any MCP-compatible client." reverse>
      <McpFlow />
    </FeatureRow>

    <FeatureRow number="05" title="Review & curate" description="Browse extracted facts, inspect provenance, promote to canonical memory, and resolve duplicates. Full visibility into what Recalium knows.">
      <FactsReview />
    </FeatureRow>

    <FeatureRow number="06" title="Private by default" description="Localhost-only by default. Sensitivity gate classifies content before indexing. Cascade deletion and a full audit trail." reverse>
      <SensitivityGate />
    </FeatureRow>

  </div>

  <CtaSection heading="Ready to own your AI memory?" />
</BaseLayout>
```

- [ ] **Step 3: Verify and commit**

```bash
cd website && pnpm dev
```

Open `/features`. Check all six rows render, alternating layout works, code snippets are readable, SVG diagrams display correctly.

```bash
git add website/src/
git commit -m "feat: add features page with alternating rows and diagrams"
```

---

## Task 9: Pricing page

**Files:**
- Create: `website/src/pages/pricing.astro`

- [ ] **Step 1: Write `pricing.astro`**

```astro
---
// website/src/pages/pricing.astro
import BaseLayout from '@layouts/BaseLayout.astro';
import CtaSection from '@components/CtaSection.astro';

const freeFeatures = [
  'Self-hosted via Docker',
  'Bring your own API keys (OpenAI / Anthropic)',
  'All ingestion paths (paste, upload, watched folder, MCP)',
  'Intelligent extraction and embeddings',
  'Hybrid search & retrieval',
  'MCP-native retrieval server',
  'Facts review and curation UI',
  'JSON export / import',
  'Full source code — MIT license',
];
---

<BaseLayout
  title="Recalium — Pricing"
  description="Recalium is free and open source forever. Self-host with Docker and bring your own API keys. A managed processing tier is coming soon."
>
  <div class="pt-28 pb-16 px-6">
    <div class="max-w-4xl mx-auto text-center mb-16">
      <h1 class="text-4xl md:text-5xl font-extrabold tracking-tight text-text-primary mb-4">
        Simple, honest pricing
      </h1>
      <p class="text-text-muted text-lg">Free forever. No surprises.</p>
    </div>

    <div class="max-w-3xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6 mb-16">

      <!-- Free tier -->
      <div class="bg-surface border border-accent rounded-card p-8">
        <div class="mb-6">
          <p class="text-xs font-semibold tracking-widest text-accent mb-2">FREE (BYOK)</p>
          <div class="text-4xl font-extrabold text-text-primary">$0</div>
          <p class="text-text-muted text-sm mt-1">forever</p>
        </div>
        <ul class="space-y-3 mb-8">
          {freeFeatures.map((f) => (
            <li class="flex items-start gap-2 text-sm text-text-secondary">
              <span class="text-green-400 mt-0.5 shrink-0">✓</span>
              {f}
            </li>
          ))}
        </ul>
        <a
          href="/docs"
          class="block text-center bg-accent text-white font-semibold rounded-full px-6 py-3 text-sm hover:bg-indigo-500 transition-colors"
        >
          Get Started Free
        </a>
      </div>

      <!-- Managed tier -->
      <div class="bg-surface border border-border rounded-card p-8 flex flex-col">
        <div class="mb-6">
          <div class="flex items-center gap-2 mb-2">
            <p class="text-xs font-semibold tracking-widest text-text-muted">MANAGED PROCESSING</p>
            <span class="text-xs bg-surface border border-border rounded-full px-2 py-0.5 text-text-muted">Coming soon</span>
          </div>
          <div class="text-4xl font-extrabold text-text-primary">TBD</div>
          <p class="text-text-muted text-sm mt-1">self-hosted + managed keys</p>
        </div>
        <ul class="space-y-3 mb-8 flex-1">
          <li class="flex items-start gap-2 text-sm text-text-secondary">
            <span class="text-green-400 mt-0.5 shrink-0">✓</span>
            Everything in Free
          </li>
          <li class="flex items-start gap-2 text-sm text-text-secondary">
            <span class="text-green-400 mt-0.5 shrink-0">✓</span>
            Recalium-provided API keys — no key management
          </li>
          <li class="flex items-start gap-2 text-sm text-text-muted">
            <span class="text-text-muted mt-0.5 shrink-0">◦</span>
            Cloud sync (roadmap)
          </li>
          <li class="flex items-start gap-2 text-sm text-text-muted">
            <span class="text-text-muted mt-0.5 shrink-0">◦</span>
            Team features (roadmap)
          </li>
        </ul>
        <button
          disabled
          class="block w-full text-center border border-border text-text-muted rounded-full px-6 py-3 text-sm cursor-not-allowed opacity-60"
        >
          Notify me
        </button>
      </div>

    </div>

    <div class="max-w-2xl mx-auto text-center">
      <p class="text-text-muted text-sm leading-relaxed">
        Recalium is open source and fully functional at zero cost. Bring your own API keys
        for OpenAI or Anthropic. The managed processing tier eliminates key management —
        same product, less setup. Cloud sync and team features are on the roadmap.
      </p>
    </div>
  </div>

  <CtaSection
    heading="Start for free today"
    primary={{ label: 'Get Started Free', href: '/docs' }}
    secondary={{ label: 'Star on GitHub', href: 'https://github.com/recalium/recalium' }}
  />
</BaseLayout>
```

- [ ] **Step 2: Verify and commit**

```bash
cd website && pnpm dev
```

Open `/pricing`. Check two-column layout, free tier highlighted with accent border, coming-soon badge.

```bash
git add website/src/pages/pricing.astro
git commit -m "feat: add pricing page"
```

---

## Task 10: Docs page

**Files:**
- Create: `website/src/layouts/DocsLayout.astro`
- Create: `website/src/pages/docs.mdx`

- [ ] **Step 1: Write `DocsLayout.astro`**

```astro
---
// website/src/layouts/DocsLayout.astro
import BaseLayout from './BaseLayout.astro';

interface Props {
  title: string;
  description: string;
}
const { title, description } = Astro.props;

const sections = [
  { id: 'prerequisites', label: 'Prerequisites' },
  { id: 'install', label: 'Install' },
  { id: 'first-run', label: 'First Run' },
  { id: 'mcp-setup', label: 'MCP Setup' },
  { id: 'configuration', label: 'Configuration' },
];
---

<BaseLayout {title} {description}>
  <div class="pt-24 max-w-6xl mx-auto px-6 flex gap-12">

    <!-- Sidebar (desktop) -->
    <aside class="hidden lg:block w-52 shrink-0 pt-8">
      <nav class="sticky top-24" aria-label="Docs navigation">
        <p class="text-xs font-semibold tracking-widest text-text-muted mb-4 uppercase">Getting Started</p>
        <ul class="space-y-2 list-none">
          {sections.map(({ id, label }) => (
            <li>
              <a
                href={`#${id}`}
                class="text-sm text-text-muted hover:text-text-secondary transition-colors block py-1"
              >
                {label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </aside>

    <!-- Main content -->
    <article class="flex-1 min-w-0 py-8 pb-24 prose prose-invert prose-sm max-w-none
      prose-headings:font-extrabold prose-headings:tracking-tight
      prose-h1:text-3xl prose-h2:text-xl prose-h2:mt-12 prose-h2:border-t prose-h2:border-border prose-h2:pt-8
      prose-code:bg-[#040810] prose-code:text-[#22d3ee] prose-code:rounded prose-code:px-1.5 prose-code:py-0.5
      prose-pre:bg-[#040810] prose-pre:border prose-pre:border-border
      prose-a:text-indigo-light prose-a:no-underline hover:prose-a:underline
    ">
      <slot />
    </article>

  </div>
</BaseLayout>
```

- [ ] **Step 2: Write `docs.mdx`**

````mdx
---
# website/src/pages/docs.mdx
layout: ../layouts/DocsLayout.astro
title: "Recalium — Getting Started"
description: "Install Recalium, import your AI conversation history, and connect it to your AI tools via MCP in minutes."
---

# Getting Started

Recalium runs locally via Docker. This guide takes you from zero to your first memory-augmented AI interaction.

---

## Prerequisites {#prerequisites}

**Required:**
- [Docker Desktop](https://docs.docker.com/get-docker/) (or Docker Engine + Compose plugin on Linux)

**Optional but recommended:**
- An OpenAI or Anthropic API key — enables AI-powered extraction and semantic search. Keyword search and manual ingestion work without one.

---

## Install {#install}

Clone the repository and start the stack:

```bash
git clone https://github.com/recalium/recalium.git
cd recalium
docker compose up
```

Recalium starts on **http://localhost:8080**. The MCP server listens on **http://localhost:3000**.

On first run, a setup wizard walks you through initial configuration.

---

## First Run {#first-run}

**1. Configure your AI provider (optional)**

In the setup wizard, enter your OpenAI or Anthropic API key. Skip this step to use keyword search only.

**2. Import your conversation history**

Three import paths:
- **Paste** — paste raw text directly into the import UI
- **Upload** — upload a ChatGPT export ZIP or Claude export JSON
- **Watched folder** — drop files into `~/.recalium/inbox` and they're ingested automatically

**3. Run your first search**

Once import completes, try a keyword or semantic search from the search bar. Each result shows the source it came from.

---

## MCP Setup {#mcp-setup}

Configure Recalium as an MCP server in your AI client so it can retrieve memory automatically.

**Claude Code (`~/.claude/settings.json`):**

```json
{
  "mcpServers": {
    "recalium": {
      "url": "http://localhost:3000/mcp",
      "transport": "http"
    }
  }
}
```

**Cursor (`~/.cursor/mcp.json`):**

```json
{
  "servers": {
    "recalium": {
      "url": "http://localhost:3000/mcp"
    }
  }
}
```

After configuring, your AI client will automatically call Recalium for relevant context on each request.

---

## Configuration {#configuration}

Copy `.env.sample` to `.env` in the repo root and edit as needed:

| Variable | Default | Description |
|---|---|---|
| `RECALIUM_PORT` | `8080` | Web UI port |
| `MCP_PORT` | `3000` | MCP server port |
| `OPENAI_API_KEY` | — | OpenAI key for extraction and embeddings |
| `ANTHROPIC_API_KEY` | — | Anthropic key (alternative to OpenAI) |
| `RECALIUM_DATA_DIR` | `./data` | Where memory is stored on disk |
| `SENSITIVITY_GATE` | `true` | Enable/disable the sensitivity pre-classifier |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warn`, `error` |

Restart the stack after changing `.env`:

```bash
docker compose down && docker compose up
```
````

- [ ] **Step 3: Verify and commit**

```bash
cd website && pnpm dev
```

Open `/docs`. Check sidebar anchor links, prose styles, code blocks, and the configuration table.

```bash
git add website/src/layouts/DocsLayout.astro website/src/pages/docs.mdx
git commit -m "feat: add docs getting-started page"
```

---

## Task 11: 404 page

**Files:**
- Create: `website/src/pages/404.astro`

- [ ] **Step 1: Write `404.astro`**

```astro
---
// website/src/pages/404.astro
import BaseLayout from '@layouts/BaseLayout.astro';
---

<BaseLayout
  title="Recalium — Page Not Found"
  description="This page doesn't exist."
>
  <div class="min-h-screen flex flex-col items-center justify-center text-center px-6 pt-16">
    <p class="text-xs font-semibold tracking-widest text-accent mb-6 uppercase">404</p>
    <h1 class="text-4xl md:text-5xl font-extrabold tracking-tight text-text-primary mb-4">
      This page doesn't exist —<br class="hidden md:block" />
      <span class="gradient-text">but your AI memory can.</span>
    </h1>
    <p class="text-text-muted mb-10 max-w-sm">
      The page you're looking for has moved or never existed.
    </p>
    <a
      href="/"
      class="bg-accent text-white font-semibold rounded-full px-6 py-3 text-sm hover:bg-indigo-500 transition-colors"
    >
      Back to home
    </a>
  </div>
</BaseLayout>
```

- [ ] **Step 2: Verify and commit**

```bash
cd website && pnpm dev
```

Navigate to a non-existent path (e.g. `/does-not-exist`). Verify 404 page renders with gradient headline.

```bash
git add website/src/pages/404.astro
git commit -m "feat: add 404 page"
```

---

## Task 12: Accessibility and final QA

**No new files — verification pass only.**

- [ ] **Step 1: Run Astro type check**

```bash
cd website && pnpm check
```

Expected: no type errors.

- [ ] **Step 2: Run production build**

```bash
cd website && pnpm build
```

Expected: clean build, no warnings about missing assets.

- [ ] **Step 3: Manual accessibility checklist**

Open `pnpm preview` and verify on each page:
- Tab through the page — all interactive elements reachable in logical order
- Skip-to-content link appears on focus (Tab from address bar)
- All images and SVG diagrams have `alt` or `aria-label`
- Nav hamburger has `aria-label`, `aria-expanded`, `aria-controls`
- Comparison table has accessible `aria-label` on ✓ and — cells
- Color contrast: white text on `#06090f` and cards on `#0d1520` both pass

- [ ] **Step 4: Verify mobile layout**

In browser devtools, test at 375px (iPhone SE) and 768px (tablet):
- Nav collapses to hamburger at mobile
- All section grids stack to single column
- Comparison table has horizontal scroll on overflow
- Feature rows stack vertically (text above visual)
- Docs sidebar hides on mobile

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: accessibility and mobile layout adjustments"
```

---

## Task 13: Cloudflare Pages deployment config

**Files:**
- Create: `website/public/_headers` (optional cache/security headers)

- [ ] **Step 1: Add `_headers` for security and caching**

```
# website/public/_headers
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()

/assets/*
  Cache-Control: public, max-age=31536000, immutable
```

- [ ] **Step 2: Verify Cloudflare Pages settings (manual step)**

In the Cloudflare Pages dashboard, confirm:
- Repository: `recalium/recalium`
- Branch: `main`
- Build command: `pnpm build`
- Build output directory: `dist`
- Root directory: `website`

- [ ] **Step 3: Final build verification**

```bash
cd website && pnpm build && pnpm preview
```

Open `http://localhost:4321` and walk through every page one final time.

- [ ] **Step 4: Commit**

```bash
git add website/public/_headers
git commit -m "chore: add Cloudflare Pages security headers"
```

---

## Done

All tasks complete when:
- `pnpm build` succeeds cleanly from `website/`
- All five pages render correctly at mobile and desktop widths
- No accessibility violations on keyboard navigation
- Cloudflare Pages deploys successfully on push to `main`
