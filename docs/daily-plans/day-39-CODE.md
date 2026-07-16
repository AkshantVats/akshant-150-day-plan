# Day 39 — Code Plan
## tool-call-analyzer: Per-Tool Stats Materialized Views + Duration Alert

**Calendar**: Saturday, 18 July 2026 · Day 39 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/tool-call-analyzer` (builds on Day 38 adapters + Kafka producer)
**Language**: Go 1.22+ · ClickHouse SQL
**Builds on**: Day 38 — OpenAI/Anthropic/LangChain adapters, golden fixtures, Kafka producer → `tools.normalized.v1`

### Shared Thread
> The Tool That Ate Your Margin meets Exclusive Time vs Wall Time — today's tool-call-analyzer commit ships ClickHouse MVs that expose which tool is burning the trace duration budget.

---

## Summary

Day 38 normalized tool call payloads and emitted them to Kafka (`tools.normalized.v1`). Day 39 adds the analytics layer:

1. ClickHouse `tool_calls` source table (receives from Kafka consumer or HTTP insert)
2. Three Materialized Views:
   - `tool_stats_1m_mv` — P99 latency, error rate, sum cost_usd per tool per 1-minute window
   - `tool_cost_rollup_mv` — cost by vendor + model per minute (for cost attribution dashboards)
   - `tool_duration_alert_mv` — fires when a tool's duration_ms > 40% of trace_duration_ms
3. Go `pkg/clickhouse/writer.go` — inserts ToolCall structs via ClickHouse HTTP API
4. Go `pkg/stats/aggregator.go` — pure-Go per-tool stats computation for unit testing
5. All tests passing: `go test ./...`

The ClickHouse MVs are the durable layer — Grafana can query them directly. The Go aggregator tests verify the stats logic without a running ClickHouse instance.

---

## Deliverables

| File | Purpose |
|---|---|
| `schema/001_tool_calls.sql` | Source table DDL: MergeTree, all ToolCall fields |
| `schema/002_tool_stats_1m_mv.sql` | MV: P99 latency + error rate + sum cost_usd per tool per minute |
| `schema/003_tool_cost_rollup_mv.sql` | MV: cost sum by vendor + model_name per minute |
| `schema/004_tool_duration_alert_mv.sql` | MV: rows where duration_ms > 40% of trace_duration_ms |
| `schema/005_apply.sh` | Shell script: applies all DDL files in order to a running ClickHouse |
| `pkg/clickhouse/writer.go` | HTTP API writer: inserts ToolCall structs as JSONEachRow |
| `pkg/clickhouse/writer_test.go` | Unit tests with `httptest.Server` mock (no real ClickHouse needed) |
| `pkg/stats/aggregator.go` | Pure-Go P99 + alert threshold + grouping aggregator |
| `pkg/stats/aggregator_test.go` | Table-driven tests for P99, error rate, duration alert logic |

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|-------------|
| AC-1 | `schema/001_tool_calls.sql` creates table with all 14 required columns | SQL reviewed in PR |
| AC-2 | `002_tool_stats_1m_mv.sql` groups by tool_name + toStartOfMinute(timestamp) | SQL reviewed in PR |
| AC-3 | Alert MV selects only rows where `(toFloat64(duration_ms)/toFloat64(trace_duration_ms))*100 > 40` | SQL reviewed in PR |
| AC-4 | `Writer.Insert` sends correct JSONEachRow to ClickHouse HTTP endpoint | `go test ./pkg/clickhouse/ -v` exits 0 |
| AC-5 | `Writer.Insert` returns error on non-200 from ClickHouse | `-run TestWriterHTTPError` exits 0 |
| AC-6 | `Aggregator.P99` returns correct value for 100-element slice | `-run TestP99Hundred` exits 0 |
| AC-7 | `Aggregator.IsAlertThreshold` returns true when tool > 40% trace duration | `-run TestAlertThreshold` exits 0 |
| AC-8 | Zero trace_duration_ms never causes division by zero | `-run TestAlertThreshold/zero_trace_duration` exits 0 |
| AC-9 | `go test ./...` exits 0 | Command output in PR description |
| AC-10 | `go build ./...` exits 0 | Command output in PR description |

---

## Part 1 — ClickHouse Schema

### `schema/001_tool_calls.sql`

```sql
-- SPDX-License-Identifier: MIT
-- tool_calls source table: receives normalized ToolCall records from Kafka consumer or HTTP insert.
-- ENGINE: MergeTree for single-node OSS. Replace with ReplicatedMergeTree in production clusters.
CREATE TABLE IF NOT EXISTS tool_calls (
    trace_id          String,
    tool_id           String,
    tool_name         LowCardinality(String),
    vendor            LowCardinality(String),
    category          LowCardinality(String),
    model_name        LowCardinality(String),
    input_tokens      UInt32,
    output_tokens     UInt32,
    cost_usd          Float64,
    duration_ms       UInt64,
    trace_duration_ms UInt64,
    has_error         UInt8,
    status            LowCardinality(String),
    timestamp         DateTime64(3, 'UTC')
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (tool_name, vendor, timestamp)
TTL timestamp + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;
```

### `schema/002_tool_stats_1m_mv.sql`

```sql
-- SPDX-License-Identifier: MIT
-- tool_stats_1m: per-tool P99 latency, error rate, cost rollup — 1-minute windows.
-- AggregatingMergeTree + quantileState gives correct P99 merge across multiple inserts.
CREATE TABLE IF NOT EXISTS tool_stats_1m (
    window              DateTime,
    tool_name           LowCardinality(String),
    vendor              LowCardinality(String),
    model_name          LowCardinality(String),
    call_count          UInt64,
    error_count         UInt64,
    cost_usd_sum        Float64,
    latency_p99_state   AggregateFunction(quantile(0.99), UInt64)
) ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMMDD(window)
ORDER BY (window, tool_name, vendor, model_name)
TTL window + INTERVAL 90 DAY;

CREATE MATERIALIZED VIEW IF NOT EXISTS tool_stats_1m_mv
TO tool_stats_1m
AS SELECT
    toStartOfMinute(timestamp)       AS window,
    tool_name,
    vendor,
    model_name,
    count()                          AS call_count,
    countIf(has_error = 1)           AS error_count,
    sum(cost_usd)                    AS cost_usd_sum,
    quantileState(0.99)(duration_ms) AS latency_p99_state
FROM tool_calls
GROUP BY window, tool_name, vendor, model_name;

-- Query helper: use quantileMerge to read P99 back out.
-- SELECT window, tool_name, quantileMerge(0.99)(latency_p99_state) AS p99_ms
-- FROM tool_stats_1m GROUP BY window, tool_name ORDER BY window DESC;
```

### `schema/003_tool_cost_rollup_mv.sql`

```sql
-- SPDX-License-Identifier: MIT
-- tool_cost_rollup: total cost by vendor + model per minute.
-- SummingMergeTree deduplicates partial sums on background merges.
CREATE TABLE IF NOT EXISTS tool_cost_rollup (
    window       DateTime,
    vendor       LowCardinality(String),
    model_name   LowCardinality(String),
    call_count   UInt64,
    cost_usd_sum Float64
) ENGINE = SummingMergeTree((call_count, cost_usd_sum))
PARTITION BY toYYYYMMDD(window)
ORDER BY (window, vendor, model_name)
TTL window + INTERVAL 90 DAY;

CREATE MATERIALIZED VIEW IF NOT EXISTS tool_cost_rollup_mv
TO tool_cost_rollup
AS SELECT
    toStartOfMinute(timestamp) AS window,
    vendor,
    model_name,
    count()                    AS call_count,
    sum(cost_usd)              AS cost_usd_sum
FROM tool_calls
GROUP BY window, vendor, model_name;
```

### `schema/004_tool_duration_alert_mv.sql`

```sql
-- SPDX-License-Identifier: MIT
-- tool_duration_alerts: captures tool calls that consumed >40% of their trace's wall time.
-- WHERE guard on trace_duration_ms > 0 prevents division by zero.
CREATE TABLE IF NOT EXISTS tool_duration_alerts (
    timestamp         DateTime64(3, 'UTC'),
    trace_id          String,
    tool_id           String,
    tool_name         LowCardinality(String),
    vendor            LowCardinality(String),
    duration_ms       UInt64,
    trace_duration_ms UInt64,
    pct_of_trace      Float64
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (timestamp, trace_id, tool_name)
TTL timestamp + INTERVAL 7 DAY;

CREATE MATERIALIZED VIEW IF NOT EXISTS tool_duration_alert_mv
TO tool_duration_alerts
AS SELECT
    timestamp,
    trace_id,
    tool_id,
    tool_name,
    vendor,
    duration_ms,
    trace_duration_ms,
    (toFloat64(duration_ms) / toFloat64(trace_duration_ms)) * 100.0 AS pct_of_trace
FROM tool_calls
WHERE trace_duration_ms > 0
  AND (toFloat64(duration_ms) / toFloat64(trace_duration_ms)) * 100.0 > 40.0;
```

### `schema/005_apply.sh`

```bash
#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Applies all ClickHouse DDL files in order.
# Usage: CLICKHOUSE_URL=http://localhost:8123 bash schema/005_apply.sh
set -euo pipefail

CLICKHOUSE_URL="${CLICKHOUSE_URL:-http://localhost:8123}"

for f in schema/001_tool_calls.sql \
          schema/002_tool_stats_1m_mv.sql \
          schema/003_tool_cost_rollup_mv.sql \
          schema/004_tool_duration_alert_mv.sql; do
    echo "Applying $f ..."
    curl -s --fail -X POST "$CLICKHOUSE_URL/" --data-binary "@$f"
    echo "  OK: $f"
done
echo "All DDL applied."
```

---

## Part 2 — ClickHouse HTTP Writer

### `pkg/clickhouse/writer.go`

```go
// SPDX-License-Identifier: MIT
// Package clickhouse provides a lightweight HTTP writer for the ClickHouse HTTP API.
// Uses INSERT INTO ... FORMAT JSONEachRow — no CGO, no native protocol required.
package clickhouse

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

// row is the ClickHouse-compatible flat representation of a ToolCall.
// Column names match the DDL exactly (snake_case).
type row struct {
	TraceID         string  `json:"trace_id"`
	ToolID          string  `json:"tool_id"`
	ToolName        string  `json:"tool_name"`
	Vendor          string  `json:"vendor"`
	Category        string  `json:"category"`
	ModelName       string  `json:"model_name"`
	InputTokens     int     `json:"input_tokens"`
	OutputTokens    int     `json:"output_tokens"`
	CostUSD         float64 `json:"cost_usd"`
	DurationMs      uint64  `json:"duration_ms"`
	TraceDurationMs uint64  `json:"trace_duration_ms"`
	HasError        uint8   `json:"has_error"`
	Status          string  `json:"status"`
	Timestamp       string  `json:"timestamp"` // "2006-01-02 15:04:05.000"
}

// Writer inserts ToolCall structs into the ClickHouse tool_calls table via HTTP JSONEachRow.
type Writer struct {
	baseURL    string
	table      string
	httpClient *http.Client
}

// New creates a Writer targeting baseURL (e.g. "http://localhost:8123").
func New(baseURL string) *Writer {
	return &Writer{
		baseURL:    baseURL,
		table:      "tool_calls",
		httpClient: &http.Client{Timeout: 5 * time.Second},
	}
}

// NewWithClient creates a Writer with an injected HTTP client (for testing).
func NewWithClient(baseURL string, client *http.Client) *Writer {
	return &Writer{baseURL: baseURL, table: "tool_calls", httpClient: client}
}

// Insert serializes tc as a JSONEachRow row and POSTs it to ClickHouse.
// durationMs is the tool span duration; traceDurationMs is the trace root span duration.
func (w *Writer) Insert(ctx context.Context, tc types.ToolCall, durationMs, traceDurationMs uint64) error {
	r := row{
		TraceID:         tc.TraceID,
		ToolID:          tc.ID,
		ToolName:        tc.Name,
		Vendor:          tc.Vendor,
		Category:        string(tc.Category),
		ModelName:       tc.ModelName,
		InputTokens:     tc.Cost.InputTokens,
		OutputTokens:    tc.Cost.OutputTokens,
		CostUSD:         tc.Cost.CostUSD,
		DurationMs:      durationMs,
		TraceDurationMs: traceDurationMs,
		HasError:        boolToUint8(tc.HasError),
		Status:          tc.Status,
		Timestamp:       time.Now().UTC().Format("2006-01-02 15:04:05.000"),
	}

	payload, err := json.Marshal(r)
	if err != nil {
		return fmt.Errorf("clickhouse: marshal failed: %w", err)
	}

	url := fmt.Sprintf("%s/?query=INSERT%%20INTO%%20%s%%20FORMAT%%20JSONEachRow", w.baseURL, w.table)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(payload))
	if err != nil {
		return fmt.Errorf("clickhouse: build request failed: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := w.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("clickhouse: HTTP request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("clickhouse: unexpected status %d", resp.StatusCode)
	}
	return nil
}

func boolToUint8(b bool) uint8 {
	if b {
		return 1
	}
	return 0
}
```

### `pkg/clickhouse/writer_test.go`

```go
// SPDX-License-Identifier: MIT
package clickhouse_test

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/AkshantVats/tool-call-analyzer/pkg/clickhouse"
	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

func TestWriterInsert(t *testing.T) {
	var receivedBody string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		receivedBody = string(body)
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	writer := clickhouse.NewWithClient(srv.URL, srv.Client())

	tc := types.ToolCall{
		ID:        "tcall-001",
		TraceID:   "trace-abc",
		Name:      "search_web",
		Vendor:    "openai",
		Category:  types.CategoryHTTP,
		ModelName: "gpt-4o",
		HasError:  false,
		Status:    "OK",
		Cost: types.CostEstimate{
			InputTokens:  512,
			OutputTokens: 64,
			CostUSD:      0.00192,
		},
	}

	if err := writer.Insert(context.Background(), tc, 120, 300); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !strings.Contains(receivedBody, `"tool_name":"search_web"`) {
		t.Errorf("expected tool_name in body, got: %s", receivedBody)
	}
	if !strings.Contains(receivedBody, `"vendor":"openai"`) {
		t.Errorf("expected vendor in body, got: %s", receivedBody)
	}
	if !strings.Contains(receivedBody, `"duration_ms":120`) {
		t.Errorf("expected duration_ms=120 in body, got: %s", receivedBody)
	}
	if !strings.Contains(receivedBody, `"trace_duration_ms":300`) {
		t.Errorf("expected trace_duration_ms=300 in body, got: %s", receivedBody)
	}
	if !strings.Contains(receivedBody, `"has_error":0`) {
		t.Errorf("expected has_error=0 in body, got: %s", receivedBody)
	}
}

func TestWriterHTTPError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()

	writer := clickhouse.NewWithClient(srv.URL, srv.Client())
	tc := types.ToolCall{Name: "test", Vendor: "openai", Status: "OK"}

	err := writer.Insert(context.Background(), tc, 100, 200)
	if err == nil {
		t.Fatal("expected error on HTTP 500, got nil")
	}
	if !strings.Contains(err.Error(), "500") {
		t.Errorf("expected 500 in error message, got: %v", err)
	}
}

func TestWriterZeroTraceDuration(t *testing.T) {
	// Zero trace_duration_ms is valid to insert — the alert MV filters it via WHERE trace_duration_ms > 0.
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	writer := clickhouse.NewWithClient(srv.URL, srv.Client())
	tc := types.ToolCall{Name: "test", Vendor: "openai", Status: "OK"}

	if err := writer.Insert(context.Background(), tc, 100, 0); err != nil {
		t.Fatalf("unexpected error for zero trace_duration_ms: %v", err)
	}
}
```

---

## Part 3 — Stats Aggregator (Pure Go)

### `pkg/stats/aggregator.go`

```go
// SPDX-License-Identifier: MIT
// Package stats provides pure-Go per-tool statistics computation.
// Mirrors the ClickHouse MV logic so unit tests can verify correctness
// without a running ClickHouse instance.
package stats

import (
	"sort"

	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

// ToolStats holds aggregated statistics for a single (tool_name, vendor) group.
type ToolStats struct {
	ToolName   string
	Vendor     string
	CallCount  int
	ErrorCount int
	CostUSDSum float64
	P99Ms      uint64
}

// Aggregator computes per-tool statistics from batches of ToolCall records.
type Aggregator struct {
	// AlertThresholdPct is the tool-duration-as-percentage-of-trace that triggers an alert.
	// Default: 40.0 (40%). Mirrors the ClickHouse alert MV threshold.
	AlertThresholdPct float64
}

// New returns an Aggregator with a 40% alert threshold.
func New() *Aggregator {
	return &Aggregator{AlertThresholdPct: 40.0}
}

// Aggregate computes per-(tool_name, vendor) stats from calls.
// durations[i] is the span duration_ms for calls[i]. Lengths must match.
func (a *Aggregator) Aggregate(calls []types.ToolCall, durations []uint64) []ToolStats {
	type key struct{ name, vendor string }
	type bucket struct {
		stats     ToolStats
		latencies []uint64
	}

	buckets := make(map[key]*bucket)
	for i, tc := range calls {
		k := key{tc.Name, tc.Vendor}
		b, ok := buckets[k]
		if !ok {
			b = &bucket{stats: ToolStats{ToolName: tc.Name, Vendor: tc.Vendor}}
			buckets[k] = b
		}
		b.stats.CallCount++
		b.stats.CostUSDSum += tc.Cost.CostUSD
		if tc.HasError {
			b.stats.ErrorCount++
		}
		if i < len(durations) {
			b.latencies = append(b.latencies, durations[i])
		}
	}

	result := make([]ToolStats, 0, len(buckets))
	for _, b := range buckets {
		b.stats.P99Ms = P99(b.latencies)
		result = append(result, b.stats)
	}
	return result
}

// P99 returns the 99th percentile of durations (milliseconds).
// Returns 0 for nil or empty slices. Does not mutate the input.
func P99(durations []uint64) uint64 {
	if len(durations) == 0 {
		return 0
	}
	sorted := make([]uint64, len(durations))
	copy(sorted, durations)
	sort.Slice(sorted, func(i, j int) bool { return sorted[i] < sorted[j] })
	idx := int(float64(len(sorted)-1) * 0.99)
	return sorted[idx]
}

// IsAlertThreshold returns true when durationMs exceeds AlertThresholdPct percent
// of traceDurationMs. Returns false when traceDurationMs is zero (division guard).
func (a *Aggregator) IsAlertThreshold(durationMs, traceDurationMs uint64) bool {
	if traceDurationMs == 0 {
		return false
	}
	pct := (float64(durationMs) / float64(traceDurationMs)) * 100.0
	return pct > a.AlertThresholdPct
}
```

### `pkg/stats/aggregator_test.go`

```go
// SPDX-License-Identifier: MIT
package stats_test

import (
	"testing"

	"github.com/AkshantVats/tool-call-analyzer/pkg/stats"
	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

func TestP99Single(t *testing.T) {
	if got := stats.P99([]uint64{100}); got != 100 {
		t.Errorf("P99([100]) = %d, want 100", got)
	}
}

func TestP99Empty(t *testing.T) {
	if got := stats.P99(nil); got != 0 {
		t.Errorf("P99(nil) = %d, want 0", got)
	}
}

func TestP99Hundred(t *testing.T) {
	// 100 values 1..100; P99 = value at index floor(99 * 0.99) = index 98 of sorted = 99
	vals := make([]uint64, 100)
	for i := range vals {
		vals[i] = uint64(i + 1)
	}
	got := stats.P99(vals)
	if got != 99 {
		t.Errorf("P99(1..100) = %d, want 99", got)
	}
}

func TestP99DoesNotMutateInput(t *testing.T) {
	input := []uint64{50, 10, 90, 30}
	_ = stats.P99(input)
	if input[0] != 50 {
		t.Error("P99 must not mutate the input slice")
	}
}

var alertTests = []struct {
	name            string
	durationMs      uint64
	traceDurationMs uint64
	wantAlert       bool
}{
	{"exactly 40 pct — not over threshold", 40, 100, false},
	{"41 pct — just over", 41, 100, true},
	{"80 pct — clear alert", 80, 100, true},
	{"zero trace duration — division guard", 100, 0, false},
	{"100 pct — whole trace", 100, 100, true},
	{"1 pct — no alert", 1, 100, false},
	{"39.9 pct — no alert", 399, 1000, false},
	{"40.1 pct — alert", 401, 1000, true},
}

func TestAlertThreshold(t *testing.T) {
	agg := stats.New()
	for _, tt := range alertTests {
		t.Run(tt.name, func(t *testing.T) {
			got := agg.IsAlertThreshold(tt.durationMs, tt.traceDurationMs)
			if got != tt.wantAlert {
				t.Errorf("IsAlertThreshold(%d, %d) = %v, want %v",
					tt.durationMs, tt.traceDurationMs, got, tt.wantAlert)
			}
		})
	}
}

func TestAggregateGroups(t *testing.T) {
	agg := stats.New()

	calls := []types.ToolCall{
		{Name: "search_web", Vendor: "openai", HasError: false, Cost: types.CostEstimate{CostUSD: 0.01}},
		{Name: "search_web", Vendor: "openai", HasError: true, Cost: types.CostEstimate{CostUSD: 0.01}},
		{Name: "bash", Vendor: "anthropic", HasError: false, Cost: types.CostEstimate{CostUSD: 0.005}},
	}
	durations := []uint64{100, 200, 80}

	results := agg.Aggregate(calls, durations)

	byKey := make(map[string]stats.ToolStats)
	for _, r := range results {
		byKey[r.ToolName+"/"+r.Vendor] = r
	}

	sw := byKey["search_web/openai"]
	if sw.CallCount != 2 {
		t.Errorf("search_web call_count = %d, want 2", sw.CallCount)
	}
	if sw.ErrorCount != 1 {
		t.Errorf("search_web error_count = %d, want 1", sw.ErrorCount)
	}
	if sw.P99Ms != 200 {
		t.Errorf("search_web P99 = %d, want 200", sw.P99Ms)
	}
	if sw.CostUSDSum < 0.019 || sw.CostUSDSum > 0.021 {
		t.Errorf("search_web cost_sum = %f, want ~0.02", sw.CostUSDSum)
	}

	bash := byKey["bash/anthropic"]
	if bash.CallCount != 1 {
		t.Errorf("bash call_count = %d, want 1", bash.CallCount)
	}
	if bash.P99Ms != 80 {
		t.Errorf("bash P99 = %d, want 80", bash.P99Ms)
	}
}
```

---

## Git Workflow

```bash
cd tool-call-analyzer

# Write all files from this plan
# (schema/*.sql, schema/005_apply.sh, pkg/clickhouse/*, pkg/stats/*)

go test ./...
# Expect: >=12 tests passing across clickhouse + stats packages

go build ./...

git add .
git commit -m "feat: Day 39 — per-tool stats MVs + duration alert + ClickHouse HTTP writer

- schema/001: tool_calls source table (MergeTree, 30-day TTL, 14 columns)
- schema/002: tool_stats_1m_mv (AggregatingMergeTree + quantileState for correct P99)
- schema/003: tool_cost_rollup_mv (SummingMergeTree by vendor + model_name per minute)
- schema/004: tool_duration_alert_mv (fires when tool > 40pct of trace wall time)
- schema/005: apply.sh DDL runner for local ClickHouse setup
- pkg/clickhouse/writer.go: HTTP JSONEachRow insert, httptest-compatible via NewWithClient
- pkg/stats/aggregator.go: pure-Go P99 + IsAlertThreshold + group Aggregate
- pkg/stats/aggregator_test.go: 8 table-driven tests, zero-guard, mutation check
- pkg/clickhouse/writer_test.go: 3 tests (insert fields, HTTP error, zero trace_duration)

go test ./...: all tests green
Self-review: 0 issues found."

git push -u origin main
```

PR targets `main`. Mark `draft: false`. PR description includes:
- Full `go test ./...` output
- DDL summary: engine choices (MergeTree / AggregatingMergeTree / SummingMergeTree) and TTL rationale
- Alert logic note: `toFloat64` cast prevents integer division truncation in ClickHouse SQL
- Alert MV 7-day TTL (short — alerts are high-frequency, not historical)
