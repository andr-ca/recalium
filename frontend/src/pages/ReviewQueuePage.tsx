import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { listReviewQueue, resolveReviewItem, dismissReviewItem, type ReviewQueueItem, ApiError } from "@/lib/api"

export function ReviewQueuePage() {
  const [items, setItems] = React.useState<ReviewQueueItem[]>([])
  const [loading, setLoading] = React.useState(true)
  const [acting, setActing] = React.useState<string | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [notes, setNotes] = React.useState<Record<string, string>>({})

  async function reload() {
    setLoading(true)
    setError(null)
    try {
      const r = await listReviewQueue("pending")
      setItems(r.items)
      setNotes(Object.fromEntries(r.items.map((item) => [item.id, item.resolution_note ?? ""])))
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load review queue")
    } finally {
      setLoading(false)
    }
  }

  React.useEffect(() => { reload() }, [])

  async function handleResolve(id: string) {
    setActing(id)
    setError(null)
    try {
      await resolveReviewItem(id, notes[id]?.trim())
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Resolve failed")
    } finally {
      setActing(null)
    }
  }

  async function handleDismiss(id: string) {
    if (!globalThis.confirm("Dismiss this review item without changing any facts?")) return
    setActing(id)
    setError(null)
    try {
      await dismissReviewItem(id)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Dismiss failed")
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Review Queue</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Compare grouped duplicate, overlapping, and conflicting facts before resolving cleanup work.
        </p>
      </div>

      {loading && <p role="status" className="text-sm text-muted-foreground">Loading…</p>}
      {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="space-y-3">
        {items.map((item) => (
          <article key={item.id} className="border rounded-lg p-4 space-y-4" aria-labelledby={`review-item-${item.id}`}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 id={`review-item-${item.id}`} className="text-sm font-semibold">
                    {item.group_type ?? item.item_type} group
                  </h2>
                  <Badge variant="outline">{item.item_type}</Badge>
                  <Badge variant="secondary">{item.status}</Badge>
                  <Badge variant="outline">{item.fact_count} facts</Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Created {new Date(item.created_at).toLocaleString()} · group {item.conflict_group_id}
                </p>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={acting === item.id} onClick={() => handleResolve(item.id)} aria-label={`Resolve review item ${item.id.slice(0, 8)}`}>
                  {acting === item.id ? "Resolving…" : "Resolve"}
                </Button>
                <Button size="sm" variant="ghost" disabled={acting === item.id} onClick={() => handleDismiss(item.id)} aria-label={`Dismiss review item ${item.id.slice(0, 8)}`}>
                  Dismiss
                </Button>
              </div>
            </div>

            {item.facts.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2" aria-label={`Fact candidates for ${item.group_type ?? item.item_type} review`}>
                {item.facts.map((fact) => (
                  <section key={fact.id} className="rounded-md border bg-muted/20 p-3 space-y-2" aria-label={`Fact candidate ${fact.id.slice(0, 8)}`}>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={fact.confidence_tier === "high" ? "default" : "outline"}>{fact.confidence_tier}</Badge>
                      <Badge variant="outline">{fact.review_status}</Badge>
                      <span className="text-xs text-muted-foreground">{fact.source_name ?? fact.source_type ?? "Unknown source"}</span>
                    </div>
                    <p className="text-sm">{fact.fact_text}</p>
                    {fact.source_span && <blockquote className="border-l-2 pl-3 text-xs italic text-muted-foreground">{fact.source_span}</blockquote>}
                    <p className="text-xs text-muted-foreground">
                      Derived by {fact.derivation_method} · {fact.derivation_model}
                    </p>
                  </section>
                ))}
              </div>
            ) : (
              <p className="rounded-md bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
                No active fact candidates remain for this group. Resolve or dismiss it to clear the queue.
              </p>
            )}

            <label className="block space-y-1 text-sm">
              <span className="font-medium">Resolution note</span>
              <textarea
                className="min-h-20 w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                value={notes[item.id] ?? ""}
                onChange={(event) => setNotes((prev) => ({ ...prev, [item.id]: event.target.value }))}
                placeholder="Explain which fact should remain, what was merged, or why the group was dismissed."
                aria-label={`Resolution note for review item ${item.id.slice(0, 8)}`}
              />
            </label>
          </article>
        ))}
        {!loading && items.length === 0 && (
          <p className="text-sm text-muted-foreground">No pending review items.</p>
        )}
      </div>
    </div>
  )
}
