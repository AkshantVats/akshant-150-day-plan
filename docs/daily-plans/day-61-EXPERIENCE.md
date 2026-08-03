# Day 61 — Experience Post Plan

**Title:** Embeddings Are Batch Jobs
**Subtitle:** Agoda · compaction windows
**Employer:** Agoda — read `docs/context/agoda-whitefalcon-tsdb-architecture.md` and
`docs/context/resume-extracted.md` before writing.
**Format:** `feature` (per `docs/BLOG-FORMAT-MIX.md`) — Day 60 was DESIGN.md-only; Day 61
ships the first real code (`pkg/embedder`, `pkg/prompthash`, `pkg/cachestore`, `pkg/worker`,
`cmd/embedworker`) against that design, so today is "we turned DESIGN into a worker."

## Bridge

Embedding worker batching is compaction — amortize API cost, control lag. Today's
`semantic-cache-engine` work (batch-of-32 embedding calls, idempotent upsert on `prompt_hash`)
makes that concrete: an embedding API call is expensive per-request the same way a storage
compaction pass is expensive per-file, so both systems buy back cost by waiting to accumulate
a batch before doing the expensive thing once.

## Content anchors — must come only from `agoda-whitefalcon-tsdb-architecture.md`

- **Compaction cadence** (Agoda team's design, hot tier → cold tier): WhiteFalcon's Redis hot
  tier flushes time-windowed buckets to Ceph/S3 as Parquet, then compaction jobs merge those
  files on a fixed cadence — **hourly → 3-hour → daily** — coarsening granularity for data
  older than the 3–7 day hot window.
- **Scale anchor**: 1.5T events/day through the Kafka → Rust consumer → Redis path (resume
  figure; Kafka forwarder cardinality post cites 1.8T — use 1.5T as the primary number per
  the doc's stated range).
- **Tenure/scope**: Akshant was a Senior Engineer, Core Infrastructure, on WhiteFalcon TSDB
  for ~5 months (Apr 2024–Sep 2024). He did not design the compaction pipeline or the
  Rust/Kafka ingest path — that is Agoda team's design. Frame this post as the pattern
  observed operating alongside that pipeline, not a claim of having built the compactor.
- Do NOT invent a specific compaction incident, a specific file-count or byte-size number for
  compaction jobs, or claim ownership of the Ceph/S3 tiering — none of those figures exist in
  the context doc; describe the *cadence* (hourly → 3-hour → daily) and the *reason*
  (amortize per-file merge cost, coarsen old data) only.

## Angle

- Open on the concrete decision `pkg/worker` makes today: batch 32 prompts before calling the
  embedding API, rather than one API call per prompt — a batch size chosen for the same
  reason WhiteFalcon's compaction jobs don't merge every new Parquet file the instant it
  lands.
- Bring in the hourly → 3-hour → daily compaction cadence as the concrete anchor for "batching
  isn't free lag, it's a deliberate window chosen to amortize a per-call cost against
  Kafka-then-Redis's continuous write pressure" — same shape of tradeoff, one dial is batch
  size (32 prompts), the other is compaction interval (hourly/3-hour/daily).
- Land on: idempotency is what makes both safe to batch. WhiteFalcon's compaction merges are
  safe to re-run because they operate on immutable time-windowed Parquet files; the embedding
  worker's upsert is safe to re-run because it's `ON CONFLICT (tenant_id, prompt_hash) DO
  NOTHING` — neither system has to worry about a retried batch corrupting state, so both can
  batch aggressively without a fragile "did this already run" check.
- So what: without idempotency, batching is a liability — a retried batch either double-writes
  or requires exact-once delivery, which is hard. With idempotency, batching is free
  optimization — the retried batch just does nothing extra. That's the design decision
  `prompt_hash`-keyed conflict handling buys, same as the append-only, re-mergeable Parquet
  files WhiteFalcon's compaction depends on.
