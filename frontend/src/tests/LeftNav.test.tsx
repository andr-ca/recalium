/**
 * Component test for left-nav layout — covers WEBUI-01 (D-19).
 *
 * Requirements:
 * - Left-nav renders all 9 items in correct order: Ingest, Archive, Facts,
 *   Canonical, Search, Explore, Review Queue, Audit, Settings
 * - All v1 route entries are enabled links once the release pages exist.
 */
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { NavSidebar } from "../components/NavSidebar";

// Expected nav items and their enabled/disabled state (D-19)
const NAV_ITEMS = [
  { label: "Ingest", path: "/ingest" },
  { label: "Archive", path: "/archive" },
  { label: "Facts", path: "/facts" },
  { label: "Canonical", path: "/canonical" },
  { label: "Search", path: "/search" },
  { label: "Explore", path: "/explore" },
  { label: "Review Queue", path: "/review-queue" },
  { label: "Audit", path: "/audit" },
  { label: "Settings", path: "/settings" },
];

function renderNav() {
  return render(
    <MemoryRouter>
      <NavSidebar />
    </MemoryRouter>
  );
}

describe("NavSidebar", () => {
  it("renders all 9 navigation items", () => {
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
    const expectedOrder = NAV_ITEMS.map((n) => n.label);
    // Extract only the labels that match nav item labels, in DOM order
    const actualLabels = navItems
      .map((el) => el.textContent?.trim() ?? "")
      .filter((t) => NAV_ITEMS.some((n) => t.includes(n.label)));
    expect(actualLabels).toEqual(expectedOrder);
  });

  it("renders all navigation items as enabled links", () => {
    renderNav();
    for (const item of NAV_ITEMS) {
      const el = screen.getByText(item.label).closest("a, button");
      expect(el, `"${item.label}" nav link/button not found`).not.toBeNull();
      expect(el?.getAttribute("aria-disabled"), `"${item.label}" must not be aria-disabled`).not.toBe("true");
      expect(el?.getAttribute("href"), `"${item.label}" must link to its v1 route`).toBe(item.path);
    }
  });
});
