import * as React from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getSettings, validateKey, ApiError, type SettingsKeyStatus } from "@/lib/api";
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

export function SettingsPage() {
  const [providers, setProviders] = React.useState<Record<Provider, ProviderState>>({
    openai: { ...DEFAULT_PROVIDER_STATE },
    anthropic: { ...DEFAULT_PROVIDER_STATE },
    ollama: { ...DEFAULT_PROVIDER_STATE },
  });
  const [isLoading, setIsLoading] = React.useState(true);

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

  const updateProvider = React.useCallback((p: Provider, patch: Partial<ProviderState>) => {
    setProviders((prev) => ({ ...prev, [p]: { ...prev[p], ...patch } }));
  }, []);

  const handleValidate = React.useCallback(async (provider: Provider) => {
    // Capture input values BEFORE the optimistic state update to avoid stale closure reads
    const { keyInput, baseUrl } = providers[provider];
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
  }, [providers]);

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
