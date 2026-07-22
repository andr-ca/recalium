import * as React from "react"
import { Link, useParams } from "react-router-dom"
import { Badge } from "@/components/ui/badge"
import { getTagFacts, type TagFact, ApiError } from "@/lib/api"

const TIER_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  high: "default",
  medium: "secondary",
  low: "outline",
}

export function TagFactsPage() {
  const { tagId = "" } = useParams()
  const [name, setName] = React.useState<string>("")
  const [facts, setFacts] = React.useState<TagFact[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [notFound, setNotFound] = React.useState(false)

  React.useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setNotFound(false)
    setFacts([])
    setName("")
    getTagFacts(tagId)
      .then((r) => {
        if (cancelled) return
        setName(r.name)
        setFacts(r.facts)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 404) setNotFound(true)
        else setError(err instanceof ApiError ? err.detail : "Failed to load tag")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [tagId])

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <Link to="/explore" className="text-sm text-muted-foreground hover:underline">← Back to Explore</Link>
        <h1 className="text-2xl font-semibold mt-1">
          {name ? name : "Tag"}
          {!loading && !notFound && !error && (
            <span className="text-muted-foreground font-normal text-lg"> · {facts.length} fact{facts.length === 1 ? "" : "s"}</span>
          )}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">Active facts carrying this tag.</p>
      </div>

      <div aria-live="polite" aria-busy={loading}>
        {loading && <output className="text-sm text-muted-foreground">Loading…</output>}
        {!loading && error && (
          <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        )}
        {!loading && notFound && <p className="text-sm text-muted-foreground">Tag not found.</p>}
        {!loading && !error && !notFound && facts.length === 0 && (
          <p className="text-sm text-muted-foreground">No active facts carry this tag.</p>
        )}

        {!loading && facts.length > 0 && (
          <ul className="space-y-3" aria-label="Facts with this tag">
            {facts.map((fact) => (
              <li key={fact.id} className="flex items-start justify-between gap-3 border rounded-lg p-4">
                <div className="space-y-2">
                  <Badge variant={TIER_VARIANT[fact.confidence_tier] ?? "outline"}>{fact.confidence_tier}</Badge>
                  <p className="text-sm">{fact.fact_text}</p>
                </div>
                <Link
                  to={`/memory/${fact.id}`}
                  className="shrink-0 text-sm text-primary hover:underline whitespace-nowrap"
                  aria-label={`Open memory details for: ${fact.fact_text.slice(0, 40)}`}
                >
                  open →
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
