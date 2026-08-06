# Day 72 — Code Plan

**Repo:** `infra-ai-streaming`, component `prompt-fingerprinter/` (continuing Day 70's
DESIGN.md and Day 71's `pkg/fingerprint`)
**Product:** RouteIQ
**Ticket:** Dual-layer cache stack — L1 exact Redis (prompt-fingerprinter's own fingerprint),
L2 semantic pgvector (`semantic-cache-engine`'s existing `pkg/lookup.Lookup`). Metrics
`l1_hit`, `l2_hit`, `miss`. Document the stack diagram in README.

## Goal

Day 70's DESIGN.md specified the ordering (fingerprint check before the semantic path ever
runs); Day 71 built the fingerprint primitives (`Normalize`/`Fingerprint`/`RedisKey`) but wired
nothing together. Day 72 is the composition day: a `pkg/stack` package that puts a Redis-backed
L1 exact-match check in front of `semantic-cache-engine`'s existing `pkg/lookup.Lookup` (which
is itself L2 — Postgres exact fallback plus pgvector nearest-neighbor), with its own
three-outcome metrics (`l1_hit` / `l2_hit` / `miss`) distinct from `lookup.Lookup`'s internal
`cache_hit`/`cache_miss` events.

## Scope

1. `pkg/stack/stack.go` — `Stack.Get(ctx, tenantID, req)`: computes the fingerprint via
   `pkg/fingerprint`, does a Redis `GET` on `RedisKey(tenantID, fingerprint)`. A hit increments
   `l1_hit` and returns immediately, skipping L2 entirely. A miss falls through to
   `semantic-cache-engine/pkg/lookup.Lookup` (L2); `Lookup`'s own `Result.Hit` becomes this
   layer's `l2_hit` or `miss`. On an `l2_hit`, the Stack writes the response back into Redis at
   the fingerprint key so the *next* byte-identical repeat is an L1 hit — the whole point of a
   two-tier design is that a prompt only ever pays the L2 cost once per tenant.
2. `pkg/stack/redis.go` — a small `RedisClient` interface (`Get`/`Set` on `[]byte`), so tests
   inject an in-memory fake instead of a live Redis instance (no Docker daemon in this sandbox,
   same constraint every prior Day has logged).
3. `pkg/stack/metrics.go` — `Metrics` interface (`IncL1Hit`, `IncL2Hit`, `IncMiss`) plus an
   in-memory counter implementation for tests; a real implementation wires to LensAI in a
   future day, same deferred-wiring pattern as `cost-budget-enforcer`'s Kafka audit log.
4. `README.md` — new "Cache stack" section: a mermaid diagram (request → L1 Redis → hit: serve
   / miss: → L2 semantic-cache-engine → hit: serve + backfill L1 / miss: pass through to
   inference), plus a one-line description of each of the three metrics.

## Out of scope

- No live Redis or Postgres instance exercised in this sandbox (no Docker daemon) — `RedisClient`
  and `lookup.Lookup`'s own dependencies (`cachestore.Reader`, `embedder.Embedder`) are exercised
  through fakes only.
- No change to `semantic-cache-engine`'s own code — `pkg/stack` depends on its `pkg/lookup`
  package as a library import, module boundary stays one-directional (prompt-fingerprinter
  depends on semantic-cache-engine, never the reverse).
- No gateway wiring (`cost-budget-enforcer/pkg/gateway`) — deferred past this day's scope, same
  as DESIGN.md's "Out of scope (Day 70)" note already flagged.

## Tests

Table tests for `Stack.Get`: L1 hit (no L2 call made), L1 miss + L2 hit (backfill written, both
counters correct), L1 miss + L2 miss (no backfill, `miss` counter only), Redis `Get` error
(fail-open to L2, mirroring `cost-budget-enforcer/pkg/middleware`'s existing fail-open
precedent for a cache-layer error). Target ≥90% pass rate per the build-slot threshold.
