import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TagFactsPage } from "../pages/TagFactsPage";
import { getTagFacts } from "@/lib/api";

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    constructor(public status: number, public detail: string) {
      super(detail);
    }
  }
  return { ApiError, getTagFacts: vi.fn() };
});

function renderAt(tagId: string) {
  return render(
    <MemoryRouter initialEntries={[`/explore/tags/${tagId}`]}>
      <Routes>
        <Route path="/explore/tags/:tagId" element={<TagFactsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("TagFactsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getTagFacts).mockResolvedValue({
      tag_id: "tag-pnpm",
      name: "entity:pnpm",
      count: 1,
      facts: [
        {
          id: "fact-1",
          fact_text: "User prefers pnpm over npm.",
          confidence_tier: "high",
          review_status: "active",
          raw_archive_id: "archive-1",
          created_at: "2026-05-02T00:00:00Z",
        },
      ],
    });
  });

  it("lists the tag's facts, each linking to its memory detail", async () => {
    renderAt("tag-pnpm");

    expect(await screen.findByText("User prefers pnpm over npm.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /entity:pnpm/i })).toBeInTheDocument();
    const openLink = screen.getByRole("link", { name: /open memory details/i });
    expect(openLink).toHaveAttribute("href", "/memory/fact-1");
  });

  it("shows a not-found message for an unknown tag", async () => {
    const { ApiError } = await import("@/lib/api");
    vi.mocked(getTagFacts).mockRejectedValue(new ApiError(404, "Tag not found"));

    renderAt("missing");

    expect(await screen.findByText(/tag not found/i)).toBeInTheDocument();
  });
});
