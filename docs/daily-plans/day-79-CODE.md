# Day 79 — Code Plan

**Repo:** `infra-ai-streaming`, component `model-quality-scorer` (new packages: `pkg/normalize`,
`pkg/rollup`; extends `pkg/store`, `pkg/consumer`)
**Product:** RouteIQ
**Ticket:** Normalize judge outputs to 0–1; roll up 1h/24h aggregates per `model_id×task_type`;
Grafana panel wired to the LensAI cross-product dashboard; add a statistical noise-floor doc.
**Branch base:** stacked on `feat/model-quality-scorer-judge-pipeline` (Day 78, PR #135 — still
open). Day 79 needs the judge pipeline's `quality_scores` writer and `rubric.WeightedScore`
output, neither of which is on `main` yet.

## Goal

Day 78's own PR description and Day 78's AI Learning post both already scope this exactly:
"No 1h/24h rollup normalization, per DESIGN.md's own scope note" and "Day 79 normalizes today's
raw 0–100 scores and rolls them up on 1h/24h windows, with a documented statistical noise floor so
a thin hour of samples never reports the same confidence as a full one." Today closes that gap.

## Scope

1. `model-quality-scorer/pkg/normalize/normalize.go` (new package) — `Score(raw float64) (float64,
   error)` converts `rubric.WeightedScore`'s 0–100 output into a 0–1 unit. 0–1 is the comparable
   unit across `task_type`s whose rubrics carry different criteria counts and weight
   distributions — the same reason a z-scored metric, not a raw one, is what you compare across
   populations with different scales. Range-validates input; out-of-range is a caller bug (the
   rubric package already guarantees `WeightedScore` returns `[0,100]`), not a data problem.
2. `deploy/clickhouse/004_quality_scores_normalized_score.sql` (new migration) — `ALTER TABLE
   infra_ai.quality_scores ADD COLUMN IF NOT EXISTS normalized_score Float64`. Additive column on
   the existing per-sample table — this is *not* a rollup table. DESIGN.md §6 already committed
   model-quality-scorer to "never pre-collapsed into a running average at write time"; storing both
   `score` (raw) and `normalized_score` per row is still one fact per judged sample, not an
   aggregate, so it doesn't violate that commitment.
3. `pkg/store/store.go` — `ScoredSample` gains `NormalizedScore float64`; `Validate` checks
   `[0,1]`. `pkg/store/clickhouse.go` — `insertSQL` and `WriteBatch`'s `batch.Append` call carry the
   new column.
4. `pkg/consumer/processor.go` — after `r.WeightedScore(result.Scores)` succeeds, call
   `normalize.Score` and populate `NormalizedScore` on the row. A normalize failure here can only
   mean `WeightedScore`'s own `[0,100]` contract broke, so it dead-letters with
   `dlq.ReasonJudgeUnavailable` the same way a bad `WeightedScore` result already does — never a new
   DLQ reason for what is, structurally, the same "judge produced something we can't trust" failure.
5. `pkg/rollup/rollup.go` (new package) — query-time aggregation, honoring DESIGN.md §6's explicit
   commitment (no materialized view, no pre-collapsed rollup table). `Query(w Window) (string,
   error)` for `Window1h`/`Window24h` returns the parameterized ClickHouse SQL
   (`toStartOfHour`/`toStartOfDay(scored_at)`, grouped by `window, model_id, task_type`, emitting
   `count()`, `avg(normalized_score)`, `stddevPop(normalized_score)`). `RollupRow` models one result
   row.
6. `pkg/rollup/confidence.go` (new file, same package) — the statistical noise floor:
   `MinSamplesForConfidence = 30` (the standard CLT rule-of-thumb threshold where a sampling
   distribution of the mean is reasonably approximated as normal regardless of the underlying
   distribution's shape), `StandardError(stddev float64, sampleCount int) float64` (`stddev /
   sqrt(n)`), and `LowConfidence(sampleCount int) bool`. All pure functions, fully unit-testable
   without a live ClickHouse connection — same sandbox constraint every prior RouteIQ module's
   DESIGN.md has logged since Day 65.
7. `model-quality-scorer/NOISE-FLOOR.md` (new doc) — explains the 30-sample floor, the standard
   error formula, and how a consumer of the rollup (RouteIQ's weighted utility function, landing
   Day 80 per Day 78's AI Learning post) should treat a `low_confidence` bucket: prefer the wider
   24h window over a thin 1h one rather than trusting a mean with an unstated, possibly-large error
   bar.
8. `dashboards/traceforge-lensai-cross-product.json` and its provisioning copy
   (`deploy/grafana/provisioning/dashboards/traceforge-lensai-cross-product.json`, kept identical) —
   new panel 5, a table sourced from `pkg/rollup.Query(Window1h)`'s SQL: `window`, `model_id`,
   `task_type`, `sample_count`, `avg_normalized_score`, with a threshold style flagging
   `sample_count < 30` — the dashboard-side view of the same noise floor `pkg/rollup` enforces
   in Go.
9. `model-quality-scorer/DESIGN.md` — short §7 addendum recording today's additions and cross-
   referencing `NOISE-FLOOR.md`, matching how prior days append rather than rewrite existing
   sections.

## Out of scope

- No live ClickHouse query actually executed (no Docker daemon, same standing constraint) —
  `pkg/rollup.Query` is verified by asserting the generated SQL text and by exercising
  `StandardError`/`LowConfidence` directly against fixture stats, not by running the query.
- No RouteIQ weighted-utility integration — Day 78's AI Learning post already scopes that to Day
  80, once cost and latency signals join quality in one function.
- No Grafana alerting rule on the low-confidence panel — the panel surfaces the flag visually;
  wiring an actual alert is a later operational concern, not part of today's scope.

## Tests

`pkg/normalize/normalize_test.go` (range validation, boundary values 0 and 100).
`pkg/rollup/rollup_test.go` (SQL text for both windows, invalid `Window` value).
`pkg/rollup/confidence_test.go` (`StandardError` against hand-computed values, `LowConfidence`
boundary at exactly 30). `pkg/store/store_test.go` extended for `NormalizedScore` range validation.
`pkg/consumer/processor_test.go` extended: a scored sample's `NormalizedScore` equals `Score/100`.
Target ≥90% pass rate per the build-slot threshold.
