# Day 47 — Code Plan
## agent-replay-engine: Diff Engine — `traceforge diff --trace-a --trace-b`

**Calendar**: Monday, Day 47 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` → `agent-replay-engine/`
**Language**: Go 1.25
**Builds on**: `pkg/eventlog` (Day 44), the `ToolName` + `InputHash` composite key `pkg/mocker`
(Day 44) uses to serve frozen responses.

### Shared Thread
> First diverging span is where two drivers got different ETAs — same debugging muscle. Today's
> code in agent-replay-engine implements that lesson: compare two traces' tool_call sequences on
> the same composite key `pkg/mocker` already used, and report the first step where they
> disagree, instead of diffing the full raw payload.

---

## Summary

Day 47 adds a structural diff engine and CLI subcommand:

1. **`pkg/diff.Compare(a, b eventlog.EventLog) Result`** — walks both traces' `tool_call` events
   in `seq_num` order, comparing `ToolName` then `InputHash` per step. Returns the first step
   where either field disagrees, or — if every shared step matches but the traces have different
   lengths — the point where the shorter trace ends (`missing_in_a` / `missing_in_b`).
2. **`cmd/traceforge` `diff` subcommand** — `traceforge diff --log <path> --trace-a <id>
   --trace-b <id>`: filters both trace IDs out of one log file, compares, and prints the step
   index, reason, and both traces' span IDs at the divergence (or "no divergence").
3. Tests: identical traces, tool-name divergence, input-hash divergence, tie-break precedence
   (tool-name wins when both differ), length-mismatch in either direction, both traces empty,
   one trace empty, non-`tool_call` events ignored. Plus CLI-level tests via the injectable
   `run()` function.

**Deliberate scope cut**: no diff of `tool_response` payloads or `final_output` text — the
question this answers is "which *decision* diverged first," not "how do the full outputs
differ." A payload-level diff on top of a located divergence is future scope.

Target: `go build ./...`, `go vet ./...`, `gofmt -l .` empty, `go test -race ./...` exits 0.

---

## `pkg/diff` — Public API

```go
// SPDX-License-Identifier: MIT
package diff

type Reason string

const (
	ReasonToolName   Reason = "tool_name"
	ReasonInputHash  Reason = "input_hash"
	ReasonMissingInA Reason = "missing_in_a"
	ReasonMissingInB Reason = "missing_in_b"
)

type Divergence struct {
	StepIndex int
	Reason    Reason
	SpanIDA, SpanIDB     string
	ToolNameA, ToolNameB string
}

type Result struct {
	Divergence               Divergence
	StepsCompared            int
	StepsTotalA, StepsTotalB int
}

func (r Result) Found() bool
func Compare(a, b eventlog.EventLog) Result
```

## CLI

```
traceforge diff --log <path> --trace-a <id> --trace-b <id>
```

## Acceptance Criteria

```bash
go build ./...     # exits 0
go vet ./...        # exits 0
gofmt -l .           # empty
go test -race ./...  # exits 0, all packages pass
```

## Series Navigation

Previous: Day 46 — agent-replay-engine: Replay Core + `traceforge replay --stop-at-step`
Next: Day 48 — agent-replay-engine: Fault Injection — `traceforge replay --inject-timeout`
