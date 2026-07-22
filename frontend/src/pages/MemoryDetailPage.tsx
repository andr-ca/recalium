import * as React from "react"
import { Link, useParams } from "react-router-dom"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  getFact,
  getFactTags,
  getFactLinks,
  getArchiveItem,
  type FactItem,
  type FactTag,
  type FactLink,
  type ArchiveItemDetail,
  ApiError,
} from "@/lib/api"

const TIER_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  high: "default",
  medium: "secondary",
  low: "outline",
}

const LINK_VARIANT: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  supports: "default",
  elaborates: "secondary",
  contradicts: "destructive",
  related: "outline",
  entity: "outline",
}

const LINK_LABEL: Record<string, string> = {
  supports: "supports",
  elaborates: "elaborates",
  contradicts: "contradicts",
  related: "related",
  entity: "shares entity",
}

export function MemoryDetailPage() {
  const { id = "" } = useParams()
  const [fact, setFact] = React.useState<FactItem | null>(null)
  const [tags, setTags] = React.useState<FactTag[]>([])
  const [links, setLinks] = React.useState<FactLink[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [notFound, setNotFound] = React.useState(false)

  React.useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setNotFound(false)
    setFact(null)
    setTags([])
    setLinks([])
    getFact(id)
      .then(async (f) => {
        // Tags and links are best-effort — a fact with no links/tags is valid,
        // and the /tags and /links endpoints 404 for non-active facts.
        const [tagRes, linkRes] = await Promise.allSettled([getFactTags(id), getFactLinks(id, "both")])
        if (cancelled) return
        setFact(f)
        setTags(tagRes.status === "fulfilled" ? tagRes.value.tags : [])
        setLinks(linkRes.status === "fulfilled" ? linkRes.value.links : [])
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 404) setNotFound(true)
        else setError(err instanceof ApiError ? err.detail : "Failed to load memory")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id])

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <Link to="/facts" className="text-sm text-muted-foreground hover:underline">← Back to Facts</Link>
        <h1 className="text-2xl font-semibold mt-1">Memory</h1>
        <p className="text-sm text-muted-foreground mt-1">
          A single fact with its tags, linked memory, and source lineage.
        </p>
      </div>

      <div aria-live="polite" aria-busy={loading}>
        {loading && <output className="text-sm text-muted-foreground">Loading…</output>}
        {!loading && error && (
          <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        )}
        {!loading && notFound && (
          <p className="text-sm text-muted-foreground">Memory not found. It may have been deleted.</p>
        )}

        {!loading && fact && (
          <div className="space-y-6">
            <section className="border rounded-lg p-4 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={TIER_VARIANT[fact.confidence_tier] ?? "outline"}>{fact.confidence_tier}</Badge>
                <Badge variant={fact.review_status === "active" ? "secondary" : "outline"}>{fact.review_status}</Badge>
                {fact.conflict_group_id && (
                  <Link to="/review-queue" aria-label="View conflict in review queue">
                    <Badge variant="destructive">in conflict group</Badge>
                  </Link>
                )}
                <span className="text-xs text-muted-foreground">{fact.derivation_model}</span>
              </div>
              <p className="text-base whitespace-pre-wrap">{fact.fact_text}</p>
            </section>

            <section className="space-y-2">
              <h2 className="text-sm font-semibold">Tags</h2>
              {tags.length === 0 ? (
                <p className="text-sm text-muted-foreground">No tags.</p>
              ) : (
                <ul className="flex flex-wrap gap-2" aria-label="Tags">
                  {tags.map((tag) => (
                    <li key={tag.tag_id}>
                      <Badge variant="outline">{tag.name}</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <RelatedMemory links={links} />

            <Lineage fact={fact} />
          </div>
        )}
      </div>
    </div>
  )
}

function RelatedMemory({ links }: Readonly<{ links: FactLink[] }>) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold">Related memory</h2>
      {links.length === 0 ? (
        <p className="text-sm text-muted-foreground">No linked memory yet.</p>
      ) : (
        <ul className="space-y-2" aria-label="Related memory">
          {links.map((link) => (
            <li key={link.link_id} className="flex items-start justify-between gap-3 border rounded-md p-3">
              <div className="space-y-1">
                <Badge variant={LINK_VARIANT[link.link_type] ?? "outline"}>
                  {LINK_LABEL[link.link_type] ?? link.link_type}
                  {link.link_type === "entity" && link.entity_name ? `: ${link.entity_name}` : ""}
                </Badge>
                <p className="text-sm">{link.other_fact_text}</p>
              </div>
              <Link
                to={`/memory/${link.other_fact_id}`}
                className="shrink-0 text-sm text-primary hover:underline whitespace-nowrap"
                aria-label={`Open linked memory: ${link.other_fact_text.slice(0, 40)}`}
              >
                open →
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function Lineage({ fact }: Readonly<{ fact: FactItem }>) {
  const [source, setSource] = React.useState<ArchiveItemDetail | null>(null)
  const [open, setOpen] = React.useState(false)
  const [loading, setLoading] = React.useState(false)

  async function toggleSource() {
    if (open) {
      setOpen(false)
      return
    }
    setOpen(true)
    if (source || loading) return
    setLoading(true)
    try {
      setSource(await getArchiveItem(fact.raw_archive_id))
    } catch {
      setSource(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold">Lineage</h2>
      <p className="text-xs text-muted-foreground">
        via {fact.derivation_method} · {fact.derivation_model}
      </p>
      {fact.source_span && (
        <blockquote className="text-sm text-muted-foreground border-l-2 pl-3 italic">{fact.source_span}</blockquote>
      )}
      <Button variant="outline" size="sm" onClick={toggleSource} aria-expanded={open}>
        {open ? "Hide source" : "View source"}
      </Button>
      {open && (
        <div className="border rounded-md p-3 bg-muted/30">
          {loading && <output className="text-sm text-muted-foreground">Loading source…</output>}
          {!loading && !source && <p className="text-sm text-muted-foreground">Source not available.</p>}
          {!loading && source && (
            <>
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="outline">{source.source_type}</Badge>
                <span className="text-xs text-muted-foreground">{new Date(source.ingested_at).toLocaleString()}</span>
              </div>
              <HighlightedSource raw={source.raw_content ?? ""} span={fact.source_span} />
            </>
          )}
        </div>
      )}
    </section>
  )
}

/** Shows a window of raw source text with the fact's source span highlighted in place. */
function HighlightedSource({ raw, span }: Readonly<{ raw: string; span: string }>) {
  const idx = span ? raw.indexOf(span) : -1
  if (idx === -1) {
    const clipped = raw.slice(0, 3000)
    return (
      <p className="text-xs font-mono whitespace-pre-wrap text-muted-foreground leading-relaxed">
        {clipped}
        {raw.length > 3000 ? " …(truncated)" : ""}
      </p>
    )
  }
  const before = raw.slice(Math.max(0, idx - 400), idx)
  const after = raw.slice(idx + span.length, idx + span.length + 400)
  return (
    <p className="text-xs font-mono whitespace-pre-wrap text-muted-foreground leading-relaxed">
      {idx > 400 ? "…" : ""}
      {before}
      <mark className="bg-yellow-200 px-0.5">{span}</mark>
      {after}
      {idx + span.length + 400 < raw.length ? "…" : ""}
    </p>
  )
}
