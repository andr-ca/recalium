import * as React from "react";
import { ArchiveItemCard } from "@/components/ArchiveItemCard";
import { listArchive, deleteArchiveItem, ApiError, type ArchiveItem } from "@/lib/api";

type LoadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; items: ArchiveItem[]; total: number }
  | { status: "error"; message: string };

const PAGE_SIZE = 50;
const PROCESSING_STATUSES: ReadonlyArray<string> = ["Processing"];

export function ArchivePage() {
  const [state, setState] = React.useState<LoadState>({ status: "idle" });
  const [searchQuery, setSearchQuery] = React.useState("");
  const [offset, setOffset] = React.useState(0);
  const [showDeleted, setShowDeleted] = React.useState(false);

  const loadArchive = React.useCallback(async (q: string, off: number, includeDeleted: boolean) => {
    setState({ status: "loading" });
    try {
      const result = await listArchive({
        offset: off,
        limit: PAGE_SIZE,
        q: q || undefined,
        include_deleted: includeDeleted || undefined,
      });
      setState({ status: "success", items: result.items, total: result.total });
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : "Failed to load archive.";
      setState({ status: "error", message });
    }
  }, []);

  // Initial load
  React.useEffect(() => {
    loadArchive("", 0, false);
  }, [loadArchive]);

  // Reload when showDeleted changes
  React.useEffect(() => {
    setOffset(0);
    loadArchive(searchQuery, 0, showDeleted);
  }, [showDeleted, searchQuery, loadArchive]);

  // Auto-refresh every 5s while any item is still processing
  React.useEffect(() => {
    if (state.status !== "success") return;

    const hasProcessing = state.items.some((item) =>
      PROCESSING_STATUSES.includes(item.status_badge)
    );
    if (!hasProcessing) return;

    const timer = setInterval(() => {
      loadArchive(searchQuery, offset, showDeleted);
    }, 5000);

    return () => clearInterval(timer);
  }, [state, searchQuery, offset, showDeleted, loadArchive]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    loadArchive(searchQuery, 0, showDeleted);
  };

  const handlePrevPage = () => {
    const newOffset = Math.max(0, offset - PAGE_SIZE);
    setOffset(newOffset);
    loadArchive(searchQuery, newOffset, showDeleted);
  };

  const handleNextPage = () => {
    if (state.status !== "success") return;
    const newOffset = offset + PAGE_SIZE;
    if (newOffset < state.total) {
      setOffset(newOffset);
      loadArchive(searchQuery, newOffset, showDeleted);
    }
  };

  const handleDelete = async (id: string) => {
    // Throws on failure — ArchiveItemCard catches and displays the error inline
    await deleteArchiveItem(id);
    // Remove item from local state on success
    setState((prev) => {
      if (prev.status !== "success") return prev;
      return {
        ...prev,
        items: prev.items.filter((item) => item.id !== id),
        total: prev.total - 1,
      };
    });
  };

  const total = state.status === "success" ? state.total : 0;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Archive</h1>
        {state.status === "success" && (
          <span className="text-sm text-muted-foreground">
            {state.total} item{state.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter by source name…"
          aria-label="Search archive"
          className="flex-1 rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <button
          type="submit"
          className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          Search
        </button>
      </form>

      {/* Show deleted toggle */}
      <label className="flex items-center gap-2 mb-6 text-sm text-muted-foreground cursor-pointer w-fit">
        <input
          type="checkbox"
          checked={showDeleted}
          onChange={(e) => setShowDeleted(e.target.checked)}
          className="rounded border-input"
          aria-label="Show deleted items"
        />
        Show deleted items
      </label>

      {/* States */}
      {state.status === "loading" && (
        <div
          role="status"
          aria-label="Loading archive"
          className="flex items-center justify-center py-12 text-muted-foreground text-sm"
        >
          Loading…
        </div>
      )}

      {state.status === "error" && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {state.message}
        </div>
      )}

      {state.status === "success" && state.items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <p className="text-lg font-semibold mb-2">No items yet</p>
          <p className="text-sm text-muted-foreground">
            {searchQuery
              ? `No items match "${searchQuery}". Try a different search.`
              : "Ingest your first conversation to get started."}
          </p>
        </div>
      )}

      {state.status === "success" && state.items.length > 0 && (
        <>
          <ul className="flex flex-col gap-3" aria-label="Archive items">
            {state.items.map((item) => {
              const isDeleted = item.deleted_at != null;
              return (
                <li key={item.id}>
                  <ArchiveItemCard
                    item={item}
                    onRetried={() => loadArchive(searchQuery, offset, showDeleted)}
                    onDelete={isDeleted ? undefined : handleDelete}
                    isDeleted={isDeleted}
                  />
                </li>
              );
            })}
          </ul>

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className="flex items-center justify-between mt-6 text-sm text-muted-foreground">
              <span>
                Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handlePrevPage}
                  disabled={offset === 0}
                  className="rounded-md border px-3 py-1.5 text-xs hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
                  aria-label="Previous page"
                >
                  ← Previous
                </button>
                <button
                  type="button"
                  onClick={handleNextPage}
                  disabled={offset + PAGE_SIZE >= total}
                  className="rounded-md border px-3 py-1.5 text-xs hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
                  aria-label="Next page"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
