import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { listAuditEvents, type AuditEventItem } from "@/lib/api"

export function AuditPage() {
  const [events, setEvents] = React.useState<AuditEventItem[]>([])
  const [loading, setLoading] = React.useState(true)
  const [offset, setOffset] = React.useState(0)
  const [hasMore, setHasMore] = React.useState(true)
  const LIMIT = 50

  async function load(off: number) {
    setLoading(true)
    try {
      const r = await listAuditEvents({ limit: LIMIT, offset: off })
      if (off === 0) {
        setEvents(r.items)
      } else {
        setEvents((prev) => [...prev, ...r.items])
      }
      setHasMore(r.items.length === LIMIT)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  React.useEffect(() => { load(0) }, [])

  function loadMore() {
    const next = offset + LIMIT
    setOffset(next)
    load(next)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Audit Log</h1>
        <p className="text-sm text-muted-foreground mt-1">All access and operation events. Newest first.</p>
      </div>

      {loading && events.length === 0 && <p className="text-sm text-muted-foreground">Loading…</p>}

      <div className="space-y-3">
        {events.map((event) => (
          <div key={event.id} className="border rounded-lg p-4 space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant="outline">{event.event_type}</Badge>
              <span className="text-sm">{event.actor}</span>
              <span className="text-xs text-muted-foreground ml-auto">{new Date(event.occurred_at).toLocaleString()}</span>
            </div>
            {event.operation_metadata && Object.keys(event.operation_metadata).length > 0 && (
              <p className="text-xs text-muted-foreground font-mono">{JSON.stringify(event.operation_metadata)}</p>
            )}
          </div>
        ))}
      </div>

      {hasMore && !loading && (
        <Button variant="outline" onClick={loadMore}>Load more</Button>
      )}
    </div>
  )
}
