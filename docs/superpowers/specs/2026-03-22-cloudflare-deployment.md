# Cloudflare Pages CI/CD Deployment — Design Spec

**Date:** 2026-03-22
**Scope:** Automate deployment of the Recalium website to Cloudflare Pages via GitHub Actions.

---

## Goal

Deploy the `website/` subdirectory (Astro static output) to Cloudflare Pages automatically:

- **PRs** get a branch preview deployment with a comment posting the preview URL.
- **Pushes to `main`** trigger a production deployment.

---

## Workflow Files

### 1. PR Preview — `.github/workflows/website-preview.yml`

**Trigger:** `pull_request` targeting `main`

**Permissions:**
- `pull-requests: write` — required to post the preview URL as a PR comment

**Permissions:**
- `contents: read` — required by `actions/checkout`
- `pull-requests: write` — required to post the preview URL as a PR comment

**Steps:**
1. Checkout repository
2. Set up pnpm v9 (pnpm setup action also configures Node.js; no separate Node setup step needed)
3. Install dependencies in `website/`
4. Run `pnpm build`
5. Deploy to Cloudflare Pages as a branch preview using `cloudflare/wrangler-action@v3` — capture the step output `deployment-url` via `id: deploy`
6. Post the preview URL as a PR comment using `actions/github-script`, reading `${{ steps.deploy.outputs.deployment-url }}`

**Wrangler action config:**
```yaml
- name: Deploy preview
  id: deploy
  uses: cloudflare/wrangler-action@v3
  with:
    apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
    command: pages deploy dist --project-name recalium
    workingDirectory: website
```

---

### 2. Production Deploy — `.github/workflows/website-deploy.yml`

**Trigger:** `push` to `main`

**Permissions:**
- `contents: read` — required by `actions/checkout`

**Steps:**
1. Checkout repository
2. Set up pnpm v9 (also configures Node.js)
3. Install dependencies in `website/`
4. Run `pnpm build`
5. Deploy to Cloudflare Pages production using `cloudflare/wrangler-action@v3`

**Wrangler action config:**
```yaml
uses: cloudflare/wrangler-action@v3
with:
  apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
  accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
  command: pages deploy dist --project-name recalium --branch main
  workingDirectory: website
```

Passing `--branch main` maps to the production alias in Cloudflare Pages.

---

## Secrets

Both secrets must be added as GitHub Actions repository secrets (Settings → Secrets and variables → Actions):

| Secret name | Description |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token with `Cloudflare Pages:Edit` permission |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID (found in the CF dashboard sidebar) |

---

## Key Configuration

| Parameter | Value |
|---|---|
| Cloudflare Pages project name | `recalium` |
| Build root directory | `website/` |
| Build command | `pnpm build` |
| Build output directory | `website/dist` (Astro default) |
| Production branch | `main` |
| pnpm version | `9` |
| Node.js version | `lts/*` — configured automatically by the pnpm setup action; no separate `setup-node` step needed |

---

## Manual Setup Steps (one-time, not automated)

### 1. Create the Cloudflare Pages project

In the Cloudflare dashboard:
- Go to **Workers & Pages → Create application → Pages → Connect to Git**
- Select the `recalium` repository
- Set the following build settings:
  - **Project name:** `recalium`
  - **Root directory:** `website`
  - **Build command:** `pnpm build`
  - **Build output directory:** `dist`
- Complete the setup (the initial build can be skipped or cancelled — CI will own deployments)

### 2. Generate a Cloudflare API token

- Go to **My Profile → API Tokens → Create Token**
- Use the **Edit Cloudflare Pages** template or create a custom token with the `Cloudflare Pages:Edit` permission scoped to your account
- Copy the token value immediately (it is shown only once)

### 3. Add GitHub Actions secrets

In the GitHub repository:
- Go to **Settings → Secrets and variables → Actions → New repository secret**
- Add `CLOUDFLARE_API_TOKEN` with the token from step 2
- Add `CLOUDFLARE_ACCOUNT_ID` with your Cloudflare account ID

---

## Out of Scope

The following are intentionally excluded from this automation and require manual action if needed:

- **Custom domain DNS setup** — configure in the Cloudflare Pages dashboard after deployment is working
- **Cloudflare Pages project creation** — one-time manual step documented above
- **Node.js version pinning** — `lts/*` is sufficient; pin explicitly only if a specific version becomes necessary
