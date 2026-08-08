# Day 80 — Code Plan

**Repo:** `infra-ai-streaming`, component `model-quality-scorer` (new package `pkg/decision`)
**Product:** RouteIQ
**Ticket:** RouteIQ decision engine v1 — weighted utility `U = w_q·quality − w_c·cost − w_l·latency`
with tenant-overridable weights; unit tests for tie-break toward cheaper model when U within ε.
**Branch base:** stacked on `feat/model-quality-scorer-rollup-normalization` (Day 79, PR #136 —
still open). Day 80 needs `pkg/rollup.Row` (and its `LowConfidence`/`StandardError` methods),
neither of which is on `main` yet.

## Goal

DESIGN.md's own "Out of scope (Day 79)" line already scopes this exactly: "No RouteIQ
weighted-utility integration — deferred to Day 80, once cost and latency signals join quality in
one function." Today writes that function: the first day any RouteIQ module actually makes a
routing *decision* rather than only measuring one input to it.

## Scope

1. `model-quality-scorer/pkg/decision/decision.go` (new package) — `RoutingWeights{WQuality,
   WCost, WLatency float64}`, `Candidate{ModelID string, Quality float64 (0-1, a rollup.Row's
   AvgNormalizedScore), CostPerCall float64, LatencyP99Ms float64, LowConfidence bool (from
   rollup.Row.LowConfidence())}`. `Utility(c Candidate, w RoutingWeights) float64` computes
   `w.WQuality*c.Quality - w.WCost*c.CostPerCall - w.WLatency*c.LatencyP99Ms`. Same additive,
   subtractive-penalty shape as a cost-aware load balancer scoring backends by (capacity − load) —
   quality is the only term that helps the score, cost and latency are both penalties.
2. `Decide(candidates []Candidate, w RoutingWeights) (Decision, error)` — picks the candidate with
   the highest utility. **Tie-break:** when two or more candidates land within a small epsilon
   (`tieEpsilon = 1e-6`) of the max utility, prefer the one with the lower `CostPerCall` — two
   models that are, for practical purposes, equally good for this tenant right now should not be
   distinguished by a rounding artifact in the utility function; cost is the deterministic,
   externally meaningful tiebreaker. If `CostPerCall` also ties exactly, break by `ModelID`
   lexicographic order so `Decide` is fully deterministic for the same input, which the tie-break
   unit tests depend on. `Decision{Winner Candidate, LowConfidence bool}` surfaces whether the
   winning candidate's own quality signal sat below NOISE-FLOOR.md's 30-sample floor — a decision
   made on a thin bucket is still a decision, but a caller (e.g. today's Grafana panel, or a later
   alerting day) needs to know its confidence wasn't fully earned yet.
3. `RoutingWeights.Validate() error` — no negative weight; not all three weights zero (a
   zero-everywhere weight set can never distinguish any two candidates, which is a config bug, not
   a valid "no preference" state — `Decide` would otherwise tie every candidate against every
   other one and silently fall through to the `ModelID` tiebreak for every decision).
4. `Candidate.Validate() error` — `ModelID` non-empty, `Quality` in `[0,1]` (the same range
   `store.ScoredSample.NormalizedScore` and `normalize.Score` already enforce — a `Candidate`'s
   quality is meant to be exactly a rollup row's `AvgNormalizedScore`, so it inherits that
   package's range contract rather than defining a second one), `CostPerCall` and `LatencyP99Ms`
   non-negative.
5. `WeightsForTenant(tenant string, overrides map[string]RoutingWeights) RoutingWeights` — looks
   up a tenant override, falls back to `DefaultWeights` (`WQuality: 1.0, WCost: 1.0, WLatency:
   1.0`) when absent. Same "override map keyed by tenant_id, default when absent" shape
   `cost-budget-enforcer`'s per-tenant budget config and `prompt-fingerprinter`'s per-tenant cache
   config both already use — RouteIQ's fourth module reuses the arc's established config pattern
   rather than inventing a fifth one.
6. `FromRollupRow(r rollup.Row, costPerCall, latencyP99Ms float64) Candidate` — the literal "cost
   and latency signals join quality in one function" DESIGN.md commits Day 80 to: takes a Day 79
   `rollup.Row` (quality) plus two externally-supplied signals (cost and latency are not
   `model-quality-scorer`'s own data — they come from wherever a future day wires in per-model
   pricing and `cost-budget-enforcer`'s existing latency observability) and produces one
   `Candidate` a `Decide` call can rank.
7. `model-quality-scorer/DESIGN.md` — short §8 addendum recording today's decision engine and
   cross-referencing this as the arc's first module that actually picks a winner, not just
   measures or gates one input.

## Out of scope

- No live cost or latency data source wired in — `FromRollupRow` takes both as caller-supplied
  arguments; a future day sources real per-model cost and `cost-budget-enforcer`/OTel latency
  numbers instead of test fixtures.
- No gateway integration — `Decide` is a pure function callable from a CLI or a future HTTP
  handler; wiring it into the live request path (which model actually gets picked for a request)
  is deferred, the same way every other RouteIQ module's core logic landed before its gateway
  wiring.
- No live ClickHouse query executed to produce real `rollup.Row` values feeding `FromRollupRow` —
  same standing sandbox constraint (no Docker daemon) every prior RouteIQ day has logged; verified
  against fixture `rollup.Row` values instead.

## Tests

`pkg/decision/decision_test.go` — `Utility` against hand-computed values; `Decide` picks the
strictly-higher-utility candidate when no tie; **tie-break toward the cheaper model when two
candidates' utilities are within `tieEpsilon`**; deterministic `ModelID` tiebreak when cost also
ties; `RoutingWeights.Validate` rejects negative and all-zero weights; `Candidate.Validate` rejects
out-of-range quality and negative cost/latency; `Decide` returns an error on an empty candidate
list; `WeightsForTenant` returns the override when present and `DefaultWeights` when absent;
`Decision.LowConfidence` is set when the winning candidate's `LowConfidence` is true.
`FromRollupRow` copies `AvgNormalizedScore` into `Quality` and `Row.LowConfidence()` into
`Candidate.LowConfidence` correctly. Target ≥90% pass rate per the build-slot threshold.
