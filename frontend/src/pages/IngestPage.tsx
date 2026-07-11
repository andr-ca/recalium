import * as React from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Toast } from "@/components/ui/toast";
import { ingestText, ingestFile, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

type Tab = "paste" | "file";

export function IngestPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = React.useState<Tab>("paste");
  const [pasteContent, setPasteContent] = React.useState("");
  const [sourceName, setSourceName] = React.useState("");
  const [isDragging, setIsDragging] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [toast, setToast] = React.useState<{ message: string; type: "success" | "error" } | null>(null);
  const dismissToast = React.useCallback(() => setToast(null), []);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // Roving-tabindex keyboard navigation for the ingest tabs (a11y — GPT5.6 #14)
  const tabOrder = React.useMemo<Tab[]>(() => ["paste", "file"], []);
  const tabRefs = React.useRef<Record<Tab, HTMLButtonElement | null>>({ paste: null, file: null });
  const handleTabKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    const idx = tabOrder.indexOf(activeTab);
    let next: number;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (idx + 1) % tabOrder.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = (idx - 1 + tabOrder.length) % tabOrder.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabOrder.length - 1;
    else return;
    e.preventDefault();
    const nextTab = tabOrder[next];
    setActiveTab(nextTab);
    tabRefs.current[nextTab]?.focus();
  };

  const handlePasteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pasteContent.trim()) return;
    setIsSubmitting(true);
    try {
      const result = await ingestText(pasteContent, sourceName || undefined);
      setToast({ message: `${result.item_count} conversation(s) ingested`, type: "success" });
      setTimeout(() => navigate("/archive"), 1500);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Ingest failed. Please try again.";
      setToast({ message: detail, type: "error" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileSubmit = async (file: File) => {
    setIsSubmitting(true);
    try {
      const result = await ingestFile(file);
      setToast({ message: `${result.item_count} conversation(s) ingested from ${file.name}`, type: "success" });
      setTimeout(() => navigate("/archive"), 1500);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "File ingest failed. Please try again.";
      setToast({ message: detail, type: "error" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSubmit(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSubmit(file);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Ingest Conversations</h1>

      {/* Tab switcher */}
      <div className="flex gap-1 mb-6 border-b" role="tablist" aria-label="Ingest method">
        {(["paste", "file"] as Tab[]).map((tab) => (
          <button
            key={tab}
            ref={(el) => { tabRefs.current[tab] = el; }}
            onClick={() => setActiveTab(tab)}
            onKeyDown={handleTabKeyDown}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-sm",
              activeTab === tab
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
            aria-selected={activeTab === tab}
            role="tab"
            tabIndex={activeTab === tab ? 0 : -1}
          >
            {tab === "paste" ? (
              <><FileText className="inline h-4 w-4 mr-1.5" aria-hidden="true" />Paste Text</>
            ) : (
              <><Upload className="inline h-4 w-4 mr-1.5" aria-hidden="true" />Upload File</>
            )}
          </button>
        ))}
      </div>

      {/* Paste tab */}
      {activeTab === "paste" && (
        <form onSubmit={handlePasteSubmit} className="flex flex-col gap-4" role="tabpanel" aria-label="Paste text tab">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="source-name" className="text-sm font-medium">
              Source name <span className="text-muted-foreground">(optional)</span>
            </label>
            <input
              id="source-name"
              type="text"
              value={sourceName}
              onChange={(e) => setSourceName(e.target.value)}
              placeholder="e.g. ChatGPT session 2026-01-15"
              className="rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="paste-content" className="text-sm font-medium">
              Content <span className="text-red-500">*</span>
            </label>
            <textarea
              id="paste-content"
              value={pasteContent}
              onChange={(e) => setPasteContent(e.target.value)}
              rows={12}
              placeholder="Paste plain text, Markdown, or JSON export here…"
              className="rounded-md border border-input px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary resize-vertical"
              required
            />
            <p className="text-xs text-muted-foreground">
              Supported: plain text, Markdown, ChatGPT JSON export, Claude JSON export, generic JSON
            </p>
          </div>
          <Button type="submit" disabled={isSubmitting || !pasteContent.trim()}>
            {isSubmitting ? "Ingesting…" : "Ingest"}
          </Button>
        </form>
      )}

      {/* File upload tab */}
      {activeTab === "file" && (
        <div className="flex flex-col gap-4" role="tabpanel" aria-label="Upload file tab">
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                fileInputRef.current?.click();
              }
            }}
            tabIndex={0}
            className={cn(
              "flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-12 cursor-pointer transition-colors",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary",
              isDragging
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/30 hover:border-primary/50"
            )}
            role="button"
            aria-label="Click or drag and drop a file to upload"
          >
            <Upload className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
            <div className="text-center">
              <p className="text-sm font-medium">
                {isDragging ? "Drop file here" : "Click to browse or drag and drop"}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Supported: .json, .txt, .md — max 50 MB
              </p>
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.txt,.md"
            className="hidden"
            onChange={handleFileInputChange}
            aria-label="File input"
          />
          {isSubmitting && (
            <p className="text-sm text-center text-muted-foreground">Uploading and ingesting…</p>
          )}
        </div>
      )}

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={dismissToast}
        />
      )}
    </div>
  );
}
