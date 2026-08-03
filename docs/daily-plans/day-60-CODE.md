# Day 60 — Code Plan

**Repo:** `infra-ai-streaming`, new component `semantic-cache-engine/`
**Product:** RouteIQ (first day of a new product arc — previous arc, TraceForge, closed at Day 59)
**Ticket:** semantic-cache-engine — DESIGN.md: embedding pipeline, pgvector schema, similarity
threshold per tenant, false-positive budget, integration with LensAI `cache_hit` events. Define
TTL and freshness decay policy.

## Goal

Day 58's synthesis post named RouteIQ as "the routing/caching layer that consumes what
TraceForge observes." Day 60 opens that arc the same way Day 14 opened `ebpf-llm-tracer`:
a DESIGN.md-first day, no runtime code yet. `semantic-cache-engine` is a new top-level
component inside `infra-ai-streaming` (same repo, same pattern as `agent-benchmark-runner`
and `tool-call-analyzer` — not a new standalone repo). Its job: cache LLM responses keyed by
embedding similarity instead of exact prompt match, so near-duplicate prompts (same intent,
different wording) can still hit cache.

## Scope

1. Create `semantic-cache-engine/` at repo root with `DESIGN.md` covering, as six sections:
   - **Embedding pipeline**: where the embedding call sits relative to the existing
     `ingestion` → Kafka → `consumer` path; which model/dimension is assumed (document as a
     pluggable interface, not a hard dependency — no live embedding model is available in
     this build's sandbox).
   - **pgvector schema**: table for `(tenant_id, prompt_hash, embedding vector(N), response,
     created_at, last_hit_at)`, the ivfflat/hnsw index choice and why, and how it composes
     with the existing multi-tenant model already used in `ingestion`/`consumer`.
   - **Similarity threshold per tenant**: a per-tenant config value (not global) with a
     documented default and the tradeoff — too low = false cache hits (wrong answer served),
     too high = cache never fires.
   - **False-positive budget**: define what a false positive costs (a wrong cached answer
     served to a user) and a target upper bound, plus how the design would measure it
     (mirrors the day's AI Learning post's dollars-not-vibes framing — do not repeat that
     post's prose here, just make the design testable).
   - **Integration with LensAI `cache_hit` events**: reuse the existing `InferenceEvent`
     `source` field pattern from Day 59 (`source='inference'` vs `source='benchmark_run'`) —
     add `source='cache_hit'` as the third documented value so cache hits land in the same
     ClickHouse table instead of a parallel one, consistent with Day 59's "one clearinghouse
     ledger" design.
   - **TTL and freshness decay policy**: cached entries decay in relevance over time even if
     never evicted by size; define the decay function and a hard TTL ceiling.
2. Add `semantic-cache-engine/README.md`: one-paragraph purpose, links to DESIGN.md, and an
   explicit "Status: design-only, no runtime code yet" line (matches `ebpf-llm-tracer`'s
   Day 14 pattern — do not imply a working service exists yet).
3. Add SPDX MIT license header convention note to `CONTRIBUTING.md` if `semantic-cache-engine`
   introduces any code stub (it should not on Day 60 — DESIGN.md and README only).
4. Update root `README.md`'s component list to add `semantic-cache-engine` alongside the
   existing `agent-benchmark-runner`, `agent-replay-engine`, `tool-call-analyzer` entries,
   one line, "design-only" status noted.

## Out of scope

- No pgvector migration, no actual embedding calls, no new Kafka topic, no ClickHouse schema
  changes — this is a design doc day, same shape as Day 14's `ebpf-llm-tracer` DESIGN.md.
- No changes to `ingestion` or `consumer` runtime code.

## Tests

No new runtime tests (design-doc-only day, no executable surface added). Run the existing
full suites (`cargo test`, `go test ./...`) unchanged to confirm the new directory doesn't
break builds — expect the pre-existing pass rate, not a new count.
