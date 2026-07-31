# Day 48 — Code Plan
## agent-replay-engine: Fault Injection — `traceforge replay --inject-timeout`

**Calendar**: Monday, Day 48 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` → `agent-replay-engine/`
**Language**: Go 1.25
**Builds on**: `pkg/mocker.ToolMocker.Respond` (Day 44), `pkg/replay.Run`'s existing generic
error propagation (Day 46).

### Shared Thread
> Synthetic timeout injection is supplier chaos testing — know the breaker trips before
> production does. Today's code in agent-replay-engine implements that lesson: force a chosen
> replay step to fail with a synthetic fault instead of serving its recorded response, so an
> agent's error-handling path can be verified on demand instead of waiting for the failure to
> happen live and get recorded.

---

## Summary

Day 48 adds fault injection to the mocker and a CLI flag to trigger it:

1. **`pkg/fault`** — `Kind` type with three values (`timeout`, `http_500`, `stale_cache`), each
   with a sentinel error (`ErrTimeout`, `ErrHTTP500`, `ErrStaleCache`) returned by `Kind.Err()`.
2. **`ToolMocker.Inject(atStep int, kind fault.Kind)`** — configures `Respond` to fail its
   `atStep`'th call (1-based, across all tool names) with `kind`'s error instead of the normal
   frozen-response lookup. `atStep <= 0` clears any configured injection.
3. **`cmd/traceforge` `replay --inject-timeout <step>`** — forces that step to fail with a
   synthetic timeout. No change needed to `pkg/replay.Run` — it already wraps any error
   `Respond` returns with the step number, so an injected fault surfaces identically to the
   existing `ErrUnknownCall` path.
4. Tests: fault kind validity + sentinel mapping, mocker injection at/before/after the
   configured step, injected calls excluded from `CallHistory`, injection cleared by
   `atStep <= 0`, injection beyond the trace length never firing, replay surfacing the wrapped
   fault with the correct `StepsRun`, and `--stop-at-step` composing correctly with an injected
   fault that never gets reached.

**Deliberate scope cut**: only `--inject-timeout` is wired up as a CLI flag this round.
`http_500` and `stale_cache` are implemented in `pkg/fault` and usable via `ToolMocker.Inject`
as a library, but `--inject-http-500` / `--inject-stale-cache` CLI flags are future scope.

Target: `go build ./...`, `go vet ./...`, `gofmt -l .` empty, `go test -race ./...` exits 0.

---

## `pkg/fault` — Public API

```go
// SPDX-License-Identifier: MIT
package fault

type Kind string

const (
	KindTimeout    Kind = "timeout"
	KindHTTP500    Kind = "http_500"
	KindStaleCache Kind = "stale_cache"
)

var (
	ErrTimeout    = errors.New("fault: injected timeout")
	ErrHTTP500    = errors.New("fault: injected http 500")
	ErrStaleCache = errors.New("fault: injected stale cache response")
)

func (k Kind) Valid() bool
func (k Kind) Err() error
```

## `pkg/mocker` addition

```go
func (m *ToolMocker) Inject(atStep int, kind fault.Kind)
```

## CLI

```
traceforge replay --log <path> --trace-id <id> [--stop-at-step N] [--inject-timeout N]
```

## Acceptance Criteria

```bash
go build ./...     # exits 0
go vet ./...        # exits 0
gofmt -l .           # empty
go test -race ./...  # exits 0, all packages pass
```

## Series Navigation

Previous: Day 47 — agent-replay-engine: Diff Engine — `traceforge diff --trace-a --trace-b`
Next: Day 49 — TBD
