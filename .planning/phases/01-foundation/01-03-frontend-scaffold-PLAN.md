---
wave: 1
depends_on: []
requirements_addressed: [WEBUI-01, WEBUI-04]
files_modified:
  - frontend/package.json
  - frontend/vite.config.ts
  - frontend/index.html
  - frontend/src/main.tsx
  - frontend/src/App.tsx
  - frontend/src/components/Layout.tsx
  - frontend/src/components/NavSidebar.tsx
  - frontend/src/pages/IngestPage.tsx
  - frontend/src/pages/ArchivePage.tsx
  - frontend/src/pages/SettingsPage.tsx
  - frontend/src/lib/api.ts
  - frontend/tailwind.css
autonomous: true
---

<objective>
Initialize the React 19 + Vite 8 + Tailwind v4 + shadcn/ui 2.x frontend with a left-nav shell, route stubs for all pages, and a typed API client stub. After this plan, `pnpm dev` shows the app with a working left-nav, navigable routes (Ingest, Archive, Settings), and disabled stubs for future pages (Facts, Canonical, Search, Review Queue, Audit).

Purpose: Establishes the UI shell (WEBUI-01) against which Ingest and Archive feature plans wire their pages. React 19 + Tailwind v4 must be used — not React 18.
Output: frontend/ project directory with all scaffold files.
</objective>

<tasks>

<task id="1" name="Initialize Vite + React 19 + Tailwind v4 project with pnpm">
  <read_first>
    - .planning/research/STACK.md (React 19.2.4, Vite 8.0.1, pnpm 10.32.1, Node >=20.19.0, Tailwind v4 CSS-first config)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-03 frontend structure, D-20 Chrome/Chromium only)
  </read_first>
  <action>
Create `frontend/package.json` with these exact dependency versions. Do NOT use `pnpm create vite` interactively — write the package.json directly:

```json
{
  "name": "recalium-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "lint": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^19.2.4",
    "react-dom": "^19.2.4",
    "react-router-dom": "^7.0.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^0.511.0",
    "tailwind-merge": "^2.6.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.4.1",
    "typescript": "^5.7.0",
    "vite": "^8.0.1",
    "@tailwindcss/vite": "^4.1.4",
    "tailwindcss": "^4.1.4",
    "vitest": "^3.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.0.0",
    "@vitest/ui": "^3.0.0"
  }
}
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

Create `frontend/vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(), // Tailwind v4: CSS-first config via @tailwindcss/vite plugin
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // Proxy API calls to FastAPI backend during development
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
    port: 5173,
  },
  build: {
    outDir: "dist",
    // Output goes to dist/ which is copied into backend/app/static/ in Docker build
  },
});
```

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <!-- Chrome/Chromium only in v1 (WEBUI-04) -->
    <title>Recalium</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `frontend/tailwind.css` (Tailwind v4 CSS-first configuration — NO tailwind.config.js):

```css
@import "tailwindcss";

/* Recalium design tokens */
@theme {
  --color-background: hsl(0 0% 100%);
  --color-foreground: hsl(222.2 84% 4.9%);
  --color-muted: hsl(210 40% 96.1%);
  --color-muted-foreground: hsl(215.4 16.3% 46.9%);
  --color-border: hsl(214.3 31.8% 91.4%);
  --color-primary: hsl(222.2 47.4% 11.2%);
  --color-primary-foreground: hsl(210 40% 98%);
  --color-sidebar-bg: hsl(222.2 84% 4.9%);
  --color-sidebar-fg: hsl(210 40% 98%);
  --color-sidebar-muted: hsl(217 32.6% 17.5%);
}
```
  </action>
  <acceptance_criteria>
    - `grep -n "\"react\": \"\\^19" frontend/package.json` returns 1 line
    - `grep -n "\"vite\": \"\\^8" frontend/package.json` returns 1 line
    - `grep -n "@tailwindcss/vite" frontend/package.json` returns 1 line (NOT tailwind.config.js approach)
    - `grep -n "\"tailwindcss\": \"\\^4" frontend/package.json` returns 1 line
    - `grep -n "tailwindcss()" frontend/vite.config.ts` returns 1 line
    - `grep -n "proxy.*\/api" frontend/vite.config.ts` returns 1 line
    - `grep -n "@import \"tailwindcss\"" frontend/tailwind.css` returns 1 line
    - `grep -n "tailwind.config" frontend/` returns 0 lines (no config file — v4 CSS-first)
  </acceptance_criteria>
</task>

<task id="2" name="Create shadcn/ui utils and shared UI primitives">
  <read_first>
    - .planning/research/STACK.md (shadcn/ui 2.x — copied components, not a package)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-19 — left-nav items)
  </read_first>
  <action>
Create `frontend/src/lib/utils.ts` (shadcn/ui standard utility):

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

Create `frontend/src/components/ui/button.tsx` (shadcn/ui Button component — copied not imported):

```typescript
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

Create `frontend/src/components/ui/badge.tsx`:

```typescript
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-destructive text-destructive-foreground",
        outline: "text-foreground",
        success: "border-transparent bg-green-100 text-green-800",
        warning: "border-transparent bg-yellow-100 text-yellow-800",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
```

Create `frontend/src/components/ui/toast.tsx` (minimal toast for ingest confirmation):

```typescript
import * as React from "react";
import { cn } from "@/lib/utils";

interface ToastProps {
  message: string;
  type?: "success" | "error" | "info";
  onDismiss: () => void;
}

export function Toast({ message, type = "info", onDismiss }: ToastProps) {
  React.useEffect(() => {
    const timer = setTimeout(onDismiss, 4000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "fixed bottom-4 right-4 z-50 rounded-lg px-4 py-3 text-sm font-medium shadow-lg",
        type === "success" && "bg-green-600 text-white",
        type === "error" && "bg-red-600 text-white",
        type === "info" && "bg-gray-800 text-white"
      )}
    >
      {message}
    </div>
  );
}
```
  </action>
  <acceptance_criteria>
    - File `frontend/src/lib/utils.ts` exists
    - `grep -n "twMerge" frontend/src/lib/utils.ts` returns 1 line
    - File `frontend/src/components/ui/button.tsx` exists
    - `grep -n "cva" frontend/src/components/ui/button.tsx` returns 1 line
    - File `frontend/src/components/ui/badge.tsx` exists
    - File `frontend/src/components/ui/toast.tsx` exists
    - `grep -n "aria-live" frontend/src/components/ui/toast.tsx` returns 1 line (accessibility)
  </acceptance_criteria>
</task>

<task id="3" name="Create left-nav Layout, all page stubs, API client, and main.tsx">
  <read_first>
    - .planning/phases/01-foundation/01-CONTEXT.md (D-15 Ingest tabs, D-16 toast+navigate, D-17 archive card, D-18 formats, D-19 left-nav order, D-21 no auth)
  </read_first>
  <action>
Create `frontend/src/components/NavSidebar.tsx` (left-nav per D-19 — 8 items in exact order):

```typescript
import { NavLink } from "react-router-dom";
import {
  Upload,
  Archive,
  Lightbulb,
  BookOpen,
  Search,
  ClipboardList,
  FileAudit,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Note: FileAudit may not exist in lucide-react; use FileText as fallback

const navItems = [
  { to: "/ingest", label: "Ingest", icon: Upload, disabled: false },
  { to: "/archive", label: "Archive", icon: Archive, disabled: false },
  { to: "/facts", label: "Facts", icon: Lightbulb, disabled: true, phase: "2" },
  { to: "/canonical", label: "Canonical", icon: BookOpen, disabled: true, phase: "2" },
  { to: "/search", label: "Search", icon: Search, disabled: true, phase: "2" },
  { to: "/review-queue", label: "Review Queue", icon: ClipboardList, disabled: true, phase: "2" },
  { to: "/audit", label: "Audit", icon: Archive, disabled: true, phase: "3" },
  { to: "/settings", label: "Settings", icon: Settings, disabled: false },
] as const;

export function NavSidebar() {
  return (
    <nav
      aria-label="Main navigation"
      className="flex h-full w-56 flex-col bg-[--color-sidebar-bg] text-[--color-sidebar-fg] py-4"
    >
      <div className="px-4 pb-6">
        <span className="text-lg font-bold tracking-tight">Recalium</span>
      </div>
      <ul className="flex flex-1 flex-col gap-1 px-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          if (item.disabled) {
            return (
              <li key={item.to}>
                <span
                  title={`Available in a future update (Phase ${item.phase})`}
                  className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium opacity-40 cursor-not-allowed select-none"
                  aria-disabled="true"
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </span>
              </li>
            );
          }
          return (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-[--color-sidebar-muted] text-white"
                      : "hover:bg-[--color-sidebar-muted] hover:text-white text-[--color-sidebar-fg]/80"
                  )
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
```

Create `frontend/src/components/Layout.tsx`:

```typescript
import { Outlet } from "react-router-dom";
import { NavSidebar } from "./NavSidebar";

export function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <NavSidebar />
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
```

Create `frontend/src/lib/api.ts` (typed API client — all calls go through this, never fetch() directly in components):

```typescript
/**
 * Typed API client for Recalium backend.
 * All fetch() calls go through this module — never import fetch directly in pages.
 */

const BASE_URL = "/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface IngestResponse {
  status: "accepted";
  item_count: number;
  archive_ids: string[];
}

export interface ArchiveItem {
  id: string;
  source_type: string;
  source_name: string | null;
  conversation_count: number;
  ingested_at: string; // ISO 8601
  status_badge: "Ingested"; // Phase 1 only; Phase 2 adds "Processing" / "Done" / "Failed"
}

export interface ArchiveListResponse {
  items: ArchiveItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface SettingsKeyStatus {
  configured: boolean;
  fingerprint: string | null; // last 4 chars, or null if not set
  validation_status: "valid" | "invalid" | "insufficient_permissions" | "unchecked" | null;
  validated_at: string | null;
}

export interface SettingsResponse {
  openai: SettingsKeyStatus;
  anthropic: SettingsKeyStatus;
  ollama: SettingsKeyStatus & { base_url: string | null };
}

export interface ValidateKeyRequest {
  provider: "openai" | "anthropic" | "ollama";
  api_key: string;
  base_url?: string; // Ollama only
}

export interface ValidateKeyResponse {
  provider: "openai" | "anthropic" | "ollama";
  status: "valid" | "invalid" | "insufficient_permissions";
  message: string;
}

// ── Error handling ─────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(`API error ${status}: ${detail}`);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
  return response.json() as Promise<T>;
}

// ── Ingest ─────────────────────────────────────────────────────────────────

export async function ingestText(content: string, sourceName?: string): Promise<IngestResponse> {
  return request<IngestResponse>("/ingest", {
    method: "POST",
    body: JSON.stringify({ mode: "text", content, source_name: sourceName }),
  });
}

export async function ingestFile(file: File): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<IngestResponse>("/ingest/file", {
    method: "POST",
    headers: {}, // Don't set Content-Type — let browser set multipart boundary
    body: formData,
  });
}

// ── Archive ────────────────────────────────────────────────────────────────

export async function listArchive(
  params: { offset?: number; limit?: number; q?: string } = {}
): Promise<ArchiveListResponse> {
  const qs = new URLSearchParams();
  if (params.offset !== undefined) qs.set("offset", String(params.offset));
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  if (params.q) qs.set("q", params.q);
  return request<ArchiveListResponse>(`/archive?${qs}`);
}

// ── Settings / BYOK ────────────────────────────────────────────────────────

export async function getSettings(): Promise<SettingsResponse> {
  return request<SettingsResponse>("/settings/keys");
}

export async function validateKey(data: ValidateKeyRequest): Promise<ValidateKeyResponse> {
  return request<ValidateKeyResponse>("/settings/keys/validate", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
```

Create page stub `frontend/src/pages/IngestPage.tsx` (placeholder — wired in Plan 01-05):

```typescript
// IngestPage — implementation in Plan 01-05 (Ingest API + parsers)
export function IngestPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Ingest</h1>
      <p className="text-muted-foreground">Ingest form coming in Plan 01-05.</p>
    </div>
  );
}
```

Create page stub `frontend/src/pages/ArchivePage.tsx`:

```typescript
// ArchivePage — implementation in Plan 01-06 (Archive API + UI)
export function ArchivePage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Archive</h1>
      <p className="text-muted-foreground">Archive list coming in Plan 01-06.</p>
    </div>
  );
}
```

Create page stub `frontend/src/pages/SettingsPage.tsx`:

```typescript
// SettingsPage — implementation in Plan 01-07 (BYOK settings API + UI)
export function SettingsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Settings</h1>
      <p className="text-muted-foreground">BYOK settings coming in Plan 01-07.</p>
    </div>
  );
}
```

Create disabled page stub `frontend/src/pages/DisabledPage.tsx`:

```typescript
interface DisabledPageProps {
  title: string;
  phase: string;
}
export function DisabledPage({ title, phase }: DisabledPageProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <h1 className="text-2xl font-bold mb-2">{title}</h1>
      <p className="text-muted-foreground">Available in Phase {phase}.</p>
    </div>
  );
}
```

Create `frontend/src/App.tsx` (router with all routes):

```typescript
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { IngestPage } from "@/pages/IngestPage";
import { ArchivePage } from "@/pages/ArchivePage";
import { SettingsPage } from "@/pages/SettingsPage";
import { DisabledPage } from "@/pages/DisabledPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/ingest" replace />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/archive" element={<ArchivePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          {/* Phase 2+ routes — visible but disabled in nav */}
          <Route path="/facts" element={<DisabledPage title="Facts" phase="2" />} />
          <Route path="/canonical" element={<DisabledPage title="Canonical Memory" phase="2" />} />
          <Route path="/search" element={<DisabledPage title="Search" phase="2" />} />
          <Route path="/review-queue" element={<DisabledPage title="Review Queue" phase="2" />} />
          <Route path="/audit" element={<DisabledPage title="Audit" phase="3" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

Create `frontend/src/main.tsx`:

```typescript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./tailwind.css";
import { App } from "./App";

const root = document.getElementById("root");
if (!root) throw new Error("Root element #root not found");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```
  </action>
  <acceptance_criteria>
    - `grep -n "Ingest\|Archive\|Facts\|Canonical\|Search\|Review Queue\|Audit\|Settings" frontend/src/components/NavSidebar.tsx | wc -l` returns 8 (all 8 nav items)
    - `grep -n "disabled: true" frontend/src/components/NavSidebar.tsx | wc -l` returns 5 (Facts, Canonical, Search, Review Queue, Audit)
    - `grep -n "Available in a future update" frontend/src/components/NavSidebar.tsx` returns 1 line
    - `grep -n "aria-disabled=\"true\"" frontend/src/components/NavSidebar.tsx` returns 1 line
    - `grep -n "export.*ingestText\|export.*ingestFile\|export.*listArchive\|export.*getSettings\|export.*validateKey" frontend/src/lib/api.ts | wc -l` returns 5
    - `grep -n "ApiError" frontend/src/lib/api.ts` returns ≥ 2 lines (class def + throw)
    - `grep -n "react-router-dom" frontend/src/App.tsx` returns 1 line
    - `grep -n "Navigate to=\"/ingest\"" frontend/src/App.tsx` returns 1 line (redirect from root)
    - File `frontend/src/main.tsx` exists with `createRoot`
  </acceptance_criteria>
</task>

</tasks>

<verification>
From `frontend/` directory:

1. `node --version` — must be ≥ 20.19.0 (Vite 8 requirement)
2. `pnpm install` — must complete without errors
3. `pnpm run build` — must produce `dist/` directory
4. `pnpm dev` — opens on localhost:5173; navigating to `/ingest`, `/archive`, `/settings` must render page title headings; navigating to `/facts` must show "Available in Phase 2"
5. `grep "tailwind.config" frontend/` — returns 0 lines (v4 CSS-first, no config file)
6. Visual check in Chrome/Chromium: left-nav shows all 8 items; disabled items are visually grayed out; tooltip appears on hover
</verification>

<must_haves>
1. React 19 (not 18) is used. Verified: `grep "\"react\": \"\\^19" frontend/package.json` returns 1 line.
2. All 8 left-nav items are present in NavSidebar.tsx in exact order: Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, Settings. Disabled items (Facts, Canonical, Search, Review Queue, Audit) have `aria-disabled="true"` and tooltip text "Available in a future update". Verified: `grep "disabled: true" frontend/src/components/NavSidebar.tsx | wc -l` returns 5.
3. Tailwind v4 CSS-first config is used — no `tailwind.config.js` or `tailwind.config.ts` file exists. Verified: `find frontend -name "tailwind.config*"` returns 0 files.
</must_haves>
