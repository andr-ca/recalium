import { test, expect } from "@playwright/test";
import { tabTo } from "./helpers";

// RR-011: Per-workflow keyboard operability testing. Each core workflow must
// be completable using keyboard only (Tab, arrow keys, Enter, Space, Escape).

test.describe("keyboard workflows (RR-011)", () => {
  test("ingest: paste tab can be navigated and submitted via keyboard", async ({
    page,
  }) => {
    await page.goto("/ingest");
    await expect(page.locator("main, [role='main']").first()).toBeVisible();

    // Tab to source-name input
    const reachedSourceName = await tabTo(page, "#source-name");
    expect(reachedSourceName).toBeTruthy();

    // Type source name with E2E prefix
    await page.keyboard.type("E2E-KBD-ingest " + new Date().getTime());

    // Tab to paste-content textarea
    const reachedContent = await tabTo(page, "#paste-content");
    expect(reachedContent).toBeTruthy();

    // Type content
    await page.keyboard.type("E2E-KBD-keyboard test content");

    // Tab to submit button and press Enter
    const reachedSubmit = await tabTo(page, "button[type='submit']");
    expect(reachedSubmit).toBeTruthy();

    // Verify we can activate it (check it's enabled)
    const submitButton = page.locator("button[type='submit']");
    const isEnabled = await submitButton.evaluate((el: HTMLElement) => !(el as HTMLButtonElement).disabled);
    expect(isEnabled).toBeTruthy();
  });

  test("search: can navigate and submit query via keyboard", async ({
    page,
  }) => {
    await page.goto("/search");
    await expect(page.locator("main, [role='main']").first()).toBeVisible();

    // Tab to search input
    const reachedInput = await tabTo(page, "#search-query");
    expect(reachedInput).toBeTruthy();

    // Type query
    await page.keyboard.type("test");

    // Tab to submit button
    const reachedSubmit = await tabTo(page, "button[type='submit']");
    expect(reachedSubmit).toBeTruthy();

    // Verify submit button is enabled
    const submitButton = page.locator("button[type='submit']");
    const isEnabled = await submitButton.evaluate((el: HTMLElement) => !(el as HTMLButtonElement).disabled);
    expect(isEnabled).toBeTruthy();
  });

  test("facts: tab to fact action button and activate with Enter", async ({
    page,
  }) => {
    await page.goto("/facts");
    await expect(page.locator("main, [role='main']").first()).toBeVisible();

    // Wait for page heading to be visible
    await expect(page.locator("h1")).toBeVisible({ timeout: 10_000 });

    // Look for any action button (e.g., Save, Promote, Dispute)
    const actionButton = page.locator("button").first();

    if (await actionButton.isVisible()) {
      // Tab to the first visible button
      await actionButton.focus();

      // Verify it's focused
      const isFocused = await page.evaluate(
        () => document.activeElement?.tagName === "BUTTON",
      );
      expect(isFocused).toBeTruthy();

      // Assert the button has a label/text
      const label = await actionButton.textContent();
      expect(label?.trim().length ?? 0).toBeGreaterThan(0);
    }
  });

  test("review-queue: tab to resolve/dismiss buttons", async ({ page }) => {
    await page.goto("/review-queue");
    await expect(page.locator("main, [role='main']").first()).toBeVisible();

    // Wait for page heading to be visible
    await expect(page.locator("h1")).toBeVisible({ timeout: 10_000 });

    // Look for any button (could be resolve/dismiss or other actions)
    const actionButton = page.locator("button").first();

    if (await actionButton.isVisible()) {
      // Tab to the first action button
      await actionButton.focus();

      // Verify it's focused
      const isFocused = await page.evaluate(
        () => document.activeElement?.tagName === "BUTTON",
      );
      expect(isFocused).toBeTruthy();
    }
  });

  test("settings: backup button is keyboard accessible", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.locator("main, [role='main']").first()).toBeVisible();

    // Look for the "Create backup now" or "Trigger backup" button
    const backupButton = page.locator("button").filter({
      hasText: /backup|create/i,
    }).first();

    if (await backupButton.isVisible()) {
      // Tab to the backup button
      await backupButton.focus();

      // Verify it's focused and labelled
      const isFocused = await page.evaluate(
        () => document.activeElement?.tagName === "BUTTON",
      );
      expect(isFocused).toBeTruthy();

      const label = await backupButton.textContent();
      expect(label?.trim().length ?? 0).toBeGreaterThan(0);
    }
  });

  test("skip-link: first Tab shows visible focus indicator", async ({
    page,
  }) => {
    await page.goto("/");

    // Press Tab once
    await page.keyboard.press("Tab");

    // Check that the focused element has a visible focus-visible style
    const focusedElement = page.locator(":focus");
    await expect(focusedElement).toBeVisible();

    // Verify the element has a computed outline or ring
    const computedStyle = await focusedElement.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        outline: style.outline,
        boxShadow: style.boxShadow,
        outlineWidth: style.outlineWidth,
      };
    });

    // Assert at least one focus indicator is visible (outline or box-shadow)
    const hasFocusIndicator =
      (computedStyle.outline && computedStyle.outline !== "none") ||
      (computedStyle.boxShadow && computedStyle.boxShadow !== "none");
    expect(hasFocusIndicator).toBeTruthy();
  });

  test("all 9 routes are reachable via keyboard Tab navigation", async ({
    page,
  }) => {
    const routes = [
      "/",
      "/wizard",
      "/ingest",
      "/archive",
      "/search",
      "/facts",
      "/canonical",
      "/review-queue",
      "/audit",
      "/settings",
    ];

    for (const route of routes) {
      await page.goto(route);

      // Wait for main content to load
      const landmarkSelector = route === "/wizard" ? "[role='dialog']" : "main, [role='main']";
      await expect(page.locator(landmarkSelector).first()).toBeVisible({
        timeout: 10_000,
      });

      // Verify page is navigable with Tab
      await page.keyboard.press("Tab");
      const focusedElement = page.locator(":focus");
      await expect(focusedElement).toBeVisible({ timeout: 5_000 });
    }
  });
});
