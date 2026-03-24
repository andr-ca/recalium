import * as React from "react"
import { useSearchParams } from "react-router-dom"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { listAuditEvents, ApiError, type AuditEventItem } from "@/lib/api"

const EVENT_TYPE_OPTIONS = [
  { value: "", label: "All types" },
  { value: "archive_delete", label: "Archive delete" },
  { value: "mcp_retrieve", label: "MCP retrieve" },
  { value: "fact_promote", label: "Fact promote" },
  { value: "canonical_create", label: "Canonical create" },
  { value: "key_validate", label: "Key validate" },
]

export function AuditPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const eventTypeFilter = searchParams.get("type") ?? ""

  const [events, setEvents] = React.useState<AuditEventItem[]>([])
  const [loading, setLoading] = React.useState(true)
  const [loadError, setLoadError] = React.useState<string | null>(null)
  const [offset, setOffset] = React.useState(0)
  const [hasMore, setHasMore] = React.useState(true)
  const [expandedId, setExpandedId] = React.useState<string | null>(null)
  const LIMIT = 50

  const load = React.useCallback(async (off: number, filter: string) => {
    setLoading(true)
    setLoadError(null)
    try {
      const r = await listAuditEvents({
        limit: LIMIT,
        offset: off,
        event_type: filter || null,
      })
      if (off === 0) {
        setEvents(r.items)
      } else {
        setEvents((prev) => [...prev, ...r.items])
      }
      setHasMore(r.items.length === LIMIT)
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.detail : "Failed to load audit events")
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    setOffset(0)
    setExpandedId(null)
    load(0, eventTypeFilter)
  }, [eventTypeFilter, load])

  function handleFilterChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value
    setSearchParams(val ? { type: val } : {})
  }

  function loadMore() {
    const next = offset + LIMIT
    setOffset(next)
    load(next, eventTypeFilter)
  }

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Audit Log</h1>
        <p className="text-sm text-muted-foreground mt-1">All access and operation events. Newest first.</p>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3">
        <label htmlFor="audit-type-filter" className="text-sm font-medium whitespace-nowrap">
          Event type
        </label>
        <select
          id="audit-type-filter"
          value={eventTypeFilter}
          onChange={handleFilterChange}
          className="rounded-md border border-input px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          aria-label="Filter audit events by type"
        >
          {EVENT_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {loading && events.length === 0 && (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}

      {loadError && (
        <p role="alert" className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">
          {loadError}
        </p>
      )}

      <div className="space-y-2" role="list" aria-label="Audit events">
        {events.map((event) => {
          const isExpanded = expandedId === event.id
          const detailId = `audit-detail-${event.id}`
          return (
            <div key={event.id} className="border rounded-lg overflow-hidden" role="listitem">
              <button
                type="button"
                className="w-full text-left flex items-center gap-2 p-4 hover:bg-muted/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                onClick={() => toggleExpand(event.id)}
                aria-expanded={isExpanded}
                aria-controls={detailId}
              >
                <Badge variant="outline">{event.event_type}</Badge>
                <span className="text-sm">{event.actor}</span>
                <span className="text-xs text-muted-foreground ml-auto">
                  {new Date(event.occurred_at).toLocaleString()}
                </span>
                <span className="text-xs text-muted-foreground ml-2" aria-hidden="true">
                  {isExpanded ? "▲" : "▼"}
                </span>
              </button>

              {isExpanded && (
                <div
                  id={detailId}
                  className="border-t bg-muted/20 p-4 space-y-2"
                  role="region"
                  aria-label={`Details for event ${event.id}`}
                >
                  <dl className="text-xs space-y-1">
                    <div className="flex gap-2">
                      <dt className="font-medium text-muted-foreground w-28">ID</dt>
                      <dd className="font-mono break-all">{event.id}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium text-muted-foreground w-28">Event type</dt>
                      <dd>{event.event_type}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium text-muted-foreground w-28">Actor</dt>
                      <dd>{event.actor}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium text-muted-foreground w-28">Occurred at</dt>
                      <dd>{new Date(event.occurred_at).toISOString()}</dd>
                    </div>
                  </dl>
                  {event.operation_metadata && Object.keys(event.operation_metadata).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">Operation metadata</p>
                      <pre className="text-xs font-mono bg-background border rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
                        {JSON.stringify(event.operation_metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {events.length === 0 && !loading && (
        <p className="text-sm text-muted-foreground">No events found.</p>
      )}

      {hasMore && !loading && (
        <Button variant="outline" onClick={loadMore}>Load more</Button>
      )}
    </div>
  )
}
