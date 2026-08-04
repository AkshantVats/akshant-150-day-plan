# Day 63 — Experience Post Plan

**Title:** Hit Rate Without Honesty Is Vanity
**Subtitle:** Agoda · dashboard trust
**Employer:** Agoda — read `docs/context/agoda-whitefalcon-tsdb-architecture.md` and
`docs/context/resume-extracted.md` before writing.
**Format:** `patterns` — format diversity check against the last 10 posts (Day 58–62, both
series) found **zero** `incident`-format posts, so no override is forced, but the angle below
is a synthesized principle drawn from one incident used as illustration, not a moment-by-moment
postmortem (no timeline/blast-radius/root-cause/fix/guardrails structure) — `patterns` per
`docs/BLOG-FORMAT-MIX.md`'s definition ("synthesized patterns from multiple incidents — not a
single fake outage").

## Bridge

Cache analytics must show false-positive proxies or operators won't trust hit rate. Today's
`semantic-cache-engine` work (Day 63: `pkg/analytics`, the thumbs-down webhook, the Grafana
panel) makes that concrete: a hit-rate-only dashboard is a vanity metric, because a rising hit
rate and a rising wrong-answer rate look identical on a chart that only counts hits.

## Content anchors — must come only from `agoda-whitefalcon-tsdb-architecture.md`

- **The cardinality incident** (`## The cardinality incident (basis for Experience posts)`):
  Prometheus scrape duration crept up while request rate stayed flat. Root cause: a `pod`
  label added to a fleet metric multiplied existing series on every new pod. No alert fired
  until scrape targets started failing outright — **the alert designed to detect stack
  degradation was the first thing to go dark.** This is the anchor: a monitoring signal that
  only reports "healthy" gives no signal at the exact moment it stops being able to see the
  problem.
- **Schema discipline enforced after the incident**: cross-product analysis required before
  any new tag, a 10k max label budget per metric (hard cap), high-cardinality labels must
  justify their combinatorial cost. This is the "what changed after" — not a single alert
  fixed, but a second, independent check added (the budget) so cardinality growth could not
  silently blow past the point where the first alert still worked.
- **Tenure/scope**: Akshant was a Senior Engineer, Core Infrastructure, on WhiteFalcon TSDB
  for ~5 months (Apr 2024–Sep 2024). He did not design RoaringBitmap, Kafka pipeline, or the
  alerting stack itself — frame this as the pattern observed operating alongside that system
  during the incident, not a claim of having designed the alerting.
- Do NOT invent a specific outage duration, a specific series count at time of failure beyond
  the doc's own worked example (`model_id (200) × tenant_id (500) × status (3) = 300,000
  series`, `+pod(50) × zone(4) → 60M combinations possible`), or claim Akshant personally
  fixed the alert — the doc only says schema discipline was enforced after, not by whom.

## Angle

- Open on the concrete decision Day 63 makes: a `pkg/analytics` hit-rate panel with no
  false-positive-proxy panel beside it is the same shape of failure as an alert that only
  tells you "no alert fired" — a number that goes up looks like health whether or not it
  actually is.
- Bring in the cardinality incident as the concrete anchor: the alert that was supposed to
  catch stack degradation had exactly one failure mode nobody had designed for — going dark
  precisely because the thing it measured (scrape success) degraded gracefully right up until
  it didn't. A cache hit-rate metric has the same blind spot: it counts hits, and a hit that
  served the wrong answer counts identically to a hit that served the right one.
- Land on: what fixed WhiteFalcon's alerting was not a better alert on the same signal, it was
  a second, independent signal (the label budget) that could catch what the first one
  couldn't see coming. `pkg/analytics`'s false-positive-proxy panel (built from the thumbs-down
  webhook, a second and different signal from the hit-rate count itself) is the same move: not
  a smarter hit-rate calculation, a second measurement that can be wrong in a different way
  than the first one.
- So what: a single dashboard number is only as trustworthy as its blind spot is small, and
  the way to shrink a blind spot is never "compute the existing number more carefully" — it's
  adding a second signal that fails independently of the first.
