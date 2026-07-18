# Day 41 — Code Plan
## tool-call-analyzer: Bottleneck Rank by Exclusive Time + Grafana Tool Cost Waterfall

**Calendar**: Monday, Day 41 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/tool-call-analyzer` (builds on Day 40 graph package + CLI)
**Language**: Go 1.22+
**Builds on**: Day 40 — `pkg/graph` (DependencyGraph, HasCycle, TopologicalSort, DetectN1), `cmd/traceforge/graph.go`

### Shared Thread
> Exclusive Time meets Cost Waterfalls — CFO-Friendly Visuals in today's tool-call-analyzer commit. Bottleneck rank identifies which tool owns the most wall time across a trace. The Grafana waterfall turns that into a chart your VP of Engineering can act on without reading logs.

---

## Summary

Day 40 built the graph intelligence layer (cycle detection, topological sort, N+1 alerts). Day 41 adds two things that turn the graph into actionable cost intelligence:

1. **`pkg/graph/exclusive_time.go`** — exclusive time computation per span: `exclusive_time = span.duration - Σ(direct child durations)`. Ranks spans by exclusive time descending. The top-ranked span is the bottleneck.
2. **`pkg/graph/exclusive_time_test.go`** — ≥10 table-driven tests: single-span graph, fan-out (parallel children), sequential chain, mixed topology, zero-duration root
3. **`pkg/waterfall/waterfall.go`** — builds a Grafana-compatible stacked bar JSON payload from a list of spans: groups by tool_name, sums cost_usd per tool per trace, sorts descending, outputs `{"data": [...]}` ready for a Grafana Bar Gauge panel
4. **`pkg/waterfall/waterfall_test.go`** — ≥8 tests: empty trace, single tool, multi-tool sort order, cost aggregation correctness, JSON shape
5. **`cmd/traceforge/bottleneck.go`** — `traceforge bottleneck --trace-id <id> [--top N] [--format text|json]` subcommand: fetches spans from ClickHouse, builds graph, computes exclusive times, prints ranked list
6. **`cmd/traceforge/waterfall.go`** — `traceforge waterfall --trace-id <id>` subcommand: fetches spans + costs from ClickHouse, builds waterfall payload, prints JSON to stdout (pipe to Grafana via Simple JSON datasource)

Target: `go test ./...` exits 0, `go build ./cmd/traceforge` exits 0.

---

## Data Model Additions

### `pkg/graph/exclusive_time.go`

```go
// SPDX-License-Identifier: MIT
package graph

// ExclusiveTimeResult holds the exclusive time for a single span.
type ExclusiveTimeResult struct {
	SpanID        string
	ToolName      string
	Vendor        string
	TotalDurationMs   uint64
	ExclusiveTimeMs   uint64 // TotalDurationMs - Σ(direct child durations)
	ChildCount    int
}

// ComputeExclusiveTimes returns ExclusiveTimeResult for every node in g,
// sorted descending by ExclusiveTimeMs (bottleneck first).
func ComputeExclusiveTimes(g *DependencyGraph) []ExclusiveTimeResult
```

**Algorithm** (O(V+E)):
1. For each node N in graph.Nodes, sum the DurationMs of all direct children (nodes where edge source == N.SpanID).
2. `exclusive_time = N.DurationMs - sum_children`. Clamp to 0 (floating point / clock skew can produce tiny negatives).
3. Collect into `[]ExclusiveTimeResult`, sort descending by ExclusiveTimeMs using `slices.SortFunc`.

**Edge cases**:
- Leaf nodes (no children): exclusive_time == DurationMs
- Root node with all children running in parallel: exclusive_time ≈ 0 if children account for all duration
- Missing children (partial trace): clamp, do not error

---

### `pkg/waterfall/waterfall.go`

```go
// SPDX-License-Identifier: MIT
package waterfall

// SpanCost is the input to the waterfall builder.
type SpanCost struct {
	SpanID   string
	ToolName string
	Vendor   string
	CostUSD  float64
}

// WaterfallEntry is one bar in the Grafana stacked bar chart.
type WaterfallEntry struct {
	ToolName string  `json:"tool_name"`
	Vendor   string  `json:"vendor"`
	CostUSD  float64 `json:"cost_usd"`
}

// WaterfallPayload is the JSON output (Grafana Simple JSON datasource shape).
type WaterfallPayload struct {
	TraceID string           `json:"trace_id"`
	Data    []WaterfallEntry `json:"data"` // sorted by CostUSD descending
}

// Build aggregates SpanCost records by (tool_name, vendor), sorts descending
// by total CostUSD, and returns a WaterfallPayload.
func Build(traceID string, spans []SpanCost) WaterfallPayload
```

**Aggregation logic**:
```
key := tool_name + ":" + vendor
totals := map[key]float64{}
for each span: totals[key] += span.CostUSD
sort entries by value descending
```

---

## CLI Subcommands

### `traceforge bottleneck`

```bash
# Text output (default)
traceforge bottleneck \
  --trace-id 7f3d9a2e-1234-5678-abcd-ef0123456789 \
  --top 5

# JSON output (pipe to jq / Grafana)
traceforge bottleneck \
  --trace-id 7f3d9a2e-1234-5678-abcd-ef0123456789 \
  --format json
```

**Sample text output**:
```
=== TraceForge Bottleneck Report ===
Trace ID  : 7f3d9a2e-1234-5678-abcd-ef0123456789
Spans     : 7

Rank  SpanID      Tool             Vendor     Excl. Time   Total Time
1     a1b2c3d4    code_interpreter anthropic    840ms        840ms
2     e5f6g7h8    search_web       openai       380ms        380ms
3     i9j0k1l2    retrieve_doc     openai       120ms        120ms
4     m3n4o5p6    plan_task        openai          8ms        848ms
5     q7r8s9t0    summarize        anthropic      62ms         62ms

Bottleneck: code_interpreter (anthropic) — 840ms exclusive time
```

**Sample JSON output** (for programmatic use):
```json
{
  "trace_id": "7f3d9a2e-1234-5678-abcd-ef0123456789",
  "bottleneck": {
    "span_id": "a1b2c3d4",
    "tool_name": "code_interpreter",
    "vendor": "anthropic",
    "exclusive_time_ms": 840,
    "total_duration_ms": 840
  },
  "ranked": [
    {"rank": 1, "span_id": "a1b2c3d4", "tool_name": "code_interpreter", "vendor": "anthropic", "exclusive_time_ms": 840, "total_duration_ms": 840},
    {"rank": 2, "span_id": "e5f6g7h8", "tool_name": "search_web", "vendor": "openai", "exclusive_time_ms": 380, "total_duration_ms": 380}
  ]
}
```

---

### `traceforge waterfall`

```bash
traceforge waterfall \
  --trace-id 7f3d9a2e-1234-5678-abcd-ef0123456789
```

**Sample JSON output** (Grafana Simple JSON datasource):
```json
{
  "trace_id": "7f3d9a2e-1234-5678-abcd-ef0123456789",
  "data": [
    {"tool_name": "code_interpreter", "vendor": "anthropic", "cost_usd": 0.0082},
    {"tool_name": "search_web",       "vendor": "openai",    "cost_usd": 0.0031},
    {"tool_name": "retrieve_doc",     "vendor": "openai",    "cost_usd": 0.0009},
    {"tool_name": "plan_task",        "vendor": "openai",    "cost_usd": 0.0004},
    {"tool_name": "summarize",        "vendor": "anthropic", "cost_usd": 0.0003}
  ]
}
```

**Grafana wiring** (instructions in PR description, not in code):
- Add Grafana Simple JSON datasource pointing to `traceforge waterfall` stdout via a thin HTTP wrapper
- Use Bar Gauge panel, field override: display name = `{{tool_name}} ({{vendor}})`, unit = `currencyUSD`
- Sort: descending by value → waterfall shape emerges naturally

---

## ClickHouse Queries

### For `bottleneck` subcommand
```sql
SELECT
  span_id,
  parent_span_id,
  tool_name,
  vendor,
  duration_ms
FROM tool_calls
WHERE trace_id = ?
ORDER BY start_time_ns ASC
```
(Same query as `graph` subcommand — reuse `pkg/clickhouse/writer.go` read path.)

### For `waterfall` subcommand
```sql
SELECT
  span_id,
  tool_name,
  vendor,
  cost_usd
FROM tool_calls
WHERE trace_id = ?
  AND cost_usd > 0
ORDER BY cost_usd DESC
```

---

## File Layout

```
pkg/
  graph/
    graph.go          (Day 40 — unchanged)
    span.go           (Day 40 — unchanged)
    graph_test.go     (Day 40 — unchanged)
    exclusive_time.go (NEW — Day 41)
    exclusive_time_test.go (NEW — Day 41)
  waterfall/
    waterfall.go      (NEW — Day 41)
    waterfall_test.go (NEW — Day 41)
cmd/
  traceforge/
    main.go           (Day 40 — add "bottleneck" + "waterfall" to switch)
    graph.go          (Day 40 — unchanged)
    bottleneck.go     (NEW — Day 41)
    waterfall.go      (NEW — Day 41)
```

---

## Test Specification

### `exclusive_time_test.go`

| Test name | Setup | Expected |
|---|---|---|
| `TestSingleSpan` | one node, no children | exclusive == total |
| `TestSequentialChain` | A→B→C each 100ms | A excl=0 (B accounts for it), B excl=0 (C accounts for it), C excl=100ms |
| `TestParallelChildren` | root 500ms, children B 200ms + C 250ms | root excl = 500 - (200+250) = 50ms |
| `TestLeafNodes` | two siblings, no children | each excl == their own duration |
| `TestPartialChildren` | root 500ms, one child 200ms (second child missing) | root excl = max(0, 300ms) |
| `TestZeroDurationRoot` | root 0ms, child 100ms | root excl = 0 (clamped) |
| `TestSortOrder` | 4 spans with varying exclusive times | results sorted descending by ExclusiveTimeMs |
| `TestEmptyGraph` | no nodes | returns empty slice, no panic |
| `TestDeepChain` | A→B→C→D each 100ms | A excl=0, B excl=0, C excl=0, D excl=100ms |
| `TestMixedTopology` | root → [A, B]; A→C | bottleneck is A (if A.excl > B.excl and C) |

### `waterfall_test.go`

| Test name | Setup | Expected |
|---|---|---|
| `TestEmptySpans` | no spans | data=[], no panic |
| `TestSingleSpan` | one span, 0.005 USD | data=[{tool, vendor, 0.005}] |
| `TestAggregation` | two search_web spans at 0.003 + 0.002 | one entry summing to 0.005 |
| `TestSort` | three tools at 0.001, 0.009, 0.004 | sorted [0.009, 0.004, 0.001] |
| `TestVendorSplit` | search_web/openai + search_web/anthropic | two separate entries |
| `TestZeroCost` | span with cost_usd=0 | included in output (0-cost tools visible) |
| `TestJSONShape` | marshalled output | trace_id present, data array not nil |
| `TestLargeTrace` | 100 spans, 10 distinct tools | 10 entries, costs sum correctly |

---

## Implementation Notes

- Reuse `pkg/clickhouse/writer.go` mock (httptest-based) from Day 39 for test isolation
- `slices` package (Go 1.21+): use `slices.SortFunc` for deterministic sort, no `sort.Slice`
- All source files: `// SPDX-License-Identifier: MIT` header on line 1
- `cmd/traceforge/main.go` switch statement: add `"bottleneck"` and `"waterfall"` cases calling `runBottleneck(args)` and `runWaterfall(args)`
- No external dependencies beyond stdlib + `database/sql` compatible ClickHouse driver already used in Day 39

---

## Acceptance Criteria

```bash
go test ./pkg/graph/... ./pkg/waterfall/...   # exits 0, ≥18 tests pass
go build ./cmd/traceforge                      # exits 0
./traceforge bottleneck --help                 # prints usage, exits 0
./traceforge waterfall --help                  # prints usage, exits 0
```

---

## Series Navigation

Previous: Day 40 — Graph Algorithms on Traces (cycle detection, N+1 detection, CLI)
Next: Day 42 — (TBD from plan.json)
