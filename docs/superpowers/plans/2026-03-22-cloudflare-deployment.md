# Cloudflare Pages Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two GitHub Actions workflows to automate Cloudflare Pages deployments — preview deploys on PRs and production deploys on push to main.

**Architecture:** Two YAML workflow files in `.github/workflows/`. A shared pnpm install + build sequence, then Cloudflare Pages deploy via `cloudflare/wrangler-action@v3`. PR workflow additionally posts the preview URL as a comment.

**Tech Stack:** GitHub Actions, cloudflare/wrangler-action@v3, pnpm v10, Astro 5 static build.

---

## File Map

**Created from scratch:**

```
.github/
└── workflows/
    ├── website-preview.yml   # PR preview deploy + comment with preview URL
    └── website-deploy.yml    # Production deploy on push to main

website/
└── .env.sample               # Updated to document deployment secrets
```

**No existing files modified** except `website/.env.sample` (append deployment secret docs).

---

## Task 1: PR Preview Workflow

**Files:**
- Create: `.github/workflows/website-preview.yml`
- Modify: `website/.env.sample`

- [ ] **Step 1: Create the `.github/workflows/` directory structure**

```bash
mkdir -p .github/workflows
```

Expected: directory `.github/workflows/` exists in repo root.

- [ ] **Step 2: Write `.github/workflows/website-preview.yml`**

Create the file at `.github/workflows/website-preview.yml` with the following exact content:

```yaml
name: Website — Preview Deploy

on:
  pull_request:
    branches: [main]
    paths:
      - 'website/**'

permissions:
  contents: read
  pull-requests: write

jobs:
  deploy-preview:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up pnpm
        uses: pnpm/action-setup@v3
        with:
          version: 10

      - name: Install dependencies
        run: pnpm install
        working-directory: website

      - name: Build
        run: pnpm build
        working-directory: website

      - name: Deploy preview to Cloudflare Pages
        id: deploy
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy dist --project-name recalium
          workingDirectory: website

      - name: Post preview URL as PR comment
        uses: actions/github-script@v7
        env:
          PREVIEW_URL: ${{ steps.deploy.outputs.deployment-url }}
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Preview deployment\n\n✅ Deployed to: ${process.env.PREVIEW_URL}`
            })
```

> **Note on pnpm version:** The project's `package.json` declares `"packageManager": "pnpm@10.28.0"`. The `pnpm/action-setup@v3` action with `version: 10` installs pnpm v10 and also configures Node LTS — no separate `actions/setup-node` step is required. Do not use `version: 9` here; it would fail because the lockfile was generated with pnpm v10.

> **Note on `PREVIEW_URL`:** The `steps.deploy.outputs.deployment-url` expression cannot be used directly inside a `with.script` JavaScript string without risk of YAML/JS escaping issues. Passing it via `env.PREVIEW_URL` and reading `process.env.PREVIEW_URL` in the script is the correct pattern.

- [ ] **Step 3: Update `website/.env.sample` to document deployment secrets**

Append the following block to the end of `website/.env.sample`:

```
# Deployment (set as GitHub Actions secrets, not locally)
# CLOUDFLARE_API_TOKEN=
# CLOUDFLARE_ACCOUNT_ID=
```

The resulting file should look like:

```
# website/.env.sample
# No environment variables required for the static site.
# Cloudflare Web Analytics token is injected via Cloudflare Pages dashboard.

# Deployment (set as GitHub Actions secrets, not locally)
# CLOUDFLARE_API_TOKEN=
# CLOUDFLARE_ACCOUNT_ID=
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/website-preview.yml website/.env.sample
git commit -m "ci: add PR preview deploy workflow"
```

Expected: commit succeeds, `git log --oneline -1` shows the new commit.

---

## Task 2: Production Deploy Workflow

**Files:**
- Create: `.github/workflows/website-deploy.yml`

- [ ] **Step 1: Write `.github/workflows/website-deploy.yml`**

Create the file at `.github/workflows/website-deploy.yml` with the following exact content:

```yaml
name: Website — Production Deploy

on:
  push:
    branches: [main]
    paths:
      - 'website/**'

permissions:
  contents: read

jobs:
  deploy-production:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up pnpm
        uses: pnpm/action-setup@v3
        with:
          version: 10

      - name: Install dependencies
        run: pnpm install
        working-directory: website

      - name: Build
        run: pnpm build
        working-directory: website

      - name: Deploy to Cloudflare Pages (production)
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy dist --project-name recalium --branch main
          workingDirectory: website
```

> **Note on `--branch main`:** Passing `--branch main` to the Wrangler pages deploy command tells Cloudflare Pages to map this deployment to the production alias. Without it, Cloudflare would treat it as a preview deployment.

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/website-deploy.yml
git commit -m "ci: add production deploy workflow"
```

Expected: commit succeeds, `git log --oneline -2` shows both new CI commits.

---

## Task 3: Verification

No automated tests exist for GitHub Actions workflow YAML. Verification is done in two stages: local checks and manual live verification.

**Files:**
- No files created or modified in this task.

- [ ] **Step 1: Run the Astro build locally to confirm it passes**

```bash
cd /home/andrey/projects/recalium/website && pnpm build
```

Expected output (approximate):

```
> recalium-website@0.0.1 build
> astro build

 astro  v5.x.x Building...
...
 astro  Build complete.
       dist/ is ready.
```

If the build fails, fix the underlying issue before proceeding. The CI workflows run the same `pnpm build` command, so a broken local build means broken CI.

- [ ] **Step 2: Validate YAML syntax of both workflow files**

Run from the repo root:

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/website-preview.yml'))" && echo "website-preview.yml: OK"
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/website-deploy.yml'))" && echo "website-deploy.yml: OK"
```

Expected output:
```
website-preview.yml: OK
website-deploy.yml: OK
```

If either command raises a `yaml.scanner.ScannerError`, open the offending file and fix the indentation or quoting error reported in the traceback.

- [ ] **Step 3: Verify file content matches the plan**

Spot-check key sections in each file:

For `website-preview.yml`:
- `on.pull_request.branches: [main]` is present
- `on.pull_request.paths` includes `'website/**'`
- `permissions.pull-requests: write` is present
- Step with `id: deploy` uses `cloudflare/wrangler-action@v3`
- Final step uses `actions/github-script@v7` with `env.PREVIEW_URL`

For `website-deploy.yml`:
- `on.push.branches: [main]` is present
- `on.push.paths` includes `'website/**'`
- No `pull-requests: write` permission (not needed)
- Wrangler command ends with `--branch main`

- [ ] **Step 4: Manual live verification (after pushing to GitHub)**

Push the `feat/website` branch and open a PR targeting `main`:

```bash
git push origin feat/website
```

Then in the GitHub UI:
1. Open a PR from `feat/website` → `main`
2. Go to the **Actions** tab of the PR
3. Confirm the `Website — Preview Deploy` workflow is triggered and running
4. After it completes, confirm a comment is posted on the PR with a Cloudflare Pages preview URL
5. Merge the PR (or push directly to `main` if you have permissions)
6. Confirm the `Website — Production Deploy` workflow is triggered
7. Verify the production URL (`https://recalium.pages.dev` or your custom domain) serves the updated site

> **Prerequisite for live verification:** The manual one-time setup steps in the section below must be completed before the workflows can succeed. Specifically, `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` must be set as repository secrets before pushing.

---

## Manual Setup (one-time, not automated)

These steps must be done once by a human before the CI workflows can deploy successfully. They are not part of the automated implementation tasks above.

### 1. Create the Cloudflare Pages project

In the [Cloudflare dashboard](https://dash.cloudflare.com):

1. Go to **Workers & Pages → Create application → Pages → Connect to Git**
2. Select the `malandr/recalium` repository
3. Configure the build settings:
   - **Project name:** `recalium`
   - **Root directory:** `website`
   - **Build command:** `pnpm build`
   - **Build output directory:** `dist`
4. Complete the setup wizard. The initial Cloudflare-managed build can be skipped or cancelled — the GitHub Actions workflows will own all subsequent deployments.

### 2. Generate a Cloudflare API token

1. Go to [My Profile → API Tokens → Create Token](https://dash.cloudflare.com/profile/api-tokens)
2. Use the **Edit Cloudflare Pages** template, or create a custom token with the `Cloudflare Pages:Edit` permission scoped to your account
3. Copy the token immediately — it is shown only once

### 3. Find your Cloudflare Account ID

In the Cloudflare dashboard sidebar (on the Workers & Pages overview page), your Account ID is displayed in the right-hand panel. Copy it.

### 4. Add GitHub Actions repository secrets

In the `malandr/recalium` GitHub repository:

1. Go to **Settings → Secrets and variables → Actions → New repository secret**
2. Add `CLOUDFLARE_API_TOKEN` with the token from step 2
3. Add `CLOUDFLARE_ACCOUNT_ID` with the account ID from step 3

| Secret name | Where to find it |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Cloudflare dashboard → My Profile → API Tokens |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard → Workers & Pages sidebar |

### Out of scope

The following require manual action if needed and are intentionally not automated:

- **Custom domain DNS setup** — configure in the Cloudflare Pages dashboard after deployment is working
- **Node.js version pinning** — `lts/*` (configured automatically by `pnpm/action-setup@v3`) is sufficient; pin explicitly only if a specific version becomes necessary
