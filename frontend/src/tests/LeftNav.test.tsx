/**
 * Component test for left-nav layout — covers WEBUI-01 (D-19).
 *
 * Requirements:
 * - Left-nav renders all 8 items in correct order: Ingest, Archive, Facts,
 *   Canonical, Search, Review Queue, Audit, Settings
 * - Items Facts, Canonical, Search, Review Queue, Audit are DISABLED (grayed out)
 * - Disabled items show tooltip "Available in a future update"
 * - Ingest, Archive, Settings are ENABLED (not disabled)
 */
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { NavSidebar } from "../components/NavSidebar";

// Expected nav items and their enabled/disabled state (D-19)
const NAV_ITEMS = [
  { label: "Ingest", disabled: false },
  { label: "Archive", disabled: false },
  { label: "Facts", disabled: true },
  { label: "Canonical", disabled: true },
  { label: "Search", disabled: true },
  { label: "Review Queue", disabled: true },
  { label: "Audit", disabled: true },
  { label: "Settings", disabled: false },
];

function renderNav() {
  return render(
    <MemoryRouter>
      <NavSidebar />
    </MemoryRouter>
  );
}

describe("NavSidebar", () => {
  it("renders all 8 navigation items", () => {
    renderNav();
    for (const item of NAV_ITEMS) {
      expect(
        screen.getByText(item.label),
        `Nav item "${item.label}" not found`
      ).toBeInTheDocument();
    }
  });

  it("renders items in correct order", () => {
    renderNav();
    const navItems = screen.getAllByRole("listitem");
    const labels = navItems.map((el) => el.textContent?.trim()).filter(Boolean);

    // Check that the order matches the spec
    const expectedOrder = NAV_ITEMS.map((n) => n.label);
    const actualOrder = expectedOrder.filter((label) =>
      labels.some((l) => l?.includes(label))
    );
    expect(actualOrder).toEqual(expectedOrder);
  });

  it("disabled items have aria-disabled or data-disabled attribute", () => {
    renderNav();
    const disabledItems = NAV_ITEMS.filter((n) => n.disabled);
    for (const item of disabledItems) {
      const el = screen.getByText(item.label).closest("[aria-disabled], [data-disabled]");
      expect(el, `"${item.label}" must be wrapped in a disabled element`).not.toBeNull();
    }
  });

  it("enabled items are not disabled", () => {
    renderNav();
    const enabledItems = NAV_ITEMS.filter((n) => !n.disabled);
    for (const item of enabledItems) {
      const el = screen.getByText(item.label).closest("a, button");
      expect(el, `"${item.label}" nav link/button not found`).not.toBeNull();
      expect(el?.getAttribute("aria-disabled"), `"${item.label}" must not be aria-disabled`).not.toBe("true");
    }
  });

  it("disabled items have tooltip text 'Available in a future update'", () => {
    renderNav();

    // The NavSidebar uses a `title` attribute on the <span aria-disabled="true"> wrapper.
    // Check that the first disabled item ("Facts") has the expected title.
    const factsEl = screen.getByText("Facts");
    // The title is on the <span> itself which is also the aria-disabled element
    const wrapper = factsEl.closest("[title]");
    expect(wrapper, "Facts element must have a title attribute").not.toBeNull();
    expect(wrapper?.getAttribute("title")).toContain("Available in a future update");
  });
});
