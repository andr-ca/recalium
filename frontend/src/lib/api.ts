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

export interface ImportResponse {
  status: string;
  source_format: string;
  conversation_count: number;
  imported: number;
  skipped: number;
  archive_ids: string[];
}

export type JobStatusBadge =
  | "Ingested"
  | "Processing"
  | "Done"
  | "Failed"
  | "Pending Provider";

export interface ArchiveItem {
  id: string;
  source_type: string;
  source_name: string | null;
  conversation_count: number;
  ingested_at: string; // ISO 8601
  status_badge: JobStatusBadge;
  job_id: string | null;
  job_error: string | null;
  deleted_at?: string | null;
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

// ── Import (ChatGPT / Claude conversation exports) ───────────────────────────

export async function importExport(file: File): Promise<ImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<ImportResponse>("/import", {
    method: "POST",
    headers: {}, // Don't set Content-Type — let browser set multipart boundary
    body: formData,
  });
}

// ── Archive ────────────────────────────────────────────────────────────────

export async function listArchive(
  params: { offset?: number; limit?: number; q?: string; include_deleted?: boolean } = {}
): Promise<ArchiveListResponse> {
  const qs = new URLSearchParams();
  if (params.offset !== undefined) qs.set("offset", String(params.offset));
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  if (params.q) qs.set("q", params.q);
  if (params.include_deleted) qs.set("include_deleted", "true");
  return request<ArchiveListResponse>(`/archive?${qs}`);
}

export async function retryJob(jobId: string): Promise<{ status: string; job_id: string }> {
  return request<{ status: string; job_id: string }>(`/jobs/${jobId}/reprocess`, {
    method: "POST",
  });
}

export async function deleteArchiveItem(id: string): Promise<void> {
  // DELETE returns 204 No Content — must use raw fetch, not request() which calls .json()
  const response = await fetch(`${BASE_URL}/archive/${id}`, { method: "DELETE" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
}

export interface ArchiveItemDetail {
  id: string;
  source_type: string;
  source_name: string | null;
  ingested_at: string;
  raw_content: string;
  status_badge: string;
}

export async function getArchiveItem(id: string): Promise<ArchiveItemDetail> {
  return request<ArchiveItemDetail>(`/archive/${id}`);
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

// ── Search / Retrieval ──────────────────────────────────────────────────────

export interface RetrievalItem {
  id: string;
  type: "canonical" | "fact" | "summary" | "excerpt";
  content: string;
  score: number;
  source_id: string;
  source_system: string;
  captured_at: string;
  conflict_label: string | null;
  provenance: {
    derivation_method: string;
    derivation_model: string;
    source_excerpt: string;
  };
}

export interface RetrievalResponse {
  query: string;
  retrieval_mode: string;
  budget_used: number;
  budget_limit: number;
  trimming_reason: "budget_met" | "result_exhausted";
  degraded_mode: boolean;
  items: RetrievalItem[];
}

export async function searchMemory(
  q: string,
  mode: "keyword" | "semantic" | "hybrid" = "hybrid",
  limit = 20,
  canonicalOnly = false,
): Promise<RetrievalResponse> {
  const params = new URLSearchParams({ q, mode, limit: String(limit) });
  if (canonicalOnly) params.set("canonical_only", "true");
  return request<RetrievalResponse>(`/search?${params}`);
}

// ── Facts ────────────────────────────────────────────────────────────────────

export interface FactItem {
  id: string;
  raw_archive_id: string;
  fact_text: string;
  source_span: string;
  confidence_tier: string;
  derivation_method: string;
  derivation_model: string;
  conflict_group_id: string | null;
  source_status: string;
  review_status: "active" | "disputed" | "stale" | "archived" | "deleted";
  created_at: string;
}

export async function listFacts(params?: { limit?: number; offset?: number; reviewStatus?: string }): Promise<{ facts: FactItem[]; count: number }> {
  const p = new URLSearchParams();
  if (params?.limit) p.set("limit", String(params.limit));
  if (params?.offset) p.set("offset", String(params.offset));
  if (params?.reviewStatus) p.set("review_status", params.reviewStatus);
  return request<{ facts: FactItem[]; count: number }>(`/facts/?${p}`);
}

export async function getFact(factId: string): Promise<FactItem> {
  return request<FactItem>(`/facts/${factId}`);
}

// ── Tags & memory links (relationship graph) ─────────────────────────────────

export interface FactTag {
  tag_id: string;
  name: string;
  assigned_by: string;
  assigned_at: string;
}

export type LinkDirection = "outgoing" | "incoming" | "both";

/** A typed edge to another fact. link_type ∈ supports | elaborates | contradicts | related | entity. */
export interface FactLink {
  link_id: string;
  link_type: string;
  confidence: number;
  entity_name: string | null;
  created_by: string;
  created_at: string;
  other_fact_id: string;
  other_fact_text: string;
}

export async function getFactTags(factId: string): Promise<{ fact_id: string; tags: FactTag[] }> {
  return request<{ fact_id: string; tags: FactTag[] }>(`/facts/${factId}/tags`);
}

export async function getFactLinks(
  factId: string,
  direction: LinkDirection = "both",
): Promise<{ fact_id: string; direction: string; links: FactLink[]; total: number }> {
  const p = new URLSearchParams({ direction });
  return request<{ fact_id: string; direction: string; links: FactLink[]; total: number }>(
    `/facts/${factId}/links?${p}`,
  );
}

export interface Tag {
  id: string;
  name: string;
  created_at: string;
  fact_count: number;
}

export async function listTags(): Promise<{ tags: Tag[]; total: number }> {
  return request<{ tags: Tag[]; total: number }>(`/tags`);
}

export interface TagFact {
  id: string;
  fact_text: string;
  confidence_tier: string;
  review_status: string;
  raw_archive_id: string;
  created_at: string;
}

export async function getTagFacts(
  tagId: string,
): Promise<{ tag_id: string; name: string; facts: TagFact[]; count: number }> {
  return request<{ tag_id: string; name: string; facts: TagFact[]; count: number }>(`/tags/${tagId}/facts`);
}



export async function updateFact(
  factId: string,
  data: { fact_text?: string; source_span?: string; confidence_tier?: string; review_status?: string },
): Promise<FactItem> {
  return request<FactItem>(`/facts/${factId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function markFactDisputed(factId: string): Promise<FactItem> {
  return request<FactItem>(`/facts/${factId}/dispute`, { method: "POST", body: JSON.stringify({}) });
}

export async function markFactStale(factId: string): Promise<FactItem> {
  return request<FactItem>(`/facts/${factId}/mark-stale`, { method: "POST", body: JSON.stringify({}) });
}

export async function archiveFact(factId: string): Promise<FactItem> {
  return request<FactItem>(`/facts/${factId}/archive`, { method: "POST", body: JSON.stringify({}) });
}

export async function deleteFact(factId: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/facts/${factId}`, { method: "DELETE" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
}

export async function promoteFactToCanonical(
  factId: string,
  rawArchiveId: string,
  content: string,
  hasSourceSpan: boolean,
  confirmed = false,
): Promise<CanonicalItem> {
  return request<CanonicalItem>(`/canonical/promote`, {
    method: "POST",
    body: JSON.stringify({
      fact_id: factId,
      raw_archive_id: rawArchiveId,
      content,
      has_source_span: hasSourceSpan,
      confirmed,
    }),
  });
}

// ── Canonical Memory ─────────────────────────────────────────────────────────

export interface CanonicalItem {
  id: string;
  raw_archive_id: string | null;
  fact_id: string | null;
  content: string;
  status: string;
  source_status: string;
  promoted_from: string;
  promoted_by: string;
  provenance_note: string | null;
  created_at: string;
  updated_at: string;
}

export async function listCanonical(params?: { include_non_active?: boolean; limit?: number; offset?: number }): Promise<{ items: CanonicalItem[]; count: number }> {
  const p = new URLSearchParams();
  if (params?.include_non_active) p.set("include_non_active", "true");
  if (params?.limit) p.set("limit", String(params.limit));
  if (params?.offset) p.set("offset", String(params.offset));
  return request<{ items: CanonicalItem[]; count: number }>(`/canonical?${p}`);
}

export async function updateCanonical(id: string, body: { content?: string; status?: string }): Promise<CanonicalItem> {
  return request<CanonicalItem>(`/canonical/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteCanonical(id: string): Promise<void> {
  // DELETE returns 204 No Content, no JSON body
  const response = await fetch(`${BASE_URL}/canonical/${id}`, { method: "DELETE" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
}

// ── Review Queue ─────────────────────────────────────────────────────────────

export interface ReviewQueueItem {
  id: string;
  conflict_group_id: string;
  group_type: string | null;
  group_source_status: string | null;
  fact_count: number;
  facts: Array<{
    id: string;
    raw_archive_id: string;
    fact_text: string;
    source_span: string;
    confidence_tier: string;
    derivation_method: string;
    derivation_model: string;
    source_status: string;
    review_status: string;
    source_name: string | null;
    source_type: string | null;
    created_at: string | null;
  }>;
  item_type: string;
  status: string;
  source_status: string;
  resolution_note: string | null;
  resolved_by: string | null;
  created_at: string;
  resolved_at: string | null;
}

export async function listReviewQueue(status = "pending", limit = 100): Promise<{ items: ReviewQueueItem[]; count: number }> {
  const p = new URLSearchParams({ status, limit: String(limit) });
  return request<{ items: ReviewQueueItem[]; count: number }>(`/review-queue?${p}`);
}

export async function resolveReviewItem(id: string, note?: string): Promise<ReviewQueueItem> {
  return request<ReviewQueueItem>(`/review-queue/${id}/resolve`, {
    method: "POST",
    body: JSON.stringify({ resolved_by: "user_ui", resolution_note: note ?? "" }),
  });
}

export async function dismissReviewItem(id: string): Promise<ReviewQueueItem> {
  return request<ReviewQueueItem>(`/review-queue/${id}/dismiss`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

// ── Audit ────────────────────────────────────────────────────────────────────

export interface AuditEventItem {
  id: string;
  event_type: string;
  actor: string;
  operation_metadata: Record<string, unknown>;
  occurred_at: string;
}

export async function listAuditEvents(params?: { limit?: number; offset?: number; event_type?: string | null }): Promise<{ items: AuditEventItem[]; count: number }> {
  const p = new URLSearchParams();
  if (params?.limit) p.set("limit", String(params.limit));
  if (params?.offset !== undefined) p.set("offset", String(params.offset));
  if (params?.event_type) p.set("event_type", params.event_type);
  return request<{ items: AuditEventItem[]; count: number }>(`/audit/events?${p}`);
}

// ── Onboarding ──────────────────────────────────────────────────────────────

export interface OnboardingStatus {
  should_show_wizard: boolean;
  has_archive_items: boolean;
  has_configured_key: boolean;
}

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  return request<OnboardingStatus>("/status/onboarding");
}

// ── Backup ───────────────────────────────────────────────────────────────────

export interface BackupItem {
  filename: string;
  created_at: string | null;
  size_bytes: number;
  has_post_deletion_events: boolean;
}

export interface BackupListResponse {
  backups: BackupItem[];
  count: number;
}

export async function listBackups(): Promise<BackupListResponse> {
  return request<BackupListResponse>("/backup/list");
}

export async function triggerBackup(): Promise<{ status: string; filename: string }> {
  return request<{ status: string; filename: string }>("/backup/trigger", { method: "POST" });
}

export async function restoreBackup(filename: string): Promise<{ status: string; filename: string }> {
  return request<{ status: string; filename: string }>("/backup/restore", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename }),
  });
}

// ── Portability (Memory Bundle) ────────────────────────────────────────────

export interface MemoryBundle {
  format: string; // "recalium-memory-bundle"
  version: string; // "2"
  exported_at: string;
  items: unknown[];
  canonical_memory?: unknown[];
  tombstones?: unknown[];
}

export interface BundleImportResponse {
  imported: number;
  skipped: number;
  canonical_imported: number;
  tombstones_applied: number;
  errors: string[];
}

export async function exportBundle(): Promise<MemoryBundle> {
  return request<MemoryBundle>("/export/bundle");
}

export async function importBundle(bundle: unknown): Promise<BundleImportResponse> {
  return request<BundleImportResponse>("/import/bundle", {
    method: "POST",
    body: JSON.stringify(bundle),
  });
}

// ── Telemetry ─────────────────────────────────────────────────────────────────

export interface TelemetryDay {
  date: string;
  searches: number;
  retrievals: number;
  facts_reviewed: number;
  canonical_created: number;
  mcp_retrievals: number;
  ui_retrievals: number;
}

export interface TelemetrySummary {
  days: number;
  summary: TelemetryDay[];
}

export async function getTelemetrySummary(days = 30): Promise<TelemetrySummary> {
  return request<TelemetrySummary>(`/telemetry/summary?days=${days}`);
}
