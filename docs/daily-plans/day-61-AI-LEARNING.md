# Day 61 — AI Learning Blog Plan

**Title:** Day 61 — Embedding Pipelines
**Subtitle:** Batch, idempotency, backfill
**day_index:** 61
**Hook:** `prompt_hash` idempotency is Kafka exactly-once for vectors.
**Format:** `deep-dive` (per `docs/BLOG-FORMAT-MIX.md`) — one mechanism (batching + idempotent
upsert) developed with a DS analogy, continuing the RouteIQ arc Day 60 opened.

## Required reading before writing

- `day-2-continuous-batching-vllm.html` (GOLD post) for depth/structure.
- Most recent AI Learning post (Day 60 — "Semantic Caching Economics") for register and to
  make the arc continuation explicit: Day 60 covered the threshold/economics side of
  `semantic-cache-engine`; Day 61 covers the embedding-pipeline side that actually populates
  the cache the threshold gets applied against.
- Today's `semantic-cache-engine` code (Day 61: `pkg/embedder`, `pkg/prompthash`,
  `pkg/cachestore`, `pkg/worker`) for the concrete technical anchor.

## Angle

- Open on or build to the hook: `prompt_hash` idempotency is Kafka exactly-once for vectors —
  Kafka's exactly-once semantics rely on a deduplication key (producer ID + sequence number)
  so a redelivered message doesn't get processed twice; the embedding worker gets the same
  guarantee for free by keying its upsert on `prompt_hash` and using `ON CONFLICT DO NOTHING`.
- Core mechanism: batch size 32 amortizes the embedding API's fixed per-request overhead
  (auth, network round trip, provider-side batching limits) across many prompts, the same way
  any batch-vs-per-item tradeoff trades latency for throughput — bigger batches mean fewer,
  cheaper-per-item calls, at the cost of the last prompt in a batch waiting longer.
- DS analogy (attr-box required): a bank teller who processes each deposit individually opens
  a new transaction, verifies, and closes it every single time — the same fixed overhead paid
  per customer; a teller who waits to batch ten deposit slips before running them through the
  ledger system once pays that fixed overhead once for ten transactions. The embedding
  worker's batch-of-32 is the same trade: pay the embedding API's fixed per-call overhead once
  per 32 prompts instead of once per prompt.
- Idempotency as the safety net that makes batching (and retries) free: without a dedup key, a
  retried batch either double-embeds (wasted API cost) or double-writes (corrupt cache state).
  With `prompt_hash` + `ON CONFLICT DO NOTHING`, a retried batch just re-does work that
  produces the same no-op result — the batch can be retried blindly.
- Backfill framing: the same worker that processes new prompts as they arrive can be pointed
  at historical prompt logs to backfill embeddings, because idempotency means running it twice
  over overlapping data is safe — no separate "backfill mode" logic needed, just the same
  batch-and-upsert loop over a different input source.

## Diagram requirement

Standard mermaid init block (CLAUDE.md §4.5). One flowchart showing: prompts arrive →
accumulate to batch of 32 → embed batch (one API call) → compute prompt_hash per item →
upsert with ON CONFLICT DO NOTHING → stored in pgvector. Labels ≤6 words, ≤8 nodes.

## Constraints

- Kicker: `Day 61 of 150`.
- ai.hook opening line, attr-box DS analogy present.
- No invented production benchmark numbers (no live pgvector/embedding API in this build's
  sandbox) — frame any latency/cost example as illustrative, not a claim of a real measured
  run.
