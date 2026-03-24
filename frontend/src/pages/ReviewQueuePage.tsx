import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { listReviewQueue, resolveReviewItem, dismissReviewItem, type ReviewQueueItem, ApiError } from "@/lib/api"

export function ReviewQueuePage() {
  const [items, setItems] = React.useState<ReviewQueueItem[]>([])
  const [loading, setLoading] = React.useState(true)
  const [acting, setActing] = React.useState<string | null>(null)

  async function reload() {
    setLoading(true)
    try {
      const r = await listReviewQueue("pending")
      setItems(r.items)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  React.useEffect(() => { reload() }, [])

  async function handleResolve(id: string) {
    setActing(id)
    try {
      await resolveReviewItem(id)
      await reload()
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Resolve failed")
    } finally {
      setActing(null)
    }
  }

  async function handleDismiss(id: string) {
    setActing(id)
    try {
      await dismissReviewItem(id)
      await reload()
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Dismiss failed")
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Review Queue</h1>
        <p className="text-sm text-muted-foreground mt-1">Duplicate and conflicting facts flagged for review.</p>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.id} className="border rounded-lg p-4 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Badge variant="outline">{item.item_type}</Badge>
                <Badge variant="secondary">{item.status}</Badge>
                <span className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleDateString()}</span>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={acting === item.id} onClick={() => handleResolve(item.id)}>Resolve</Button>
                <Button size="sm" variant="ghost" disabled={acting === item.id} onClick={() => handleDismiss(item.id)}>Dismiss</Button>
              </div>
            </div>
            <p className="text-xs text-muted-foreground font-mono">group: {item.conflict_group_id}</p>
          </div>
        ))}
        {!loading && items.length === 0 && (
          <p className="text-sm text-muted-foreground">No pending review items.</p>
        )}
      </div>
    </div>
  )
}
