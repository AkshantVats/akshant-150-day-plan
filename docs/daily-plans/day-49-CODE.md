# Day 49 — Code Plan
## agent-replay-engine: Streaming Replay — `eventlog.Scanner` + `RunFromReader`

**Calendar**: Tuesday, Day 49 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` → `agent-replay-engine/`
**Language**: Go 1.25
**Builds on**: `pkg/eventlog.ReadJSONL` (Day 44), `pkg/mocker.LoadFromLog` (Day 44),
`pkg/replay.Run` (Day 46) — this day adds streaming twins of all three rather than replacing
them.

### Shared Thread
> Streaming JSONL is paginated TSDB queries — never load the whole day into RAM. Today's code in
> agent-replay-engine implements that lesson: replay a trace out of a shared log file without
> ever buffering the whole file, the same way a bounded query never materializes a full day's
> rows before filtering.

---

## Summary

Day 49 targets "Replay perf: 100-step trace <3s; streaming parser memory profile" — in practice
a memory-bound problem, not a throughput one (in-process replay of 100 steps is µs-scale
regardless of how the log is read). The real risk is `traceforge replay` OOMing on a laptop
against a multi-GB shared log file that happens to contain the one trace someone needs to debug.

1. **`pkg/eventlog.Scanner`** — `bufio.Scanner`-style line-at-a-time JSON Lines reader. Never
   buffers the file or re-sorts; trusts the recorder's append-only ordering guarantee.
2. **`pkg/mocker.LoadFromReader(r, traceID)`** — streams a log through a `Scanner` and builds a
   `ToolMocker` scoped to one trace in a single pass (a `pending` map resolves a
   `tool_call`/`tool_response` pair regardless of which arrives first). Returns `sawAny` so a
   caller can distinguish "unknown trace_id" from "trace has events but no completed calls."
3. **`pkg/replay.RunFromReader(r, traceID, mocker, stopAtStep)`** — streams the tool-call
   sequence directly, the streaming twin of `Run`. An early `--stop-at-step` returns without
   reading the rest of `r`.
4. **`cmd/traceforge replay` now streams by default** — two sequential passes over `--log`
   (mocker build, then replay) instead of one `ReadJSONL` pass, trading a second read for never
   holding the whole file at once. `--stop-at-step`'s CLI message drops the "N steps remain"
   count it can no longer compute without reading to EOF.
5. **`BenchmarkRunBatchVsStream`** — `Run`+`ReadJSONL` vs `RunFromReader` on a 51-trace shared
   log; real numbers land in DESIGN.md § Streaming Replay, not fabricated ones.
6. Tests: `Scanner` (order preservation, blank lines, malformed line, large payload),
   `LoadFromReader` (matches `LoadFromLog`, unknown trace, response-before-call ordering),
   `RunFromReader` (matches `Run` to completion and stopped-early, empty trace, a
   `trackingReader`-based proof that an early stop doesn't read the rest of the stream, a
   100-step perf regression guard).

**Deliberate scope cut**: streaming assumes the input is already `seq_num`-ordered (an
append-only recorder's guarantee) — `RunFromReader` does not re-sort, because buffering enough
of the log to sort it would defeat the point of streaming. `Run`/`ReadJSONL` remain the batch
path for callers that need sorted random access to a whole log.

Target: `go build ./...`, `go vet ./...`, `gofmt -l .` empty, `go test -race ./...` exits 0.

---

## `pkg/eventlog` — New Public API

```go
// SPDX-License-Identifier: MIT
package eventlog

type Scanner struct { /* unexported */ }

func NewScanner(r io.Reader) *Scanner
func (s *Scanner) Scan() bool
func (s *Scanner) Event() AgentEvent
func (s *Scanner) Err() error
```

## `pkg/mocker` — New Public API

```go
func LoadFromReader(r io.Reader, traceID string) (m *ToolMocker, sawAny bool, err error)
```

## `pkg/replay` — New Public API

```go
func RunFromReader(r io.Reader, traceID string, m *mocker.ToolMocker, stopAtStep int) (Result, error)
```

## Acceptance Criteria

```bash
go build ./...       # exits 0
go vet ./...          # exits 0
gofmt -l .             # empty
go test -race ./...    # exits 0, all packages pass
go test ./pkg/replay/ -bench BenchmarkRunBatchVsStream -benchmem -run '^$'   # reports real numbers
```

## Series Navigation

Previous: Day 47 — agent-replay-engine: `traceforge diff`, first diverging span
Next: Day 50 — TBD
