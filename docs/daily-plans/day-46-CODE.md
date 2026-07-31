# Day 46 — Code Plan
## agent-replay-engine: Replay Core + `traceforge replay --stop-at-step`

**Calendar**: Sunday, Day 46 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` → `agent-replay-engine/`
**Language**: Go 1.25
**Builds on**: `pkg/eventlog` (Day 44), `pkg/mocker` (Day 44). Day 45 diverged into trace export
(`pkg/export`, `pkg/objectstore`) instead of the replay runner originally slotted for Day 45 —
Day 46 picks up the deferred deliverable.

### Shared Thread
> `--stop-at-step` is OTA rollback for agents — fix before step 7 ships. Today's code in
> agent-replay-engine implements that lesson: replay a recorded run through a caller-chosen
> number of steps, inspect state, and stop before re-triggering a step you already know is
> broken — the same discipline as a partial OTA rollout that halts before the blast-radius
> device population.

---

## Summary

Day 46 adds the replay runner deferred from Day 44's scope note (DESIGN.md's Replay Algorithm
section) and a CLI to drive it:

1. **`pkg/eventlog.FilterByTraceID`** — isolates one trace's events out of a log file that may
   hold multiple recorded runs, so the CLI's `--trace-id` flag has something to filter against.
2. **`pkg/replay/replay.go`** — `Run(log, mocker, stopAtStep)`: walks the recorded `tool_call`
   sequence in `seq_num` order, serving each frozen response via `mocker.ToolMocker.Respond`.
   Halts after `stopAtStep` steps instead of always running to the recorded `final_output`.
3. **`cmd/traceforge/main.go`** — CLI entry point. `replay` subcommand: `--log`, `--trace-id`,
   `--stop-at-step`. Stdlib `flag` only, no new dependency.
4. Tests across all three: replay to completion, stop at step 6 of 7 (the blog's exact
   scenario), stop-at-step beyond log length, unknown tool call, missing `final_output`, empty
   trace, plus CLI-level tests via an injectable `run(args, stdout, stderr) int`.

**Deliberate scope cut**: a live `ModelClient` — one that decides which tool call to issue next
and can diverge from the recorded sequence — is out of scope. `Run` replays the recorded
`tool_call` list directly against the mocker. That's enough for the Day 46 use case (partial
replay, halt before a known-bad step); model-driven divergence detection is future scope, noted
in `pkg/replay`'s package doc rather than left silent.

Target: `go test ./...` exits 0, `go vet ./...` exits 0, `gofmt -l .` empty.

---

## `pkg/replay` — Public API

```go
// SPDX-License-Identifier: MIT
package replay

type Result struct {
	Output       string   // recorded final_output text; empty if stopped early
	CallHistory  []string // mocker.CallHistory() at the point replay stopped
	StepsRun     int
	StoppedEarly bool // true when stopAtStep halted replay before the end
	Err          error
}

// Run replays log against m, serving at most stopAtStep recorded tool calls.
// stopAtStep <= 0 means no limit — replay every recorded call and report
// the recorded final_output.
func Run(log eventlog.EventLog, m *mocker.ToolMocker, stopAtStep int) Result
```

## CLI

```
traceforge replay --log <path> --trace-id <id> [--stop-at-step N]
```

- `--log` — path to a recorded event log (JSON Lines)
- `--trace-id` — which recorded run to replay, out of possibly several in the same log file
- `--stop-at-step` — halt after this many tool-call steps; omit to run to completion

---

## Test Specification Summary

| File | Scenarios | Type |
|---|---|---|
| `pkg/eventlog/event_test.go` (addition) | `FilterByTraceID` ordering + isolation | unit |
| `pkg/replay/replay_test.go` | run to completion, stop at step 6/7, stop-at-step beyond length, unknown tool call, missing final_output, empty trace | unit |
| `cmd/traceforge/main_test.go` | replay to completion, stop at step 6, unknown trace_id, missing required flags, trace_id filtering doesn't leak another trace's calls, unknown subcommand | unit (via injectable `run()`) |

## Acceptance Criteria

```bash
go build ./...     # exits 0
go vet ./...        # exits 0
gofmt -l .           # empty
go test -race ./...  # exits 0, all packages pass
```

---

## Series Navigation

Previous: Day 45 — agent-replay-engine: Trace Export to Object Storage — zstd, Checksums, Retention
Next: Day 47 — TBD
