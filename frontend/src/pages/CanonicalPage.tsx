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
  const [editingId, setEditingId] = React.useState<string | null>(null)
  const [editContent, setEditContent] = React.useState("")

  async function reload() {
    setLoading(true)
    try {
      const r = await listCanonical({ include_non_active: true })
      setItems(r.items)
    } catch (err) {
      console.error(err)
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Canonical Memory</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Trusted facts promoted from extracted knowledge. These rank first in all retrievals.
        </p>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.id} className="border rounded-lg p-4 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant={STATUS_VARIANT[item.status] ?? "outline"}>{item.status}</Badge>
                <Badge variant="outline">{item.promoted_from}</Badge>
                <span className="text-xs text-muted-foreground">by {item.promoted_by}</span>
              </div>
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" onClick={() => { setEditingId(item.id); setEditContent(item.content) }}>Edit</Button>
                <Button variant="ghost" size="sm" onClick={() => handleMarkStatus(item.id, "disputed")}>Dispute</Button>
                <Button variant="ghost" size="sm" onClick={() => handleMarkStatus(item.id, "stale")}>Stale</Button>
                <Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleDelete(item.id)}>Delete</Button>
              </div>
            </div>
            {editingId === item.id ? (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="flex-1 h-9 rounded-md border border-input bg-background px-3 text-sm"
                />
                <Button size="sm" onClick={() => handleSaveEdit(item.id)}>Save</Button>
                <Button size="sm" variant="outline" onClick={() => setEditingId(null)}>Cancel</Button>
              </div>
            ) : (
              <p className="text-sm">{item.content}</p>
            )}
            {item.provenance_note && (
              <p className="text-xs text-muted-foreground">Note: {item.provenance_note}</p>
            )}
          </div>
        ))}
        {!loading && items.length === 0 && (
          <p className="text-sm text-muted-foreground">No canonical items yet. Promote facts from the Facts page.</p>
        )}
      </div>
    </div>
  )
}
