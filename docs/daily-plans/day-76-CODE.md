# Day 76 — Code Plan

**Repo:** `infra-ai-streaming`, component `prompt-fingerprinter` (new packages: `pkg/admin`,
`pkg/rules`, `pkg/lensai`; extends `pkg/fingerprint` and `pkg/stack`)
**Product:** RouteIQ
**Ticket:** Admin REST API `PUT /tenants/{id}/fingerprint-rules` (strip_punctuation, lowercase,
max_prompt_bytes); integration test proving duplicate prompts skip the embedding API; emit
`cache_hit_type=exact` to the LensAI ingest pipeline.

## Goal

DESIGN.md §6 already committed to this scope for Day 76: "the admin `PUT /tenants/{id}/
fingerprint-rules` endpoint" and starting to emit `cache_hit_type=exact` — the point where the
`cache_hit_exact` source value DESIGN.md §4 reserved on Day 70 actually starts producing events
instead of just being documented. Today closes both gaps and adds the integration test that proves
the whole point of Day 70-75's work: a byte-identical duplicate prompt never reaches the (simulated)
embedding API a second time.

## Scope

1. `pkg/fingerprint/rules.go` (new) — `Rules{StripPunctuation, Lowercase, MaxPromptBytes}`, a
   tenant's optional normalization overrides layered on top of `Normalize`'s fixed §1 contract, not
   replacing it. `Rules{}` (zero value) is a documented no-op — `Apply` returns the request
   unchanged — so a tenant that has never called the admin API fingerprints exactly as every tenant
   did before Day 76 shipped. `Apply` runs in a fixed order (strip punctuation → lowercase →
   truncate to `MaxPromptBytes` on a valid UTF-8 boundary) so the same `Rules` value always produces
   the same output for the same input regardless of caller.
2. `pkg/rules/store.go` (new package) — `Store`, a concurrency-safe `map[string]fingerprint.Rules`
   mutated only through the admin handler. `ForTenant` returns the zero value for an unconfigured
   tenant (today's default). `Put` validates `MaxPromptBytes` (must be `>= 0`, capped at a 1MB
   ceiling so an operator typo can't disable the cap in the other direction) before committing a
   full replace — PUT semantics, not `cost-budget-enforcer/pkg/admin`'s partial-PATCH pointer-field
   style, because a fingerprint-rules resource is small enough that "send the whole thing" is the
   simpler contract.
3. `pkg/admin/admin.go` (new package) — `Handler` serving `PUT /tenants/{id}/fingerprint-rules`,
   same `parseTenantID`/`writeError` shape as `cost-budget-enforcer/pkg/admin`. No audit-publish
   step (that module's audit log is specific to budget changes with a rollback-on-publish-failure
   contract; a fingerprint-rules change has no dollar impact to audit the same way) — out of scope
   note below.
4. `pkg/lensai/writer.go` (new package) — mirrors `cost-budget-enforcer/pkg/lensai`'s `Writer`/
   `Event` shape exactly (same `/ingest` HTTP envelope every Go producer in this repo already
   posts through, which is what actually reaches LensAI's Kafka topic on the Rust ingestion side —
   no direct Kafka client in this module, same as every sibling `pkg/lensai`). `SourceCacheHitExact
   = "cache_hit_exact"` is DESIGN.md §4's already-reserved value; `EmitExactHit` posts it at
   `cost_usd=0`.
5. `pkg/stack/stack.go` — `Stack` gains two optional fields, both nil-safe like `Metrics` already
   is: `Rules RulesProvider` (applied to the request before fingerprinting, when set) and `Emitter
   EventEmitter` (fired best-effort on an L1 hit, when set). Neither field changes `Get`'s return
   value or existing test behavior when left nil — this is additive wiring, not a signature change
   to any existing call.
6. `pkg/stack/integration_test.go` (new) — the ticket's required integration test:
   `TestIntegration_DuplicatePromptSkipsEmbeddingAPI` sends the same prompt twice through `Stack.Get`
   with a call-counting L2 fake standing in for the embedding API, and asserts the fake is called
   exactly once. A second test, `TestIntegration_AdminRulesExpandDuplicateDetection`, wires
   `pkg/admin`'s `Handler` behind an `httptest.Server`, `PUT`s `{lowercase: true,
   strip_punctuation: true}` for a tenant, and shows two prompts that differ only in case and
   punctuation — which would fingerprint differently under the Day 70 default — now collide and the
   second request resolves at L1, skipping L2 (the embedding stand-in) entirely.
7. `DESIGN.md` — new §8 documenting today's three additions and why `Rules` layers on top of
   `Normalize` rather than replacing it (preserves §1's "one function, every call path" invariant:
   the base contract still runs identically for every tenant; `Rules` only changes what bytes reach
   it, and does so identically for a given tenant's own requests).

## Out of scope

- No live Redis, Postgres, or Kafka broker exercised (no Docker daemon, the same constraint every
  prior prompt-fingerprinter day has logged) — the admin API and LensAI writer are both tested
  against `httptest.Server` fakes, the same pattern `cost-budget-enforcer/pkg/admin` and
  `pkg/lensai` already established.
- No audit trail for a fingerprint-rules change — `cost-budget-enforcer/pkg/audit`'s
  publish-or-rollback contract is specific to budget changes with real financial consequences; a
  normalization-rule change has no equivalent "roll back the money" case. If this needs an audit
  trail later, it should reuse that package rather than fork a second one.
- No gateway wiring — same "Out of scope" note DESIGN.md §3 has carried since Day 70. `pkg/admin`
  and `pkg/rules` are library-level today, the same shape every other RouteIQ module's admin API
  shipped in before its gateway integration day.

## Tests

Two new packages (`pkg/rules`, `pkg/admin`, `pkg/lensai`) each get direct unit tests mirroring
`cost-budget-enforcer`'s equivalents; `pkg/fingerprint/rules_test.go` covers `Rules.Apply` directly
(zero-value no-op, each flag independently, UTF-8-safe truncation); `pkg/stack/integration_test.go`
covers the two integration scenarios above. Target ≥90% pass rate per the build-slot threshold.
