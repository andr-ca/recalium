/**
 * WizardPage — first-run wizard.
 *
 * BYOK-01: Explains BYOK model, cost estimates, provider links.
 * BYOK-06: Shows token cost estimate before bulk import.
 *
 * Steps:
 *   1. Welcome + BYOK explanation + cost estimates + provider links
 *   2. Key setup (optional — can skip)
 *   3. First import with cost estimate preview
 *
 * Shown when: archive empty + no key configured + localStorage('wizard_dismissed') not set.
 * Dismissed by: completing step 3, clicking "Skip wizard", or clicking the X button.
 */
import * as React from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  validateKey,
  ingestText,
  ingestFile,
  ApiError,
} from "@/lib/api";

const PROVIDER_LINKS = {
  openai: {
    label: "OpenAI",
    url: "https://platform.openai.com/api-keys",
    costPer100: "$0.02",
    detail: "gpt-4o-mini • ~$0.15/1M tokens",
  },
  anthropic: {
    label: "Anthropic",
    url: "https://console.anthropic.com/settings/keys",
    costPer100: "$0.03",
    detail: "claude-3-haiku • ~$0.25/1M tokens",
  },
  ollama: {
    label: "Ollama (local)",
    url: "https://ollama.com/download",
    costPer100: "$0.00",
    detail: "Runs on your machine — no API costs",
  },
} as const;

export function WizardPage() {
  const navigate = useNavigate();
  const [step, setStep] = React.useState<1 | 2 | 3>(1);
  const [keyInput, setKeyInput] = React.useState("");
  const [provider, setProvider] = React.useState<"openai" | "anthropic" | "ollama">("openai");
  const [baseUrl, setBaseUrl] = React.useState("http://localhost:11434");
  const [isValidating, setIsValidating] = React.useState(false);
  const [validationResult, setValidationResult] = React.useState<string | null>(null);
  const [importText, setImportText] = React.useState("");
  const [importFile, setImportFile] = React.useState<File | null>(null);
  const [isImporting, setIsImporting] = React.useState(false);
  const [importError, setImportError] = React.useState<string | null>(null);
  const [importDone, setImportDone] = React.useState(false);
  const stepTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup pending step-transition timer on unmount
  React.useEffect(() => {
    return () => {
      if (stepTimerRef.current !== null) clearTimeout(stepTimerRef.current);
    };
  }, []);

  function dismiss() {
    if (stepTimerRef.current !== null) clearTimeout(stepTimerRef.current);
    localStorage.setItem("wizard_dismissed", "1");
    navigate("/");
  }

  async function handleValidate() {
    setIsValidating(true);
    setValidationResult(null);
    try {
      const result = await validateKey({
        provider,
        api_key: keyInput,
        base_url: provider === "ollama" ? baseUrl : undefined,
      });
      setValidationResult(result.status === "valid" ? "valid" : result.message);
      if (result.status === "valid") {
        stepTimerRef.current = setTimeout(() => setStep(3), 800);
      }
    } catch (err) {
      setValidationResult(err instanceof ApiError ? err.detail : "Validation failed");
    } finally {
      setIsValidating(false);
    }
  }

  async function handleImport() {
    setIsImporting(true);
    setImportError(null);
    try {
      if (importFile) {
        await ingestFile(importFile);
      } else if (importText.trim()) {
        await ingestText(importText.trim(), "First conversation");
      } else {
        setImportError("Please paste text or upload a file.");
        setIsImporting(false);
        return;
      }
      setImportDone(true);
    } catch (err) {
      setImportError(err instanceof ApiError ? err.detail : "Import failed");
    } finally {
      setIsImporting(false);
    }
  }

  const costPreview = React.useMemo(() => {
    if (!importFile && !importText.trim()) return null;
    const chars = importFile ? importFile.size : importText.length;
    const tokens = Math.ceil(chars / 4);
    const costUsd = tokens * 0.00000015;
    return { tokens, costUsd };
  }, [importText, importFile]);

  return (
    <div
      className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="First-run wizard"
    >
      <div className="bg-background border rounded-xl shadow-xl max-w-lg w-full p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">Welcome to Recalium</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Step {step} of 3
            </p>
          </div>
          <button
            type="button"
            onClick={dismiss}
            aria-label="Close wizard"
            className="text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary rounded p-1"
          >
            ✕
          </button>
        </div>

        {/* Step indicator */}
        <div className="flex gap-1" role="list" aria-label="Wizard steps">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              role="listitem"
              aria-label={`Step ${s}${s === step ? " (current)" : s < step ? " (complete)" : ""}`}
              className={`h-1 flex-1 rounded-full ${
                s <= step ? "bg-primary" : "bg-muted"
              }`}
            />
          ))}
        </div>

        {/* Step 1: Welcome + BYOK explanation */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold mb-1">Your keys, your data</h2>
              <p className="text-sm text-muted-foreground">
                Recalium uses <strong>Bring Your Own Key (BYOK)</strong> — your conversations are
                processed using your own API keys. No data ever goes to Recalium servers.
              </p>
            </div>

            <div className="rounded-lg border p-4 space-y-3">
              <h3 className="text-sm font-medium">Estimated cost per 100 conversations</h3>
              <div className="space-y-2">
                {Object.values(PROVIDER_LINKS).map((p) => (
                  <div key={p.label} className="flex items-center justify-between text-sm">
                    <a
                      href={p.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary rounded"
                      aria-label={`Get ${p.label} API key (opens in new tab)`}
                    >
                      {p.label} ↗
                    </a>
                    <span className="text-muted-foreground text-xs">{p.detail}</span>
                    <Badge variant="outline">{p.costPer100}</Badge>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                * Estimates based on average 2,000-token conversation. Actual costs depend on
                your content length and chosen model.
              </p>
            </div>

            <p className="text-sm text-muted-foreground">
              <strong>No key required</strong> to start — keyword search and ingestion work
              without any API keys. Semantic search and AI summarization require a key.
            </p>

            <div className="flex gap-2 pt-2">
              <Button onClick={() => setStep(2)} className="flex-1" aria-label="Continue to key setup">
                Set up a key
              </Button>
              <Button variant="outline" onClick={() => setStep(3)} aria-label="Skip key setup">
                Skip for now
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: Key setup */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold mb-1">Configure a provider key</h2>
              <p className="text-sm text-muted-foreground">
                Enter your API key below. It will be validated with a test call and stored only
                in your <code className="text-xs font-mono">.env</code> file — never in the database.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="wizard-provider" className="text-sm font-medium">Provider</label>
                <select
                  id="wizard-provider"
                  value={provider}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (v === "openai" || v === "anthropic" || v === "ollama") setProvider(v);
                  }}
                  className="rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="ollama">Ollama (local)</option>
                </select>
              </div>

              {provider === "ollama" && (
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="wizard-base-url" className="text-sm font-medium">Ollama URL</label>
                  <input
                    id="wizard-base-url"
                    type="url"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="http://localhost:11434"
                    className="rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <label htmlFor="wizard-key" className="text-sm font-medium">
                  API Key{provider === "ollama" ? " (optional)" : ""}
                </label>
                <input
                  id="wizard-key"
                  type="password"
                  value={keyInput}
                  onChange={(e) => setKeyInput(e.target.value)}
                  placeholder={provider === "openai" ? "sk-…" : provider === "anthropic" ? "sk-ant-…" : "Leave empty if no auth"}
                  autoComplete="off"
                  className="rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              {validationResult && (
                <p
                  role="alert"
                  className={`text-xs rounded px-2 py-1.5 ${
                    validationResult === "valid"
                      ? "bg-green-50 text-green-700"
                      : "bg-red-50 text-red-600"
                  }`}
                >
                  {validationResult === "valid" ? "Key validated! Continuing…" : validationResult}
                </p>
              )}
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                onClick={handleValidate}
                disabled={isValidating || (!keyInput.trim() && provider !== "ollama")}
                className="flex-1"
                aria-label={`Validate ${provider} key${isValidating ? " (validating)" : ""}`}
              >
                {isValidating ? "Validating…" : "Validate & continue"}
              </Button>
              <Button variant="outline" onClick={() => setStep(3)} aria-label="Skip key validation">
                Skip
              </Button>
              <Button variant="outline" onClick={() => setStep(1)} aria-label="Go back to step 1">
                Back
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: First import */}
        {step === 3 && !importDone && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold mb-1">Import your first conversation</h2>
              <p className="text-sm text-muted-foreground">
                Paste text below or upload a ChatGPT/Claude JSON export to get started.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="wizard-text" className="text-sm font-medium">Paste conversation text</label>
                <textarea
                  id="wizard-text"
                  value={importText}
                  onChange={(e) => {
                    setImportText(e.target.value);
                    setImportFile(null);
                  }}
                  rows={4}
                  placeholder="Paste any conversation text here…"
                  className="rounded-md border border-input px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                />
              </div>

              <div className="text-center text-xs text-muted-foreground">— or —</div>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="wizard-file" className="text-sm font-medium">Upload a file</label>
                <input
                  id="wizard-file"
                  type="file"
                  accept=".json,.txt,.md"
                  onChange={(e) => {
                    const f = e.target.files?.[0] ?? null;
                    setImportFile(f);
                    if (f) setImportText("");
                  }}
                  className="text-sm file:mr-3 file:rounded file:border-0 file:bg-primary file:text-primary-foreground file:px-3 file:py-1 file:text-xs"
                  aria-label="Upload conversation file (JSON, TXT, or Markdown)"
                />
              </div>

              {/* BYOK-06: Cost estimate before import */}
              {costPreview && (
                <div
                  className="rounded-md bg-muted/50 border px-3 py-2 text-xs text-muted-foreground"
                  role="note"
                  aria-label="Estimated processing cost"
                >
                  <strong>Estimated cost:</strong>{" "}
                  ~{costPreview.tokens.toLocaleString()} tokens ≈ ${costPreview.costUsd.toFixed(4)}{" "}
                  (OpenAI gpt-4o-mini estimate, order-of-magnitude)
                </div>
              )}

              {importError && (
                <p role="alert" className="text-xs text-red-600 bg-red-50 rounded px-2 py-1.5">
                  {importError}
                </p>
              )}
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                onClick={handleImport}
                disabled={isImporting || (!importText.trim() && !importFile)}
                className="flex-1"
                aria-label={`Import conversation${isImporting ? " (importing)" : ""}`}
              >
                {isImporting ? "Importing…" : "Import"}
              </Button>
              <Button variant="outline" onClick={dismiss} aria-label="Skip import and go to dashboard">
                Skip
              </Button>
            </div>
          </div>
        )}

        {/* Step 3 done */}
        {step === 3 && importDone && (
          <div className="space-y-4 text-center">
            <div className="text-4xl" aria-hidden="true">✓</div>
            <h2 className="text-base font-semibold">You're set up!</h2>
            <p className="text-sm text-muted-foreground">
              Your conversation is being processed. Head to Search to try your first query.
            </p>
            <Button onClick={dismiss} className="w-full" aria-label="Go to dashboard">
              Go to dashboard
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
