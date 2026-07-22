import * as React from "react"
import { Link } from "react-router-dom"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { listTags, type Tag, ApiError } from "@/lib/api"

const ENTITY_PREFIX = "entity:"

/** Strip the `entity:` prefix for display; topics are shown as-is. */
function displayName(tag: Tag): string {
  return tag.name.startsWith(ENTITY_PREFIX) ? tag.name.slice(ENTITY_PREFIX.length) : tag.name
}

export function ExplorePage() {
  const [tags, setTags] = React.useState<Tag[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  const load = React.useCallback(() => {
    setLoading(true)
    setError(null)
    listTags()
      .then((r) => setTags(r.tags))
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Failed to load tags"))
      .finally(() => setLoading(false))
  }, [])

  React.useEffect(() => {
    load()
  }, [load])

  const entities = tags.filter((t) => t.name.startsWith(ENTITY_PREFIX))
  const topics = tags.filter((t) => !t.name.startsWith(ENTITY_PREFIX))

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Explore</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Browse memory by entity and topic. Pick a tag to see every fact that carries it.
        </p>
      </div>

      <div aria-live="polite" aria-busy={loading}>
        {loading && <output className="text-sm text-muted-foreground">Loading…</output>}
        {!loading && error && (
          <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm">
            <p className="text-destructive">{error}</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={load}>Retry</Button>
          </div>
        )}
        {!loading && !error && tags.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No tags yet. Tags are created when conversations are processed into facts.
          </p>
        )}

        {!loading && !error && tags.length > 0 && (
          <div className="space-y-8">
            <TagGroup title="Entities" tags={entities} emptyLabel="No entity tags yet." />
            <TagGroup title="Topics" tags={topics} emptyLabel="No topic tags yet." />
          </div>
        )}
      </div>
    </div>
  )
}

function TagGroup({ title, tags, emptyLabel }: Readonly<{ title: string; tags: Tag[]; emptyLabel: string }>) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold">
        {title} <span className="text-muted-foreground font-normal">({tags.length})</span>
      </h2>
      {tags.length === 0 ? (
        <p className="text-sm text-muted-foreground">{emptyLabel}</p>
      ) : (
        <ul className="flex flex-wrap gap-2" aria-label={title}>
          {tags.map((tag) => (
            <li key={tag.id}>
              <Link
                to={`/explore/tags/${tag.id}`}
                className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                aria-label={`${displayName(tag)} — ${tag.fact_count} fact${tag.fact_count === 1 ? "" : "s"}`}
              >
                <span className="font-medium">{displayName(tag)}</span>
                <Badge variant="secondary">{tag.fact_count}</Badge>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
