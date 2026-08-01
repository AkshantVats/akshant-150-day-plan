# Day 52 — Code Plan
## agent-benchmark-runner: Orchestrator — Parallel Runs, ClickHouse `benchmark_runs`, Seed Control

**Calendar**: Friday, Day 52 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` → `agent-benchmark-runner/` (builds on Day 51's
`pkg/task`, `pkg/criteria`, `pkg/compare`)
**Language**: Go 1.25
**Builds on**: Day 51 fixed the *scenario* (Task YAML) and the *bar* (typed criteria) as
data. Day 52 answers "how many times do you actually have to run it" and "where do the
results go so a benchmark result outlives the terminal it printed to."

### Shared Thread
> `agent-benchmark-runner orchestrator — parallel runs, ClickHouse benchmark_runs, seed control.`
> A single run against a Task is an anecdote, not a benchmark — LLM agents are
> non-deterministic even at temperature 0 in practice (tool latency jitter, retries,
> provider-side sampling). Day 52 runs a Task N times per agent under bounded
> concurrency, derives a distinct reproducible seed per repetition from one base seed, and
> persists every repetition to ClickHouse so a benchmark result is a queryable table, not
> a scrollback buffer.

---

## Summary

1. **`pkg/orchestrator/orchestrator.go`** — `Run(ctx, cfg, agentFn)`: executes `cfg.Repetitions`
   runs of `cfg.Task` against `agentFn`, bounded by `cfg.MaxParallel` concurrent workers
   (a semaphore, not an unbounded goroutine-per-repetition fan-out — see "Why Bounded
   Parallelism" below). Each repetition gets a deterministic derived seed
   (`deriveSeed(baseSeed, repetitionIndex)`) so a full N-run batch reproduces byte-for-byte
   from one base seed.
2. **`pkg/orchestrator/summary.go`** — `Summarize(results []RunResult) Summary`: pass rate
   with a 95% Wilson confidence interval, plus median and P95 of tool-call step count
   across repetitions. Ties directly into today's AI Learning post (N runs, confidence
   over a single anecdote).
3. **`pkg/orchestrator/orchestrator_test.go`** — concurrency bound is actually respected
   (tracked via an atomic high-water-mark counter), seed derivation is deterministic and
   distinct per repetition, partial-failure handling (agentFn returns an error for one
   repetition — the rest still complete), summary math against known fixtures.
4. **`pkg/orchestrator/summary_test.go`** — Wilson interval against reference values,
   median/P95 against hand-computed fixtures (even and odd N).
5. **`pkg/store/schema/001_benchmark_runs.sql`** — ClickHouse DDL for `benchmark_runs`:
   one row per repetition (task_id, agent_name, repetition_index, seed, passed, step_count,
   duration_ms, divergence_step, timestamp).
6. **`pkg/store/writer.go`** — `Writer` interface (`WriteRuns(ctx, []RunRecord) error`) plus
   `RunRecord` (the flat row shape) and a mapping helper from `orchestrator.RunResult`.
   `ClickHouseWriter` implements `Writer` over `github.com/ClickHouse/clickhouse-go/v2` —
   new module dependency, added via `go get`.
7. **`pkg/store/writer_test.go`** — `RunResult` → `RunRecord` mapping, no ClickHouse
   dependency.
8. **`pkg/store/integration_test.go`** — `//go:build integration`, skips without
   `CLICKHOUSE_DSN` set (same pattern as `consumer/internal/clickhouse/integration_test.go`),
   so the default `go test -race ./...` run stays hermetic.
9. **`DESIGN.md`** — Day 52 addendum: why bounded parallelism, why the seed is *derived*
   per repetition instead of reused, why persistence is a separate `Writer` interface
   instead of baked into `orchestrator.Run`.
10. **`README.md`** — orchestrator usage + `benchmark_runs` schema note.

Target: `go test -race ./...` exits 0 (module total, including new orchestrator/store
tests), `go vet ./...` exits 0, `gofmt -l .` empty. CI already runs these three steps for
`agent-benchmark-runner` (wired Day 51) — no workflow changes needed.

---

## Key Design Decisions

- **Bounded parallelism, not one goroutine per repetition.** An agent run makes real
  outbound calls (to a model provider, to tools). Firing all N repetitions at once turns a
  benchmark into a self-inflicted burst that can trip the very rate limits the agent under
  test would hit in production — an unrepresentative failure mode, not a signal about the
  agent. `cfg.MaxParallel` bounds concurrency the same way a k6 scenario bounds virtual
  users: it names its own concurrency instead of borrowing it as a side effect of a loop.
- **Seed is derived, not shared, per repetition.** Day 51 pinned the seed to the *task* so
  two agents being compared see the same randomness. Day 52 runs N repetitions of *one*
  task; reusing the same seed N times would make every repetition identical (and the
  N-run statistic meaningless — median-of-N-identical-numbers is not evidence of
  anything). `deriveSeed(base, i)` gives each repetition its own reproducible draw while
  the whole batch still reproduces deterministically from one recorded base seed.
- **Persistence is an injected `Writer`, not inlined in `Run`.** `pkg/orchestrator` stays
  free of any ClickHouse dependency, matching the Day 51 packages' no-I/O discipline —
  `Run` returns `[]RunResult` and a caller (a future CLI) decides whether/where to persist.
  This is also why `orchestrator_test.go` needs no database.
- **`benchmark_runs` is one row per repetition, not one row per batch.** A per-batch
  summary row would need to be recomputed (median/P95 change composition) every time a
  later repetition's data corrects it; a per-repetition row lets any consumer — this
  package's `Summarize`, a Grafana panel, an ad-hoc `SELECT quantile(0.95)(step_count)` —
  compute its own statistic from raw rows instead of trusting a pre-aggregated one.

---

## Acceptance Criteria

```bash
gofmt -l .           # empty
go vet ./...         # exits 0
go test -race ./...  # exits 0
```

## Series Navigation

Previous: Day 51 — agent-benchmark-runner: DESIGN.md — Task YAML, Compare Two Agents, Success Criteria
Next: Day 53 — TBD
