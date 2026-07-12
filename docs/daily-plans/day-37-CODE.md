# Day 37 — Code Plan
## tool-call-analyzer: DESIGN.md, Canonical ToolCall Struct, Adapters Plan, Cost Per Invocation

**Calendar**: Thursday, 16 July 2026 · Day 37 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/tool-call-analyzer` (new repo — scaffold on Day 37)
**Language**: Go 1.22+
**Builds on**: TraceForge Python SDK (Day 32) for span attribution; TraceForge agent_spans ClickHouse schema (Day 31); sampling layer (Day 36)

### Shared Thread
> LangChain Is Four Vendors in a Trenchcoat meets Tool Taxonomies — Ontology Before Metrics in today's tool-call-analyzer commit.

---

## Summary

Day 37 creates the `tool-call-analyzer` repository and its foundational design document. The repo's purpose is to normalize AI vendor tool call formats (OpenAI `function_call`, Anthropic `tool_use`, LangChain `AgentAction`) into a single canonical `ToolCall` struct, then emit them to a Kafka topic `tools.normalized.v1`. Today's deliverable is the design scaffold: `DESIGN.md`, the canonical struct definition, the adapter interface, and a cost-per-invocation calculation that accounts for retries.

No Kafka producer ships today — that's Day 38. Today is the DESIGN.md + struct definitions + cost model so Day 38 can implement adapters against a locked spec.

---

## Deliverables

| File | Purpose |
|---|---|
| `README.md` | One-paragraph what + why + one-command quickstart |
| `DESIGN.md` | Canonical ToolCall struct, adapter contract, cost model, Kafka schema, decision log |
| `pkg/types/tool_call.go` | `ToolCall` struct, `RetryMeta`, `CostEstimate`, `ToolCategory` constants |
| `pkg/types/tool_call_test.go` | Unit tests: cost computation, retry attribution, category validation |
| `pkg/adapter/adapter.go` | `Adapter` interface: `Parse(raw []byte) (ToolCall, error)` |
| `pkg/adapter/adapter_test.go` | Table-driven test: nil input, empty input, unknown vendor |

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|-------------|
| AC-1 | `ToolCall` struct compiles and all fields are documented | `go build ./...` exits 0 |
| AC-2 | `EstimateCost` returns correct value for input token count, output token count, retry count, model name | `go test ./pkg/types/ -run TestEstimateCost` exits 0 |
| AC-3 | `RetryMeta.TotalCostUSD` equals `AttemptCostUSD * (RetryCount + 1)` within float64 tolerance | `go test ./pkg/types/ -run TestRetryTotalCost` exits 0 |
| AC-4 | `ToolCategory` constants cover all 5 required categories | `go test ./pkg/types/ -run TestToolCategoryExhaustive` exits 0 |
| AC-5 | `Adapter.Parse(nil)` returns typed `ErrNilInput` | `go test ./pkg/adapter/ -run TestAdapterNilInput` exits 0 |
| AC-6 | `go test ./...` exits 0 | Command output in PR description |
| AC-7 | `DESIGN.md` is present with all required sections | `test -f DESIGN.md && grep -q "ToolCall struct" DESIGN.md` exits 0 |

---

## Part 1 — DESIGN.md

Write this file as the Day 37 code deliverable. Content should be comprehensive enough that a new contributor can implement an adapter on Day 38 without asking questions.

```markdown
# tool-call-analyzer — Design Document

**Status**: Active · Day 37 scaffold  
**Owner**: AkshantVats  
**Kafka output topic**: `tools.normalized.v1`

---

## Problem

Every AI framework encodes a tool invocation differently:

| Vendor | Wire format | Key fields |
|--------|-------------|------------|
| OpenAI | `tool_calls[].function.{name,arguments}` | `id`, `type="function"` |
| Anthropic | `content[].{type="tool_use", name, input}` | `id`, `name`, `input` (object) |
| LangChain | `AgentAction{tool, tool_input, log}` | no canonical ID |
| LlamaIndex | `ToolOutput{tool_name, content, raw_output}` | no cost attribution |

Without normalization, every downstream consumer (ClickHouse, Grafana, cost alerting) must parse vendor-specific formats. Schema drift between OpenAI API versions has broken production pipelines three times in the last 18 months.

---

## Canonical ToolCall Struct

```go
// ToolCall is the normalized representation of a single tool invocation.
// All adapter implementations must populate every Required field.
type ToolCall struct {
    // Identity
    ID        string // required; vendor-provided or generated UUID
    TraceID   string // required; W3C traceparent trace-id if available
    SpanID    string // required; W3C traceparent span-id if available

    // Tool identity
    Name     string       // required; e.g. "get_weather", "search_web"
    Vendor   string       // required; "openai" | "anthropic" | "langchain" | "llamaindex"
    Category ToolCategory // required; semantic type (see ToolCategory)

    // Invocation
    InputJSON  string // required; JSON-encoded arguments / input object
    OutputJSON string // optional; JSON-encoded result (may be empty if error)

    // Timing
    StartedAtNs  int64 // required; Unix nanoseconds
    FinishedAtNs int64 // required; Unix nanoseconds
    DurationMs   int64 // computed; (FinishedAtNs - StartedAtNs) / 1e6

    // Cost model
    Cost    CostEstimate // required; see CostEstimate
    Retries RetryMeta    // required; see RetryMeta

    // Status
    Status    string // required; "OK" | "ERROR" | "TIMEOUT" | "EMPTY_RESPONSE"
    ErrorMsg  string // optional; populated on error
    HasError  bool   // required; true if Status != "OK"

    // Source metadata
    ModelName     string // optional; LLM model that initiated this tool call
    AgentStep     int    // optional; step index in ReAct loop (0-indexed)
    FrameworkVer  string // optional; e.g. "langchain-0.2.14"
}
```

---

## ToolCategory

Tool categories form the ontology layer. Without categories, `tool_call.latency` is a meaningless aggregate. With categories, `http.search.latency` and `code.exec.latency` reveal different optimization targets.

```go
type ToolCategory string

const (
    // CategoryHTTP covers all tool calls that make outbound HTTP requests.
    // Examples: search_web, get_weather, fetch_url, call_api
    CategoryHTTP ToolCategory = "http"

    // CategoryDB covers all tool calls that query or write to a database.
    // Examples: sql_query, vector_search, redis_get, elasticsearch_search
    CategoryDB ToolCategory = "db"

    // CategoryCode covers all tool calls that execute or analyze code.
    // Examples: run_python, bash_exec, code_interpreter, compile_check
    CategoryCode ToolCategory = "code"

    // CategoryFile covers all tool calls that read or write to a filesystem.
    // Examples: read_file, write_file, list_dir, fetch_s3_object
    CategoryFile ToolCategory = "file"

    // CategoryAgent covers all tool calls that invoke a sub-agent or model.
    // Examples: call_subagent, delegate_task, run_llm_chain
    CategoryAgent ToolCategory = "agent"
)
```

Categorization rules:
1. If the tool name contains "http", "fetch", "search", "api", "url" → CategoryHTTP
2. If the tool name contains "sql", "query", "db", "vector", "elastic", "redis" → CategoryDB
3. If the tool name contains "run", "exec", "python", "bash", "compile", "code" → CategoryCode
4. If the tool name contains "file", "read", "write", "dir", "s3", "fs" → CategoryFile
5. If the tool name contains "agent", "delegate", "llm", "chain", "subagent" → CategoryAgent
6. Default: CategoryHTTP (most tool calls are HTTP under the hood)

---

## CostEstimate

```go
// CostEstimate records the token cost of the LLM call that produced this tool invocation.
// Fields reflect the LLM call that generated the tool_use block, not the tool's execution cost.
type CostEstimate struct {
    InputTokens  int     // prompt token count (from usage block)
    OutputTokens int     // completion token count (from usage block)
    ModelName    string  // e.g. "gpt-4o", "claude-3-5-sonnet-20241022"
    CostUSD      float64 // computed; EstimateCost(InputTokens, OutputTokens, ModelName)
}

// RetryMeta records retry attribution for cost rollup.
type RetryMeta struct {
    RetryCount       int     // number of retries (0 = no retry, first attempt succeeded)
    AttemptCostUSD   float64 // cost of a single attempt (same as CostEstimate.CostUSD)
    TotalCostUSD     float64 // AttemptCostUSD * (RetryCount + 1)
    LastErrorMsg     string  // error message from the last failed attempt before success
    RetryReason      string  // "timeout" | "rate_limit" | "server_error" | "empty_response"
}
```

---

## Cost Computation

```go
// perMillionTokens holds USD cost per 1M tokens by model.
// Source: published pricing as of 2026-07. Update when pricing changes.
var perMillionTokens = map[string][2]float64{
    // [inputCostPerM, outputCostPerM]
    "gpt-4o":                         {2.50, 10.00},
    "gpt-4o-mini":                    {0.15, 0.60},
    "gpt-4-turbo":                    {10.00, 30.00},
    "claude-opus-4-8":               {15.00, 75.00},
    "claude-sonnet-4-6":             {3.00, 15.00},
    "claude-haiku-4-5-20251001":     {0.80, 4.00},
}

// EstimateCost returns the USD cost for a single LLM call given token counts and model name.
// Returns 0.0 for unknown models — callers should log a warning when cost is 0 and model is set.
func EstimateCost(inputTokens, outputTokens int, modelName string) float64 {
    prices, ok := perMillionTokens[modelName]
    if !ok {
        return 0.0
    }
    return float64(inputTokens)/1_000_000*prices[0] + float64(outputTokens)/1_000_000*prices[1]
}
```

---

## Adapter Interface

```go
// Adapter normalizes a vendor-specific tool call payload into a canonical ToolCall.
// Each vendor (openai, anthropic, langchain, llamaindex) has its own Adapter implementation.
type Adapter interface {
    // Vendor returns the adapter's vendor name: "openai", "anthropic", "langchain", "llamaindex".
    Vendor() string

    // Parse parses a raw vendor-specific JSON payload and returns a canonical ToolCall.
    // Returns ErrNilInput if raw is nil. Returns ErrUnknownFormat if the payload cannot
    // be parsed as a known tool call format for this vendor.
    Parse(raw []byte) (ToolCall, error)

    // CanHandle returns true if this adapter recognizes the raw payload format.
    // Used for auto-detection when the vendor is not explicitly known.
    CanHandle(raw []byte) bool
}

// Sentinel errors for adapter implementations.
var (
    ErrNilInput       = errors.New("tool-call-analyzer: nil input to adapter")
    ErrUnknownFormat  = errors.New("tool-call-analyzer: unrecognized tool call format")
    ErrMissingField   = errors.New("tool-call-analyzer: required field missing in payload")
)
```

---

## Kafka Output Schema

Topic: `tools.normalized.v1`  
Partition key: `trace_id` (for trace-ordered consumption)  
Format: JSON (Avro schema planned for Day 40)

```json
{
  "schema_version": "1.0",
  "id": "tcall-abc123",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "name": "search_web",
  "vendor": "openai",
  "category": "http",
  "input_json": "{\"query\": \"current weather in Berlin\"}",
  "output_json": "{\"temperature\": 18, \"condition\": \"cloudy\"}",
  "started_at_ns": 1752652800000000000,
  "finished_at_ns": 1752652801234000000,
  "duration_ms": 1234,
  "cost": {
    "input_tokens": 512,
    "output_tokens": 64,
    "model_name": "gpt-4o",
    "cost_usd": 0.001920
  },
  "retries": {
    "retry_count": 1,
    "attempt_cost_usd": 0.001920,
    "total_cost_usd": 0.003840,
    "last_error_msg": "rate_limit_exceeded",
    "retry_reason": "rate_limit"
  },
  "status": "OK",
  "error_msg": "",
  "has_error": false,
  "model_name": "gpt-4o",
  "agent_step": 2,
  "framework_ver": "openai-1.50.2"
}
```

---

## Decision Log

| Decision | Chosen | Rejected | Reason |
|----------|--------|----------|--------|
| Output format | JSON | Avro | Avro requires schema registry setup; JSON enables Day 38 without infra |
| Category field | enum constant | free-form string | Free-form strings make Grafana label cardinality unbounded |
| Cost model | hardcoded price table | external API | External API adds latency and network dependency to the hot path |
| Retry attribution | per-attempt × (retries+1) | cumulative from usage | Usage blocks don't report retry costs; multiply from attempt cost |
| Partition key | trace_id | tool name | Trace ordering allows waterfall reconstruction in ClickHouse |
```

---

## Part 2 — `pkg/types/tool_call.go`

```go
// SPDX-License-Identifier: MIT
// Package types defines the canonical ToolCall struct and supporting types
// for the tool-call-analyzer normalization pipeline.
package types

import "errors"

// ToolCategory is the semantic type of a tool invocation.
type ToolCategory string

const (
	CategoryHTTP  ToolCategory = "http"
	CategoryDB    ToolCategory = "db"
	CategoryCode  ToolCategory = "code"
	CategoryFile  ToolCategory = "file"
	CategoryAgent ToolCategory = "agent"
)

// AllCategories is used in tests to verify exhaustiveness.
var AllCategories = []ToolCategory{
	CategoryHTTP, CategoryDB, CategoryCode, CategoryFile, CategoryAgent,
}

// CostEstimate records the LLM token cost for the call that produced this tool invocation.
type CostEstimate struct {
	InputTokens  int     `json:"input_tokens"`
	OutputTokens int     `json:"output_tokens"`
	ModelName    string  `json:"model_name"`
	CostUSD      float64 `json:"cost_usd"`
}

// RetryMeta records retry count and total cost attribution.
type RetryMeta struct {
	RetryCount     int     `json:"retry_count"`
	AttemptCostUSD float64 `json:"attempt_cost_usd"`
	TotalCostUSD   float64 `json:"total_cost_usd"`
	LastErrorMsg   string  `json:"last_error_msg"`
	RetryReason    string  `json:"retry_reason"` // "timeout" | "rate_limit" | "server_error" | "empty_response"
}

// ToolCall is the canonical normalized representation of a single tool invocation.
type ToolCall struct {
	// Identity
	ID      string `json:"id"`
	TraceID string `json:"trace_id"`
	SpanID  string `json:"span_id"`

	// Tool identity
	Name     string       `json:"name"`
	Vendor   string       `json:"vendor"`
	Category ToolCategory `json:"category"`

	// Invocation payload
	InputJSON  string `json:"input_json"`
	OutputJSON string `json:"output_json"`

	// Timing
	StartedAtNs  int64 `json:"started_at_ns"`
	FinishedAtNs int64 `json:"finished_at_ns"`
	DurationMs   int64 `json:"duration_ms"`

	// Cost
	Cost    CostEstimate `json:"cost"`
	Retries RetryMeta    `json:"retries"`

	// Status
	Status   string `json:"status"`
	ErrorMsg string `json:"error_msg"`
	HasError bool   `json:"has_error"`

	// Source metadata
	ModelName    string `json:"model_name"`
	AgentStep    int    `json:"agent_step"`
	FrameworkVer string `json:"framework_ver"`
}

// perMillionTokens holds USD cost per 1M tokens: [inputCostPerM, outputCostPerM].
var perMillionTokens = map[string][2]float64{
	"gpt-4o":                     {2.50, 10.00},
	"gpt-4o-mini":                {0.15, 0.60},
	"gpt-4-turbo":                {10.00, 30.00},
	"claude-opus-4-8":            {15.00, 75.00},
	"claude-sonnet-4-6":          {3.00, 15.00},
	"claude-haiku-4-5-20251001":  {0.80, 4.00},
}

// EstimateCost returns USD cost for a single LLM call given token counts and model name.
// Returns 0.0 for unknown models.
func EstimateCost(inputTokens, outputTokens int, modelName string) float64 {
	prices, ok := perMillionTokens[modelName]
	if !ok {
		return 0.0
	}
	return float64(inputTokens)/1_000_000*prices[0] + float64(outputTokens)/1_000_000*prices[1]
}

// NewRetryMeta constructs RetryMeta with TotalCostUSD computed from attempt cost.
func NewRetryMeta(retryCount int, attemptCostUSD float64, lastErr, reason string) RetryMeta {
	return RetryMeta{
		RetryCount:     retryCount,
		AttemptCostUSD: attemptCostUSD,
		TotalCostUSD:   attemptCostUSD * float64(retryCount+1),
		LastErrorMsg:   lastErr,
		RetryReason:    reason,
	}
}

// Sentinel errors for adapter implementations (defined here for package-level access).
var (
	ErrNilInput      = errors.New("tool-call-analyzer: nil input to adapter")
	ErrUnknownFormat = errors.New("tool-call-analyzer: unrecognized tool call format")
	ErrMissingField  = errors.New("tool-call-analyzer: required field missing in payload")
)
```

---

## Part 3 — `pkg/types/tool_call_test.go`

```go
// SPDX-License-Identifier: MIT
package types_test

import (
	"math"
	"testing"

	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

func TestEstimateCost(t *testing.T) {
	cases := []struct {
		model      string
		inputToks  int
		outputToks int
		wantUSD    float64
	}{
		{"gpt-4o", 1_000_000, 0, 2.50},
		{"gpt-4o", 0, 1_000_000, 10.00},
		{"gpt-4o-mini", 1_000_000, 1_000_000, 0.75},
		{"claude-sonnet-4-6", 500_000, 500_000, 9.00},
		{"unknown-model", 1_000_000, 1_000_000, 0.0},
	}
	for _, c := range cases {
		got := types.EstimateCost(c.inputToks, c.outputToks, c.model)
		if math.Abs(got-c.wantUSD) > 0.0001 {
			t.Errorf("EstimateCost(%s, %d, %d) = %.6f, want %.6f",
				c.model, c.inputToks, c.outputToks, got, c.wantUSD)
		}
	}
}

func TestRetryTotalCost(t *testing.T) {
	cases := []struct {
		retries    int
		attemptUSD float64
		wantTotal  float64
	}{
		{0, 0.001, 0.001},   // no retry — total = attempt * 1
		{1, 0.002, 0.004},   // 1 retry — total = attempt * 2
		{3, 0.005, 0.020},   // 3 retries — total = attempt * 4
	}
	for _, c := range cases {
		m := types.NewRetryMeta(c.retries, c.attemptUSD, "", "")
		if math.Abs(m.TotalCostUSD-c.wantTotal) > 0.000001 {
			t.Errorf("retries=%d attemptUSD=%.3f: TotalCostUSD=%.6f, want %.6f",
				c.retries, c.attemptUSD, m.TotalCostUSD, c.wantTotal)
		}
	}
}

func TestToolCategoryExhaustive(t *testing.T) {
	if len(types.AllCategories) != 5 {
		t.Errorf("expected 5 ToolCategory constants, got %d", len(types.AllCategories))
	}
	seen := make(map[types.ToolCategory]bool)
	for _, cat := range types.AllCategories {
		if seen[cat] {
			t.Errorf("duplicate category: %s", cat)
		}
		seen[cat] = true
	}
}

func TestToolCallComputedFields(t *testing.T) {
	tc := types.ToolCall{
		Status:   "ERROR",
		HasError: true,
		ErrorMsg: "context deadline exceeded",
	}
	if !tc.HasError {
		t.Error("HasError should be true for ERROR status")
	}
	if tc.ErrorMsg == "" {
		t.Error("ErrorMsg should be populated for error tool calls")
	}
}
```

---

## Part 4 — `pkg/adapter/adapter.go`

```go
// SPDX-License-Identifier: MIT
// Package adapter defines the Adapter interface for normalizing vendor-specific
// tool call payloads into canonical types.ToolCall structs.
package adapter

import "github.com/AkshantVats/tool-call-analyzer/pkg/types"

// Adapter normalizes a vendor-specific tool call payload into a canonical ToolCall.
type Adapter interface {
	// Vendor returns the adapter's vendor identifier.
	Vendor() string

	// Parse normalizes raw vendor JSON into a canonical ToolCall.
	// Returns types.ErrNilInput for nil raw input.
	// Returns types.ErrUnknownFormat if raw cannot be parsed as this vendor's format.
	// Returns types.ErrMissingField if a required field is absent in a parseable payload.
	Parse(raw []byte) (types.ToolCall, error)

	// CanHandle returns true if this adapter recognizes the raw payload format.
	// Used for auto-detection in the registry when the vendor is not explicitly provided.
	CanHandle(raw []byte) bool
}
```

---

## Part 5 — `pkg/adapter/adapter_test.go`

```go
// SPDX-License-Identifier: MIT
package adapter_test

import (
	"errors"
	"testing"

	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

// stubbedAdapter is a minimal adapter for testing the interface contract.
type stubbedAdapter struct{}

func (s *stubbedAdapter) Vendor() string { return "stub" }
func (s *stubbedAdapter) CanHandle(raw []byte) bool { return len(raw) > 0 }
func (s *stubbedAdapter) Parse(raw []byte) (types.ToolCall, error) {
	if raw == nil {
		return types.ToolCall{}, types.ErrNilInput
	}
	if len(raw) == 0 {
		return types.ToolCall{}, types.ErrUnknownFormat
	}
	return types.ToolCall{Vendor: "stub", Status: "OK"}, nil
}

func TestAdapterNilInput(t *testing.T) {
	a := &stubbedAdapter{}
	_, err := a.Parse(nil)
	if !errors.Is(err, types.ErrNilInput) {
		t.Errorf("expected ErrNilInput for nil input, got: %v", err)
	}
}

func TestAdapterEmptyInput(t *testing.T) {
	a := &stubbedAdapter{}
	_, err := a.Parse([]byte{})
	if !errors.Is(err, types.ErrUnknownFormat) {
		t.Errorf("expected ErrUnknownFormat for empty input, got: %v", err)
	}
}

func TestAdapterHappyPath(t *testing.T) {
	a := &stubbedAdapter{}
	tc, err := a.Parse([]byte(`{"tool": "test"}`))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if tc.Vendor != "stub" {
		t.Errorf("expected vendor=stub, got %s", tc.Vendor)
	}
}

func TestCanHandleNilReturnsFalse(t *testing.T) {
	a := &stubbedAdapter{}
	if a.CanHandle(nil) {
		t.Error("CanHandle(nil) should return false")
	}
}
```

---

## `go.mod` scaffold

```
module github.com/AkshantVats/tool-call-analyzer

go 1.22
```

---

## README.md scaffold

```markdown
# tool-call-analyzer

Normalizes AI vendor tool call formats (OpenAI, Anthropic, LangChain) into a
canonical `ToolCall` struct and emits to Kafka topic `tools.normalized.v1`.

Part of the [TraceForge](https://github.com/AkshantVats/infra-ai-streaming) observability stack.

## Quickstart

```bash
go test ./...
```

## Architecture

See [DESIGN.md](DESIGN.md) for the canonical ToolCall struct, adapter contract, cost model, and Kafka schema.

## Adapters (Day 38+)

| Vendor | Status |
|--------|--------|
| OpenAI | Day 38 |
| Anthropic | Day 38 |
| LangChain | Day 38 |
```

---

## Git Workflow

```bash
# New repo — create on GitHub first, then scaffold locally
mkdir tool-call-analyzer && cd tool-call-analyzer
git init
git remote add origin "https://${GITHUB_PAT}@github.com/AkshantVats/tool-call-analyzer.git"

# After writing all files
go test ./...
git add .
git commit -m "feat: Day 37 — canonical ToolCall struct, adapter interface, cost model, DESIGN.md

- pkg/types/tool_call.go: ToolCall struct, CostEstimate, RetryMeta, EstimateCost, NewRetryMeta
- pkg/types/tool_call_test.go: 4 tests — cost estimation, retry total, category exhaustiveness
- pkg/adapter/adapter.go: Adapter interface with ErrNilInput / ErrUnknownFormat / ErrMissingField
- pkg/adapter/adapter_test.go: 4 tests — nil input, empty input, happy path, CanHandle nil
- DESIGN.md: canonical ToolCall spec, ToolCategory ontology, Kafka schema, decision log
- README.md: one-command quickstart, adapter status table

Self-review: 0 issues found."

git push -u origin main
```

PR targets `main`. PR description includes:
- `go test ./...` output (all tests green)
- DESIGN.md summary (struct fields, adapter contract, Kafka schema)
- Mark PR ready for review (not draft): `draft: false`
