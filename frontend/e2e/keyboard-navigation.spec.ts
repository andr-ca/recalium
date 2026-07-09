import { test, expect } from "@playwright/test";

// RR-011: core workflows must be keyboard-operable. This is a STARTER smoke
// suite — expand with per-workflow coverage (ingest paste/upload, archive
// retry/delete, search modes/filters, facts edit/promote, canonical edit,
// review queue resolve, audit detail, backup/restore) and axe checks.

const CORE_ROUTES = [
  "/",
  "/ingest",
  "/archive",
  "/search",
  "/facts",
  "/canonical",
];

test.describe("keyboard navigation (RR-011 starter)", () => {
  test("home renders a main landmark", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("main, [role='main']").first()).toBeVisible();
  });

  test("Tab moves focus to a labelled, visible control", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    const active = page.locator(":focus");
    await expect(active).toBeVisible();
    const label = await active.evaluate(
      (el) => el.getAttribute("aria-label") || el.textContent || "",
    );
    expect(label.trim().length).toBeGreaterThan(0);
  });

  for (const route of CORE_ROUTES) {
    test(`route ${route} loads without a crash`, async ({ page }) => {
      const resp = await page.goto(route);
      expect(resp?.ok() ?? true).toBeTruthy();
      await expect(page.locator("body")).toBeVisible();
    });
  }
});
