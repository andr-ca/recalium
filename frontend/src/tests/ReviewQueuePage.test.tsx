import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReviewQueuePage } from "../pages/ReviewQueuePage";
import { dismissReviewItem, listReviewQueue, resolveReviewItem, type ReviewQueueItem } from "@/lib/api";

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    constructor(public status: number, public detail: string) {
      super(detail);
    }
  }
  return {
    ApiError,
    listReviewQueue: vi.fn(),
    resolveReviewItem: vi.fn(),
    dismissReviewItem: vi.fn(),
  };
});

const reviewItem: ReviewQueueItem = {
  id: "review-1",
  conflict_group_id: "group-1",
  group_type: "overlap",
  group_source_status: "active",
  fact_count: 2,
  facts: [
    {
      id: "fact-1",
      raw_archive_id: "archive-1",
      fact_text: "Recalium uses FastAPI.",
      source_span: "FastAPI backend",
      confidence_tier: "high",
      derivation_method: "rule_based",
      derivation_model: "local_rules_v1",
      source_status: "active",
      review_status: "active",
      source_name: "copilot-session",
      source_type: "copilot_chat",
      created_at: "2026-04-27T00:00:00Z",
    },
    {
      id: "fact-2",
      raw_archive_id: "archive-1",
      fact_text: "Recalium has a Python backend.",
      source_span: "Python/FastAPI",
      confidence_tier: "medium",
      derivation_method: "rule_based",
      derivation_model: "local_rules_v1",
      source_status: "active",
      review_status: "active",
      source_name: "codex-session",
      source_type: "codex_chat",
      created_at: "2026-04-27T00:00:00Z",
    },
  ],
  item_type: "overlap",
  status: "pending",
  source_status: "active",
  resolution_note: null,
  resolved_by: null,
  created_at: "2026-04-27T00:00:00Z",
  resolved_at: null,
};

describe("ReviewQueuePage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubGlobal("confirm", vi.fn(() => true));
    vi.mocked(listReviewQueue).mockResolvedValue({ items: [reviewItem], count: 1 });
    vi.mocked(resolveReviewItem).mockResolvedValue({ ...reviewItem, status: "resolved" });
    vi.mocked(dismissReviewItem).mockResolvedValue({ ...reviewItem, status: "dismissed" });
  });

  it("shows grouped fact comparison and resolves with a note", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);

    expect(await screen.findByText("overlap group")).toBeInTheDocument();
    expect(screen.getByText("Recalium uses FastAPI.")).toBeInTheDocument();
    expect(screen.getByText("Recalium has a Python backend.")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/resolution note/i), "Keep the more specific FastAPI fact.");
    await user.click(screen.getByRole("button", { name: /resolve review item/i }));

    expect(resolveReviewItem).toHaveBeenCalledWith("review-1", "Keep the more specific FastAPI fact.");
  });

  it("dismisses a pending item after confirmation", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);

    await screen.findByText("overlap group");
    await user.click(screen.getByRole("button", { name: /dismiss review item/i }));

    expect(globalThis.confirm).toHaveBeenCalled();
    expect(dismissReviewItem).toHaveBeenCalledWith("review-1");
  });
});
