# Day 53 — Experience Blog Plan

**Title**: 14 Calls vs 9 — The Report Hiring Managers Get
**Subtitle**: Agoda · efficiency · cost per outcome
**Employer context**: `docs/context/agoda-whitefalcon-tsdb-architecture.md` (cross-tier
quantile merge — Akshant's contribution) + `docs/context/resume-extracted.md` for tenure
and scale numbers. Relevant lines only:
- Agoda, Bangkok, Apr 2024 – Sep 2024, Sr. Software Engineer, Core Infrastructure —
  WhiteFalcon TSDB. Contributed the cross-tier query engine extension: before, a query
  spanning the Redis hot tier and the S3/Parquet cold tier required two manual queries
  stitched by the caller; after, a single request spans both tiers with correct
  histogram-bucket merge logic (percentiles are not additive across tiers).
- Do NOT claim RoaringBitmap engine, Kafka pipeline, or storage tiering design — Agoda
  team's work. Akshant's scope: cross-tier query engine extension, new Kubernetes-tag
  cardinality dimension, 2–3 new Grafana query types.

**Format**: `patterns` (lessons/pattern essay, per `docs/BLOG-FORMAT-MIX.md`) — the
title/subtitle signals ("efficiency", "cost per outcome") map to a synthesized lesson
about audience-appropriate reporting, not a single incident. Avoids a fourth
cross-tier-query post reading as a repeat of `when-percentiles-lie-cross-tier-queries.html`
by anchoring on the *reporting* lesson (which summary reaches which reader) rather than
re-explaining the histogram-merge mechanism itself.

**Bridge**: comparison markdown is the executive summary of a trace — dollars and steps,
not vibes. Today's code in `agent-benchmark-runner` (`pkg/report`) implements that lesson:
a `Report.Headline` that leads with a call-count/divergence comparison instead of a
pass/fail badge, the same discipline that made the Agoda cross-tier fix legible to a
reviewer who never opened the histogram-merge diff — round trips, not percentile math.

## Angle

At Agoda, the cross-tier query engine fix was accurately explained two ways: the
engineering explanation (histogram bucket counts merge correctly where pre-computed
percentiles don't) and the outcome explanation (two manual queries became one). The first
explanation is what an engineer reviewing the diff needs. The second is what a reviewer
who's deciding whether the contribution mattered actually reads and restates — and it
needs no background in percentile statistics to land.

Bridge into `agent-benchmark-runner`: the report generator's headline —
`"14 calls vs 9, diverged at step 5"` — does the identical job on a much smaller stage.
Two independent pass/fail badges answer "did each one pass," which a benchmark's
`compare.Result` already reports per agent; they don't answer "where did the runs
actually differ," which is the question a reviewer opens a benchmark report to ask first.
`pkg/report` renders three shapes off the same `Report` struct — markdown, JSON, an SVG
timeline — for three different readers, mirroring the three honest summaries the Agoda
self-review needed (engineer / dashboard / non-code reviewer).

## Series Navigation

Previous: Day 52 — Parallel Runs — Respect the Rate Limit
Next: Day 54 — TBD
