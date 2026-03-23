import { Badge } from "@/components/ui/badge";
import type { ArchiveItem } from "@/lib/api";

interface ArchiveItemCardProps {
  item: ArchiveItem;
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

export function ArchiveItemCard({ item }: ArchiveItemCardProps) {
  const badgeVariant = SOURCE_BADGE_VARIANTS[item.source_type] ?? "outline";

  return (
    <article
      className="rounded-lg border border-border bg-card px-5 py-4 flex items-start gap-4 hover:bg-muted/30 transition-colors"
      aria-label={`Archive item: ${item.source_name ?? item.source_type}`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <Badge variant={badgeVariant}>{item.source_type}</Badge>
          <Badge variant="success">{item.status_badge}</Badge>
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
      </div>
    </article>
  );
}
