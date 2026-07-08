import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FactsPage } from "../pages/FactsPage";
import {
  listFacts,
  updateFact,
  markFactDisputed,
  markFactStale,
  archiveFact,
  deleteFact,
  promoteFactToCanonical,
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
    listFacts: vi.fn(),
    updateFact: vi.fn(),
    markFactDisputed: vi.fn(),
    markFactStale: vi.fn(),
    archiveFact: vi.fn(),
    deleteFact: vi.fn(),
    promoteFactToCanonical: vi.fn(),
  };
});

const fact: FactItem = {
  id: "fact-1",
  raw_archive_id: "archive-1",
  fact_text: "Recalium uses FastAPI.",
  source_span: "The backend is FastAPI.",
  confidence_tier: "high",
  derivation_method: "rule_based",
  derivation_model: "local_rules_v1",
  conflict_group_id: null,
  source_status: "active",
  review_status: "active",
  created_at: "2026-04-27T00:00:00Z",
};

describe("FactsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubGlobal("confirm", vi.fn(() => true));
    vi.mocked(listFacts).mockResolvedValue({ facts: [fact], count: 1 });
    vi.mocked(updateFact).mockImplementation(async (_id, body) => ({
      ...fact,
      fact_text: body.fact_text ?? fact.fact_text,
      source_span: body.source_span ?? fact.source_span,
      confidence_tier: body.confidence_tier ?? fact.confidence_tier,
      review_status: (body.review_status ?? fact.review_status) as FactItem["review_status"],
    }));
    vi.mocked(markFactDisputed).mockResolvedValue({ ...fact, review_status: "disputed" });
    vi.mocked(markFactStale).mockResolvedValue({ ...fact, review_status: "stale" });
    vi.mocked(archiveFact).mockResolvedValue({ ...fact, review_status: "archived" });
    vi.mocked(deleteFact).mockResolvedValue(undefined);
    vi.mocked(promoteFactToCanonical).mockResolvedValue({
      id: "canonical-1",
      raw_archive_id: fact.raw_archive_id,
      fact_id: fact.id,
      content: fact.fact_text,
      status: "active",
      source_status: "active",
      promoted_from: "fact",
      promoted_by: "user_ui",
      provenance_note: null,
      created_at: "2026-04-27T00:00:00Z",
      updated_at: "2026-04-27T00:00:00Z",
    });
  });

  it("edits facts and sends lifecycle actions", async () => {
    const user = userEvent.setup();
    render(<FactsPage />);

    const textarea = await screen.findByLabelText(/edit fact text/i);
    await user.clear(textarea);
    await user.type(textarea, "Recalium uses FastAPI and PostgreSQL.");
    await user.click(screen.getByRole("button", { name: /save edit/i }));

    expect(updateFact).toHaveBeenCalledWith("fact-1", {
      fact_text: "Recalium uses FastAPI and PostgreSQL.",
    });

    await user.click(screen.getByRole("button", { name: /mark disputed/i }));
    expect(markFactDisputed).toHaveBeenCalledWith("fact-1");

    await user.click(screen.getByRole("button", { name: /mark stale/i }));
    expect(markFactStale).toHaveBeenCalledWith("fact-1");
  });

  it("can show archived/deleted facts and suppress a fact", async () => {
    const user = userEvent.setup();
    render(<FactsPage />);

    await screen.findByText("Recalium uses FastAPI.");
    expect(listFacts).toHaveBeenCalledWith({ limit: 100, reviewStatus: undefined });

    await user.click(screen.getByRole("button", { name: /show archived\/deleted/i }));
    await waitFor(() => {
      expect(listFacts).toHaveBeenLastCalledWith({ limit: 100, reviewStatus: "all" });
    });

    await user.click(screen.getByRole("button", { name: /^archive$/i }));
    expect(archiveFact).toHaveBeenCalledWith("fact-1");

    await user.click(screen.getByRole("button", { name: /^delete$/i }));
    expect(deleteFact).toHaveBeenCalledWith("fact-1");
  });
});
