import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { listCanonical, updateCanonical, deleteCanonical, type CanonicalItem, ApiError } from "@/lib/api"

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  active: "default",
  disputed: "destructive",
  stale: "secondary",
}

export function CanonicalPage() {
  const [items, setItems] = React.useState<CanonicalItem[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [editingId, setEditingId] = React.useState<string | null>(null)
  const [editContent, setEditContent] = React.useState("")
  const [query, setQuery] = React.useState("")
  const [selected, setSelected] = React.useState<Set<string>>(new Set())
  const [bulkBusy, setBulkBusy] = React.useState(false)
  const [bulkMsg, setBulkMsg] = React.useState<string | null>(null)

  async function reload() {
    setLoading(true)
    setError(null)
    try {
      const r = await listCanonical({ include_non_active: true })
      setItems(r.items)
      setSelected(new Set())
    } catch (err) {
      console.error(err)
      setError(err instanceof ApiError ? err.detail : "Failed to load canonical memory.")
    } finally {
      setLoading(false)
    }
  }

  React.useEffect(() => { reload() }, [])

  async function handleMarkStatus(id: string, status: string) {
    try {
      await updateCanonical(id, { status })
      await reload()
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Update failed")
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this canonical item permanently?")) return
    try {
      await deleteCanonical(id)
      await reload()
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Delete failed")
    }
  }

  async function handleSaveEdit(id: string) {
    try {
      await updateCanonical(id, { content: editContent })
      setEditingId(null)
      await reload()
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Update failed")
    }
  }

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase()
    return q ? items.filter((i) => i.content.toLowerCase().includes(q)) : items
  }, [items, query])

  const allFilteredSelected = filtered.length > 0 && filtered.every((i) => selected.has(i.id))

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleAll() {
    setSelected((prev) => {
      const next = new Set(prev)
      if (allFilteredSelected) filtered.forEach((i) => next.delete(i.id))
      else filtered.forEach((i) => next.add(i.id))
      return next
    })
  }

  async function handleBulkDelete() {
    const ids = [...selected]
    if (ids.length === 0) return
    if (!window.confirm(`Delete ${ids.length} canonical item${ids.length === 1 ? "" : "s"}? This cannot be undone.`)) return
    setBulkBusy(true)
    setBulkMsg(null)
    const results = await Promise.allSettled(ids.map((id) => deleteCanonical(id)))
    const failed = results.filter((r) => r.status === "rejected").length
    const ok = results.length - failed
    const noun = ok === 1 ? "item" : "items"
    setBulkMsg(failed === 0 ? `Deleted ${ok} ${noun}.` : `Deleted ${ok} ${noun}, failed ${failed}.`)
    setBulkBusy(false)
    await reload()
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Canonical Memory</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Trusted facts promoted from extracted knowledge. These rank first in all retrievals.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search canonical memory…"
          aria-label="Search canonical memory"
          className="w-full sm:max-w-xs h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        />
        {selected.size > 0 && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">{selected.size} selected</span>
            <Button variant="destructive" size="sm" disabled={bulkBusy} onClick={handleBulkDelete}>
              {bulkBusy ? "Deleting…" : `Delete selected (${selected.size})`}
            </Button>
          </div>
        )}
      </div>
      <output aria-live="polite" className="block text-sm text-muted-foreground">
        {loading ? "Loading…" : (bulkMsg ?? "")}
      </output>

      {!loading && error && (
        <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm">
          <p className="font-medium text-destructive">Couldn't load canonical memory</p>
          <p className="text-muted-foreground mt-1">{error}</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => reload()}>Retry</Button>
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No canonical memory yet. Promote trusted facts from the Facts page.
        </p>
      )}

      {!loading && !error && items.length > 0 && filtered.length === 0 && (
        <p className="text-sm text-muted-foreground">No canonical items match "{query}".</p>
      )}

      {!loading && !error && filtered.length > 0 && (
        <label className="flex w-fit items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={allFilteredSelected}
            onChange={toggleAll}
            aria-label="Select all canonical items"
            className="rounded border-input"
          />
          Select all{query ? " (filtered)" : ""}
        </label>
      )}

      <div className="space-y-3">
        {filtered.map((item) => (
          <div key={item.id} className="border rounded-lg p-4 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <input
                  type="checkbox"
                  checked={selected.has(item.id)}
                  onChange={() => toggle(item.id)}
                  aria-label={`Select canonical item ${item.id.slice(0, 8)}`}
                  className="rounded border-input"
                />
                <Badge variant={STATUS_VARIANT[item.status] ?? "outline"}>{item.status}</Badge>
                <Badge variant="outline">{item.promoted_from}</Badge>
                <span className="text-xs text-muted-foreground">by {item.promoted_by}</span>
              </div>
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" onClick={() => { setEditingId(item.id); setEditContent(item.content) }} aria-label={`Edit canonical item ${item.id.slice(0, 8)}`}>Edit</Button>
                <Button variant="ghost" size="sm" onClick={() => handleMarkStatus(item.id, "disputed")} aria-label={`Mark canonical item ${item.id.slice(0, 8)} as disputed`}>Dispute</Button>
                <Button variant="ghost" size="sm" onClick={() => handleMarkStatus(item.id, "stale")} aria-label={`Mark canonical item ${item.id.slice(0, 8)} as stale`}>Stale</Button>
                <Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleDelete(item.id)} aria-label={`Delete canonical item ${item.id.slice(0, 8)}`}>Delete</Button>
              </div>
            </div>
            {editingId === item.id ? (
              <div className="flex gap-2">
                <label htmlFor={`edit-canonical-${item.id}`} className="sr-only">Edit content for canonical item {item.id.slice(0, 8)}</label>
                <input
                  id={`edit-canonical-${item.id}`}
                  type="text"
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="flex-1 h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                />
                <Button size="sm" onClick={() => handleSaveEdit(item.id)} aria-label={`Save edit for canonical item ${item.id.slice(0, 8)}`}>Save</Button>
                <Button size="sm" variant="outline" onClick={() => setEditingId(null)} aria-label="Cancel edit">Cancel</Button>
              </div>
            ) : (
              <p className="text-sm">{item.content}</p>
            )}
            {item.provenance_note && (
              <p className="text-xs text-muted-foreground">Note: {item.provenance_note}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
