import * as React from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  getSettings,
  validateKey,
  getTelemetrySummary,
  listBackups,
  triggerBackup,
  restoreBackup,
  ApiError,
  type BackupItem,
  type SettingsKeyStatus,
  type TelemetrySummary,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Provider = "openai" | "anthropic" | "ollama";

interface ProviderState {
  keyInput: string;
  baseUrl: string; // Ollama only
  isValidating: boolean;
  status: SettingsKeyStatus | null;
  error: string | null;
}

const DEFAULT_PROVIDER_STATE: ProviderState = {
  keyInput: "",
  baseUrl: "",
  isValidating: false,
  status: null,
  error: null,
};

function StatusBadge({ status }: { status: string | null | undefined }) {
  if (!status || status === "unchecked") {
    return <Badge variant="outline">Not validated</Badge>;
  }
  if (status === "valid") return <Badge variant="success">Valid</Badge>;
  if (status === "insufficient_permissions") return <Badge variant="warning">Insufficient permissions</Badge>;
  return <Badge variant="destructive">Invalid</Badge>;
}

const PROVIDERS_CONFIG: Array<{
  id: Provider;
  label: string;
  description: string;
  keyLabel: string;
  keyPlaceholder: string;
  hasBaseUrl: boolean;
}> = [
  {
    id: "openai",
    label: "OpenAI",
    description: "Used for embeddings (text-embedding-3-small) and summarization/extraction.",
    keyLabel: "API Key",
    keyPlaceholder: "sk-…",
    hasBaseUrl: false,
  },
  {
    id: "anthropic",
    label: "Anthropic",
    description: "Used for summarization and fact extraction (Claude models).",
    keyLabel: "API Key",
    keyPlaceholder: "sk-ant-…",
    hasBaseUrl: false,
  },
  {
    id: "ollama",
    label: "Ollama",
    description: "Local Ollama instance for high-privacy processing (no data leaves your machine).",
    keyLabel: "API Key (optional)",
    keyPlaceholder: "Leave empty if no auth required",
    hasBaseUrl: true,
  },
];

function TelemetrySection({
  telemetry7,
  telemetryAll,
  telemetryLoading,
  verboseAudit,
  onVerboseAuditChange,
}: {
  telemetry7: TelemetrySummary | null;
  telemetryAll: TelemetrySummary | null;
  telemetryLoading: boolean;
  verboseAudit: boolean;
  onVerboseAuditChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  const searches7d = telemetry7 ? telemetry7.summary.reduce((s, d) => s + d.searches, 0) : 0;
  const retrievals7d = telemetry7 ? telemetry7.summary.reduce((s, d) => s + d.retrievals, 0) : 0;
  const factsTotal = telemetryAll ? telemetryAll.summary.reduce((s, d) => s + d.facts_reviewed, 0) : 0;
  const canonicalTotal = telemetryAll ? telemetryAll.summary.reduce((s, d) => s + d.canonical_created, 0) : 0;
  const mcpTotal = telemetryAll ? telemetryAll.summary.reduce((s, d) => s + d.mcp_retrievals, 0) : 0;
  const uiTotal = telemetryAll ? telemetryAll.summary.reduce((s, d) => s + d.ui_retrievals, 0) : 0;

  const hasData = telemetry7 !== null || telemetryAll !== null;

  return (
    <section className="mt-10" aria-labelledby="telemetry-heading">
      <h2 id="telemetry-heading" className="text-lg font-semibold mb-1">Local Telemetry</h2>
      <p className="text-sm text-muted-foreground mb-4">
        Usage metrics collected locally.{" "}
        <strong>Telemetry never leaves this machine.</strong>
      </p>

      {telemetryLoading ? (
        <p className="text-sm text-muted-foreground">Loading telemetry…</p>
      ) : !hasData ? (
        <p className="text-sm text-muted-foreground">Telemetry available after processing begins.</p>
      ) : (
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div>
            <dt className="text-muted-foreground">Searches (last 7 days)</dt>
            <dd className="font-semibold">{searches7d}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Retrievals (last 7 days)</dt>
            <dd className="font-semibold">{retrievals7d}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Facts reviewed (total)</dt>
            <dd className="font-semibold">{factsTotal}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Canonical items created (total)</dt>
            <dd className="font-semibold">{canonicalTotal}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">MCP retrievals (total)</dt>
            <dd className="font-semibold">{mcpTotal}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">UI retrievals (total)</dt>
            <dd className="font-semibold">{uiTotal}</dd>
          </div>
        </dl>
      )}

      {/* Verbose audit toggle */}
      <div className="mt-5 flex items-center gap-3">
        <input
          id="verbose-audit-toggle"
          type="checkbox"
          checked={verboseAudit}
          onChange={onVerboseAuditChange}
          className="h-4 w-4 rounded border-input accent-primary"
        />
        <label htmlFor="verbose-audit-toggle" className="text-sm">
          Verbose audit logging{" "}
          <span className="text-muted-foreground">(logs additional metadata per event — client-side preference only in v1)</span>
        </label>
      </div>
    </section>
  );
}

function formatBackupSize(sizeBytes: number) {
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  const kib = sizeBytes / 1024;
  if (kib < 1024) return `${kib.toFixed(1)} KiB`;
  return `${(kib / 1024).toFixed(1)} MiB`;
}

function BackupRestoreSection() {
  const [backups, setBackups] = React.useState<BackupItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [acting, setActing] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const loadBackups = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listBackups();
      setBackups(result.backups);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load backups");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadBackups();
  }, [loadBackups]);

  async function handleCreateBackup() {
    setActing("backup");
    setMessage(null);
    setError(null);
    try {
      const result = await triggerBackup();
      setMessage(`Created backup ${result.filename}.`);
      await loadBackups();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Backup failed");
    } finally {
      setActing(null);
    }
  }

  async function handleRestore(backup: BackupItem) {
    const warning = backup.has_post_deletion_events
      ? " This backup predates one or more deletion events and may restore data that was later removed."
      : "";
    if (!globalThis.confirm(`Restore backup ${backup.filename}?${warning} The app may need to be restarted after restore.`)) return;

    setActing(backup.filename);
    setMessage(null);
    setError(null);
    try {
      await restoreBackup(backup.filename);
      setMessage(`Restore requested for ${backup.filename}. Restart the app if the UI still shows old data.`);
      await loadBackups();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Restore failed");
    } finally {
      setActing(null);
    }
  }

  return (
    <section className="mt-10" aria-labelledby="backup-restore-heading">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 id="backup-restore-heading" className="text-lg font-semibold mb-1">Backup and Restore</h2>
          <p className="text-sm text-muted-foreground">
            Create a local backup on demand, review the retained backup inventory, and restore a known-good copy.
          </p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={loadBackups} disabled={loading || acting !== null}>
            Refresh
          </Button>
          <Button type="button" size="sm" onClick={handleCreateBackup} disabled={acting !== null}>
            {acting === "backup" ? "Creating…" : "Create backup now"}
          </Button>
        </div>
      </div>

      {message && (
        <output className="mt-4 block rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
          {message}
        </output>
      )}
      {error && (
        <p role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {loading && <p className="mt-4 text-sm text-muted-foreground">Loading backups…</p>}

      {!loading && backups.length === 0 && (
        <p className="mt-4 text-sm text-muted-foreground">No backups found yet. Create one before testing restore.</p>
      )}

      {!loading && backups.length > 0 && (
        <ul className="mt-4 overflow-hidden rounded-lg border" aria-label="Available backups">
          {backups.map((backup) => {
            const createdLabel = backup.created_at ? new Date(backup.created_at).toLocaleString() : "Unknown time";
            return (
              <li key={backup.filename} className="flex flex-col gap-3 border-b p-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="break-all text-sm font-medium">{backup.filename}</span>
                    {backup.has_post_deletion_events && <Badge variant="warning">May include deleted data</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {createdLabel} · {formatBackupSize(backup.size_bytes)}
                  </p>
                  {backup.has_post_deletion_events && (
                    <p className="text-xs text-yellow-700">
                      This backup predates deletion events. Review privacy impact before restoring it.
                    </p>
                  )}
                </div>
                <Button
                  type="button"
                  variant={backup.has_post_deletion_events ? "outline" : "default"}
                  size="sm"
                  onClick={() => handleRestore(backup)}
                  disabled={acting !== null}
                  aria-label={`Restore backup ${backup.filename}`}
                >
                  {acting === backup.filename ? "Restoring…" : "Restore"}
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export function SettingsPage() {
  const [providers, setProviders] = React.useState<Record<Provider, ProviderState>>({
    openai: { ...DEFAULT_PROVIDER_STATE },
    anthropic: { ...DEFAULT_PROVIDER_STATE },
    ollama: { ...DEFAULT_PROVIDER_STATE },
  });
  const [isLoading, setIsLoading] = React.useState(true);
  const [telemetry7, setTelemetry7] = React.useState<TelemetrySummary | null>(null);
  const [telemetryAll, setTelemetryAll] = React.useState<TelemetrySummary | null>(null);
  const [telemetryLoading, setTelemetryLoading] = React.useState(true);
  const [verboseAudit, setVerboseAudit] = React.useState<boolean>(
    () => localStorage.getItem("verbose_audit") === "true"
  );

  // Load current settings on mount
  React.useEffect(() => {
    async function load() {
      try {
        const settings = await getSettings();
        setProviders((prev) => ({
          openai: { ...prev.openai, status: settings.openai },
          anthropic: { ...prev.anthropic, status: settings.anthropic },
          ollama: {
            ...prev.ollama,
            status: settings.ollama,
            baseUrl: settings.ollama.base_url ?? "",
          },
        }));
      } catch {
        // Settings load failure is non-fatal — user can still attempt validation
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  React.useEffect(() => {
    async function loadTelemetry() {
      setTelemetryLoading(true);
      try {
        const [t7, tAll] = await Promise.all([
          getTelemetrySummary(7),
          getTelemetrySummary(365),
        ]);
        setTelemetry7(t7);
        setTelemetryAll(tAll);
      } catch {
        // Non-fatal
      } finally {
        setTelemetryLoading(false);
      }
    }
    loadTelemetry();
  }, []);

  const updateProvider = React.useCallback((p: Provider, patch: Partial<ProviderState>) => {
    setProviders((prev) => ({ ...prev, [p]: { ...prev[p], ...patch } }));
  }, []);

  // Ref keeps latest providers snapshot so handleValidate never captures a stale closure
  const providersRef = React.useRef(providers);
  React.useEffect(() => { providersRef.current = providers; }, [providers]);

  const handleValidate = React.useCallback(async (provider: Provider) => {
    // Read from ref so we always get the current keyInput/baseUrl, even if state updated
    const { keyInput, baseUrl } = providersRef.current[provider];
    setProviders((prev) => ({ ...prev, [provider]: { ...prev[provider], isValidating: true, error: null } }));
    try {
      const result = await validateKey({
        provider,
        api_key: keyInput,
        base_url: provider === "ollama" ? baseUrl : undefined,
      });
      setProviders((prev) => ({
        ...prev,
        [provider]: {
          ...prev[provider],
          isValidating: false,
          status: {
            configured: true,
            fingerprint: result.status === "valid" ? "****" : null,
            validation_status: result.status,
            validated_at: new Date().toISOString(),
          },
          error: result.status !== "valid" ? result.message : null,
          keyInput: "", // Clear key from input after validation
        },
      }));
    } catch (err) {
      setProviders((prev) => ({
        ...prev,
        [provider]: {
          ...prev[provider],
          isValidating: false,
          error: err instanceof ApiError ? err.detail : "Validation failed. Please try again.",
        },
      }));
    }
  }, []);

  function handleVerboseAuditChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.checked;
    setVerboseAudit(val);
    localStorage.setItem("verbose_audit", String(val));
  }

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Settings</h1>
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Settings</h1>
      <p className="text-sm text-muted-foreground mb-8">
        Configure API provider keys. Keys are validated with a lightweight test call and{" "}
        <strong>never stored in the database</strong> — only the last 4 characters are saved as a
        fingerprint. The system works for ingestion and browsing without any keys configured.
      </p>

      <div className="flex flex-col gap-6">
        {PROVIDERS_CONFIG.map((config) => {
          const state = providers[config.id];
          const isConfigured = state.status?.configured ?? false;
          const fingerprint = state.status?.fingerprint;
          const validationStatus = state.status?.validation_status;

          return (
            <section
              key={config.id}
              className="rounded-lg border border-border p-5"
              aria-label={`${config.label} configuration`}
            >
              <div className="flex items-start justify-between mb-1">
                <h2 className="text-base font-semibold">{config.label}</h2>
                <div className="flex items-center gap-2">
                  {isConfigured && fingerprint && (
                    <span className="text-xs text-muted-foreground font-mono">
                      ****{fingerprint}
                    </span>
                  )}
                  <StatusBadge status={validationStatus} />
                </div>
              </div>
              <p className="text-sm text-muted-foreground mb-4">{config.description}</p>

              <div className="flex flex-col gap-3">
                {config.hasBaseUrl && (
                  <div className="flex flex-col gap-1.5">
                    <label
                      htmlFor={`${config.id}-base-url`}
                      className="text-sm font-medium"
                    >
                      Endpoint URL
                    </label>
                    <input
                      id={`${config.id}-base-url`}
                      type="url"
                      value={state.baseUrl}
                      onChange={(e) => updateProvider(config.id, { baseUrl: e.target.value })}
                      placeholder="http://localhost:11434"
                      className="rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                )}

                <div className="flex gap-2">
                  <div className="flex-1 flex flex-col gap-1.5">
                    <label
                      htmlFor={`${config.id}-key`}
                      className="text-sm font-medium"
                    >
                      {config.keyLabel}
                    </label>
                    <input
                      id={`${config.id}-key`}
                      type="password"
                      value={state.keyInput}
                      onChange={(e) => updateProvider(config.id, { keyInput: e.target.value })}
                      placeholder={
                        isConfigured
                          ? `Currently set (ends in ****${fingerprint ?? "????"}) — enter new key to update`
                          : config.keyPlaceholder
                      }
                      autoComplete="off"
                      className="rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div className="flex items-end">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={
                        state.isValidating ||
                        (config.id !== "ollama" && !state.keyInput.trim()) ||
                        (config.id === "ollama" && !state.baseUrl.trim())
                      }
                      onClick={() => handleValidate(config.id)}
                      aria-label={`Validate ${config.label}${state.isValidating ? " (validating)" : ""}`}
                    >
                      {state.isValidating ? "Validating…" : "Validate"}
                    </Button>
                  </div>
                </div>

                {state.error && (
                  <p
                    role="alert"
                    className={cn(
                      "text-xs rounded px-2 py-1.5",
                      validationStatus === "insufficient_permissions"
                        ? "bg-yellow-50 text-yellow-700"
                        : "bg-red-50 text-red-600"
                    )}
                  >
                    {state.error}
                  </p>
                )}
              </div>
            </section>
          );
        })}
      </div>

      {/* Telemetry Section */}
      <TelemetrySection telemetry7={telemetry7} telemetryAll={telemetryAll} telemetryLoading={telemetryLoading} verboseAudit={verboseAudit} onVerboseAuditChange={handleVerboseAuditChange} />

      <BackupRestoreSection />

      <div className="mt-8 rounded-lg border border-muted bg-muted/30 px-4 py-3">
        <p className="text-xs text-muted-foreground">
          <strong>No keys required</strong> — Recalium is fully usable for ingestion, archive
          browsing, and keyword search without any configured keys. Provider keys are only needed
          for AI-powered summarization, fact extraction, and semantic search (Phase 2+).
        </p>
      </div>
    </div>
  );
}
