# Day 42 — Code Plan
## tool-call-analyzer: Dual-Write cost_usd to LensAI Ingest + Unified Tenant Grafana Board

**Calendar**: Tuesday, Day 42 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/tool-call-analyzer` (builds on Day 41 waterfall + exclusive time + CLI)
**Language**: Go 1.22+
**Builds on**: Day 41 — `pkg/waterfall` (WaterfallPayload), `cmd/traceforge/waterfall.go`, `cmd/traceforge/bottleneck.go`

### Shared Thread
> One Dashboard for Inference and Tools meets Unified Billing Events — One Envelope in today's tool-call-analyzer commit. Dual-write sends each completed tool span's cost_usd to LensAI's ingest endpoint alongside the existing ClickHouse write. The unified Grafana board joins both data sources on tenant_id + trace_id — one query face, two pipelines.

---

## Summary

Day 41 built cost waterfall visualization and exclusive time ranking. Day 42 adds two things that turn tool-call cost data into cross-system intelligence:

1. **`pkg/dualwrite/dualwrite.go`** — fire-and-forget HTTP POST client: after each span is written to ClickHouse, sends a normalized `BillingEvent` envelope to LensAI's ingest endpoint (configurable via `LENSAI_INGEST_URL` env var). Non-blocking — ClickHouse write path is not gated on LensAI availability.
2. **`pkg/dualwrite/dualwrite_test.go`** — ≥8 table-driven tests: happy path POST, LensAI 5xx (fire-and-forget does not surface error to caller), timeout (configured 2s deadline), zero-cost span (still sent, cost_usd=0), missing env var (no-op, no panic), envelope shape verification
3. **`pkg/dualwrite/envelope.go`** — `BillingEvent` struct (the unified schema): `tenant_id`, `trace_id`, `span_id`, `source` ("tool" | "inference"), `tool_name`, `vendor`, `cost_usd`, `duration_ms`, `timestamp_ns`
4. **`pkg/grafana/board.go`** — builds a Grafana dashboard JSON (v8 format) with two panel rows: Row 1 inference panels (LensAI data, read-only placeholder panels referencing LensAI datasource UID), Row 2 tool panels (Bar Gauge from tool-call-analyzer waterfall data, Time Series for exclusive time trends). Panels linked by Grafana variable `$tenant_id`.
5. **`pkg/grafana/board_test.go`** — ≥6 tests: JSON is valid, `$tenant_id` variable present, at least one LensAI panel, at least one tool panel, datasource UIDs configurable via struct fields, no panel has an empty title
6. **`cmd/traceforge/dualwrite.go`** — `traceforge dualwrite --span-id <id>` subcommand: reads one span from ClickHouse by span_id, constructs BillingEvent, sends to LensAI ingest, prints result
7. **`cmd/traceforge/board.go`** — `traceforge board --out dashboard.json` subcommand: generates the unified Grafana JSON board and writes it to `--out` path (default: stdout)

Target: `go test ./...` exits 0, `go build ./cmd/traceforge` exits 0.

---

## Data Model

### `pkg/dualwrite/envelope.go`

```go
// SPDX-License-Identifier: MIT
package dualwrite

// BillingEvent is the unified schema sent to LensAI ingest and to ClickHouse.
// source="tool" comes from tool-call-analyzer; source="inference" comes from LensAI SDK.
// Both systems emit the same envelope so one ClickHouse MV can join them.
type BillingEvent struct {
    TenantID    string  `json:"tenant_id"`
    TraceID     string  `json:"trace_id"`
    SpanID      string  `json:"span_id"`
    Source      string  `json:"source"`       // "tool" | "inference"
    ToolName    string  `json:"tool_name"`    // empty for inference events
    Vendor      string  `json:"vendor"`
    CostUSD     float64 `json:"cost_usd"`
    DurationMs  uint64  `json:"duration_ms"`
    TimestampNs int64   `json:"timestamp_ns"`
}
```

### `pkg/dualwrite/dualwrite.go`

```go
// SPDX-License-Identifier: MIT
package dualwrite

import (
    "bytes"
    "context"
    "encoding/json"
    "net/http"
    "os"
    "time"
)

const defaultTimeout = 2 * time.Second

// Send fires BillingEvent to the LensAI ingest endpoint from LENSAI_INGEST_URL.
// Returns immediately if env var is unset (no-op). Does not block the caller on error.
func Send(ev BillingEvent) {
    url := os.Getenv("LENSAI_INGEST_URL")
    if url == "" {
        return
    }
    go func() {
        body, err := json.Marshal(ev)
        if err != nil {
            return
        }
        ctx, cancel := context.WithTimeout(context.Background(), defaultTimeout)
        defer cancel()
        req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
        if err != nil {
            return
        }
        req.Header.Set("Content-Type", "application/json")
        resp, err := http.DefaultClient.Do(req)
        if err != nil {
            return
        }
        resp.Body.Close()
    }()
}
```

**Key design decisions**:
- `go func()` — fire-and-forget goroutine so the ClickHouse write path is never gated on LensAI
- 2s timeout via `context.WithTimeout` — goroutine does not leak on network partitions
- No retry — LensAI ingest is idempotent (span_id is the dedup key); retries are the ingest layer's job
- Silent error drop inside goroutine — errors are observable via LensAI ingest metrics, not via caller error propagation

---

### `pkg/grafana/board.go`

```go
// SPDX-License-Identifier: MIT
package grafana

// BoardConfig holds datasource UIDs from the environment.
type BoardConfig struct {
    LensAIDatasourceUID string // UID of the LensAI Prometheus/ClickHouse datasource in Grafana
    ToolsDatasourceUID  string // UID of the tool-call-analyzer ClickHouse datasource
    TenantID            string // Default value for $tenant_id variable (empty = no default)
}

// Board returns a Grafana dashboard JSON ([]byte) with:
// - Template variable: $tenant_id
// - Row 1: LensAI inference panels (cost_usd by model, token usage time series)
// - Row 2: Tool panels (waterfall bar gauge, exclusive time trend, N+1 alert count)
func Board(cfg BoardConfig) ([]byte, error)
```

**Panel layout**:
```
Row 1 — Inference (LensAI)
  [Stat] Total inference cost today   [Bar Gauge] Cost by model
  [Time Series] Token usage over time

Row 2 — Tools (TraceForge)
  [Bar Gauge] Cost waterfall by tool  [Time Series] Exclusive time P99 trend
  [Stat] N+1 alerts fired today
```

All panels filtered by `$tenant_id` Grafana variable (injected into each panel's SQL WHERE clause).

---

## CLI Subcommands

### `traceforge dualwrite`

```bash
# Send one span to LensAI ingest (test mode)
LENSAI_INGEST_URL=http://localhost:8080/ingest \
  traceforge dualwrite \
  --span-id a1b2c3d4-5678-90ab-cdef-1234567890ab

# Output on success:
# sent: span a1b2c3d4 → http://localhost:8080/ingest (200 OK)

# Output when LENSAI_INGEST_URL unset:
# LENSAI_INGEST_URL not set — no-op
```

### `traceforge board`

```bash
# Print unified Grafana JSON to stdout
traceforge board \
  --lensai-uid abc123 \
  --tools-uid def456

# Write to file
traceforge board \
  --lensai-uid abc123 \
  --tools-uid def456 \
  --out dashboard.json

# Output: valid Grafana v8 dashboard JSON
# Import at: Grafana → Dashboards → Import → Upload JSON
```

---

## Integration with Existing Write Path

In `pkg/clickhouse/writer.go` (added in Day 39), after the `INSERT INTO tool_calls` succeeds:

```go
// Dual-write to LensAI — fire-and-forget, does not gate the ClickHouse write
dualwrite.Send(dualwrite.BillingEvent{
    TenantID:    span.TenantID,
    TraceID:     span.TraceID,
    SpanID:      span.SpanID,
    Source:      "tool",
    ToolName:    span.ToolName,
    Vendor:      span.Vendor,
    CostUSD:     span.CostUSD,
    DurationMs:  span.DurationMs,
    TimestampNs: span.StartTimeNs,
})
```

No changes to the ClickHouse schema or existing tests. The dual-write is additive.

---

## File Layout

```
pkg/
  dualwrite/
    envelope.go           (NEW — Day 42)
    dualwrite.go          (NEW — Day 42)
    dualwrite_test.go     (NEW — Day 42)
  grafana/
    board.go              (NEW — Day 42)
    board_test.go         (NEW — Day 42)
  clickhouse/
    writer.go             (Day 39 — add dualwrite.Send call after INSERT)
cmd/
  traceforge/
    main.go               (add "dualwrite" + "board" to switch)
    dualwrite.go          (NEW — Day 42)
    board.go              (NEW — Day 42)
```

---

## Test Specification

### `dualwrite_test.go`

| Test name | Setup | Expected |
|---|---|---|
| `TestSendHappyPath` | httptest server returns 200 | goroutine completes, no panic |
| `TestSendServer5xx` | httptest server returns 500 | no error surfaced to caller, returns normally |
| `TestSendTimeout` | httptest server sleeps 5s (> 2s deadline) | goroutine times out cleanly, no goroutine leak |
| `TestSendZeroCost` | CostUSD=0 | still POSTs, server receives valid JSON |
| `TestSendNoEnvVar` | LENSAI_INGEST_URL="" | returns immediately, no HTTP call made |
| `TestEnvelopeShape` | marshal BillingEvent | all 9 fields present in JSON output |
| `TestSendMalformedURL` | LENSAI_INGEST_URL="not-a-url" | no panic, returns normally |
| `TestSendSourceField` | source="tool" | JSON body contains `"source":"tool"` |

### `board_test.go`

| Test name | Setup | Expected |
|---|---|---|
| `TestBoardValidJSON` | Board(cfg) | output is valid JSON, no error |
| `TestTenantVariable` | Board(cfg) | JSON contains `"$tenant_id"` string |
| `TestLensAIPanelPresent` | cfg.LensAIDatasourceUID = "abc" | at least one panel references "abc" |
| `TestToolsPanelPresent` | cfg.ToolsDatasourceUID = "def" | at least one panel references "def" |
| `TestNoPanelEmptyTitle` | Board(cfg) | all panels have non-empty title fields |
| `TestDatasourceUIDs` | two different UIDs | both appear in JSON output |

---

## Implementation Notes

- `pkg/grafana/board.go`: build the dashboard JSON as a Go struct with `json.Marshal` — no string templating, no raw JSON concatenation. Use `map[string]interface{}` for panels where Grafana's schema is version-specific.
- `LENSAI_INGEST_URL` env var: read inside `Send()`, not at package init — allows tests to set/unset without restart.
- `httptest.NewServer` in tests: assign to `LENSAI_INGEST_URL` within test, defer `server.Close()`.
- All source files: `// SPDX-License-Identifier: MIT` header on line 1.
- `cmd/traceforge/main.go` switch: add `"dualwrite"` and `"board"` cases.

---

## Acceptance Criteria

```bash
go test ./pkg/dualwrite/... ./pkg/grafana/...   # exits 0, ≥14 tests pass
go build ./cmd/traceforge                        # exits 0
traceforge dualwrite --help                      # prints usage, exits 0
traceforge board --help                          # prints usage, exits 0
LENSAI_INGEST_URL='' traceforge dualwrite --span-id x  # prints no-op message, exits 0
```

---

## Series Navigation

Previous: Day 41 — Bottleneck Rank by Exclusive Time + Grafana Tool Cost Waterfall
Next: Day 43 — (from plan.json)
