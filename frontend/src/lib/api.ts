/**
 * Typed API client for Recalium backend.
 * All fetch() calls go through this module — never import fetch directly in pages.
 */

const BASE_URL = "/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface IngestResponse {
  status: "accepted";
  item_count: number;
  archive_ids: string[];
}

export interface ArchiveItem {
  id: string;
  source_type: string;
  source_name: string | null;
  conversation_count: number;
  ingested_at: string; // ISO 8601
  status_badge: "Ingested"; // Phase 1 only; Phase 2 adds "Processing" / "Done" / "Failed"
}

export interface ArchiveListResponse {
  items: ArchiveItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface SettingsKeyStatus {
  configured: boolean;
  fingerprint: string | null; // last 4 chars, or null if not set
  validation_status: "valid" | "invalid" | "insufficient_permissions" | "unchecked" | null;
  validated_at: string | null;
}

export interface SettingsResponse {
  openai: SettingsKeyStatus;
  anthropic: SettingsKeyStatus;
  ollama: SettingsKeyStatus & { base_url: string | null };
}

export interface ValidateKeyRequest {
  provider: "openai" | "anthropic" | "ollama";
  api_key: string;
  base_url?: string; // Ollama only
}

export interface ValidateKeyResponse {
  provider: "openai" | "anthropic" | "ollama";
  status: "valid" | "invalid" | "insufficient_permissions";
  message: string;
}

// ── Error handling ─────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(`API error ${status}: ${detail}`);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
  return response.json() as Promise<T>;
}

// ── Ingest ─────────────────────────────────────────────────────────────────

export async function ingestText(content: string, sourceName?: string): Promise<IngestResponse> {
  return request<IngestResponse>("/ingest", {
    method: "POST",
    body: JSON.stringify({ mode: "text", content, source_name: sourceName }),
  });
}

export async function ingestFile(file: File): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<IngestResponse>("/ingest/file", {
    method: "POST",
    headers: {}, // Don't set Content-Type — let browser set multipart boundary
    body: formData,
  });
}

// ── Archive ────────────────────────────────────────────────────────────────

export async function listArchive(
  params: { offset?: number; limit?: number; q?: string } = {}
): Promise<ArchiveListResponse> {
  const qs = new URLSearchParams();
  if (params.offset !== undefined) qs.set("offset", String(params.offset));
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  if (params.q) qs.set("q", params.q);
  return request<ArchiveListResponse>(`/archive?${qs}`);
}

// ── Settings / BYOK ────────────────────────────────────────────────────────

export async function getSettings(): Promise<SettingsResponse> {
  return request<SettingsResponse>("/settings/keys");
}

export async function validateKey(data: ValidateKeyRequest): Promise<ValidateKeyResponse> {
  return request<ValidateKeyResponse>("/settings/keys/validate", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
