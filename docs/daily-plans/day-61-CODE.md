# Day 61 — Code Plan

**Repo:** `infra-ai-streaming`, component `semantic-cache-engine/` (subdirectory module,
continuing the Day 44+ / Day 60 precedent — not a separate GitHub repo)
**Product:** RouteIQ
**Ticket:** Embedding worker: call embedding API (OpenAI `text-embedding-3-small` or local),
batch size 32, write vectors to pgvector table `prompts(tenant_id, prompt_hash, embedding,
created_at)`. Idempotent on `prompt_hash`.

## Goal

Day 60 shipped `semantic-cache-engine/DESIGN.md` — pgvector schema, per-tenant similarity
threshold, TTL/decay policy, all design-only. Day 61 turns the embedding-pipeline section of
that design into the first runtime code: a worker that actually calls an embedding API in
batches of 32 and upserts vectors into the `prompts` table, idempotent on `prompt_hash` so
retries and redeliveries never double-write.

## Scope

1. `pkg/embedder` — an `OpenAIEmbedder` implementing a small `Embedder` interface
   (`Embed(ctx, []string) ([][]float32, error)`) over `text-embedding-3-small`, matching the
   pluggable-interface shape DESIGN.md specified (no hard dependency on one provider).
2. `pkg/prompthash` — normalize (trim, lowercase, collapse whitespace) then SHA-256 the prompt
   text to produce `prompt_hash`, matching DESIGN.md's schema column.
3. `pkg/cachestore` — pgvector upsert via `pgx/v5`, `INSERT ... ON CONFLICT (tenant_id,
   prompt_hash) DO NOTHING`, so re-running the worker over already-embedded prompts is a
   no-op rather than a duplicate row or an error.
4. `pkg/worker` — batches incoming prompts into groups of 32 before calling the embedder (one
   API call per batch, not per prompt), plus in-run dedup so the same prompt_hash appearing
   twice in one batch collapses to a single embed + upsert call.
5. `cmd/embedworker` — CLI entrypoint wiring the above together, reading from the existing
   ingestion path per DESIGN.md's "where the embedding call sits relative to `ingestion` →
   Kafka → `consumer`" placement.

## Out of scope

- No changes to the `pricing_refresh`/`sku_pricing_refresh`-style Kafka topics or the
  `ingestion`/`consumer` runtime paths themselves — this worker consumes from the existing
  path, it doesn't modify it.
- No live pgvector/Postgres instance in this build's sandbox — integration test for the
  upsert/idempotency path is written but gated behind `-tags=integration` and `PGVECTOR_DSN`,
  skipped here and logged as follow-on CI scope (DESIGN.md section 7).
- No backfill tooling yet (future day).

## Tests

Unit tests for `prompthash` normalization, `embedder` batching/dedup logic, and `cachestore`
upsert SQL construction — target 100% pass on the unit suite. Integration test for actual
pgvector idempotency is present but skipped without a live DSN, not silently dropped.
