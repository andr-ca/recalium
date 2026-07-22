import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryDetailPage } from "../pages/MemoryDetailPage";
import {
  getFact,
  getFactTags,
  getFactLinks,
  getArchiveItem,
  type FactItem,
} from "@/lib/api";

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    constructor(public status: number, public detail: string) {
      super(detail);
    }
  }
  return {
    ApiError,
    getFact: vi.fn(),
    getFactTags: vi.fn(),
    getFactLinks: vi.fn(),
    getArchiveItem: vi.fn(),
  };
});

const fact: FactItem = {
  id: "fact-1",
  raw_archive_id: "archive-1",
  fact_text: "User prefers pnpm over npm.",
  source_span: "let's standardize on pnpm",
  confidence_tier: "high",
  derivation_method: "llm_extraction",
  derivation_model: "gpt-4o-mini",
  conflict_group_id: null,
  source_status: "active",
  review_status: "active",
  created_at: "2026-05-02T00:00:00Z",
};

function renderAt(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/memory/${id}`]}>
      <Routes>
        <Route path="/memory/:id" element={<MemoryDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("MemoryDetailPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getFact).mockResolvedValue(fact);
    vi.mocked(getFactTags).mockResolvedValue({
      fact_id: "fact-1",
      tags: [{ tag_id: "t1", name: "entity:pnpm", assigned_by: "pipeline", assigned_at: "2026-05-02T00:00:00Z" }],
    });
    vi.mocked(getFactLinks).mockResolvedValue({
      fact_id: "fact-1",
      direction: "both",
      total: 1,
      links: [
        {
          link_id: "l1",
          link_type: "contradicts",
          confidence: 0.9,
          entity_name: null,
          created_by: "pipeline",
          created_at: "2026-05-05T00:00:00Z",
          other_fact_id: "fact-2",
          other_fact_text: "User asked to switch to npm.",
        },
      ],
    });
    vi.mocked(getArchiveItem).mockResolvedValue({
      id: "archive-1",
      source_type: "chatgpt",
      source_name: "conv",
      ingested_at: "2026-05-02T00:00:00Z",
      raw_content: "…let's standardize on pnpm across the org…",
      status_badge: "Done",
    });
  });

  it("renders the fact with its tags and a linked memory that navigates to the other fact", async () => {
    renderAt("fact-1");

    expect(await screen.findByText("User prefers pnpm over npm.")).toBeInTheDocument();
    expect(screen.getByText("entity:pnpm")).toBeInTheDocument();
    // Related memory: shows the linked fact text and a typed link badge.
    expect(screen.getByText("User asked to switch to npm.")).toBeInTheDocument();
    expect(screen.getByText("contradicts")).toBeInTheDocument();
    const openLink = screen.getByRole("link", { name: /open linked memory/i });
    expect(openLink).toHaveAttribute("href", "/memory/fact-2");
  });

  it("reveals the highlighted source span when View source is clicked", async () => {
    const user = userEvent.setup();
    renderAt("fact-1");

    await screen.findByText("User prefers pnpm over npm.");
    await user.click(screen.getByRole("button", { name: /view source/i }));

    await waitFor(() => expect(getArchiveItem).toHaveBeenCalledWith("archive-1"));
    // The span is highlighted via a <mark>.
    const marks = document.querySelectorAll("mark");
    expect(Array.from(marks).some((m) => m.textContent === "let's standardize on pnpm")).toBe(true);
  });

  it("shows a not-found message when the fact is missing", async () => {
    const { ApiError } = await import("@/lib/api");
    vi.mocked(getFact).mockRejectedValue(new ApiError(404, "not found"));

    renderAt("missing-id");

    expect(await screen.findByText(/memory not found/i)).toBeInTheDocument();
  });
});
