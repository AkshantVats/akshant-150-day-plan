# Day 72 — Experience Post Plan

**Title:** Two-Tier Cache Metrics
**Subtitle:** Agoda · hit ratio by tier
**Format:** `deep-dive` (per `docs/BLOG-FORMAT-MIX.md` — a metrics/observability angle on a
design already covered as `design` on Day 70, so today goes deep-dive instead of repeating format)
**Bridge:** `l1_hit`/`l2_hit`/`miss` is hot/cold query stats for prompts. Today's
prompt-fingerprinter dual-layer cache stack makes that concrete.

## Employer context used

`docs/context/agoda-whitefalcon-tsdb-architecture.md` — WhiteFalcon's Redis hot tier (last
3–7 days, per-hour granularity) vs. Ceph/S3 cold tier (Parquet, coarser granularity); Akshant's
~5-month tenure as a contributing Senior Engineer, NOT the system's designer — attribution
boundary strictly observed. Specifically the cross-tier query engine work: extending the Scala
query layer so one Grafana request could span both tiers, and the observability question that
came with it — how do you know, for any given query, whether it resolved from hot or fell
through to cold?

## Structure (deep-dive format: one mechanism, held up against a real-system parallel)

1. The naive first question about a cache stack's health ("what's the hit rate?") vs. the
   question that actually matters once there are two tiers ("hit rate *at which tier*") — a
   single blended number hides whether the expensive tier is doing needless work.
2. WhiteFalcon's hot/cold split as the direct precedent: a query resolved entirely from Redis
   costs one round trip; a query that fell through to Ceph/S3 paid a materially different
   latency and I/O cost, and knowing the split between the two was what made "should we shrink
   or extend the hot window" an answerable question with real numbers instead of a guess.
3. prompt-fingerprinter's `l1_hit` / `l2_hit` / `miss` as the same three-way split, one layer
   earlier in the request path: an `l1_hit` is a Redis `GET`; an `l2_hit` paid `semantic-cache-
   engine`'s embedding-model round trip; a `miss` paid full inference. Same shape of question —
   which tier actually did the work — different systems.
4. Where the parallel breaks: WhiteFalcon's tier boundary is time (recency); prompt-
   fingerprinter's tier boundary is match type (exact vs. fuzzy). A query doesn't get "more
   likely to hit cold" as it ages the way a prompt doesn't get "more likely to need L2" over
   time — the two boundaries are conceptually different axes that happen to produce the same
   three-bucket observability shape.
5. Why backfilling L2 hits into L1 (so a repeated prompt becomes an `l1_hit` next time) doesn't
   have a clean WhiteFalcon analog — Ceph/S3 data doesn't get promoted back into Redis on a
   cold hit, because WhiteFalcon's tiers are governed by a retention window, not a cache
   promotion policy. That's the one place today's design had to invent something Agoda's
   two-tier split didn't need.

Gold reference read: `blog/series/experience/day-70-exact-match-before-fuzzy.html` (direct
precedent, same arc) and `blog/series/experience/cardinality-is-the-silent-killer-roaringbitmap-lessons.html`
(most recent Agoda-context post, for register match).

## Format diversity check

Last 10 Experience posts (days 63–71): 63 deep-dive, 64 deep-dive, 65 design, 66 incident, 67
feature, 68 design, 69 design, 70 design, 71 deep-dive. Incident count is 1 of 10 — well under
the 4-of-10 trigger. `deep-dive` for Day 72 is chosen for the mechanism-vs-parallel shape of the
metrics story, not because incident-avoidance requires it.
