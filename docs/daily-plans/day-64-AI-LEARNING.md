# Day 64 — AI Learning Blog Plan

**Title:** Day 64 — Load Testing ANN
**Subtitle:** 1k QPS methodology
**day_index:** 64
**Hook:** Same k6 discipline as ingestion — p99 under SLA.
**Format:** `deep-dive` (per `docs/BLOG-FORMAT-MIX.md`) — one mechanism (why load-testing an
ANN index means measuring the tail, not the mean, and what a closed-loop harness can and can't
tell you) developed with a DS analogy, continuing the RouteIQ arc Day 60–63 opened.

## Required reading before writing

- `day-2-continuous-batching-vllm.html` (GOLD post) for depth/structure.
- Most recent AI Learning post (Day 63 — "Cache Quality Metrics") for register, and to make
  the arc continuation explicit: Day 62 covered how the lookup finds a candidate, Day 63
  covered whether the threshold that decided "close enough" was right, Day 64 covers whether
  the whole path is fast enough once real concurrent traffic hits it.
- Today's `semantic-cache-engine` code (Day 64: `pkg/loadtest`, `cmd/loadtest`,
  `docker-compose.yml`) for the concrete technical anchor.

## Angle

- Open on or build to the hook: the same k6-style discipline that validated the ingestion
  pipeline's P99 (README.md's engineering targets: 1M events/min, P99 < 100ms) applies to a
  cache lookup — a single "average latency: 3ms" number tells you nothing about whether the
  cache stays inside its SLA under load, because averages are exactly what tail latency hides
  behind.
- Core mechanism: closed-loop vs. open-loop load generation. A closed-loop harness (issue the
  next request only after the previous one completes, or on a fixed-rate ticker with a bounded
  worker pool — what `pkg/loadtest.Run` does) under-counts tail latency during a slowdown,
  because a worker stuck on a slow request stops generating new load instead of piling requests
  up the way real, independent clients would — the well-known "coordinated omission" problem.
  An open-loop generator (fixed arrival rate regardless of whether prior requests finished)
  is closer to real traffic and would expose that pile-up as it happens.
- Explain what `pkg/loadtest` actually measures and why that's still useful: p50/p95/p99 over
  `FindNearest` calls at a target QPS with bounded concurrency, honest about being a
  closed-loop harness — good for "is the index's own query cost within budget under a given
  concurrency," not a substitute for a full open-loop production-traffic replay.
- DS analogy (attr-box required): a toll booth with one lane open queues cars politely one at a
  time — average wait looks fine right up until a burst arrives, and then every car behind
  the burst waits in a growing line the "average wait per car so far" doesn't show yet. A
  closed-loop load test is like timing only the cars already through the booth; an open-loop
  test is like counting the whole line, including the cars still waiting. The load-testing
  harness's job is to measure percentiles, not averages, precisely because the tail is where
  the queue shows up first.
- Land on: `pkg/loadtest`'s p99 number from this sandbox run is real math over real
  measurements, but it's measured against `MemStore`'s simulated flat-latency stand-in (no live
  Docker daemon here) with evenly distributed synthetic tenants — a number worth publishing with
  its scope stated, not a number worth treating as the production p99 until it's re-run against
  a live pgvector instance under realistic per-tenant skew.

## Required elements

- attr-box DS analogy (toll booth / single-lane queue, above).
- `ai.hook` opening: "Same k6 discipline as ingestion — p99 under SLA."
- Mermaid diagram(s): closed-loop harness request flow (ticker → worker pool → FindNearest →
  latency histogram), max 8 nodes, labels ≤ 6 words, required init block per CLAUDE.md §4.5.
- Kicker `Day 64 of 150`.

## Self-review reminders

Max 3 sentences/paragraph. `Day 64` in `<title>`, `<h1>`, accent tag, meta line. No fabricated
production p99 numbers — only the sandbox `MemStore` numbers from `BENCHMARKS.md`, explicitly
scoped as such.
