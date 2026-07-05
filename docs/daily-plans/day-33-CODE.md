# Day 33 — Code Plan
## agent-trace-collector — Go SDK: `StartSpan`/`EndSpan` + W3C Context Propagation

**Calendar**: Sunday, 6 July 2026 · Day 33 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` (traceforge/ subdirectory — continuing from Day 32)
**Language**: Go 1.22+
**Builds on**: Day 32 — Python SDK `traceforge.wrap_openai()`; Day 31 — HTTP ingest endpoint on `:8080`

### Shared Thread
> SDK Wrappers meets Context Propagation in Polyglot Agents in today's Go SDK commit.

---

## Summary

Day 33 ships the Go instrumentation layer for TraceForge. The Python SDK wraps OpenAI calls — the Go SDK wraps any outbound HTTP call or sub-agent invocation. Together they complete a cross-language trace: a Python agent calls a Go tool, the `traceparent` header carries the trace ID across the boundary, and the waterfall appears unbroken in Grafana.

Three deliverables:
1. **Go SDK core** — `StartSpan`/`EndSpan` with `context.Context` propagation and W3C TraceContext header inject/extract
2. **Kafka producer** — batch span emit to `agent-spans` Kafka topic (matching infra-ai-streaming producer pattern)
3. **Example agent** — `examples/weather_calc/main.go` showing a two-tool agent (weather + calculator) with a full multi-hop trace

---

## Deliverables

| File | Purpose |
|---|---|
| `traceforge/sdk/go/traceforge/span.go` | `Span` struct, context key, `NewSpan()` |
| `traceforge/sdk/go/traceforge/tracer.go` | `StartSpan()`, `EndSpan()`, `SpanFromContext()` |
| `traceforge/sdk/go/traceforge/propagation.go` | W3C `traceparent` inject/extract |
| `traceforge/sdk/go/traceforge/emit.go` | HTTP POST to collector + Kafka producer |
| `traceforge/sdk/go/traceforge/tracer_test.go` | Unit + integration tests |
| `traceforge/sdk/go/examples/weather_calc/main.go` | Example agent with two tools |
| `traceforge/sdk/go/go.mod` | Module manifest |

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|-------------|
| AC-1 | `StartSpan(ctx, "tool_name")` returns a new context with span embedded and a `*Span` | Unit test |
| AC-2 | `EndSpan(span, StatusOK, nil)` sets `latency_ms` and emits to collector via HTTP | Integration test with mock server |
| AC-3 | `InjectTraceContext(ctx, http.Header)` writes a valid `traceparent` header | Unit test |
| AC-4 | `ExtractTraceContext(ctx, http.Header)` reads `traceparent` and sets `trace_id`+`parent_span_id` on the context span | Unit test |
| AC-5 | Kafka producer sends spans as JSON to `agent-spans` topic; configurable via `TRACEFORGE_KAFKA_BROKERS` | Unit test with mock Kafka writer |
| AC-6 | Example agent produces a 3-span trace (root + weather + calculator) with connected `parent_span_id` chain | Manual run output in PR description |
| AC-7 | `go test ./traceforge/sdk/go/...` exits 0 | Command output in PR description |

---

## Part 1 — Span Struct (`span.go`)

```go
// SPDX-License-Identifier: MIT
package traceforge

import (
	"crypto/rand"
	"encoding/hex"
	"time"
)

// ToolKind categorises the type of work a span represents.
type ToolKind string

const (
	ToolKindModelCall  ToolKind = "model_call"
	ToolKindRetrieval  ToolKind = "retrieval"
	ToolKindCodeExec   ToolKind = "code_execution"
	ToolKindHTTP       ToolKind = "http"
	ToolKindSubAgent   ToolKind = "sub_agent"
	ToolKindUnknown    ToolKind = "unknown"
)

// SpanStatus mirrors OpenTelemetry status codes.
type SpanStatus string

const (
	StatusOK    SpanStatus = "OK"
	StatusError SpanStatus = "ERROR"
	StatusUnset SpanStatus = "UNSET"
)

// Span holds telemetry for one unit of work inside an agent trace.
type Span struct {
	TraceID      string            `json:"trace_id"`
	SpanID       string            `json:"span_id"`
	ParentSpanID string            `json:"parent_span_id,omitempty"`
	ToolName     string            `json:"tool_name"`
	ToolKind     ToolKind          `json:"tool_kind"`
	Model        string            `json:"model,omitempty"`
	Status       SpanStatus        `json:"status"`
	StartTime    string            `json:"start_time"`   // RFC3339 UTC
	LatencyMs    int64             `json:"latency_ms"`
	InputTokens  int               `json:"input_tokens"`
	OutputTokens int               `json:"output_tokens"`
	TotalTokens  int               `json:"total_tokens"`
	CostUSD      float64           `json:"cost_usd"`
	ErrorMessage string            `json:"error_message,omitempty"`
	Attributes   map[string]string `json:"attributes,omitempty"`

	startWall time.Time // unexported; used by EndSpan
}

// NewTraceID generates a random 128-bit trace ID as a 32-char hex string.
func NewTraceID() string {
	return randomHex(16)
}

// NewSpanID generates a random 64-bit span ID as a 16-char hex string.
func NewSpanID() string {
	return randomHex(8)
}

func randomHex(n int) string {
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		panic("traceforge: crypto/rand unavailable: " + err.Error())
	}
	return hex.EncodeToString(b)
}
```

---

## Part 2 — Tracer (`tracer.go`)

```go
// SPDX-License-Identifier: MIT
package traceforge

import (
	"context"
	"time"
)

type contextKey struct{}

// StartSpan creates a new span under the current trace in ctx.
// If ctx carries no trace, a fresh trace ID is generated.
// Returns the enriched context and the mutable *Span.
func StartSpan(ctx context.Context, toolName string, opts ...SpanOption) (context.Context, *Span) {
	parent, _ := SpanFromContext(ctx)

	traceID := NewTraceID()
	parentID := ""
	if parent != nil && parent.TraceID != "" {
		traceID = parent.TraceID
		parentID = parent.SpanID
	}

	s := &Span{
		TraceID:      traceID,
		SpanID:       NewSpanID(),
		ParentSpanID: parentID,
		ToolName:     toolName,
		ToolKind:     ToolKindUnknown,
		Status:       StatusUnset,
		Attributes:   make(map[string]string),
		startWall:    time.Now().UTC(),
	}
	s.StartTime = s.startWall.Format(time.RFC3339Nano)

	for _, o := range opts {
		o(s)
	}

	return context.WithValue(ctx, contextKey{}, s), s
}

// EndSpan records latency, applies status/error, and emits the span.
// Call deferred immediately after StartSpan.
func EndSpan(span *Span, status SpanStatus, err error, emitters ...Emitter) {
	span.Status = status
	span.LatencyMs = time.Since(span.startWall).Milliseconds()
	if err != nil {
		span.ErrorMessage = err.Error()
		span.Status = StatusError
	}
	for _, e := range emitters {
		_ = e.Emit(span) // non-blocking; errors logged inside Emitter
	}
}

// SpanFromContext retrieves the active span from ctx (nil if absent).
func SpanFromContext(ctx context.Context) (*Span, bool) {
	s, ok := ctx.Value(contextKey{}).(*Span)
	return s, ok && s != nil
}

// SpanOption is a functional option for StartSpan.
type SpanOption func(*Span)

// WithToolKind sets the tool kind on the span.
func WithToolKind(k ToolKind) SpanOption {
	return func(s *Span) { s.ToolKind = k }
}

// WithModel sets the model field (for LLM calls).
func WithModel(m string) SpanOption {
	return func(s *Span) { s.Model = m }
}

// WithAttribute attaches an arbitrary key-value attribute.
func WithAttribute(k, v string) SpanOption {
	return func(s *Span) { s.Attributes[k] = v }
}
```

---

## Part 3 — W3C TraceContext Propagation (`propagation.go`)

```go
// SPDX-License-Identifier: MIT
package traceforge

import (
	"context"
	"fmt"
	"net/http"
	"strings"
)

const traceparentHeader = "traceparent"

// InjectTraceContext writes the W3C traceparent header into h from the span in ctx.
// Format: 00-<traceId>-<spanId>-01
// No-op if ctx carries no active span.
func InjectTraceContext(ctx context.Context, h http.Header) {
	span, ok := SpanFromContext(ctx)
	if !ok || span.TraceID == "" {
		return
	}
	h.Set(traceparentHeader, fmt.Sprintf("00-%s-%s-01", span.TraceID, span.SpanID))
}

// ExtractTraceContext reads the traceparent header from h and returns a context
// with a new span that inherits the trace ID and uses the incoming span ID as parent.
// If the header is absent or malformed, ctx is returned unchanged.
func ExtractTraceContext(ctx context.Context, h http.Header) context.Context {
	v := h.Get(traceparentHeader)
	if v == "" {
		return ctx
	}
	parts := strings.Split(v, "-")
	if len(parts) != 4 {
		return ctx
	}
	traceID, parentSpanID := parts[1], parts[2]
	if len(traceID) != 32 || len(parentSpanID) != 16 {
		return ctx
	}
	placeholder := &Span{
		TraceID:      traceID,
		SpanID:       parentSpanID,
		ParentSpanID: "",
	}
	return context.WithValue(ctx, contextKey{}, placeholder)
}
```

---

## Part 4 — Emitters (`emit.go`)

```go
// SPDX-License-Identifier: MIT
package traceforge

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

// Emitter is any sink that can receive a span.
type Emitter interface {
	Emit(span *Span) error
}

// --- HTTP Emitter ---

// HTTPEmitter POSTs spans to the TraceForge collector over HTTP.
type HTTPEmitter struct {
	Endpoint string
	client   *http.Client
}

// NewHTTPEmitter creates an emitter targeting endpoint (defaults to $TRACEFORGE_ENDPOINT or localhost:8080).
func NewHTTPEmitter(endpoint string) *HTTPEmitter {
	if endpoint == "" {
		endpoint = os.Getenv("TRACEFORGE_ENDPOINT")
	}
	if endpoint == "" {
		endpoint = "http://localhost:8080/v1/spans"
	}
	return &HTTPEmitter{
		Endpoint: endpoint,
		client:   &http.Client{Timeout: 2 * time.Second},
	}
}

func (e *HTTPEmitter) Emit(span *Span) error {
	body, err := json.Marshal([]Span{*span})
	if err != nil {
		return err
	}
	resp, err := e.client.Post(e.Endpoint, "application/json", bytes.NewReader(body))
	if err != nil {
		log.Printf("traceforge: http emit failed: %v", err)
		return nil // non-blocking
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		log.Printf("traceforge: collector returned %d", resp.StatusCode)
	}
	return nil
}

// --- Kafka Emitter ---

// KafkaEmitter writes spans as JSON to a Kafka topic using a simple producer.
// Uses the same sarama-pattern as infra-ai-streaming's producer.
type KafkaEmitter struct {
	brokers []string
	topic   string
}

// NewKafkaEmitter creates a Kafka emitter. Brokers from TRACEFORGE_KAFKA_BROKERS (comma-separated) if empty.
func NewKafkaEmitter(brokers []string, topic string) *KafkaEmitter {
	if len(brokers) == 0 {
		raw := os.Getenv("TRACEFORGE_KAFKA_BROKERS")
		if raw == "" {
			raw = "localhost:9092"
		}
		for _, b := range splitComma(raw) {
			brokers = append(brokers, b)
		}
	}
	if topic == "" {
		topic = "agent-spans"
	}
	return &KafkaEmitter{brokers: brokers, topic: topic}
}

func (e *KafkaEmitter) Emit(span *Span) error {
	b, err := json.Marshal(span)
	if err != nil {
		return fmt.Errorf("traceforge kafka: marshal: %w", err)
	}
	// In production, reuse a sync.Producer. For the SDK, a single-message send is fine.
	return kafkaSendBytes(e.brokers, e.topic, []byte(span.TraceID), b)
}

func splitComma(s string) []string {
	var out []string
	for _, part := range bytes.Split([]byte(s), []byte(",")) {
		if t := bytes.TrimSpace(part); len(t) > 0 {
			out = append(out, string(t))
		}
	}
	return out
}
```

The Kafka send implementation (`kafkaSendBytes`) wraps `github.com/IBM/sarama` matching the producer pattern already established in `infra-ai-streaming/cmd/producer`. Create a thin internal helper to avoid duplicating sarama config:

```go
// internal/kafkautil/send.go (shared with infra-ai-streaming producer)
func kafkaSendBytes(brokers []string, topic string, key, value []byte) error {
    cfg := sarama.NewConfig()
    cfg.Producer.Return.Successes = true
    cfg.Producer.RequiredAcks = sarama.WaitForLocal
    p, err := sarama.NewSyncProducer(brokers, cfg)
    if err != nil {
        log.Printf("traceforge kafka: producer init: %v", err)
        return nil // non-blocking
    }
    defer p.Close()
    _, _, err = p.SendMessage(&sarama.ProducerMessage{
        Topic: topic,
        Key:   sarama.ByteEncoder(key),
        Value: sarama.ByteEncoder(value),
    })
    if err != nil {
        log.Printf("traceforge kafka: send: %v", err)
    }
    return nil
}
```

---

## Part 5 — Tests (`tracer_test.go`)

```go
// SPDX-License-Identifier: MIT
package traceforge_test

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/akshantvats/infra-ai-streaming/traceforge/sdk/go/traceforge"
)

// --- Context propagation ---

func TestStartSpanCreatesNewTrace(t *testing.T) {
	ctx, span := traceforge.StartSpan(context.Background(), "test_tool")
	if span.TraceID == "" {
		t.Fatal("expected non-empty trace_id")
	}
	if span.SpanID == "" {
		t.Fatal("expected non-empty span_id")
	}
	if span.ParentSpanID != "" {
		t.Fatalf("expected empty parent_span_id for root span, got %q", span.ParentSpanID)
	}
	got, ok := traceforge.SpanFromContext(ctx)
	if !ok || got.SpanID != span.SpanID {
		t.Fatal("span not retrievable from context")
	}
}

func TestChildSpanInheritsTraceID(t *testing.T) {
	ctx, root := traceforge.StartSpan(context.Background(), "root")
	_, child := traceforge.StartSpan(ctx, "child")

	if child.TraceID != root.TraceID {
		t.Fatalf("child trace_id %q != root trace_id %q", child.TraceID, root.TraceID)
	}
	if child.ParentSpanID != root.SpanID {
		t.Fatalf("child parent_span_id %q != root span_id %q", child.ParentSpanID, root.SpanID)
	}
}

func TestEndSpanRecordsLatency(t *testing.T) {
	_, span := traceforge.StartSpan(context.Background(), "slow_tool")
	traceforge.EndSpan(span, traceforge.StatusOK, nil)
	if span.LatencyMs < 0 {
		t.Fatalf("expected non-negative latency_ms, got %d", span.LatencyMs)
	}
	if span.Status != traceforge.StatusOK {
		t.Fatalf("expected StatusOK, got %q", span.Status)
	}
}

func TestEndSpanSetsErrorStatus(t *testing.T) {
	_, span := traceforge.StartSpan(context.Background(), "bad_tool")
	err := fmt.Errorf("something broke")
	traceforge.EndSpan(span, traceforge.StatusOK, err)
	if span.Status != traceforge.StatusError {
		t.Fatalf("expected StatusError on non-nil error, got %q", span.Status)
	}
	if span.ErrorMessage == "" {
		t.Fatal("expected error_message to be set")
	}
}

// --- W3C TraceContext ---

func TestInjectTraceContext(t *testing.T) {
	ctx, span := traceforge.StartSpan(context.Background(), "caller")
	h := http.Header{}
	traceforge.InjectTraceContext(ctx, h)

	tp := h.Get("traceparent")
	if tp == "" {
		t.Fatal("expected traceparent header")
	}
	parts := strings.Split(tp, "-")
	if len(parts) != 4 {
		t.Fatalf("expected 4 parts in traceparent, got %d: %q", len(parts), tp)
	}
	if parts[1] != span.TraceID {
		t.Fatalf("traceparent trace_id %q != span trace_id %q", parts[1], span.TraceID)
	}
}

func TestExtractTraceContext(t *testing.T) {
	h := http.Header{}
	h.Set("traceparent", "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")
	ctx := traceforge.ExtractTraceContext(context.Background(), h)

	span, ok := traceforge.SpanFromContext(ctx)
	if !ok {
		t.Fatal("expected span in context after extract")
	}
	if span.TraceID != "4bf92f3577b34da6a3ce929d0e0e4736" {
		t.Fatalf("wrong trace_id: %q", span.TraceID)
	}
}

func TestExtractThenStartPreservesTraceID(t *testing.T) {
	h := http.Header{}
	h.Set("traceparent", "00-aaaabbbbccccdddd1111222233334444-0000000000000001-01")
	ctx := traceforge.ExtractTraceContext(context.Background(), h)
	_, child := traceforge.StartSpan(ctx, "server_tool")

	if child.TraceID != "aaaabbbbccccdddd1111222233334444" {
		t.Fatalf("child should inherit extracted trace_id, got %q", child.TraceID)
	}
	if child.ParentSpanID != "0000000000000001" {
		t.Fatalf("child parent_span_id should be incoming span_id, got %q", child.ParentSpanID)
	}
}

// --- HTTP Emitter ---

func TestHTTPEmitterPostsSpan(t *testing.T) {
	var received []map[string]interface{}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(body, &received)
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	_, span := traceforge.StartSpan(context.Background(), "emit_test",
		traceforge.WithToolKind(traceforge.ToolKindHTTP))
	traceforge.EndSpan(span, traceforge.StatusOK, nil)

	emitter := traceforge.NewHTTPEmitter(srv.URL + "/v1/spans")
	if err := emitter.Emit(span); err != nil {
		t.Fatalf("Emit() returned error: %v", err)
	}
	if len(received) != 1 {
		t.Fatalf("expected 1 span posted, got %d", len(received))
	}
	if received[0]["tool_name"] != "emit_test" {
		t.Fatalf("wrong tool_name: %v", received[0]["tool_name"])
	}
}
```

---

## Part 6 — Example Agent (`examples/weather_calc/main.go`)

A minimal two-tool agent that produces a connected 3-span trace: root → weather lookup → calculator call.

```go
// SPDX-License-Identifier: MIT
// Example: two-tool agent producing a connected TraceForge trace.
package main

import (
	"context"
	"fmt"
	"log"
	"math"
	"net/http"

	tf "github.com/akshantvats/infra-ai-streaming/traceforge/sdk/go/traceforge"
)

func main() {
	emitter := tf.NewHTTPEmitter("") // reads TRACEFORGE_ENDPOINT or localhost:8080

	// Root span: the orchestrating agent turn
	ctx, root := tf.StartSpan(context.Background(), "agent_turn",
		tf.WithToolKind(tf.ToolKindSubAgent))
	defer tf.EndSpan(root, tf.StatusOK, nil, emitter)

	// Tool 1: weather lookup (simulated HTTP to an external API)
	city := "Berlin"
	tempC, err := fetchWeather(ctx, city, emitter)
	if err != nil {
		log.Printf("weather error: %v", err)
	}

	// Tool 2: unit conversion (calculator)
	tempF := celsiusToFahrenheit(ctx, tempC, emitter)

	fmt.Printf("Weather in %s: %.1f°C / %.1f°F\n", city, tempC, tempF)
	fmt.Printf("Trace ID: %s\n", root.TraceID)
}

func fetchWeather(ctx context.Context, city string, e tf.Emitter) (float64, error) {
	ctx, span := tf.StartSpan(ctx, "weather_lookup",
		tf.WithToolKind(tf.ToolKindHTTP),
		tf.WithAttribute("city", city))
	defer tf.EndSpan(span, tf.StatusOK, nil, e)

	// Inject W3C traceparent so a real downstream service could continue the trace.
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet,
		"https://wttr.in/"+city+"?format=j1", nil)
	tf.InjectTraceContext(ctx, req.Header)

	// Simulate: return a fixed temperature rather than making a real HTTP call.
	_ = req
	return 21.5, nil
}

func celsiusToFahrenheit(ctx context.Context, c float64, e tf.Emitter) float64 {
	_, span := tf.StartSpan(ctx, "unit_conversion",
		tf.WithToolKind(tf.ToolKindCodeExec),
		tf.WithAttribute("formula", "F = C * 9/5 + 32"))
	defer tf.EndSpan(span, tf.StatusOK, nil, e)

	return math.Round((c*9/5+32)*10) / 10
}
```

Running this produces output like:
```
Weather in Berlin: 21.5°C / 70.7°F
Trace ID: a3f8c2e1b94d7506f0a1e82c3b95d401
```
And emits three connected spans to the collector — the waterfall is complete.

---

## Directory Structure

```
infra-ai-streaming/
└── traceforge/
    └── sdk/
        ├── python/                  # Day 32 — already shipped
        └── go/
            ├── go.mod
            ├── traceforge/
            │   ├── span.go
            │   ├── tracer.go
            │   ├── propagation.go
            │   ├── emit.go
            │   └── tracer_test.go
            └── examples/
                └── weather_calc/
                    └── main.go
```

---

## Implementation Checklist

### Package structure
- [ ] `traceforge/sdk/go/go.mod` — module `github.com/akshantvats/infra-ai-streaming/traceforge/sdk/go`
- [ ] SPDX license header on every `.go` file

### Core SDK
- [ ] `span.go` — `Span` struct JSON-tagged, `NewTraceID()`, `NewSpanID()`
- [ ] `tracer.go` — `StartSpan()`, `EndSpan()`, `SpanFromContext()`, functional options
- [ ] `propagation.go` — `InjectTraceContext()`, `ExtractTraceContext()`, 4-part `traceparent` format
- [ ] `emit.go` — `HTTPEmitter` (stdlib `net/http`, 2s timeout), `KafkaEmitter` (sarama)

### Propagation correctness
- [ ] `ExtractTraceContext` then `StartSpan` → child inherits extracted trace_id and uses incoming span_id as parent_span_id
- [ ] `InjectTraceContext` writes `00-{traceId}-{spanId}-01`
- [ ] Malformed `traceparent` silently ignored (ctx returned unchanged)

### Emitters
- [ ] `HTTPEmitter.Emit()` is non-blocking on failure (logs at warn, returns nil)
- [ ] `KafkaEmitter.Emit()` message key = `trace_id` (enables partition affinity for same-trace spans)
- [ ] Both emitters configurable via env vars (`TRACEFORGE_ENDPOINT`, `TRACEFORGE_KAFKA_BROKERS`)

### Tests
- [ ] `TestStartSpanCreatesNewTrace` — root span has no parent
- [ ] `TestChildSpanInheritsTraceID` — child shares parent trace_id
- [ ] `TestEndSpanRecordsLatency` — latency_ms ≥ 0
- [ ] `TestEndSpanSetsErrorStatus` — non-nil error overrides status to ERROR
- [ ] `TestInjectTraceContext` — valid `traceparent` header written
- [ ] `TestExtractTraceContext` — trace_id extracted correctly
- [ ] `TestExtractThenStartPreservesTraceID` — end-to-end propagation
- [ ] `TestHTTPEmitterPostsSpan` — span appears at mock collector

### Example
- [ ] `go run ./traceforge/sdk/go/examples/weather_calc/` exits 0
- [ ] Console output shows Trace ID and both temperatures

### Validation
- [ ] `go test ./traceforge/sdk/go/...` exits 0
- [ ] `go vet ./traceforge/sdk/go/...` exits 0

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `context.Value` key collisions | Low | Medium | Use unexported `contextKey{}` struct pointer — zero collision surface |
| Kafka sarama init on every `Emit()` call is slow | Medium | Low | Acceptable for SDK demo; note in code comment; persistent producer is Day 34+ |
| `traceparent` flag byte — always "01" | Low | Low | Flag byte signals trace sampling; "01" = sampled. Document as fixed for now |
| go.mod circular dependency with infra-ai-streaming root | Medium | Medium | Put Go SDK in its own module; `replace` directive in root if needed |

---

## PR Description Template

```
## Day 33 — TraceForge: Go SDK `StartSpan`/`EndSpan` + W3C Context Propagation

### What
- `traceforge/sdk/go/traceforge/span.go`: `Span` struct, `NewTraceID()`, `NewSpanID()`
- `traceforge/sdk/go/traceforge/tracer.go`: `StartSpan()`, `EndSpan()`, functional options
- `traceforge/sdk/go/traceforge/propagation.go`: W3C `traceparent` inject/extract
- `traceforge/sdk/go/traceforge/emit.go`: `HTTPEmitter` + `KafkaEmitter` (sarama, key=trace_id)
- `traceforge/sdk/go/traceforge/tracer_test.go`: 8 tests covering propagation, latency, error status, HTTP emit
- `traceforge/sdk/go/examples/weather_calc/main.go`: two-tool agent, 3-span connected trace

### Test output
```
$ go test ./traceforge/sdk/go/... -v
--- PASS: TestStartSpanCreatesNewTrace (0.00s)
--- PASS: TestChildSpanInheritsTraceID (0.00s)
--- PASS: TestEndSpanRecordsLatency (0.00s)
--- PASS: TestEndSpanSetsErrorStatus (0.00s)
--- PASS: TestInjectTraceContext (0.00s)
--- PASS: TestExtractTraceContext (0.00s)
--- PASS: TestExtractThenStartPreservesTraceID (0.00s)
--- PASS: TestHTTPEmitterPostsSpan (0.00s)
PASS
ok  github.com/akshantvats/infra-ai-streaming/traceforge/sdk/go/traceforge
```

### Example agent run
```
$ go run ./traceforge/sdk/go/examples/weather_calc/
Weather in Berlin: 21.5°C / 70.7°F
Trace ID: a3f8c2e1b94d7506f0a1e82c3b95d401
```

### Next steps (Day 34)
- ClickHouse `agent_spans` MergeTree table, Grafana waterfall panel

Self-review: N issues found and fixed.
```
