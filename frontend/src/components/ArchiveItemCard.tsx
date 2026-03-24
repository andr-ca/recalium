import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { retryJob, ApiError, type ArchiveItem } from "@/lib/api";

interface ArchiveItemCardProps {
  item: ArchiveItem;
  onRetried?: () => void;
  onDelete?: (id: string) => Promise<void>;
  isDeleted?: boolean;
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

export function ArchiveItemCard({ item, onRetried, onDelete, isDeleted = false }: ArchiveItemCardProps) {
  const sourceBadgeVariant = SOURCE_BADGE_VARIANTS[item.source_type] ?? "outline";
  const statusVariant: BadgeVariant = STATUS_BADGE_VARIANTS[item.status_badge] ?? "secondary";
  const [retrying, setRetrying] = React.useState(false);
  const [confirmDelete, setConfirmDelete] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [deleteError, setDeleteError] = React.useState<string | null>(null);

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

  const handleDeleteClick = () => {
    setDeleteError(null);
    setConfirmDelete(true);
  };

  const handleDeleteCancel = () => {
    setConfirmDelete(false);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!onDelete || isDeleting) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await onDelete(item.id);
    } catch (err) {
      const msg = err instanceof ApiError
        ? err.detail
        : err instanceof Error
        ? err.message
        : "Delete failed";
      setDeleteError(msg);
      setConfirmDelete(false);
    } finally {
      setIsDeleting(false);
    }
  };

  const showRetryButton = item.status_badge === "Failed" && item.job_id != null;

  return (
    <article
      className={cn(
        "rounded-lg border bg-card px-5 py-4 flex items-start gap-4 transition-colors",
        isDeleted
          ? "border-dashed border-border opacity-60"
          : "border-border hover:bg-muted/30"
      )}
      aria-label={`Archive item: ${item.source_name ?? item.source_type}`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <Badge variant={sourceBadgeVariant}>{item.source_type}</Badge>
          <Badge variant={statusVariant}>{item.status_badge}</Badge>
          {isDeleted && (
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground font-medium">
              Deleted
            </span>
          )}
          {showRetryButton && !isDeleted && (
            <button
              type="button"
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
        {deleteError && (
          <p className="text-xs text-destructive mt-1">{deleteError}</p>
        )}
        {confirmDelete && !isDeleted && (
          <div className="mt-2 flex items-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground">Delete this item?</span>
            <button
              type="button"
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
              className="rounded-md bg-destructive text-destructive-foreground px-2 py-0.5 text-xs hover:bg-destructive/90 disabled:opacity-50 transition-colors"
              aria-label="Confirm delete archive item"
            >
              {isDeleting ? "Deleting…" : "Confirm"}
            </button>
            <button
              type="button"
              onClick={handleDeleteCancel}
              disabled={isDeleting}
              className="rounded-md border border-border px-2 py-0.5 text-xs hover:bg-muted disabled:opacity-50 transition-colors"
              aria-label="Cancel delete"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {onDelete && !isDeleted && !confirmDelete && (
        <button
          type="button"
          onClick={handleDeleteClick}
          className="shrink-0 rounded-md border border-destructive/40 text-destructive px-2 py-1 text-xs hover:bg-destructive/10 transition-colors"
          aria-label={`Delete archive item: ${item.source_name ?? item.source_type}`}
        >
          Delete
        </button>
      )}
    </article>
  );
}
