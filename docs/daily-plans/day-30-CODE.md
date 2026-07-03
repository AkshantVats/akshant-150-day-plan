# Day 30 — Code Plan
## agent-trace-collector — DESIGN.md: Span Schema, Execution Graph, Tool Taxonomy, OTel Mapping

**Calendar**: Thursday, 3 July 2026 · Day 30 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/agent-trace-collector` (new repo — Day 30 creates it)
**Language**: Markdown (DESIGN.md), Go (stub types)
**Builds on**: Days 27–29 — infra-ai-streaming OTel Collector integration (OSS-03), lensai-integration quickstart, Day 29 OTLP ingestion pipeline

### Shared Thread
> Step 7 Failed Silently meets ReAct Loops as Distributed Workflows in today's agent-trace-collector commit.

---

## Summary

Day 30 launches `agent-trace-collector` — the TraceForge repository for collecting, structuring, and forwarding agent execution traces. Today's deliverable is the foundational design document (`DESIGN.md`) and stub Go types (`pkg/schema/span.go`), establishing:

1. **Agent execution graph model** — how a multi-step agent run maps to a trace tree (root trace → tool-call spans → sub-agent spans)
2. **Canonical span schema** — `trace_id`, `span_id`, `parent_span_id`, `tool_name`, `model`, `tokens`, `cost_usd`, `status`, `latency_ms` — with OTel attribute name mapping
3. **Tool taxonomy** — classification of tool calls (retrieval, code-execution, browser, file-io, sub-agent) and how each maps to span attributes
4. **OTel mapping** — how spans forward to an OTel Collector via OTLP/gRPC, reusing the receiver built in OSS-03

This is a design + scaffolding day. No production-ready ingest pipeline yet — that comes in Days 31–33. The goal is a `DESIGN.md` that another engineer could read and build from, and `pkg/schema/span.go` stubs that encode the schema in Go types.

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|---------------|
| AC-1 | `agent-trace-collector` repo exists, public, MIT licensed | GitHub URL accessible |
| AC-2 | `DESIGN.md` present at repo root with all five sections (executive summary, execution graph, span schema, tool taxonomy, OTel mapping) | File rendered on GitHub |
| AC-3 | `pkg/schema/span.go` defines `Span`, `TraceID`, `SpanID`, `ToolKind`, `SpanStatus` types with JSON + OTLP field tags | `go build ./...` exits 0 |
| AC-4 | `DESIGN.md` mermaid diagram compiles without error (node count ≤ 8, labels ≤ 6 words) | Mermaid live editor validation |
| AC-5 | OTel attribute mapping table in `DESIGN.md` covers all 9 schema fields | Manual review |
| AC-6 | `go vet ./...` exits 0 | Command output in PR description |
| AC-7 | `README.md` has one-command build: `git clone ... && cd agent-trace-collector && go build ./...` | README rendered on GitHub |

---

## Part 1 — Repository Scaffold

### 1.1 Directory structure

```
agent-trace-collector/
├── DESIGN.md
├── README.md
├── LICENSE              (MIT)
├── go.mod               (module github.com/akshantvats/agent-trace-collector)
├── go.sum
├── pkg/
│   └── schema/
│       ├── span.go      (canonical span types)
│       └── span_test.go (round-trip JSON test)
└── docs/
    └── otel-mapping.md  (verbose OTel attribute expansion, referenced from DESIGN.md)
```

### 1.2 go.mod

```go
module github.com/akshantvats/agent-trace-collector

go 1.22
```

No external dependencies on Day 30. The OTLP forwarding client (using `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc`) is added on Day 31.

---

## Part 2 — Span Schema (`pkg/schema/span.go`)

```go
// SPDX-License-Identifier: MIT
package schema

import "time"

// TraceID is a 128-bit identifier for an agent execution run.
// Encoded as 32 lowercase hex characters (UUID v4 without dashes).
type TraceID string

// SpanID is a 64-bit identifier for a single tool call or sub-agent invocation.
// Encoded as 16 lowercase hex characters.
type SpanID string

// ToolKind classifies tool calls for downstream aggregation and cost allocation.
type ToolKind string

const (
	ToolKindRetrieval     ToolKind = "retrieval"      // vector search, document fetch, web search
	ToolKindCodeExec      ToolKind = "code_execution"  // bash, python repl, SQL query
	ToolKindBrowser       ToolKind = "browser"         // playwright, puppeteer, CDP
	ToolKindFileIO        ToolKind = "file_io"         // read, write, glob, grep
	ToolKindSubAgent      ToolKind = "sub_agent"       // spawning a child agent
	ToolKindModelCall     ToolKind = "model_call"      // direct LLM completion (root model call)
	ToolKindUnknown       ToolKind = "unknown"
)

// SpanStatus mirrors OTel span status codes.
type SpanStatus string

const (
	SpanStatusOK    SpanStatus = "OK"
	SpanStatusError SpanStatus = "ERROR"
	SpanStatusUnset SpanStatus = "UNSET"
)

// Span is the canonical TraceForge span for a single step in an agent execution.
// All monetary fields are in USD. All duration fields are in milliseconds.
//
// OTel mapping: see docs/otel-mapping.md for full attribute name list.
// OTel resource attributes: service.name="agent-trace-collector", service.version.
type Span struct {
	// --- Identity ---
	TraceID  TraceID `json:"trace_id"`            // OTLP: trace_id (128-bit bytes)
	SpanID   SpanID  `json:"span_id"`             // OTLP: span_id (64-bit bytes)
	ParentID SpanID  `json:"parent_span_id"`      // OTLP: parent_span_id; empty = root span

	// --- What happened ---
	ToolName string     `json:"tool_name"`          // e.g. "Read", "Bash", "agent"
	ToolKind ToolKind   `json:"tool_kind"`          // classified by taxonomy (see ToolKind consts)
	Model    string     `json:"model"`              // e.g. "claude-sonnet-4-6", "" for non-model calls
	Status   SpanStatus `json:"status"`             // OK | ERROR | UNSET

	// --- Timing ---
	StartTime  time.Time     `json:"start_time"`    // RFC3339Nano; OTLP: start_time_unix_nano
	LatencyMs  int64         `json:"latency_ms"`    // duration in milliseconds

	// --- Token + cost ---
	InputTokens  int     `json:"input_tokens"`      // prompt tokens consumed (0 for non-model calls)
	OutputTokens int     `json:"output_tokens"`     // completion tokens produced
	TotalTokens  int     `json:"total_tokens"`      // input + output; redundant but convenient
	CostUSD      float64 `json:"cost_usd"`          // total cost for this span in USD

	// --- Error detail ---
	ErrorMessage string `json:"error_message,omitempty"` // populated when Status = ERROR

	// --- Freeform metadata ---
	Attributes map[string]string `json:"attributes,omitempty"` // arbitrary key-value pairs
}
```

### 2.1 Round-trip test (`pkg/schema/span_test.go`)

```go
// SPDX-License-Identifier: MIT
package schema_test

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/akshantvats/agent-trace-collector/pkg/schema"
)

func TestSpanRoundTrip(t *testing.T) {
	s := schema.Span{
		TraceID:      "4bf92f3577b34da6a3ce929d0e0e4736",
		SpanID:       "00f067aa0ba902b7",
		ParentID:     "",
		ToolName:     "Read",
		ToolKind:     schema.ToolKindFileIO,
		Model:        "",
		Status:       schema.SpanStatusOK,
		StartTime:    time.Date(2026, 7, 3, 2, 0, 0, 0, time.UTC),
		LatencyMs:    42,
		InputTokens:  0,
		OutputTokens: 0,
		TotalTokens:  0,
		CostUSD:      0.0,
	}

	b, err := json.Marshal(s)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var s2 schema.Span
	if err := json.Unmarshal(b, &s2); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}

	if s.TraceID != s2.TraceID || s.SpanID != s2.SpanID || s.LatencyMs != s2.LatencyMs {
		t.Errorf("round-trip mismatch: got %+v, want %+v", s2, s)
	}
}
```

---

## Part 3 — DESIGN.md Structure

The full `DESIGN.md` is the primary Day 30 deliverable. It must cover all five sections below. Write it in first-person engineering voice — decisions should include rationale ("I chose X because Y"), not just declarations.

### Section 1 — Executive Summary (< 200 words)

TraceForge `agent-trace-collector` answers the question: what exactly did the agent do, step by step, and what did each step cost? The collector accepts spans from any agent runtime (Claude Code, LangChain, custom loops), normalises them to a canonical schema, and forwards them to an OTel Collector via OTLP/gRPC — reusing the receiver from OSS-03 in `infra-ai-streaming`. The schema is intentionally minimal: nine fields that any LLM orchestration framework can populate without bespoke instrumentation. Every span maps directly to an OTel span, enabling existing observability tooling (Jaeger, Grafana Tempo, ClickHouse + Grafana) to visualise agent execution trees without a custom UI.

### Section 2 — Agent Execution Graph

**Key points to cover:**
- Every agent run is a trace: a directed tree of spans rooted at the top-level model call
- Parallel tool calls produce sibling spans with the same parent
- Sub-agent invocations produce a child span whose `TraceID` is the same root trace but whose `ParentID` points to the spawning span
- A span's `start_time` + `latency_ms` establishes the timeline; overlapping sibling spans indicate parallelism
- The execution graph is reconstructed client-side from the flat span stream: group by `trace_id`, build tree by `parent_span_id`

**Mermaid diagram (canonical execution graph):**

```
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e3a5f',
    'primaryTextColor': '#f0f4f8',
    'primaryBorderColor': '#4a90d9',
    'lineColor': '#4a90d9',
    'secondaryColor': '#0d2137',
    'tertiaryColor': '#0a1a2e',
    'background': 'transparent',
    'nodeBorder': '#4a90d9',
    'clusterBkg': '#0d2137',
    'titleColor': '#f0f4f8',
    'edgeLabelBackground': '#0d2137'
  }
}}%%
flowchart TD
    A["Root: model call\n(trace root)"] --> B["Tool: Read file"]
    A --> C["Tool: Bash command"]
    A --> D["Sub-agent spawn"]
    D --> E["Sub-agent model call"]
    E --> F["Sub-agent tool: Grep"]
    A --> G["Tool: Edit file"]
```

**Caption:** A single agent run produces one trace tree. The root span is the top-level model call. Tool calls are direct children. Sub-agent invocations create a subtree — all under the same `trace_id`, linked by `parent_span_id`.

### Section 3 — Span Schema

Present the nine canonical fields in a table:

| Field | Type | OTel attribute | Description |
|---|---|---|---|
| `trace_id` | `string` (hex128) | `TraceId` | Root identifier for one agent run |
| `span_id` | `string` (hex64) | `SpanId` | Identifier for this specific step |
| `parent_span_id` | `string` (hex64) | `ParentSpanId` | Empty = root span |
| `tool_name` | `string` | `traceforge.tool.name` | Human-readable tool name (e.g. "Read") |
| `model` | `string` | `traceforge.model` | Model ID (e.g. "claude-sonnet-4-6"); empty for non-LLM tools |
| `tokens` | `int` (total) | `traceforge.tokens.total` | Input + output tokens; broken out in extended attributes |
| `cost_usd` | `float64` | `traceforge.cost.usd` | Monetary cost for this span |
| `status` | `enum` | `SpanStatus` (OTel) | OK \| ERROR \| UNSET |
| `latency_ms` | `int64` | derived from `StartTime + EndTime` | Wall-clock duration in milliseconds |

**Design decision to explain:** `tokens` stores total (input + output) as the canonical field because it's the denominator for most cost calculations. Input and output are stored in `Attributes` as `traceforge.tokens.input` / `traceforge.tokens.output` for breakdowns that need them. This keeps the canonical schema tight while allowing precision when needed.

### Section 4 — Tool Taxonomy

**Purpose:** Classify tool calls so downstream queries can aggregate by category.

| ToolKind | Examples | When `model` field is set |
|---|---|---|
| `retrieval` | vector search, web search, document fetch | No |
| `code_execution` | Bash, Python REPL, SQL query | No |
| `browser` | Playwright, Puppeteer, CDP navigate | No |
| `file_io` | Read, Write, Edit, Glob, Grep | No |
| `sub_agent` | Agent tool spawning a child agent | No (model is on the child root span) |
| `model_call` | Top-level LLM completion | **Yes** |
| `unknown` | Any unclassified tool | No |

**Classification rule:** any span that directly invokes an LLM API endpoint gets `tool_kind: model_call` and has `model` populated. Everything else gets the appropriate category with an empty `model` field. Sub-agent spans are `sub_agent` at the parent; the child agent's first model call is `model_call` in the child subtree.

**Design decision to explain:** `sub_agent` is a first-class ToolKind rather than being handled as a nested `model_call` because sub-agent spans have different semantics — they represent boundary crossings where token and cost accounting resets. A query for "total tokens per top-level run" must stop at `sub_agent` boundaries to avoid double-counting when sub-agents are also reporting their own spans.

### Section 5 — OTel Mapping

**How spans forward to the OTel Collector:**

1. `agent-trace-collector` receives spans (initially via HTTP POST to its own endpoint, gRPC in Day 31)
2. Normalises to the canonical `Span` schema
3. Constructs OTel `ResourceSpans` with resource attribute `service.name = "agent-trace-collector"`
4. Emits via OTLP/gRPC to the OTel Collector running as a sidecar (port 4317) — same collector deployed by OSS-03
5. The collector's existing pipeline routes to ClickHouse via the `lensai_schema` processor

**Mapping diagram:**

```
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e3a5f',
    'primaryTextColor': '#f0f4f8',
    'primaryBorderColor': '#4a90d9',
    'lineColor': '#4a90d9',
    'secondaryColor': '#0d2137',
    'tertiaryColor': '#0a1a2e',
    'background': 'transparent',
    'nodeBorder': '#4a90d9',
    'clusterBkg': '#0d2137',
    'titleColor': '#f0f4f8',
    'edgeLabelBackground': '#0d2137'
  }
}}%%
flowchart LR
    A["Agent runtime"] --> B["Span HTTP endpoint\n:8080/v1/spans"]
    B --> C["Canonical schema\nnormalisation"]
    C --> D["OTLP/gRPC exporter\nport 4317"]
    D --> E["OTel Collector\n(OSS-03 sidecar)"]
    E --> F["ClickHouse\nlensai.agent_spans"]
```

**ClickHouse target table** (to be created Day 31):
```sql
CREATE TABLE IF NOT EXISTS lensai.agent_spans (
    trace_id        String,
    span_id         String,
    parent_span_id  String DEFAULT '',
    tool_name       String,
    tool_kind       LowCardinality(String),
    model           String DEFAULT '',
    input_tokens    UInt32 DEFAULT 0,
    output_tokens   UInt32 DEFAULT 0,
    total_tokens    UInt32 DEFAULT 0,
    cost_usd        Float64 DEFAULT 0.0,
    status          LowCardinality(String),
    latency_ms      UInt32,
    error_message   String DEFAULT '',
    started_at      DateTime64(3),
    ingested_at     DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (started_at, trace_id, span_id)
PARTITION BY toYYYYMM(started_at);
```

---

## Implementation Checklist

### Repo setup
- [ ] Create `agent-trace-collector` repo (public, MIT)
- [ ] `go mod init github.com/akshantvats/agent-trace-collector`
- [ ] Create `LICENSE` (MIT, 2026 AkshantVats)
- [ ] Write `README.md` with: what TraceForge is, one-command build (`go build ./...`), architecture overview linking to DESIGN.md

### Schema
- [ ] Create `pkg/schema/span.go` with all types and constants
- [ ] Create `pkg/schema/span_test.go` with round-trip JSON test
- [ ] `go build ./...` exits 0
- [ ] `go test ./...` exits 0 (round-trip test passes)
- [ ] `go vet ./...` exits 0

### DESIGN.md
- [ ] Section 1: Executive Summary (< 200 words, clear what problem it solves)
- [ ] Section 2: Execution Graph with mermaid diagram (≤ 8 nodes, ≤ 6 word labels)
- [ ] Section 3: Span Schema table (9 fields, OTel column, description column)
- [ ] Section 4: Tool Taxonomy table + classification rule + sub_agent design decision
- [ ] Section 5: OTel Mapping with forwarding flow diagram + ClickHouse DDL
- [ ] Mermaid init block matches spec exactly on both diagrams
- [ ] `docs/otel-mapping.md` exists (referenced from DESIGN.md for verbose attribute list)

### Validation
- [ ] `go build ./...` exits 0
- [ ] `go test ./...` exits 0
- [ ] `go vet ./...` exits 0
- [ ] Both mermaid diagrams validated in Mermaid live editor
- [ ] PR opened with test output in description
- [ ] PR marked ready for review (not draft)
- [ ] PR URL recorded in `DAILY_PROGRESS.md`
- [ ] `Self-review: N issues found and fixed.` in commit message

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OTel OTLP types in Go require importing large proto deps | Medium | Low | Day 30 only defines schema types — OTLP exporter dependency added Day 31 |
| ClickHouse `agent_spans` table not yet created | Low | Low | DDL is in DESIGN.md; table created Day 31 when ingest pipeline lands |
| `parent_span_id` ambiguity for root spans | Medium | Low | Document that root spans use empty string `""`, not null or zero-value TraceID |
| Naming conflict with OTel's own `SpanID` type | Low | Medium | Package named `schema`, not `otel` — no import path conflict; OTel types imported under alias in Day 31 |

---

## PR Description Template

```
## Day 30 — agent-trace-collector: DESIGN.md + Span Schema

### What
- New repo: `agent-trace-collector` (TraceForge agent execution trace collection)
- `DESIGN.md`: five-section design document — execution graph model, span schema,
  tool taxonomy, OTel attribute mapping, ClickHouse DDL target
- `pkg/schema/span.go`: canonical `Span` type, `ToolKind` + `SpanStatus` enums
- `pkg/schema/span_test.go`: JSON round-trip test
- `docs/otel-mapping.md`: verbose OTel attribute expansion

### Test output
```
$ go build ./...
(exit 0)

$ go test ./...
ok  github.com/akshantvats/agent-trace-collector/pkg/schema   0.003s

$ go vet ./...
(exit 0)
```

### Next steps (Day 31)
- HTTP ingestion endpoint (`POST /v1/spans`)
- OTLP/gRPC exporter wired to OTel Collector
- ClickHouse `agent_spans` table creation + writer

Self-review: N issues found and fixed.
```

---

## Definition of Done

- [ ] `go build ./...` exits 0
- [ ] `go test ./...` exits 0 (round-trip test passes)
- [ ] `go vet ./...` exits 0
- [ ] `DESIGN.md` present with all five sections
- [ ] Both mermaid diagrams validated
- [ ] PR opened, marked ready for review (not draft)
- [ ] PR URL in `DAILY_PROGRESS.md`
- [ ] `Self-review: N issues found and fixed.` in commit message
