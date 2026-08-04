# Day 63 — Code Plan

**Repo:** `infra-ai-streaming`, component `semantic-cache-engine/` (subdirectory module,
continuing the Day 44+ / Day 60 / Day 61 / Day 62 precedent — not a separate GitHub repo)
**Product:** RouteIQ
**Ticket:** Cache analytics: hit rate, false-positive proxy (user thumbs-down webhook stub),
cost-saved estimate. Grafana panel + BENCHMARKS.md sweep thresholds 0.88–0.96 on a held-out
prompt set.

## Goal

Day 61 populated the cache (embedding worker) and Day 62 wired the lookup path plus the
`cache_hit` dual-write into LensAI's `infra_ai.inference_events` table (DESIGN.md §5). Both
days left the cache's *quality* unmeasured: nothing yet turns the `cache_hit` event stream
into a hit rate, nothing captures the false-positive signal DESIGN.md §4 designed for, and
nothing gives an operator a dollar figure for what the cache is worth. Day 63 closes that gap:
turn the event stream that already exists into an operator-visible number, add the minimal
webhook DESIGN.md §4 called "a required consumer of the cache_hit event stream," and validate
the shipped `0.92` default (DESIGN.md §8) against real threshold/false-positive tradeoff data
instead of a single point estimate.

## Scope

1. `pkg/lensai` — add a second event kind, `source="cache_feedback"`, dual-written on the same
   `infra_ai.inference_events` table `cache_hit` already uses (DESIGN.md §5's "one clearinghouse
   ledger" principle: a second small table would need its own dashboard and its own join back
   to tenant/model cost data, which is exactly what §5 designed `cache_hit` to avoid).
2. `pkg/feedback` — an HTTP handler package (`Handler`, an `Emitter` interface mirroring
   `pkg/lookup`'s `EventEmitter` pattern for testability) that accepts a thumbs-down signal —
   `{tenant_id, prompt_hash}` — and emits a `cache_feedback` event. This is DESIGN.md §4's
   "sampled human ... review pass" made concrete as the minimal real signal available without
   a judge-LLM pipeline: a user who got a wrong cached answer can flag it.
3. `cmd/feedbackwebhook` — CLI/server entry point wiring the handler to an HTTP listener,
   mirroring `cmd/cachelookup`'s fail-fast required-env-var pattern (`LENSAI_INGEST_URL`).
4. `pkg/analytics` — pure, unit-tested functions (`HitRate`, `FalsePositiveRateProxy`,
   `EstimatedCostSaved`) plus exported ClickHouse SQL query constants that a Grafana panel
   queries verbatim, so the dashboard and the tested Go logic can never silently drift apart.
   `FalsePositiveRateProxy` is explicitly a proxy, not DESIGN.md §4's real measured rate — it is
   `thumbsdown_count / cache_hit_count` from users who bothered to flag, a lower bound on the
   true rate, and the doc comment says so.
5. Grafana dashboard `deploy/grafana/provisioning/dashboards/semantic-cache-analytics.json` —
   three panels (hit rate, false-positive-proxy rate, estimated $ saved) over
   `infra_ai.inference_events`, reusing the `${tenant_id}` templating pattern
   `tool-call-analyzer/grafana/unified-tenant-cost.json` established.
6. `semantic-cache-engine/BENCHMARKS.md` — a threshold sweep (0.88, 0.90, 0.92, 0.94, 0.96)
   over a held-out labeled prompt-pair set, reporting precision/recall/false-positive-rate at
   each threshold, run via `cmd/threshold-sweep` and pasted with real output — not fabricated
   numbers. **OPENAI_API_KEY in this sandbox is at its billing quota limit (confirmed by a
   live probe, HTTP 429 `insufficient_quota` — same constraint Day 62 hit for DALL-E)**, so the
   sweep cannot call the real `text-embedding-3-small` API. The sweep tool uses a small local,
   deterministic bag-of-words cosine-similarity function instead of a live embedding call —
   documented plainly in BENCHMARKS.md as a proxy for the real embedder, not a claim of
   measuring `pkg/embedder.OpenAIEmbedder`'s actual behavior. This keeps DESIGN.md §8's shipped
   `0.92` default checked against *some* real, reproducible numbers rather than none, while
   being honest that it is not the same signal a live pgvector + OpenAI run would produce.

## Out of scope

- No real human/LLM-judge review pipeline (DESIGN.md §4's full design) — the webhook is the
  minimal real signal, not the full pipeline.
- No live ClickHouse/pgvector in this sandbox — `pkg/analytics`'s SQL constants are
  unit-testable as strings/pure functions only; no new integration test, same gap already
  logged for Days 61–62.
- No changes to `pkg/lookup`'s hit/miss decision logic — Day 63 measures the existing 0.92
  default, it does not change it.

## Tests

Unit tests for `pkg/analytics` (hit rate / false-positive-proxy / cost-saved arithmetic,
including zero-denominator edge cases), `pkg/feedback` (handler validates input, calls emitter,
maps emitter errors to 5xx / bad input to 4xx), `pkg/lensai`'s new `EmitCacheFeedback` (mirrors
existing `EmitCacheHit` test shape against an `httptest.Server`), and `cmd/threshold-sweep`
(deterministic sweep output over a small fixed fixture). Target 100% pass on the unit suite.
