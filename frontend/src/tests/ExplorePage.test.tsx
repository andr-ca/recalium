import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExplorePage } from "../pages/ExplorePage";
import { listTags } from "@/lib/api";

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    constructor(public status: number, public detail: string) {
      super(detail);
    }
  }
  return { ApiError, listTags: vi.fn() };
});

describe("ExplorePage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listTags).mockResolvedValue({
      total: 2,
      tags: [
        { id: "tag-pnpm", name: "entity:pnpm", created_at: "2026-05-01T00:00:00Z", fact_count: 23 },
        { id: "tag-tooling", name: "tooling", created_at: "2026-05-01T00:00:00Z", fact_count: 7 },
      ],
    });
  });

  it("splits entities from topics and links each tag to its facts", async () => {
    render(
      <MemoryRouter>
        <ExplorePage />
      </MemoryRouter>,
    );

    // Entity name is shown with the `entity:` prefix stripped.
    const entityLink = await screen.findByRole("link", { name: /pnpm — 23 facts/i });
    expect(entityLink).toHaveAttribute("href", "/explore/tags/tag-pnpm");

    const topicLink = screen.getByRole("link", { name: /tooling — 7 facts/i });
    expect(topicLink).toHaveAttribute("href", "/explore/tags/tag-tooling");

    expect(screen.getByText("Entities")).toBeInTheDocument();
    expect(screen.getByText("Topics")).toBeInTheDocument();
  });
});
