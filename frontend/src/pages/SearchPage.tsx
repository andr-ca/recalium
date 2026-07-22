import * as React from "react"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { searchMemory, getArchiveItem, deleteCanonical, deleteFact, type RetrievalItem, type RetrievalResponse, type ArchiveItemDetail, ApiError } from "@/lib/api"

type Mode = "hybrid" | "keyword" | "semantic"

const TYPE_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  canonical: "default",
  fact: "secondary",
  summary: "outline",
  excerpt: "outline",
}

export function SearchPage() {
  const [query, setQuery] = React.useState("")
  const [mode, setMode] = React.useState<Mode>("hybrid")
  const [response, setResponse] = React.useState<RetrievalResponse | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [panelSourceId, setPanelSourceId] = React.useState<string | null>(null)
  const [canonicalOnly, setCanonicalOnly] = React.useState(false)
  const [selected, setSelected] = React.useState<Set<string>>(new Set())
  const [bulkBusy, setBulkBusy] = React.useState(false)
  const [bulkMsg, setBulkMsg] = React.useState<string | null>(null)

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleBulkDelete() {
    if (!response) return
    const targets = response.items.filter(
      (it) => selected.has(it.id) && (it.type === "fact" || it.type === "canonical"),
    )
    if (targets.length === 0) return
    if (!window.confirm(`Delete ${targets.length} item${targets.length === 1 ? "" : "s"}? This cannot be undone.`)) return
    setBulkBusy(true)
    setBulkMsg(null)
    const results = await Promise.allSettled(
      targets.map((it) => (it.type === "canonical" ? deleteCanonical(it.id) : deleteFact(it.id))),
    )
    const okIds = new Set<string>()
    let failed = 0
    results.forEach((r, i) => {
      if (r.status === "fulfilled") okIds.add(targets[i].id)
      else failed += 1
    })
    setResponse((prev) => (prev ? { ...prev, items: prev.items.filter((it) => !okIds.has(it.id)) } : prev))
    setSelected(new Set())
    const noun = okIds.size === 1 ? "item" : "items"
    setBulkMsg(failed === 0 ? `Deleted ${okIds.size} ${noun}.` : `Deleted ${okIds.size} ${noun}, failed ${failed}.`)
    setBulkBusy(false)
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setSelected(new Set())
    setBulkMsg(null)
    try {
      const result = await searchMemory(query, mode, 20, canonicalOnly)
      setResponse(result)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Search failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Search Memory</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Retrieve relevant items using keyword, semantic, or hybrid search.
        </p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 items-center">
        <label htmlFor="search-query" className="sr-only">Search query</label>
        <input
          id="search-query"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search your memory…"
          className="flex-1 h-10 rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-primary focus:outline-none"
        />
        <div className="flex gap-1">
          {(["hybrid", "keyword", "semantic"] as Mode[]).map((m) => (
            <Button
              key={m}
              type="button"
              variant={mode === m ? "default" : "outline"}
              size="sm"
              onClick={() => setMode(m)}
              aria-pressed={mode === m}
            >
              {m}
            </Button>
          ))}
        </div>
        <Button type="submit" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </Button>
      </form>

      <label className="flex w-fit items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={canonicalOnly}
          onChange={(e) => setCanonicalOnly(e.target.checked)}
          className="rounded border-input"
        />
        <span>Canonical only</span>
      </label>

      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}

      <div aria-live="polite" aria-busy={loading}>
        {response && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <span>{response.items.length} results</span>
              <span>mode: {response.retrieval_mode}</span>
              <span>budget: {response.budget_used}/{response.budget_limit}</span>
              {response.degraded_mode && <Badge variant="destructive">degraded</Badge>}
              {selected.size > 0 && (
                <Button variant="destructive" size="sm" disabled={bulkBusy} onClick={handleBulkDelete}>
                  {bulkBusy ? "Deleting…" : `Delete selected (${selected.size})`}
                </Button>
              )}
              {bulkMsg && <span>{bulkMsg}</span>}
            </div>

            {response.items.map((item: RetrievalItem) => (
              <div key={item.id} className="border rounded-lg p-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    {(item.type === "fact" || item.type === "canonical") && (
                      <input
                        type="checkbox"
                        checked={selected.has(item.id)}
                        onChange={() => toggle(item.id)}
                        aria-label={`Select ${item.type} result`}
                        className="rounded border-input"
                      />
                    )}
                    <Badge variant={TYPE_VARIANT[item.type] ?? "outline"}>{item.type}</Badge>
                    {item.conflict_label && (
                      <Badge variant="destructive">{item.conflict_label}</Badge>
                    )}
                    <span className="text-xs text-muted-foreground">{item.source_system}</span>
                    <span className="text-xs text-muted-foreground">score: {item.score.toFixed(4)}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPanelSourceId(panelSourceId === item.source_id ? null : item.source_id)}
                    aria-label={`View source for ${item.type} item`}
                    aria-pressed={panelSourceId === item.source_id}
                  >
                    Source
                  </Button>
                </div>
                <p className="text-sm whitespace-pre-wrap">{item.content}</p>
                {item.type === "fact" && (
                  <Link
                    to={`/memory/${item.id}`}
                    className="inline-block text-sm text-primary hover:underline"
                    aria-label="Open memory detail, links, and lineage for this fact"
                  >
                    Open memory →
                  </Link>
                )}
                {item.provenance?.derivation_method && (
                  <p className="text-xs text-muted-foreground">
                    via {item.provenance.derivation_method} · {item.provenance.derivation_model}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Inline provenance panel — no Sheet component available */}
      {panelSourceId && (
        <ProvenanceInlinePanel sourceId={panelSourceId} onClose={() => setPanelSourceId(null)} />
      )}
    </div>
  )
}

function ProvenanceInlinePanel({ sourceId, onClose }: { sourceId: string; onClose: () => void }) {
  const [item, setItem] = React.useState<ArchiveItemDetail | null>(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    setLoading(true)
    getArchiveItem(sourceId)
      .then(setItem)
      .catch(() => setItem(null))
      .finally(() => setLoading(false))
  }, [sourceId])

  return (
    <div className="border rounded-lg p-4 bg-muted/30 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Source Archive Item</span>
        <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close provenance panel">Close</Button>
      </div>
      {loading && <p role="status" className="text-sm text-muted-foreground">Loading…</p>}
      {!loading && !item && <p className="text-sm text-muted-foreground">Not found.</p>}
      {!loading && item && (
        <>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{item.source_type}</Badge>
            <span className="text-xs text-muted-foreground">{new Date(item.ingested_at).toLocaleString()}</span>
          </div>
          <p className="text-xs font-mono whitespace-pre-wrap text-muted-foreground leading-relaxed">
            {item.raw_content?.slice(0, 2000)}
            {(item.raw_content?.length ?? 0) > 2000 && " …(truncated)"}
          </p>
        </>
      )}
    </div>
  )
}
