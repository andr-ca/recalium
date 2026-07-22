import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SearchPage } from "../pages/SearchPage";
import { searchMemory, deleteFact, deleteCanonical, type RetrievalItem, type RetrievalResponse } from "@/lib/api";

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    constructor(public status: number, public detail: string) {
      super(detail);
    }
  }
  return {
    ApiError,
    searchMemory: vi.fn(),
    getArchiveItem: vi.fn(),
    deleteFact: vi.fn(),
    deleteCanonical: vi.fn(),
  };
});

function result(id: string, type: RetrievalItem["type"], content: string): RetrievalItem {
  return {
    id,
    type,
    content,
    score: 0.5,
    source_id: `src-${id}`,
    source_system: type === "canonical" ? "canonical" : "chatgpt",
    captured_at: "2026-05-01T00:00:00Z",
    conflict_label: null,
    provenance: { derivation_method: "llm", derivation_model: "m", source_excerpt: "" },
  };
}

const response: RetrievalResponse = {
  query: "postgres",
  retrieval_mode: "hybrid",
  budget_used: 100,
  budget_limit: 2000,
  trimming_reason: "budget_met",
  degraded_mode: false,
  items: [
    result("fact-1", "fact", "Facts use pgvector."),
    result("canon-1", "canonical", "Canonical about Postgres."),
    result("exc-1", "excerpt", "An excerpt from a source."),
  ],
};

const renderPage = () => render(<MemoryRouter><SearchPage /></MemoryRouter>);

describe("SearchPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubGlobal("confirm", vi.fn(() => true));
    vi.mocked(searchMemory).mockResolvedValue(response);
    vi.mocked(deleteFact).mockResolvedValue(undefined);
    vi.mocked(deleteCanonical).mockResolvedValue(undefined);
  });

  it("passes canonical_only when the filter is checked", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByLabelText(/canonical only/i));
    await user.type(screen.getByLabelText(/search query/i), "postgres");
    await user.click(screen.getByRole("button", { name: /^search$/i }));

    await waitFor(() => expect(searchMemory).toHaveBeenCalledWith("postgres", "hybrid", 20, true));
  });

  it("bulk-deletes selected fact and canonical results via the correct endpoints", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/search query/i), "postgres");
    await user.click(screen.getByRole("button", { name: /^search$/i }));
    await screen.findByText("Facts use pgvector.");

    // Excerpt results are not deletable — no checkbox.
    expect(screen.queryByLabelText(/select excerpt result/i)).not.toBeInTheDocument();

    await user.click(screen.getByLabelText(/select fact result/i));
    await user.click(screen.getByLabelText(/select canonical result/i));
    await user.click(screen.getByRole("button", { name: /delete selected \(2\)/i }));

    await waitFor(() => {
      expect(deleteFact).toHaveBeenCalledWith("fact-1");
      expect(deleteCanonical).toHaveBeenCalledWith("canon-1");
    });
    await waitFor(() => expect(screen.queryByText("Facts use pgvector.")).not.toBeInTheDocument());
    expect(screen.getByText("An excerpt from a source.")).toBeInTheDocument();
  });
});
