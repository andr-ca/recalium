import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/** Run axe WCAG 2.2 AA scan and assert no violations. */
export async function expectNoAxeViolations(page: Page, context?: string) {
    const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
        .analyze();
    const summary = results.violations.map(
        (v) => `${v.id} (${v.impact}): ${v.nodes.length} nodes — ${v.help}`,
    );
    expect(summary, `axe violations on ${context ?? page.url()}`).toEqual([]);
}

/** Press Tab until predicate matches the focused element or maxTabs exhausted. */
export async function tabTo(
    page: Page,
    predicate: string, // CSS selector the focused element must match
    maxTabs = 40,
): Promise<boolean> {
    for (let i = 0; i < maxTabs; i++) {
        await page.keyboard.press("Tab");
        const matched = await page.evaluate(
            (sel) => document.activeElement?.matches(sel) ?? false,
            predicate,
        );
        if (matched) return true;
    }
    return false;
}
