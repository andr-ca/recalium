import { test, expect } from "@playwright/test";
import { expectNoAxeViolations } from "./helpers";

// RR-011: Automated axe WCAG 2.2 AA accessibility scans on all v1 routes.
const ALL_ROUTES = [
  "/wizard",
  "/ingest",
  "/archive",
  "/settings",
  "/search",
  "/facts",
  "/canonical",
  "/review-queue",
  "/audit",
];

test.describe("axe accessibility scans (RR-011)", () => {
  for (const route of ALL_ROUTES) {
    test(`${route} has no axe violations`, async ({ page }) => {
      await page.goto(route);
      // Wait for main landmark or dialog to be visible before scanning
      const selector = route === "/wizard" ? "[role='dialog']" : "main, [role='main']";
      await expect(page.locator(selector).first()).toBeVisible({
        timeout: 10_000,
      });
      // Run axe scan
      await expectNoAxeViolations(page, route);
    });
  }
});
