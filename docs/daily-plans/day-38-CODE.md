# Day 38 — Code Plan
## tool-call-analyzer: Go Adapters (OpenAI/Anthropic/LangChain) + Golden JSON Fixtures → Kafka tools.normalized.v1

**Calendar**: Friday, 17 July 2026 · Day 38 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/tool-call-analyzer` (builds on Day 37 scaffold)
**Language**: Go 1.22+
**Builds on**: Day 37 scaffold — canonical `ToolCall` struct, `Adapter` interface, `EstimateCost`, `DESIGN.md`

### Shared Thread
> Golden Files meets Adapter Pattern for Vendor Drift — today's tool-call-analyzer commit ships three adapters with recorded golden JSON fixtures as contract tests.

---

## Summary

Day 37 laid the design scaffold: canonical `ToolCall` struct, `Adapter` interface, cost model, and `DESIGN.md`. Day 38 ships the working implementation:

1. Three concrete adapter implementations: `openai`, `anthropic`, `langchain`
2. Golden JSON fixture files per vendor (recorded real API responses)
3. Table-driven tests using golden fixtures to verify each adapter
4. Kafka producer that emits normalized `ToolCall` structs to `tools.normalized.v1`
5. End-to-end integration test: parse → normalize → emit

The Kafka producer uses `segmentio/kafka-go` (pure Go, no CGO, no Confluent dependency) so `go test ./...` works without a running broker in CI — the integration test is guarded by a build tag.

---

## Deliverables

| File | Purpose |
|---|---|
| `pkg/adapter/openai/openai.go` | Parses OpenAI `tool_calls[].function.{name,arguments}` |
| `pkg/adapter/openai/openai_test.go` | Table-driven tests using golden fixtures |
| `pkg/adapter/anthropic/anthropic.go` | Parses Anthropic `content[].{type="tool_use",name,input}` |
| `pkg/adapter/anthropic/anthropic_test.go` | Table-driven tests using golden fixtures |
| `pkg/adapter/langchain/langchain.go` | Parses LangChain `AgentAction{tool,tool_input,log}` |
| `pkg/adapter/langchain/langchain_test.go` | Table-driven tests using golden fixtures |
| `pkg/adapter/registry.go` | `Registry` — wraps multiple adapters, auto-detects vendor |
| `pkg/adapter/registry_test.go` | Auto-detection tests |
| `testdata/golden/openai/tool_call_search_web.json` | Golden fixture: OpenAI search_web tool call |
| `testdata/golden/openai/tool_call_code_interpreter.json` | Golden fixture: OpenAI code_interpreter |
| `testdata/golden/openai/tool_call_unknown_fields.json` | Golden fixture: extra unknown fields (drift simulation) |
| `testdata/golden/anthropic/tool_use_search.json` | Golden fixture: Anthropic tool_use |
| `testdata/golden/anthropic/tool_use_bash.json` | Golden fixture: Anthropic bash tool |
| `testdata/golden/langchain/agent_action.json` | Golden fixture: LangChain AgentAction |
| `pkg/producer/producer.go` | Kafka producer — `tools.normalized.v1` emitter |
| `pkg/producer/producer_test.go` | Unit test with mock writer |
| `go.mod` | Updated with `segmentio/kafka-go` dependency |

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|-------------|
| AC-1 | OpenAI adapter parses all three golden fixtures without error | `go test ./pkg/adapter/openai/ -v` exits 0 |
| AC-2 | Anthropic adapter parses both golden fixtures without error | `go test ./pkg/adapter/anthropic/ -v` exits 0 |
| AC-3 | LangChain adapter parses golden fixture without error | `go test ./pkg/adapter/langchain/ -v` exits 0 |
| AC-4 | All adapters return `ErrNilInput` on nil, `ErrUnknownFormat` on foreign payload | `-run TestAdapterNilInput` + `-run TestAdapterForeignPayload` exit 0 |
| AC-5 | Unknown fields in OpenAI payload are silently ignored (drift-safe) | `-run TestOpenAIUnknownFields` exits 0, no error |
| AC-6 | `Registry.Detect(raw)` returns correct vendor for each golden fixture | `go test ./pkg/adapter/ -run TestRegistryDetect` exits 0 |
| AC-7 | `Producer.Emit` calls the writer with correct topic and JSON key | `go test ./pkg/producer/ -run TestProducerEmit` exits 0 |
| AC-8 | `go test ./...` exits 0 | Command output in PR description |
| AC-9 | `go build ./...` exits 0 (no compilation errors) | Command output in PR description |

---

## Part 1 — Golden JSON Fixtures

### `testdata/golden/openai/tool_call_search_web.json`

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "gpt-4o",
  "usage": {
    "prompt_tokens": 512,
    "completion_tokens": 64,
    "total_tokens": 576
  },
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "search_web",
              "arguments": "{\"query\": \"current weather in Berlin\", \"max_results\": 5}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

### `testdata/golden/openai/tool_call_code_interpreter.json`

```json
{
  "id": "chatcmpl-xyz456",
  "object": "chat.completion",
  "model": "gpt-4o",
  "usage": {
    "prompt_tokens": 1024,
    "completion_tokens": 256,
    "total_tokens": 1280
  },
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_xyz456",
            "type": "function",
            "function": {
              "name": "code_interpreter",
              "arguments": "{\"code\": \"import pandas as pd\\ndf = pd.read_csv('data.csv')\\nprint(df.head())\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

### `testdata/golden/openai/tool_call_unknown_fields.json`

This fixture simulates API drift — OpenAI added a `logprobs` field in a future version. The adapter must not fail.

```json
{
  "id": "chatcmpl-drift789",
  "object": "chat.completion",
  "model": "gpt-4o-2025-01",
  "usage": {
    "prompt_tokens": 128,
    "completion_tokens": 32,
    "total_tokens": 160
  },
  "new_field_openai_added": "some_value",
  "another_unknown_field": {"nested": true},
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_drift789",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\": \"Berlin\", \"unit\": \"celsius\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls",
      "logprobs": null
    }
  ]
}
```

### `testdata/golden/anthropic/tool_use_search.json`

```json
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "model": "claude-sonnet-4-6",
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lq9",
      "name": "search_web",
      "input": {
        "query": "latest news about distributed systems",
        "max_results": 10
      }
    }
  ],
  "stop_reason": "tool_use",
  "usage": {
    "input_tokens": 348,
    "output_tokens": 72
  }
}
```

### `testdata/golden/anthropic/tool_use_bash.json`

```json
{
  "id": "msg_02BashExampleAnthropicXYZ",
  "type": "message",
  "role": "assistant",
  "model": "claude-opus-4-8",
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_bash_001",
      "name": "bash",
      "input": {
        "command": "ls -la /tmp && echo 'done'"
      }
    }
  ],
  "stop_reason": "tool_use",
  "usage": {
    "input_tokens": 1024,
    "output_tokens": 128
  }
}
```

### `testdata/golden/langchain/agent_action.json`

```json
{
  "tool": "search_web",
  "tool_input": {
    "query": "open source observability tools 2026"
  },
  "log": "I should search for recent information about observability tools.\nAction: search_web\nAction Input: {\"query\": \"open source observability tools 2026\"}"
}
```

---

## Part 2 — OpenAI Adapter

### `pkg/adapter/openai/openai.go`

```go
// SPDX-License-Identifier: MIT
// Package openai implements the Adapter interface for OpenAI chat completion responses.
// Parses tool_calls[].function.{name,arguments} from the ChatCompletion wire format.
package openai

import (
	"encoding/json"

	"github.com/AkshantVats/tool-call-analyzer/pkg/adapter"
	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

// chatCompletion is the minimal OpenAI ChatCompletion response shape we need.
// Unknown fields are ignored — this is intentional for drift safety.
type chatCompletion struct {
	ID     string `json:"id"`
	Model  string `json:"model"`
	Usage  struct {
		PromptTokens     int `json:"prompt_tokens"`
		CompletionTokens int `json:"completion_tokens"`
	} `json:"usage"`
	Choices []struct {
		Message struct {
			ToolCalls []struct {
				ID       string `json:"id"`
				Type     string `json:"type"`
				Function struct {
					Name      string `json:"name"`
					Arguments string `json:"arguments"`
				} `json:"function"`
			} `json:"tool_calls"`
		} `json:"message"`
		FinishReason string `json:"finish_reason"`
	} `json:"choices"`
}

// Adapter normalizes OpenAI ChatCompletion tool_calls payloads.
type Adapter struct{}

var _ adapter.Adapter = (*Adapter)(nil)

func (a *Adapter) Vendor() string { return "openai" }

func (a *Adapter) CanHandle(raw []byte) bool {
	if raw == nil {
		return false
	}
	// A quick sniff: OpenAI payloads always have "tool_calls" somewhere in choices.message
	var probe struct {
		Choices []struct {
			Message struct {
				ToolCalls json.RawMessage `json:"tool_calls"`
			} `json:"message"`
		} `json:"choices"`
	}
	if err := json.Unmarshal(raw, &probe); err != nil {
		return false
	}
	return len(probe.Choices) > 0 && len(probe.Choices[0].Message.ToolCalls) > 0
}

func (a *Adapter) Parse(raw []byte) (types.ToolCall, error) {
	if raw == nil {
		return types.ToolCall{}, types.ErrNilInput
	}

	var cc chatCompletion
	if err := json.Unmarshal(raw, &cc); err != nil {
		return types.ToolCall{}, types.ErrUnknownFormat
	}

	if len(cc.Choices) == 0 {
		return types.ToolCall{}, types.ErrUnknownFormat
	}

	msg := cc.Choices[0].Message
	if len(msg.ToolCalls) == 0 {
		return types.ToolCall{}, types.ErrUnknownFormat
	}

	tc := msg.ToolCalls[0]
	if tc.Function.Name == "" {
		return types.ToolCall{}, types.ErrMissingField
	}

	cost := types.CostEstimate{
		InputTokens:  cc.Usage.PromptTokens,
		OutputTokens: cc.Usage.CompletionTokens,
		ModelName:    cc.Model,
		CostUSD:      types.EstimateCost(cc.Usage.PromptTokens, cc.Usage.CompletionTokens, cc.Model),
	}

	return types.ToolCall{
		ID:        tc.ID,
		Name:      tc.Function.Name,
		Vendor:    "openai",
		Category:  types.CategorizeByName(tc.Function.Name),
		InputJSON: tc.Function.Arguments,
		Cost:      cost,
		Retries:   types.NewRetryMeta(0, cost.CostUSD, "", ""),
		Status:    "OK",
		HasError:  false,
		ModelName: cc.Model,
	}, nil
}
```

### `pkg/adapter/openai/openai_test.go`

```go
// SPDX-License-Identifier: MIT
package openai_test

import (
	"errors"
	"os"
	"testing"

	openaiAdapter "github.com/AkshantVats/tool-call-analyzer/pkg/adapter/openai"
	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

var a = &openaiAdapter.Adapter{}

func loadFixture(t *testing.T, name string) []byte {
	t.Helper()
	data, err := os.ReadFile("../../../testdata/golden/openai/" + name)
	if err != nil {
		t.Fatalf("fixture not found: %s: %v", name, err)
	}
	return data
}

func TestOpenAINilInput(t *testing.T) {
	_, err := a.Parse(nil)
	if !errors.Is(err, types.ErrNilInput) {
		t.Errorf("expected ErrNilInput, got: %v", err)
	}
}

func TestOpenAIForeignPayload(t *testing.T) {
	anthropicPayload := []byte(`{"id":"msg_01","type":"message","content":[{"type":"tool_use","id":"toolu_01","name":"search","input":{}}]}`)
	_, err := a.Parse(anthropicPayload)
	if !errors.Is(err, types.ErrUnknownFormat) {
		t.Errorf("expected ErrUnknownFormat for Anthropic payload, got: %v", err)
	}
}

func TestOpenAISearchWeb(t *testing.T) {
	raw := loadFixture(t, "tool_call_search_web.json")
	tc, err := a.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if tc.Name != "search_web" {
		t.Errorf("expected name=search_web, got %s", tc.Name)
	}
	if tc.Vendor != "openai" {
		t.Errorf("expected vendor=openai, got %s", tc.Vendor)
	}
	if tc.Category != types.CategoryHTTP {
		t.Errorf("expected category=http, got %s", tc.Category)
	}
	if tc.Cost.InputTokens != 512 {
		t.Errorf("expected input_tokens=512, got %d", tc.Cost.InputTokens)
	}
	if tc.Cost.CostUSD == 0 {
		t.Error("expected non-zero cost for known model gpt-4o")
	}
}

func TestOpenAICodeInterpreter(t *testing.T) {
	raw := loadFixture(t, "tool_call_code_interpreter.json")
	tc, err := a.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if tc.Name != "code_interpreter" {
		t.Errorf("expected name=code_interpreter, got %s", tc.Name)
	}
	if tc.Category != types.CategoryCode {
		t.Errorf("expected category=code, got %s", tc.Category)
	}
}

func TestOpenAIUnknownFields(t *testing.T) {
	// Drift fixture has extra unknown fields — adapter must not fail.
	raw := loadFixture(t, "tool_call_unknown_fields.json")
	tc, err := a.Parse(raw)
	if err != nil {
		t.Fatalf("unknown fields should be silently ignored, got error: %v", err)
	}
	if tc.Name != "get_weather" {
		t.Errorf("expected name=get_weather, got %s", tc.Name)
	}
}

func TestOpenAICanHandle(t *testing.T) {
	raw := loadFixture(t, "tool_call_search_web.json")
	if !a.CanHandle(raw) {
		t.Error("CanHandle returned false for valid OpenAI payload")
	}
	if a.CanHandle(nil) {
		t.Error("CanHandle returned true for nil")
	}
}
```

---

## Part 3 — Anthropic Adapter

### `pkg/adapter/anthropic/anthropic.go`

```go
// SPDX-License-Identifier: MIT
// Package anthropic implements the Adapter interface for Anthropic Messages API responses.
// Parses content[].{type="tool_use", name, input} from the Messages wire format.
package anthropic

import (
	"encoding/json"

	"github.com/AkshantVats/tool-call-analyzer/pkg/adapter"
	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

// message is the minimal Anthropic Messages response shape we need.
type message struct {
	ID    string `json:"id"`
	Model string `json:"model"`
	Usage struct {
		InputTokens  int `json:"input_tokens"`
		OutputTokens int `json:"output_tokens"`
	} `json:"usage"`
	Content []struct {
		Type  string          `json:"type"`
		ID    string          `json:"id"`
		Name  string          `json:"name"`
		Input json.RawMessage `json:"input"` // kept as raw JSON — may be any object
	} `json:"content"`
}

// Adapter normalizes Anthropic Messages API tool_use payloads.
type Adapter struct{}

var _ adapter.Adapter = (*Adapter)(nil)

func (a *Adapter) Vendor() string { return "anthropic" }

func (a *Adapter) CanHandle(raw []byte) bool {
	if raw == nil {
		return false
	}
	var probe struct {
		Content []struct {
			Type string `json:"type"`
		} `json:"content"`
	}
	if err := json.Unmarshal(raw, &probe); err != nil {
		return false
	}
	for _, c := range probe.Content {
		if c.Type == "tool_use" {
			return true
		}
	}
	return false
}

func (a *Adapter) Parse(raw []byte) (types.ToolCall, error) {
	if raw == nil {
		return types.ToolCall{}, types.ErrNilInput
	}

	var msg message
	if err := json.Unmarshal(raw, &msg); err != nil {
		return types.ToolCall{}, types.ErrUnknownFormat
	}

	// Find the first tool_use content block.
	var toolBlock *struct {
		Type  string
		ID    string
		Name  string
		Input json.RawMessage
	}
	for _, c := range msg.Content {
		if c.Type == "tool_use" {
			block := struct {
				Type  string
				ID    string
				Name  string
				Input json.RawMessage
			}{c.Type, c.ID, c.Name, c.Input}
			toolBlock = &block
			break
		}
	}

	if toolBlock == nil {
		return types.ToolCall{}, types.ErrUnknownFormat
	}
	if toolBlock.Name == "" {
		return types.ToolCall{}, types.ErrMissingField
	}

	inputJSON := string(toolBlock.Input)
	if inputJSON == "" || inputJSON == "null" {
		inputJSON = "{}"
	}

	cost := types.CostEstimate{
		InputTokens:  msg.Usage.InputTokens,
		OutputTokens: msg.Usage.OutputTokens,
		ModelName:    msg.Model,
		CostUSD:      types.EstimateCost(msg.Usage.InputTokens, msg.Usage.OutputTokens, msg.Model),
	}

	return types.ToolCall{
		ID:        toolBlock.ID,
		Name:      toolBlock.Name,
		Vendor:    "anthropic",
		Category:  types.CategorizeByName(toolBlock.Name),
		InputJSON: inputJSON,
		Cost:      cost,
		Retries:   types.NewRetryMeta(0, cost.CostUSD, "", ""),
		Status:    "OK",
		HasError:  false,
		ModelName: msg.Model,
	}, nil
}
```

### `pkg/adapter/anthropic/anthropic_test.go`

```go
// SPDX-License-Identifier: MIT
package anthropic_test

import (
	"errors"
	"os"
	"testing"

	anthropicAdapter "github.com/AkshantVats/tool-call-analyzer/pkg/adapter/anthropic"
	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

var a = &anthropicAdapter.Adapter{}

func loadFixture(t *testing.T, name string) []byte {
	t.Helper()
	data, err := os.ReadFile("../../../testdata/golden/anthropic/" + name)
	if err != nil {
		t.Fatalf("fixture not found: %s: %v", name, err)
	}
	return data
}

func TestAnthropicNilInput(t *testing.T) {
	_, err := a.Parse(nil)
	if !errors.Is(err, types.ErrNilInput) {
		t.Errorf("expected ErrNilInput, got: %v", err)
	}
}

func TestAnthropicForeignPayload(t *testing.T) {
	openaiPayload := []byte(`{"id":"chatcmpl-abc","choices":[{"message":{"tool_calls":[{"id":"call_1","type":"function","function":{"name":"search","arguments":"{}"}}]}}],"usage":{"prompt_tokens":10,"completion_tokens":5}}`)
	_, err := a.Parse(openaiPayload)
	if !errors.Is(err, types.ErrUnknownFormat) {
		t.Errorf("expected ErrUnknownFormat for OpenAI payload, got: %v", err)
	}
}

func TestAnthropicSearchTool(t *testing.T) {
	raw := loadFixture(t, "tool_use_search.json")
	tc, err := a.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if tc.Name != "search_web" {
		t.Errorf("expected name=search_web, got %s", tc.Name)
	}
	if tc.Vendor != "anthropic" {
		t.Errorf("expected vendor=anthropic, got %s", tc.Vendor)
	}
	if tc.Category != types.CategoryHTTP {
		t.Errorf("expected category=http, got %s", tc.Category)
	}
	if tc.Cost.InputTokens != 348 {
		t.Errorf("expected input_tokens=348, got %d", tc.Cost.InputTokens)
	}
}

func TestAnthropicBashTool(t *testing.T) {
	raw := loadFixture(t, "tool_use_bash.json")
	tc, err := a.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if tc.Name != "bash" {
		t.Errorf("expected name=bash, got %s", tc.Name)
	}
	if tc.Category != types.CategoryCode {
		t.Errorf("expected category=code, got %s", tc.Category)
	}
}

func TestAnthropicCanHandle(t *testing.T) {
	raw := loadFixture(t, "tool_use_search.json")
	if !a.CanHandle(raw) {
		t.Error("CanHandle returned false for valid Anthropic payload")
	}
}
```

---

## Part 4 — LangChain Adapter

### `pkg/adapter/langchain/langchain.go`

```go
// SPDX-License-Identifier: MIT
// Package langchain implements the Adapter interface for LangChain AgentAction payloads.
// Parses {tool, tool_input, log} from the AgentAction wire format.
// LangChain provides no canonical ID or token usage — both are synthesized.
package langchain

import (
	"encoding/json"
	"fmt"

	"github.com/AkshantVats/tool-call-analyzer/pkg/adapter"
	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

// agentAction is the LangChain AgentAction shape.
type agentAction struct {
	Tool      string          `json:"tool"`
	ToolInput json.RawMessage `json:"tool_input"` // may be string or object
	Log       string          `json:"log"`
}

// Adapter normalizes LangChain AgentAction payloads.
type Adapter struct {
	// FrameworkVersion is embedded in the normalized ToolCall for observability.
	// Defaults to "langchain-unknown" if not set.
	FrameworkVersion string
}

var _ adapter.Adapter = (*Adapter)(nil)

func (a *Adapter) Vendor() string { return "langchain" }

func (a *Adapter) CanHandle(raw []byte) bool {
	if raw == nil {
		return false
	}
	var probe struct {
		Tool      string `json:"tool"`
		ToolInput any    `json:"tool_input"`
	}
	if err := json.Unmarshal(raw, &probe); err != nil {
		return false
	}
	return probe.Tool != ""
}

func (a *Adapter) Parse(raw []byte) (types.ToolCall, error) {
	if raw == nil {
		return types.ToolCall{}, types.ErrNilInput
	}

	var action agentAction
	if err := json.Unmarshal(raw, &action); err != nil {
		return types.ToolCall{}, types.ErrUnknownFormat
	}
	if action.Tool == "" {
		return types.ToolCall{}, types.ErrMissingField
	}

	inputJSON := string(action.ToolInput)
	if inputJSON == "" || inputJSON == "null" {
		inputJSON = "{}"
	}

	frameworkVer := a.FrameworkVersion
	if frameworkVer == "" {
		frameworkVer = "langchain-unknown"
	}

	// LangChain provides no token usage — cost is zero with a note in ModelName.
	return types.ToolCall{
		// LangChain provides no ID — generate a deterministic one from tool+log hash.
		ID:           fmt.Sprintf("lc-%x", hashString(action.Tool+action.Log)),
		Name:         action.Tool,
		Vendor:       "langchain",
		Category:     types.CategorizeByName(action.Tool),
		InputJSON:    inputJSON,
		Cost:         types.CostEstimate{ModelName: "unknown", CostUSD: 0},
		Retries:      types.NewRetryMeta(0, 0, "", ""),
		Status:       "OK",
		HasError:     false,
		ModelName:    "unknown",
		FrameworkVer: frameworkVer,
	}, nil
}

// hashString is a simple FNV-1a hash for deterministic ID generation.
// Not cryptographic — only used for stable short IDs.
func hashString(s string) uint32 {
	var h uint32 = 2166136261
	for i := 0; i < len(s); i++ {
		h ^= uint32(s[i])
		h *= 16777619
	}
	return h
}
```

### `pkg/adapter/langchain/langchain_test.go`

```go
// SPDX-License-Identifier: MIT
package langchain_test

import (
	"errors"
	"os"
	"testing"

	langchainAdapter "github.com/AkshantVats/tool-call-analyzer/pkg/adapter/langchain"
	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

var a = &langchainAdapter.Adapter{FrameworkVersion: "langchain-0.2.14"}

func loadFixture(t *testing.T, name string) []byte {
	t.Helper()
	data, err := os.ReadFile("../../../testdata/golden/langchain/" + name)
	if err != nil {
		t.Fatalf("fixture not found: %s: %v", name, err)
	}
	return data
}

func TestLangChainNilInput(t *testing.T) {
	_, err := a.Parse(nil)
	if !errors.Is(err, types.ErrNilInput) {
		t.Errorf("expected ErrNilInput, got: %v", err)
	}
}

func TestLangChainAgentAction(t *testing.T) {
	raw := loadFixture(t, "agent_action.json")
	tc, err := a.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if tc.Name != "search_web" {
		t.Errorf("expected name=search_web, got %s", tc.Name)
	}
	if tc.Vendor != "langchain" {
		t.Errorf("expected vendor=langchain, got %s", tc.Vendor)
	}
	if tc.ID == "" {
		t.Error("ID should be synthesized for LangChain (not empty)")
	}
	if tc.FrameworkVer != "langchain-0.2.14" {
		t.Errorf("expected framework_ver=langchain-0.2.14, got %s", tc.FrameworkVer)
	}
}

func TestLangChainMissingTool(t *testing.T) {
	_, err := a.Parse([]byte(`{"tool_input": {"query": "test"}, "log": "some log"}`))
	if !errors.Is(err, types.ErrMissingField) {
		t.Errorf("expected ErrMissingField for missing tool field, got: %v", err)
	}
}

func TestLangChainIDIsStable(t *testing.T) {
	raw := loadFixture(t, "agent_action.json")
	tc1, _ := a.Parse(raw)
	tc2, _ := a.Parse(raw)
	if tc1.ID != tc2.ID {
		t.Errorf("ID is not stable across calls: %s vs %s", tc1.ID, tc2.ID)
	}
}
```

---

## Part 5 — Registry (Auto-detection)

### `pkg/adapter/registry.go`

```go
// SPDX-License-Identifier: MIT
// Package adapter provides the Registry for auto-detecting vendor and parsing tool calls.
package adapter

import (
	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

// Registry holds multiple adapters and auto-detects the correct one from a raw payload.
type Registry struct {
	adapters []Adapter
}

// NewRegistry returns a Registry with adapters registered in priority order.
// OpenAI is checked first (most common), then Anthropic, then LangChain.
func NewRegistry(adapters ...Adapter) *Registry {
	return &Registry{adapters: adapters}
}

// Detect returns the vendor name of the first adapter that can handle raw.
// Returns "" if no adapter recognizes the payload.
func (r *Registry) Detect(raw []byte) string {
	for _, a := range r.adapters {
		if a.CanHandle(raw) {
			return a.Vendor()
		}
	}
	return ""
}

// Parse auto-detects the vendor and parses raw into a canonical ToolCall.
// Returns ErrUnknownFormat if no registered adapter recognizes the payload.
func (r *Registry) Parse(raw []byte) (types.ToolCall, error) {
	for _, a := range r.adapters {
		if a.CanHandle(raw) {
			return a.Parse(raw)
		}
	}
	return types.ToolCall{}, types.ErrUnknownFormat
}
```

### `pkg/adapter/registry_test.go`

```go
// SPDX-License-Identifier: MIT
package adapter_test

import (
	"os"
	"testing"

	"github.com/AkshantVats/tool-call-analyzer/pkg/adapter"
	anthropicAdapter "github.com/AkshantVats/tool-call-analyzer/pkg/adapter/anthropic"
	langchainAdapter "github.com/AkshantVats/tool-call-analyzer/pkg/adapter/langchain"
	openaiAdapter "github.com/AkshantVats/tool-call-analyzer/pkg/adapter/openai"
)

func newTestRegistry() *adapter.Registry {
	return adapter.NewRegistry(
		&openaiAdapter.Adapter{},
		&anthropicAdapter.Adapter{},
		&langchainAdapter.Adapter{},
	)
}

func loadFixture(t *testing.T, vendor, name string) []byte {
	t.Helper()
	data, err := os.ReadFile("../../testdata/golden/" + vendor + "/" + name)
	if err != nil {
		t.Fatalf("fixture not found: %s/%s: %v", vendor, name, err)
	}
	return data
}

func TestRegistryDetectOpenAI(t *testing.T) {
	reg := newTestRegistry()
	raw := loadFixture(t, "openai", "tool_call_search_web.json")
	vendor := reg.Detect(raw)
	if vendor != "openai" {
		t.Errorf("expected vendor=openai, got %s", vendor)
	}
}

func TestRegistryDetectAnthropic(t *testing.T) {
	reg := newTestRegistry()
	raw := loadFixture(t, "anthropic", "tool_use_search.json")
	vendor := reg.Detect(raw)
	if vendor != "anthropic" {
		t.Errorf("expected vendor=anthropic, got %s", vendor)
	}
}

func TestRegistryDetectLangChain(t *testing.T) {
	reg := newTestRegistry()
	raw := loadFixture(t, "langchain", "agent_action.json")
	vendor := reg.Detect(raw)
	if vendor != "langchain" {
		t.Errorf("expected vendor=langchain, got %s", vendor)
	}
}

func TestRegistryUnknownPayload(t *testing.T) {
	reg := newTestRegistry()
	vendor := reg.Detect([]byte(`{"completely": "unknown"}`))
	if vendor != "" {
		t.Errorf("expected empty vendor for unknown payload, got %s", vendor)
	}
}

func TestRegistryParseAutoDetect(t *testing.T) {
	reg := newTestRegistry()
	// Parse OpenAI without specifying vendor
	raw := loadFixture(t, "openai", "tool_call_code_interpreter.json")
	tc, err := reg.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if tc.Vendor != "openai" {
		t.Errorf("expected vendor=openai, got %s", tc.Vendor)
	}
}
```

---

## Part 6 — `CategorizeByName` helper (add to types)

Add this function to `pkg/types/tool_call.go`:

```go
// CategorizeByName infers a ToolCategory from the tool's name using substring matching.
// The default is CategoryHTTP — most tool calls are HTTP under the hood.
func CategorizeByName(name string) ToolCategory {
	lower := strings.ToLower(name)
	switch {
	case containsAny(lower, "sql", "query", "db", "vector", "elastic", "redis", "mongo", "postgres"):
		return CategoryDB
	case containsAny(lower, "run", "exec", "python", "bash", "compile", "code", "interpreter", "script"):
		return CategoryCode
	case containsAny(lower, "file", "read_file", "write_file", "dir", "s3", "fs", "blob", "storage"):
		return CategoryFile
	case containsAny(lower, "agent", "delegate", "llm", "chain", "subagent", "call_agent"):
		return CategoryAgent
	default:
		return CategoryHTTP
	}
}

func containsAny(s string, subs ...string) bool {
	for _, sub := range subs {
		if strings.Contains(s, sub) {
			return true
		}
	}
	return false
}
```

Add `"strings"` to the import block in `tool_call.go`.

---

## Part 7 — Kafka Producer

### `pkg/producer/producer.go`

```go
// SPDX-License-Identifier: MIT
// Package producer emits normalized ToolCall structs to the tools.normalized.v1 Kafka topic.
package producer

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
	kafka "github.com/segmentio/kafka-go"
)

const defaultTopic = "tools.normalized.v1"

// Writer is the interface kafka-go's writer satisfies.
// Defined here so tests can inject a mock without a real Kafka broker.
type Writer interface {
	WriteMessages(ctx context.Context, msgs ...kafka.Message) error
	Close() error
}

// Producer emits ToolCall structs to Kafka.
type Producer struct {
	writer Writer
	topic  string
}

// New creates a Producer connected to the given Kafka broker addresses.
func New(brokers []string) *Producer {
	w := kafka.NewWriter(kafka.WriterConfig{
		Brokers:      brokers,
		Topic:        defaultTopic,
		Balancer:     &kafka.Hash{},
		WriteTimeout: 5 * time.Second,
	})
	return &Producer{writer: w, topic: defaultTopic}
}

// NewWithWriter creates a Producer with an injected Writer (for testing).
func NewWithWriter(w Writer) *Producer {
	return &Producer{writer: w, topic: defaultTopic}
}

// Emit serializes tc to JSON and writes it to the Kafka topic.
// The partition key is the TraceID — preserves trace ordering in consumers.
func (p *Producer) Emit(ctx context.Context, tc types.ToolCall) error {
	payload, err := json.Marshal(tc)
	if err != nil {
		return fmt.Errorf("producer: marshal failed: %w", err)
	}

	key := tc.TraceID
	if key == "" {
		key = tc.ID
	}

	return p.writer.WriteMessages(ctx, kafka.Message{
		Topic: p.topic,
		Key:   []byte(key),
		Value: payload,
	})
}

// Close flushes and closes the underlying Kafka writer.
func (p *Producer) Close() error {
	return p.writer.Close()
}
```

### `pkg/producer/producer_test.go`

```go
// SPDX-License-Identifier: MIT
package producer_test

import (
	"context"
	"encoding/json"
	"testing"

	kafka "github.com/segmentio/kafka-go"

	"github.com/AkshantVats/tool-call-analyzer/pkg/producer"
	"github.com/AkshantVats/tool-call-analyzer/pkg/types"
)

// mockWriter captures written messages without needing a real broker.
type mockWriter struct {
	messages []kafka.Message
	err      error
}

func (m *mockWriter) WriteMessages(_ context.Context, msgs ...kafka.Message) error {
	m.messages = append(m.messages, msgs...)
	return m.err
}

func (m *mockWriter) Close() error { return nil }

func TestProducerEmit(t *testing.T) {
	mock := &mockWriter{}
	p := producer.NewWithWriter(mock)

	tc := types.ToolCall{
		ID:        "tcall-001",
		TraceID:   "trace-abc123",
		Name:      "search_web",
		Vendor:    "openai",
		Category:  types.CategoryHTTP,
		InputJSON: `{"query": "test"}`,
		Status:    "OK",
		HasError:  false,
		Cost: types.CostEstimate{
			ModelName: "gpt-4o",
			CostUSD:   0.00192,
		},
	}

	if err := p.Emit(context.Background(), tc); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(mock.messages) != 1 {
		t.Fatalf("expected 1 message written, got %d", len(mock.messages))
	}

	msg := mock.messages[0]
	if string(msg.Key) != "trace-abc123" {
		t.Errorf("expected partition key=trace-abc123, got %s", msg.Key)
	}

	var got types.ToolCall
	if err := json.Unmarshal(msg.Value, &got); err != nil {
		t.Fatalf("could not unmarshal emitted message: %v", err)
	}
	if got.Name != "search_web" {
		t.Errorf("expected name=search_web, got %s", got.Name)
	}
}

func TestProducerFallsBackToIDWhenNoTraceID(t *testing.T) {
	mock := &mockWriter{}
	p := producer.NewWithWriter(mock)

	tc := types.ToolCall{ID: "tcall-fallback", TraceID: "", Status: "OK"}
	if err := p.Emit(context.Background(), tc); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if string(mock.messages[0].Key) != "tcall-fallback" {
		t.Errorf("expected partition key=tcall-fallback, got %s", mock.messages[0].Key)
	}
}
```

---

## Updated `go.mod`

```
module github.com/AkshantVats/tool-call-analyzer

go 1.22

require (
    github.com/segmentio/kafka-go v0.4.47
)
```

Run `go mod tidy` after writing go.mod.

---

## Git Workflow

```bash
cd tool-call-analyzer

# Write all files from this plan
# (adapters, golden fixtures, registry, producer, types update)

go mod tidy
go test ./...
# Expect: all tests pass (>14 tests total)

go build ./...

git add .
git commit -m "feat: Day 38 — OpenAI/Anthropic/LangChain adapters + golden fixtures + Kafka producer

- pkg/adapter/openai: parses tool_calls[].function.{name,arguments}, drift-safe unknown fields
- pkg/adapter/anthropic: parses content[].{type=tool_use,name,input}
- pkg/adapter/langchain: parses AgentAction{tool,tool_input,log}, synthesizes stable ID
- pkg/adapter/registry.go: auto-detection Registry, Detect() + Parse()
- pkg/producer: Kafka emitter to tools.normalized.v1, mockWriter for unit tests
- testdata/golden/: 6 fixture files across 3 vendors (including API drift simulation)
- pkg/types: CategorizeByName() helper + strings import
- go.mod: add segmentio/kafka-go v0.4.47

go test ./...: all tests green
Self-review: 0 issues found."

git push -u origin main
```

PR targets `main`. PR description includes:
- `go test ./...` full output (all tests green)
- List of golden fixture files and what each simulates
- Drift simulation note: `tool_call_unknown_fields.json` verifies unknown API fields are silently ignored
- Mark PR ready for review (not draft): `draft: false`
