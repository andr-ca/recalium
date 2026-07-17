import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SettingsPage } from "../pages/SettingsPage";
import {
  getSettings,
  getTelemetrySummary,
  listBackups,
  triggerBackup,
  restoreBackup,
  exportBundle,
  importBundle,
  ApiError as ApiErrorClass,
} from "@/lib/api";

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    constructor(public status: number, public detail: string) {
      super(detail);
    }
  }
  return {
    ApiError,
    getSettings: vi.fn(),
    validateKey: vi.fn(),
    getTelemetrySummary: vi.fn(),
    listBackups: vi.fn(),
    triggerBackup: vi.fn(),
    restoreBackup: vi.fn(),
    exportBundle: vi.fn(),
    importBundle: vi.fn(),
  };
});

const settingsResponse = {
  openai: { configured: false, fingerprint: null, validation_status: "unchecked", validated_at: null },
  anthropic: { configured: false, fingerprint: null, validation_status: "unchecked", validated_at: null },
  ollama: { configured: false, fingerprint: null, validation_status: "unchecked", validated_at: null, base_url: "http://localhost:11434" },
} as const;

const telemetryResponse = {
  days: 7,
  summary: [],
};

const backup = {
  filename: "recalium-20260427.dump",
  created_at: "2026-04-27T00:00:00Z",
  size_bytes: 2048,
  has_post_deletion_events: true,
};

const bundle = {
  format: "recalium-memory-bundle",
  version: "2",
  exported_at: "2026-07-17T00:00:00Z",
  items: [{ id: "item-1" }, { id: "item-2" }],
  canonical_memory: [{ id: "canonical-1" }],
  tombstones: [{ id: "tombstone-1" }],
};

describe("SettingsPage backup and restore", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    vi.stubGlobal("confirm", vi.fn(() => true));
    vi.mocked(getSettings).mockResolvedValue(settingsResponse);
    vi.mocked(getTelemetrySummary).mockResolvedValue(telemetryResponse);
    vi.mocked(listBackups).mockResolvedValue({ backups: [backup], count: 1 });
    vi.mocked(triggerBackup).mockResolvedValue({ status: "ok", filename: backup.filename });
    vi.mocked(restoreBackup).mockResolvedValue({ status: "ok", filename: backup.filename });
  });

  it("shows backup inventory warnings and can create a backup", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    expect(await screen.findByText(backup.filename)).toBeInTheDocument();
    expect(screen.getByText(/may include deleted data/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /create backup now/i }));

    expect(triggerBackup).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByText(`Created backup ${backup.filename}.`)).toBeInTheDocument();
    });
  });

  it("restores a selected backup after confirmation", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    await screen.findByText(backup.filename);
    await user.click(screen.getByRole("button", { name: `Restore backup ${backup.filename}` }));

    expect(globalThis.confirm).toHaveBeenCalledWith(expect.stringContaining(backup.filename));
    expect(restoreBackup).toHaveBeenCalledWith(backup.filename);
  });
});

describe("SettingsPage memory portability (export/import)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    vi.stubGlobal("confirm", vi.fn(() => true));
    vi.mocked(getSettings).mockResolvedValue(settingsResponse);
    vi.mocked(getTelemetrySummary).mockResolvedValue(telemetryResponse);
    vi.mocked(listBackups).mockResolvedValue({ backups: [], count: 0 });
    vi.mocked(exportBundle).mockResolvedValue(bundle);
    vi.mocked(importBundle).mockResolvedValue({
      imported: 2,
      skipped: 0,
      canonical_imported: 1,
      tombstones_applied: 1,
      errors: [],
    });
  });

  it("renders portability section", async () => {
    render(<SettingsPage />);
    expect(await screen.findByText("Memory Portability")).toBeInTheDocument();
  });

  it("imports bundle after file selection and confirmation", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    const fileInput = await screen.findByLabelText(/Select memory bundle file to import/i) as HTMLInputElement;
    const file = new File([JSON.stringify(bundle)], "bundle.json", { type: "application/json" });

    await user.upload(fileInput, file);

    // Confirmation dialog should appear
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /Import confirmation/i })).toBeInTheDocument();
    });

    // Click confirm
    await user.click(screen.getByRole("button", { name: /Confirm/i }));

    expect(importBundle).toHaveBeenCalledWith(bundle);
    await waitFor(() => {
      expect(screen.getByText(/Import completed/i)).toBeInTheDocument();
    });
  });

  it("shows inline error for malformed JSON", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    const fileInput = await screen.findByLabelText(/Select memory bundle file to import/i) as HTMLInputElement;
    const file = new File(["not valid json"], "bundle.json", { type: "application/json" });

    await user.upload(fileInput, file);

    await waitFor(() => {
      expect(screen.getByText(/Failed to parse JSON file/i)).toBeInTheDocument();
    });

    // API should NOT be called
    expect(importBundle).not.toHaveBeenCalled();
  });

  it("shows error from backend (422)", async () => {
    vi.mocked(importBundle).mockRejectedValue(new ApiErrorClass(422, "Invalid bundle version"));
    const user = userEvent.setup();
    render(<SettingsPage />);

    const fileInput = await screen.findByLabelText(/Select memory bundle file to import/i) as HTMLInputElement;
    const file = new File([JSON.stringify(bundle)], "bundle.json", { type: "application/json" });

    await user.upload(fileInput, file);
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /Import confirmation/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Confirm/i }));

    await waitFor(() => {
      expect(screen.getByText("Invalid bundle version")).toBeInTheDocument();
    });
  });

  it("shows partial success with error messages", async () => {
    vi.mocked(importBundle).mockResolvedValue({
      imported: 1,
      skipped: 1,
      canonical_imported: 0,
      tombstones_applied: 1,
      errors: ["Error 1", "Error 2"],
    });

    const user = userEvent.setup();
    render(<SettingsPage />);

    const fileInput = await screen.findByLabelText(/Select memory bundle file to import/i) as HTMLInputElement;
    const file = new File([JSON.stringify(bundle)], "bundle.json", { type: "application/json" });

    await user.upload(fileInput, file);
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /Import confirmation/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Confirm/i }));

    await waitFor(() => {
      // Should show result summary
      expect(screen.getByText(/Import completed/i)).toBeInTheDocument();
      // Should show error count
      expect(screen.getByText(/There were 2 error/i)).toBeInTheDocument();
    });
  });
});
