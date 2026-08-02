# Day 55 — Code Plan
## agent-benchmark-runner: LensAI Integration — Benchmark Completion Emits Ingest Events

**Calendar**: Monday, Day 55 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` → `agent-benchmark-runner/` (builds on Day 50-54's
`pkg/orchestrator`, `pkg/criteria`, `pkg/task`, `pkg/store`, `pkg/report` — the full
run/grade/summarize/persist/render path)
**Language**: Go 1.25
**Precedent**: Day 42 (`tool-call-analyzer/pkg/lensai`) already dual-writes tool-call cost
onto LensAI's `/ingest` pipeline using LensAI's own `InferenceEvent`-shaped envelope, with
a `source: "tool_call"` discriminator field layered on top (silently ignored by LensAI's
Rust struct today, since `InferenceEvent` doesn't use `#[serde(deny_unknown_fields)]`,
per `ingestion/src/handlers/event.rs`). Day 55 repeats that exact pattern for
`agent-benchmark-runner`, one module over, with `source: "benchmark_run"`.

### Shared Thread
> Two Products, One Tenant Bill meets Cross-Product Metrics — LensAI × TraceForge in
> today's `agent-benchmark-runner` commit.
> One `tenant_id` to rule cost — design the join on Day 1.

---

## Summary

1. **`pkg/lensai/writer.go`** — new package. `Event` (LensAI ingest wire envelope, field
   names/JSON tags mirroring `ingestion/src/handlers/event.rs::InferenceEvent`, plus the
   same additive `TraceID`/`Source` fields Day 42 introduced). `SourceBenchmarkRun =
   "benchmark_run"` discriminator. `Writer` (HTTP POST to `/ingest`, `New`/`NewWithClient`
   constructors matching `tool-call-analyzer/pkg/lensai`'s injection pattern). `Insert`
   dual-writes one event per **batch**, not per repetition. `ToEvent(summary
   orchestrator.Summary, taskID, agentName, tenantID, batchID string, duration
   time.Duration, completedAt time.Time) Event` builds the envelope from an
   `orchestrator.Summary` — no HTTP round trip required, so callers can build the event for
   dry-run output the same way `tool-call-analyzer/pkg/lensai.ToEvent` does.
2. **`pkg/lensai/writer_test.go`** — httptest server asserting: `X-Tenant-ID` header set,
   correct `source`/`trace_id`/`model_id` mapping, `status` derives to `pass`/`fail`/`error`
   from `Summary.PassRate`/`Completed`, `cost_usd` stays `0.0` (see design decision below),
   missing tenant ID rejected before any HTTP call, HTTP 202 accepted, HTTP 500 surfaced as
   an error, `ToEvent` alone (no server) produces the expected envelope for a batch with
   zero completed repetitions (all `Err` set) without panicking or dividing by zero.
3. **`DESIGN.md`** — Day 55 addendum: why one event per batch and not per repetition; why
   `cost_usd` stays zero instead of estimating a dollar figure; why `ModelID` carries
   `AgentName` and `TraceID` carries `TaskID` rather than the reverse.
4. **`README.md`** — `pkg/lensai` row in the package table + a short "LensAI Ingest" usage
   section, mirroring `tool-call-analyzer/README.md`'s existing section for the same
   package.

Target: `go test -race ./...` exits 0 (module-wide, previous day counts plus new lensai
tests), `go vet ./...` exits 0, `gofmt -l .` empty. CI already runs these three steps for
`agent-benchmark-runner` — no workflow changes needed.

---

## Key Design Decisions

- **One event per completed batch, not one per repetition.** `pkg/store`'s
  `benchmark_runs` table already stores one row per `orchestrator.RunResult` for full
  statistical fidelity (Day 50's rationale: a pre-aggregated row can't be recomputed
  without re-running the batch). The LensAI-facing question is coarser — "how is this
  agent doing, next to its inference spend, on one shared dashboard" — so ingest volume
  should scale with "how many benchmark batches ran," not "how many repetitions each batch
  had." A per-repetition event would also make `PassRate`'s confidence interval invisible
  to LensAI entirely, since no single repetition carries a Wilson interval — only the
  `Summary` does.
- **`CostUSD` stays `0.0` — Day 55 does not estimate a dollar figure for a benchmark
  batch.** `orchestrator.RunResult` and `criteria.RunOutcome` carry no cost data; the only
  cost data in this module lives in `pkg/report.CostReport` (Day 54), which is scoped to
  two-agent `pkg/compare` output, not the single-agent `orchestrator.Run` path this event
  is emitted from. Inventing a cost estimate here would double-count: if the agent under
  test makes tool calls, those calls' actual dollar cost is *already* dual-written by
  `tool-call-analyzer/pkg/lensai` at the point the calls happen. A benchmark-run event
  claiming its own nonzero cost would sit on the same tenant's bill as a second, unrelated
  number for work already billed elsewhere.
- **`ModelID` carries `AgentName`, `TraceID` carries `TaskID`.** LensAI's dashboards join
  and group primarily on `model_id`; on the shared ingest face, "which agent configuration
  was under test" is the dimension a viewer actually wants to slice by (same reasoning Day
  42 used to fall back `ModelID` to the tool's name when no model name was available).
  `TraceID` correlates every batch run against the same `Task` — including, later, both
  sides of an A/B `pkg/compare` run if a future day chooses to emit one event per agent
  side instead of a single combined one.
- **`Status` derives from `Summary`, not from any single repetition's `Err`.**
  `Completed == 0` (every repetition errored) maps to `"error"`; `PassRate == 1.0` maps to
  `"pass"`; anything else maps to `"fail"`. This mirrors the existing `hasError`/`status`
  derivation in `tool-call-analyzer/pkg/lensai.ToEvent`, generalized from a single call's
  boolean outcome to a batch's completion state.
