import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  archiveFact,
  deleteFact,
  listFacts,
  markFactDisputed,
  markFactStale,
  promoteFactToCanonical,
  updateFact,
  type FactItem,
  ApiError,
} from "@/lib/api"

const TIER_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  high: "default",
  medium: "secondary",
  low: "outline",
}

export function FactsPage() {
  const [facts, setFacts] = React.useState<FactItem[]>([])
  const [loading, setLoading] = React.useState(true)
  const [showAll, setShowAll] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [promotedIds, setPromotedIds] = React.useState<Set<string>>(new Set())
  const [promoting, setPromoting] = React.useState<string | null>(null)
  const [saving, setSaving] = React.useState<string | null>(null)
  const [drafts, setDrafts] = React.useState<Record<string, string>>({})

  const loadFacts = React.useCallback(() => {
    setLoading(true)
    setError(null)
    listFacts({ limit: 100, reviewStatus: showAll ? "all" : undefined })
      .then((r) => {
        setFacts(r.facts)
        setDrafts(Object.fromEntries(r.facts.map((fact) => [fact.id, fact.fact_text])))
      })
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Failed to load facts"))
      .finally(() => setLoading(false))
  }, [showAll])

  React.useEffect(() => {
    loadFacts()
  }, [loadFacts])

  function updateFactInState(next: FactItem) {
    setFacts((prev) => prev.map((fact) => (fact.id === next.id ? next : fact)))
    setDrafts((prev) => ({ ...prev, [next.id]: next.fact_text }))
  }

  async function handlePromote(fact: FactItem) {
    const hasSourceSpan = !!fact.source_span?.trim()
    const needsConfirm = !hasSourceSpan
    if (needsConfirm && !window.confirm("This fact has no source span. Promote to canonical memory anyway?")) return
    setPromoting(fact.id)
    try {
      await promoteFactToCanonical(
        fact.id,
        fact.raw_archive_id,
        fact.fact_text,
        hasSourceSpan,
        needsConfirm,
      )
      setPromotedIds((prev) => new Set([...prev, fact.id]))
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Promote failed")
    } finally {
      setPromoting(null)
    }
  }

  async function handleSave(fact: FactItem) {
    const nextText = drafts[fact.id]?.trim()
    if (!nextText) {
      setError("Fact text cannot be empty")
      return
    }
    setSaving(fact.id)
    setError(null)
    try {
      updateFactInState(await updateFact(fact.id, { fact_text: nextText }))
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed")
    } finally {
      setSaving(null)
    }
  }

  async function handleStatus(fact: FactItem, action: "dispute" | "stale" | "archive" | "delete") {
    const labels = { dispute: "mark this fact disputed", stale: "mark this fact stale", archive: "archive this fact", delete: "delete this fact" }
    if ((action === "archive" || action === "delete") && !globalThis.confirm(`Are you sure you want to ${labels[action]}?`)) return
    setSaving(fact.id)
    setError(null)
    try {
      if (action === "dispute") updateFactInState(await markFactDisputed(fact.id))
      if (action === "stale") updateFactInState(await markFactStale(fact.id))
      if (action === "archive") {
        const next = await archiveFact(fact.id)
        if (showAll) updateFactInState(next)
        else setFacts((prev) => prev.filter((item) => item.id !== fact.id))
      }
      if (action === "delete") {
        await deleteFact(fact.id)
        setFacts((prev) => prev.filter((item) => item.id !== fact.id))
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : `${action} failed`)
    } finally {
      setSaving(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Extracted Facts</h1>
          <p className="text-sm text-muted-foreground mt-1">Review, correct, suppress, and promote source-backed extracted facts.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowAll((value) => !value)}>
            {showAll ? "Hide archived/deleted" : "Show archived/deleted"}
          </Button>
          <Button variant="outline" size="sm" onClick={loadFacts}>Refresh</Button>
        </div>
      </div>

      {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {loading && <p role="status" className="text-sm text-muted-foreground">Loading…</p>}

      <div className="space-y-3">
        {facts.map((fact) => (
          <div key={fact.id} className="border rounded-lg p-4 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant={TIER_VARIANT[fact.confidence_tier] ?? "outline"}>{fact.confidence_tier}</Badge>
                <Badge variant={fact.review_status === "active" ? "secondary" : "outline"}>{fact.review_status}</Badge>
                {fact.conflict_group_id && <Badge variant="destructive">conflict</Badge>}
                <span className="text-xs text-muted-foreground">{fact.derivation_model}</span>
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={promoting === fact.id || promotedIds.has(fact.id) || fact.review_status !== "active"}
                  onClick={() => handlePromote(fact)}
                  aria-label={`${promotedIds.has(fact.id) ? "Already promoted" : "Promote"} fact: ${fact.fact_text.slice(0, 40)}`}
                >
                  {promotedIds.has(fact.id) ? "Promoted" : "Promote"}
                </Button>
              </div>
            </div>
            <label className="block space-y-1 text-sm">
              <span className="font-medium">Fact text</span>
              <textarea
                className="min-h-20 w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[--color-ring]"
                value={drafts[fact.id] ?? fact.fact_text}
                onChange={(event) => setDrafts((prev) => ({ ...prev, [fact.id]: event.target.value }))}
                aria-label={`Edit fact text: ${fact.fact_text.slice(0, 40)}`}
              />
            </label>
            {fact.source_span && (
              <blockquote className="text-xs text-muted-foreground border-l-2 pl-3 italic">{fact.source_span}</blockquote>
            )}
            <div className="flex flex-wrap gap-2 pt-2">
              <Button variant="default" size="sm" disabled={saving === fact.id} onClick={() => handleSave(fact)}>Save edit</Button>
              <Button variant="outline" size="sm" disabled={saving === fact.id} onClick={() => handleStatus(fact, "dispute")}>Mark disputed</Button>
              <Button variant="outline" size="sm" disabled={saving === fact.id} onClick={() => handleStatus(fact, "stale")}>Mark stale</Button>
              <Button variant="outline" size="sm" disabled={saving === fact.id} onClick={() => handleStatus(fact, "archive")}>Archive</Button>
              <Button variant="outline" size="sm" disabled={saving === fact.id} onClick={() => handleStatus(fact, "delete")}>Delete</Button>
            </div>
          </div>
        ))}
        {!loading && facts.length === 0 && (
          <p className="text-sm text-muted-foreground">No facts extracted yet. Ingest and process some conversations first.</p>
        )}
      </div>
    </div>
  )
}
