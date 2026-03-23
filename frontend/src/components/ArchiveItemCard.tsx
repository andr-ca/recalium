import * as React from "react";
import { Badge } from "@/components/ui/badge";
import type { ArchiveItem } from "@/lib/api";
import { retryJob } from "@/lib/api";

interface ArchiveItemCardProps {
  item: ArchiveItem;
  onRetried?: () => void;
}

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const SOURCE_BADGE_VARIANTS: Record<string, "default" | "secondary" | "outline"> = {
  ChatGPT: "default",
  Claude: "secondary",
  JSON: "outline",
  "Text Paste": "outline",
  Markdown: "outline",
};

type BadgeVariant = "success" | "warning" | "destructive" | "secondary";
const STATUS_BADGE_VARIANTS: Record<string, BadgeVariant> = {
  Ingested: "secondary",
  Processing: "warning",
  Done: "success",
  Failed: "destructive",
  "Pending Provider": "warning",
};

export function ArchiveItemCard({ item, onRetried }: ArchiveItemCardProps) {
  const sourceBadgeVariant = SOURCE_BADGE_VARIANTS[item.source_type] ?? "outline";
  const statusVariant: BadgeVariant = STATUS_BADGE_VARIANTS[item.status_badge] ?? "secondary";
  const [retrying, setRetrying] = React.useState(false);

  const handleRetry = async () => {
    if (!item.job_id || retrying) return;
    setRetrying(true);
    try {
      await retryJob(item.job_id);
      onRetried?.();
    } catch {
      // Retry failed — page will refresh on next poll cycle
    } finally {
      setRetrying(false);
    }
  };

  const showRetryButton = item.status_badge === "Failed" && item.job_id != null;

  return (
    <article
      className="rounded-lg border border-border bg-card px-5 py-4 flex items-start gap-4 hover:bg-muted/30 transition-colors"
      aria-label={`Archive item: ${item.source_name ?? item.source_type}`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <Badge variant={sourceBadgeVariant}>{item.source_type}</Badge>
          <Badge variant={statusVariant}>{item.status_badge}</Badge>
          {showRetryButton && (
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="rounded-md border border-destructive text-destructive px-2 py-0.5 text-xs hover:bg-destructive/10 disabled:opacity-50 transition-colors"
              aria-label="Retry failed pipeline job"
            >
              {retrying ? "Retrying…" : "Retry"}
            </button>
          )}
        </div>
        <h2 className="text-sm font-semibold truncate">
          {item.source_name ?? item.source_type}
        </h2>
        <p className="text-xs text-muted-foreground mt-1">
          {item.conversation_count === 1
            ? "1 conversation"
            : `${item.conversation_count} conversations`}{" "}
          · Ingested {formatDate(item.ingested_at)}
        </p>
        {item.status_badge === "Failed" && item.job_error && (
          <p className="text-xs text-destructive mt-1 truncate" title={item.job_error}>
            {item.job_error.slice(0, 120)}
          </p>
        )}
      </div>
    </article>
  );
}
