# Day 64 — Experience Post Plan

**Title:** pgvector Under Load
**Subtitle:** Agoda · index hot spots
**Employer:** Agoda — read `docs/context/agoda-whitefalcon-tsdb-architecture.md` and
`docs/context/resume-extracted.md` before writing.
**Format:** `deep-dive` — format diversity check against the last 10 posts (Day 54–63, both
series) found zero `incident`-format posts, so no override is forced. The post teaches one
mechanism (why an index's query cost depends on how load is distributed across it, not just
total volume) through one employer anchor, per `docs/BLOG-FORMAT-MIX.md`'s `deep-dive`
definition.

## Bridge

ANN index tuning is hot-partition management for vectors. Today's `semantic-cache-engine`
work (Day 64: `docker-compose.yml`, `pkg/loadtest`, a real load-test harness) makes that
concrete: an HNSW index's latency isn't a single number, it's a distribution shaped by how
lookups land across the index — and that's the same shape of problem the RoaringBitmap
inverted index at Agoda had with skewed tag-value cardinality.

## Content anchors — must come only from `agoda-whitefalcon-tsdb-architecture.md`

- **RoaringBitmap indexing** (`## Indexing — RoaringBitmap inverted index`): one bitmap per tag
  value, mapping to the set of series IDs carrying that value; query execution is set
  operations (intersect/subtract) across bitmaps. Cardinality constraint: bitmaps grow with
  distinct values × series count, and **high-traffic metrics with high-cardinality tags balloon
  specific bitmaps overnight** — not the whole index uniformly, specific hot bitmaps. This is
  the anchor: an index's cost is never evenly spread: some tag values (some vectors, some
  tenants) are hotter than others, and that skew — not the average — is what determines tail
  latency.
- **The cardinality incident**: Prometheus scrape duration crept up while request rate stayed
  flat; root cause was a `pod` label added to a fleet metric multiplying existing series on
  every new pod — the label explosion example (`model_id (200) × tenant_id (500) × status (3)
  = 300,000 series`, then `+ pod(50) × zone(4) → 60M combinations possible`) is the concrete,
  quotable number. No alert fired until scrape targets started failing outright.
- **Schema discipline enforced after**: cross-product analysis required before any new tag,
  10k max label budget per metric (hard cap), high-cardinality labels must justify their
  combinatorial cost. This is the "what changed" — a budget/guardrail on skew, not just a
  bigger index.
- **Tenure/scope**: Senior Engineer, Core Infrastructure, WhiteFalcon TSDB, ~5 months
  (Apr–Sep 2024). Frame as observing/contributing alongside the RoaringBitmap engine (adding
  the Kubernetes cardinality dimension, cross-tier query engine work), never as having designed
  the RoaringBitmap engine itself.
- Do not invent new scale numbers beyond the doc's own ranges (1.5T–1.8T events/day) or a new
  incident beyond the cardinality incident already documented.

## Today's code anchor (semantic-cache-engine, Day 64)

`pkg/loadtest` drives `FindNearest` — the HNSW ANN query path — at a target QPS and reports
p50/p95/p99, not just an average. The reason that distinction matters is the same reason a
RoaringBitmap index's *average* bitmap size never predicted the cardinality incident: skew
hides inside an average. A cache where 90% of tenants have ten cached prompts and one tenant
has a hundred thousand doesn't have one query cost — the p50 lookup is cheap and the p99
lookup is walking a much bigger graph neighborhood for that one hot tenant. Load-testing at a
flat aggregate QPS without per-tenant skew, as Day 64's harness sandbox run necessarily does
(no live Postgres — `docker-compose.yml` is written and schema-validated but not run end to
end here), measures the easy case; the honest caveat is that the real p99 risk lives in the
skewed case this run cannot reproduce without a live multi-tenant dataset.

## Angle

- Open on the RoaringBitmap bitmap-hot-spot mechanic, not on today's code.
- Turn: pgvector's HNSW index has the same shape of risk — an index's cost model is a
  distribution across keys/tags/vectors, not a single number, and skew in that distribution
  (one tenant, one tag value, one hot partition) is invisible until you measure percentiles
  instead of an average.
- Land on Day 64's honest gap: the load-test harness measures p50/p95/p99 correctly, but only
  the sandbox's evenly-distributed synthetic seed data — the real test (per-tenant skew,
  matching the cardinality incident's lesson) needs a live instance this sandbox doesn't have.
  A guardrail (per-tenant budget, akin to Agoda's 10k label cap) is the natural next design
  question, not yet built.

## Self-review reminders

Max 3 sentences/paragraph. `Day 64` in `<title>`, `<h1>`, accent tag, and meta line (kicker
`Experience · Day 64 of 150`). No invented Agoda system names or numbers outside the context
doc.
