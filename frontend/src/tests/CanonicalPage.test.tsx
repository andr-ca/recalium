import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CanonicalPage } from "../pages/CanonicalPage";
import { listCanonical, deleteCanonical, type CanonicalItem } from "@/lib/api";

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    constructor(public status: number, public detail: string) {
      super(detail);
    }
  }
  return {
    ApiError,
    listCanonical: vi.fn(),
    updateCanonical: vi.fn(),
    deleteCanonical: vi.fn(),
  };
});

function item(id: string, content: string): CanonicalItem {
  return {
    id,
    raw_archive_id: `a-${id}`,
    fact_id: `f-${id}`,
    content,
    status: "active",
    source_status: "active",
    promoted_from: "fact",
    promoted_by: "user_ui",
    provenance_note: null,
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
  };
}

const items = [
  item("c1", "Recalium uses PostgreSQL with pgvector."),
  item("c2", "The frontend is built with React and Vite."),
];

describe("CanonicalPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubGlobal("confirm", vi.fn(() => true));
    vi.mocked(listCanonical).mockResolvedValue({ items, count: items.length });
    vi.mocked(deleteCanonical).mockResolvedValue(undefined);
  });

  it("filters canonical items by search text", async () => {
    const user = userEvent.setup();
    render(<CanonicalPage />);

    await screen.findByText("Recalium uses PostgreSQL with pgvector.");
    await user.type(screen.getByLabelText(/search canonical memory/i), "react");

    expect(screen.getByText("The frontend is built with React and Vite.")).toBeInTheDocument();
    expect(screen.queryByText("Recalium uses PostgreSQL with pgvector.")).not.toBeInTheDocument();
  });

  it("bulk-deletes the selected canonical items and reloads", async () => {
    const user = userEvent.setup();
    render(<CanonicalPage />);

    await screen.findByText("Recalium uses PostgreSQL with pgvector.");
    await user.click(screen.getByLabelText(/select all canonical items/i));
    await user.click(screen.getByRole("button", { name: /delete selected \(2\)/i }));

    await waitFor(() => expect(deleteCanonical).toHaveBeenCalledTimes(2));
    expect(deleteCanonical).toHaveBeenCalledWith("c1");
    expect(deleteCanonical).toHaveBeenCalledWith("c2");
    // initial load + reload after delete
    expect(listCanonical).toHaveBeenCalledTimes(2);
  });
});
