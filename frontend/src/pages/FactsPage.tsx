import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { listFacts, promoteFactToCanonical, type FactItem, ApiError } from "@/lib/api"

const TIER_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  high: "default",
  medium: "secondary",
  low: "outline",
}

export function FactsPage() {
  const [facts, setFacts] = React.useState<FactItem[]>([])
  const [loading, setLoading] = React.useState(true)
  const [promotedIds, setPromotedIds] = React.useState<Set<string>>(new Set())
  const [promoting, setPromoting] = React.useState<string | null>(null)

  React.useEffect(() => {
    listFacts({ limit: 100 })
      .then((r) => setFacts(r.facts))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  async function handlePromote(fact: FactItem) {
    const needsConfirm = !fact.source_span?.trim()
    if (needsConfirm && !window.confirm("This fact has no source span. Promote to canonical memory anyway?")) return
    setPromoting(fact.id)
    try {
      await promoteFactToCanonical(fact.id, needsConfirm)
      setPromotedIds((prev) => new Set([...prev, fact.id]))
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Promote failed")
    } finally {
      setPromoting(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Extracted Facts</h1>
        <p className="text-sm text-muted-foreground mt-1">Facts extracted from your archive with source provenance.</p>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      <div className="space-y-3">
        {facts.map((fact) => (
          <div key={fact.id} className="border rounded-lg p-4 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant={TIER_VARIANT[fact.confidence_tier] ?? "outline"}>{fact.confidence_tier}</Badge>
                {fact.conflict_group_id && <Badge variant="destructive">conflict</Badge>}
                <span className="text-xs text-muted-foreground">{fact.derivation_model}</span>
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={promoting === fact.id || promotedIds.has(fact.id)}
                onClick={() => handlePromote(fact)}
              >
                {promotedIds.has(fact.id) ? "Promoted" : "Promote"}
              </Button>
            </div>
            <p className="text-sm">{fact.fact_text}</p>
            {fact.source_span && (
              <blockquote className="text-xs text-muted-foreground border-l-2 pl-3 italic">{fact.source_span}</blockquote>
            )}
          </div>
        ))}
        {!loading && facts.length === 0 && (
          <p className="text-sm text-muted-foreground">No facts extracted yet. Ingest and process some conversations first.</p>
        )}
      </div>
    </div>
  )
}
