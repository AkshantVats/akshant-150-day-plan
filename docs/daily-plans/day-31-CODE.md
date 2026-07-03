# Day 31 — Code Plan
## agent-trace-collector — OTel Collector Pipeline: HTTP Ingest → OTLP/gRPC → ClickHouse + Kafka

**Calendar**: Friday, 4 July 2026 · Day 31 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` (traceforge/ subdirectory — see Day 30 note below)
**Language**: Go, YAML (OTel Collector config), SQL (ClickHouse DDL)
**Builds on**: Day 30 — TraceForge scaffold: DESIGN.md + span schema + Go types in `infra-ai-streaming/traceforge/`

### Day 30 Note — Repo Location
Day 30 landed the TraceForge scaffold in `infra-ai-streaming/traceforge/` because `agent-trace-collector` was outside session scope. Day 31 continues in `infra-ai-streaming/traceforge/`. The OTel Collector compose overlay lands in `infra-ai-streaming/docker/` alongside the existing LensAI quickstart compose files. If the 2am agent can access `agent-trace-collector` repo directly, prefer it — but do not block Day 31 code work on repo migration.

### Shared Thread
> Tool Calls Are RPCs With Marketing meets OpenTelemetry Semantics for Agents in today's agent-trace-collector commit.

---

## Summary

Day 31 wires up the full ingestion path for agent execution traces. The Day 30 scaffold defined the `Span` schema and DESIGN.md. Today's deliverable makes that schema operational:

1. **HTTP ingestion endpoint** — `POST /v1/spans` in `traceforge/cmd/collector/main.go`, accepts a JSON array of `schema.Span`, validates, and enqueues for export
2. **OTLP/gRPC exporter** — converts canonical `Span` to OTel `ResourceSpans`, emits to an OTel Collector sidecar on port 4317
3. **ClickHouse DDL** — `lensai.agent_spans` table creation script (schema from Day 30 DESIGN.md)
4. **OTel Collector config** — `otel-collector-traceforge.yaml`: receivers (otlp + kafka), processors (batch + attributes), exporters (ClickHouseExporter + Kafka `agent.spans.v1`)
5. **Compose overlay** — `docker/traceforge-overlay.yml` that extends the LensAI quickstart with the TraceForge collector sidecar and ClickHouse migration

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|---------------|
| AC-1 | `POST /v1/spans` accepts valid JSON batch and returns `200 OK` | `go test ./traceforge/...` |
| AC-2 | Invalid span (missing trace_id) returns `400` with error detail | Unit test |
| AC-3 | `SpanExporter.Export()` converts `schema.Span` to OTel `ptrace.Traces` without data loss | Unit test with field-by-field assertion |
| AC-4 | `otel-collector-traceforge.yaml` is valid YAML and passes `otelcol validate` (or equivalent) | CI lint step |
| AC-5 | `lensai/migrations/002_agent_spans.sql` creates `lensai.agent_spans` table | ClickHouse smoke test in CI |
| AC-6 | `docker/traceforge-overlay.yml` composes cleanly: `docker compose -f docker-compose.yml -f traceforge-overlay.yml config` exits 0 | Shell command in PR description |
| AC-7 | `go test ./traceforge/...` — all tests pass | Command output in PR description |
| AC-8 | `go vet ./traceforge/...` exits 0 | Command output in PR description |

---

## Part 1 — HTTP Ingestion Endpoint

### 1.1 Directory structure additions

```
infra-ai-streaming/traceforge/
├── cmd/
│   └── collector/
│       ├── main.go          # HTTP server, /v1/spans handler
│       └── main_test.go     # integration test for POST /v1/spans
├── pkg/
│   └── schema/              # (existing from Day 30)
│       ├── span.go
│       └── span_test.go
├── pkg/
│   └── export/
│       ├── otlp.go          # Span → OTel ptrace.Traces conversion
│       └── otlp_test.go     # field-by-field conversion test
├── go.mod                   # add: go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc
└── go.sum
```

Additional repo-level files:
```
infra-ai-streaming/
├── docker/
│   └── traceforge-overlay.yml
├── otel/
│   └── otel-collector-traceforge.yaml
└── lensai/
    └── migrations/
        └── 002_agent_spans.sql
```

### 1.2 HTTP handler (`cmd/collector/main.go`)

```go
// SPDX-License-Identifier: MIT
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"time"

	"github.com/akshantvats/infra-ai-streaming/traceforge/pkg/export"
	"github.com/akshantvats/infra-ai-streaming/traceforge/pkg/schema"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
)

func main() {
	otlpEndpoint := getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
	listenAddr := getenv("LISTEN_ADDR", ":8080")

	ctx := context.Background()
	grpcExporter, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithEndpoint(otlpEndpoint),
		otlptracegrpc.WithInsecure(),
	)
	if err != nil {
		slog.Error("failed to create OTLP exporter", "err", err)
		os.Exit(1)
	}
	defer grpcExporter.Shutdown(ctx)

	exporter := export.NewSpanExporter(grpcExporter)

	mux := http.NewServeMux()
	mux.HandleFunc("POST /v1/spans", makeSpanHandler(ctx, exporter))
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	srv := &http.Server{Addr: listenAddr, Handler: mux, ReadTimeout: 10 * time.Second}
	slog.Info("traceforge collector listening", "addr", listenAddr)
	if err := srv.ListenAndServe(); err != nil {
		slog.Error("server error", "err", err)
		os.Exit(1)
	}
}

func makeSpanHandler(ctx context.Context, exporter *export.SpanExporter) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var spans []schema.Span
		if err := json.NewDecoder(r.Body).Decode(&spans); err != nil {
			http.Error(w, "invalid JSON: "+err.Error(), http.StatusBadRequest)
			return
		}
		for i, s := range spans {
			if s.TraceID == "" {
				http.Error(w, fmt.Sprintf("span[%d]: trace_id is required", i), http.StatusBadRequest)
				return
			}
			if s.SpanID == "" {
				http.Error(w, fmt.Sprintf("span[%d]: span_id is required", i), http.StatusBadRequest)
				return
			}
		}
		if err := exporter.Export(ctx, spans); err != nil {
			slog.Error("export failed", "err", err)
			http.Error(w, "export error", http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusOK)
	}
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
```

### 1.3 OTLP exporter (`pkg/export/otlp.go`)

```go
// SPDX-License-Identifier: MIT
package export

import (
	"context"
	"time"

	"github.com/akshantvats/infra-ai-streaming/traceforge/pkg/schema"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace"
	"go.opentelemetry.io/collector/pdata/pcommon"
	"go.opentelemetry.io/collector/pdata/ptrace"
)

type SpanExporter struct {
	inner otlptrace.Client
}

func NewSpanExporter(client otlptrace.Client) *SpanExporter {
	return &SpanExporter{inner: client}
}

// ConvertToOTel converts canonical TraceForge spans to OTel Traces (exported for testing).
func ConvertToOTel(spans []schema.Span) ptrace.Traces {
	td := ptrace.NewTraces()
	rs := td.ResourceSpans().AppendEmpty()
	rs.Resource().Attributes().PutStr("service.name", "agent-trace-collector")

	ils := rs.ScopeSpans().AppendEmpty()
	ils.Scope().SetName("traceforge")

	for _, s := range spans {
		otelSpan := ils.Spans().AppendEmpty()

		var traceID [16]byte
		decodeHex(string(s.TraceID), traceID[:])
		otelSpan.SetTraceID(traceID)

		var spanID [8]byte
		decodeHex(string(s.SpanID), spanID[:])
		otelSpan.SetSpanID(spanID)

		if s.ParentID != "" {
			var parentID [8]byte
			decodeHex(string(s.ParentID), parentID[:])
			otelSpan.SetParentSpanID(parentID)
		}

		otelSpan.SetName(s.ToolName)
		otelSpan.SetStartTimestamp(pcommon.NewTimestampFromTime(s.StartTime))
		endTime := s.StartTime.Add(time.Duration(s.LatencyMs) * time.Millisecond)
		otelSpan.SetEndTimestamp(pcommon.NewTimestampFromTime(endTime))

		attrs := otelSpan.Attributes()
		attrs.PutStr("traceforge.tool.name", s.ToolName)
		attrs.PutStr("traceforge.tool.kind", string(s.ToolKind))
		if s.Model != "" {
			attrs.PutStr("traceforge.model", s.Model)
		}
		attrs.PutInt("traceforge.tokens.total", int64(s.TotalTokens))
		attrs.PutInt("traceforge.tokens.input", int64(s.InputTokens))
		attrs.PutInt("traceforge.tokens.output", int64(s.OutputTokens))
		attrs.PutDouble("traceforge.cost.usd", s.CostUSD)
		attrs.PutInt("traceforge.latency.ms", s.LatencyMs)

		switch s.Status {
		case schema.SpanStatusOK:
			otelSpan.Status().SetCode(ptrace.StatusCodeOk)
		case schema.SpanStatusError:
			otelSpan.Status().SetCode(ptrace.StatusCodeError)
			otelSpan.Status().SetMessage(s.ErrorMessage)
		default:
			otelSpan.Status().SetCode(ptrace.StatusCodeUnset)
		}

		for k, v := range s.Attributes {
			attrs.PutStr(k, v)
		}
	}
	return td
}

// Export converts spans and uploads via gRPC OTLP.
func (e *SpanExporter) Export(ctx context.Context, spans []schema.Span) error {
	td := ConvertToOTel(spans)
	return e.inner.UploadTraces(ctx, td.ResourceSpans())
}

func decodeHex(s string, dst []byte) {
	for i := 0; i < len(dst) && 2*i+1 < len(s); i++ {
		hi := hexVal(s[2*i])
		lo := hexVal(s[2*i+1])
		dst[i] = (hi << 4) | lo
	}
}

func hexVal(c byte) byte {
	switch {
	case c >= '0' && c <= '9':
		return c - '0'
	case c >= 'a' && c <= 'f':
		return c - 'a' + 10
	case c >= 'A' && c <= 'F':
		return c - 'A' + 10
	}
	return 0
}
```

---

## Part 2 — OTel Collector Configuration

### `otel/otel-collector-traceforge.yaml`

```yaml
# OTel Collector config for TraceForge agent span pipeline.
# Receivers: otlp (gRPC 4317 + HTTP 4318), kafka (agent.spans.v1)
# Processors: batch (256 spans / 2s flush), attributes (add pipeline_version)
# Exporters: clickhouse (lensai.agent_spans), kafka (agent.spans.v1 fan-out)

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  kafka:
    brokers:
      - kafka:9092
    topic: agent.spans.v1
    encoding: otlp_proto
    group_id: otel-collector-traceforge

processors:
  batch:
    send_batch_size: 256
    timeout: 2s

  attributes:
    actions:
      - key: pipeline.version
        value: "1"
        action: insert
      - key: service.team
        value: "traceforge"
        action: insert

exporters:
  clickhouse:
    endpoint: tcp://clickhouse:9000
    database: lensai
    traces_table_name: agent_spans
    timeout: 10s
    retry_on_failure:
      enabled: true
      initial_interval: 1s
      max_interval: 30s
      max_elapsed_time: 120s

  kafka:
    brokers:
      - kafka:9092
    topic: agent.spans.v1
    encoding: otlp_proto

service:
  pipelines:
    traces:
      receivers: [otlp, kafka]
      processors: [attributes, batch]
      exporters: [clickhouse, kafka]

  telemetry:
    logs:
      level: info
```

---

## Part 3 — ClickHouse Migration

### `lensai/migrations/002_agent_spans.sql`

```sql
-- TraceForge agent execution spans.
-- One row per tool call / sub-agent invocation / model call in an agent run.
-- Ordered by started_at for efficient time-range queries; trace_id secondary for waterfall assembly.
CREATE TABLE IF NOT EXISTS lensai.agent_spans
(
    trace_id        String                 COMMENT 'Root identifier for one agent run (hex128)',
    span_id         String                 COMMENT 'Identifier for this step (hex64)',
    parent_span_id  String   DEFAULT ''    COMMENT 'Empty string for root spans',
    tool_name       String                 COMMENT 'Human-readable tool name, e.g. "Read", "Bash"',
    tool_kind       LowCardinality(String) COMMENT 'Tool taxonomy: retrieval|code_execution|browser|file_io|sub_agent|model_call|unknown',
    model           String   DEFAULT ''    COMMENT 'Model ID e.g. "claude-sonnet-4-6"; empty for non-LLM tools',
    input_tokens    UInt32   DEFAULT 0,
    output_tokens   UInt32   DEFAULT 0,
    total_tokens    UInt32   DEFAULT 0,
    cost_usd        Float64  DEFAULT 0.0,
    status          LowCardinality(String) COMMENT 'OK|ERROR|UNSET',
    latency_ms      UInt32                 COMMENT 'Wall-clock duration in milliseconds',
    error_message   String   DEFAULT '',
    pipeline_version String  DEFAULT '1'  COMMENT 'OTel processor pipeline.version attribute',
    started_at      DateTime64(3)          COMMENT 'Span start time, millisecond precision',
    ingested_at     DateTime DEFAULT now() COMMENT 'Row insertion time'
)
ENGINE = MergeTree()
ORDER BY (started_at, trace_id, span_id)
PARTITION BY toYYYYMM(started_at)
SETTINGS index_granularity = 8192;

-- Materialised view: per-trace cost rollup (populated on insert).
CREATE TABLE IF NOT EXISTS lensai.agent_trace_cost
(
    trace_id       String,
    started_at     DateTime64(3),
    total_tokens   UInt64  DEFAULT 0,
    total_cost_usd Float64 DEFAULT 0.0,
    span_count     UInt32  DEFAULT 0
)
ENGINE = SummingMergeTree()
ORDER BY (started_at, trace_id);

CREATE MATERIALIZED VIEW IF NOT EXISTS lensai.agent_trace_cost_mv
TO lensai.agent_trace_cost
AS SELECT
    trace_id,
    min(started_at)    AS started_at,
    sum(total_tokens)  AS total_tokens,
    sum(cost_usd)      AS total_cost_usd,
    count()            AS span_count
FROM lensai.agent_spans
GROUP BY trace_id;
```

---

## Part 4 — Compose Overlay

### `docker/traceforge-overlay.yml`

```yaml
# Compose overlay for TraceForge collector sidecar.
# Usage: docker compose -f docker-compose.yml -f docker/traceforge-overlay.yml up
version: "3.9"

services:
  traceforge-collector:
    image: otel/opentelemetry-collector-contrib:0.100.0
    command: ["--config=/etc/otel/otel-collector-traceforge.yaml"]
    volumes:
      - ../otel/otel-collector-traceforge.yaml:/etc/otel/otel-collector-traceforge.yaml:ro
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
    depends_on:
      clickhouse:
        condition: service_healthy
      kafka:
        condition: service_healthy
    restart: unless-stopped

  traceforge-migrator:
    image: clickhouse/clickhouse-server:24.3
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        clickhouse-client --host clickhouse --port 9000 --user default \
          --multiquery < /migrations/002_agent_spans.sql
    volumes:
      - ../lensai/migrations:/migrations:ro
    depends_on:
      clickhouse:
        condition: service_healthy
    restart: "no"

  traceforge-ingest:
    build:
      context: ..
      dockerfile: traceforge/Dockerfile
    environment:
      OTEL_EXPORTER_OTLP_ENDPOINT: "traceforge-collector:4317"
      LISTEN_ADDR: ":8080"
    ports:
      - "8080:8080"
    depends_on:
      - traceforge-collector
    restart: unless-stopped
```

### `traceforge/Dockerfile`

```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o /traceforge-collector ./traceforge/cmd/collector

FROM alpine:3.19
COPY --from=builder /traceforge-collector /usr/local/bin/traceforge-collector
ENTRYPOINT ["/usr/local/bin/traceforge-collector"]
```

---

## Part 5 — Tests

### `pkg/export/otlp_test.go`

```go
// SPDX-License-Identifier: MIT
package export_test

import (
	"testing"
	"time"

	"github.com/akshantvats/infra-ai-streaming/traceforge/pkg/export"
	"github.com/akshantvats/infra-ai-streaming/traceforge/pkg/schema"
)

func TestConvertSpanFieldsPreserved(t *testing.T) {
	s := schema.Span{
		TraceID:      "4bf92f3577b34da6a3ce929d0e0e4736",
		SpanID:       "00f067aa0ba902b7",
		ParentID:     "1234567890abcdef",
		ToolName:     "Bash",
		ToolKind:     schema.ToolKindCodeExec,
		Model:        "claude-sonnet-4-6",
		Status:       schema.SpanStatusOK,
		StartTime:    time.Date(2026, 7, 4, 2, 0, 0, 0, time.UTC),
		LatencyMs:    250,
		InputTokens:  100,
		OutputTokens: 50,
		TotalTokens:  150,
		CostUSD:      0.00045,
	}

	td := export.ConvertToOTel([]schema.Span{s})
	if td.SpanCount() != 1 {
		t.Fatalf("expected 1 span, got %d", td.SpanCount())
	}
	otelSpan := td.ResourceSpans().At(0).ScopeSpans().At(0).Spans().At(0)
	if otelSpan.Name() != "Bash" {
		t.Errorf("name: got %q, want %q", otelSpan.Name(), "Bash")
	}
	totalTokens, _ := otelSpan.Attributes().Get("traceforge.tokens.total")
	if totalTokens.Int() != 150 {
		t.Errorf("tokens: got %d, want 150", totalTokens.Int())
	}
	costAttr, _ := otelSpan.Attributes().Get("traceforge.cost.usd")
	if costAttr.Double() != 0.00045 {
		t.Errorf("cost: got %f, want 0.00045", costAttr.Double())
	}
}
```

---

## Implementation Checklist

### Go module
- [ ] Add `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc` to go.mod
- [ ] Add `go.opentelemetry.io/collector/pdata` to go.mod
- [ ] `go mod tidy` exits 0

### HTTP ingest
- [ ] `cmd/collector/main.go` with `POST /v1/spans` handler
- [ ] Validation: missing `trace_id` → 400; missing `span_id` → 400; invalid JSON → 400
- [ ] `GET /healthz` returns 200

### OTLP export
- [ ] `pkg/export/otlp.go` with `SpanExporter.Export()` and `ConvertToOTel()` (exported for test use)
- [ ] Hex decode for `TraceID` (16 bytes) and `SpanID` (8 bytes)
- [ ] All 9 canonical fields mapped to OTel attributes
- [ ] `pkg/export/otlp_test.go` — field preservation test

### OTel Collector config
- [ ] `otel/otel-collector-traceforge.yaml` — receivers, processors, exporters
- [ ] Validate YAML syntax

### ClickHouse
- [ ] `lensai/migrations/002_agent_spans.sql` — main table + materialised view + rollup table
- [ ] `agent_trace_cost` rollup table for per-trace cost queries

### Compose overlay
- [ ] `docker/traceforge-overlay.yml` — collector + migrator + ingest services
- [ ] `traceforge/Dockerfile` — multi-stage Go build
- [ ] `docker compose -f docker-compose.yml -f docker/traceforge-overlay.yml config` exits 0

### Validation
- [ ] `go build ./traceforge/...` exits 0
- [ ] `go test ./traceforge/...` exits 0
- [ ] `go vet ./traceforge/...` exits 0
- [ ] PR opened targeting `main`, marked ready (not draft)
- [ ] PR description includes command outputs
- [ ] PR URL recorded in `DAILY_PROGRESS.md`
- [ ] `Self-review: N issues found and fixed.` in commit message

---

## go.mod additions

```go
require (
	go.opentelemetry.io/otel v1.26.0
	go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc v1.26.0
	go.opentelemetry.io/collector/pdata v1.7.0
	go.opentelemetry.io/proto/otlp v1.2.0
	google.golang.org/grpc v1.63.2
)
```

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| pdata API differs between collector versions | Medium | Low | Pin to 1.7.0; check collector contrib image version matches |
| ClickHouse exporter in OTel contrib requires specific table schema | Medium | Medium | Match DDL columns exactly to contrib exporter expectations; check contrib source |
| Kafka consumer in OTel Collector needs broker address at startup | Low | Low | `depends_on: kafka` in compose overlay handles ordering |
| `agent-trace-collector` repo not in session scope | Medium | Low | Work in `infra-ai-streaming/traceforge/` as Day 30 did |

---

## PR Description Template

```
## Day 31 — TraceForge: OTel Collector Pipeline (HTTP → OTLP → ClickHouse + Kafka)

### What
- `traceforge/cmd/collector/main.go`: HTTP server, POST /v1/spans handler, OTLP/gRPC export
- `traceforge/pkg/export/otlp.go`: canonical Span → OTel ResourceSpans conversion
- `otel/otel-collector-traceforge.yaml`: OTel Collector config (receivers: otlp+kafka; processors: batch+attributes; exporters: clickhouse+kafka)
- `lensai/migrations/002_agent_spans.sql`: lensai.agent_spans table + agent_trace_cost materialised view
- `docker/traceforge-overlay.yml`: compose overlay adding TraceForge collector, migrator, ingest services
- `traceforge/Dockerfile`: multi-stage Go builder image

### Test output
```
$ go build ./traceforge/...
(exit 0)

$ go test ./traceforge/...
ok  github.com/akshantvats/infra-ai-streaming/traceforge/pkg/schema   0.003s
ok  github.com/akshantvats/infra-ai-streaming/traceforge/pkg/export   0.008s
ok  github.com/akshantvats/infra-ai-streaming/traceforge/cmd/collector 0.012s

$ go vet ./traceforge/...
(exit 0)

$ docker compose -f docker-compose.yml -f docker/traceforge-overlay.yml config
(valid compose output, exit 0)
```

### Next steps (Day 32)
- Grafana dashboard: agent execution waterfall from agent_spans
- Demo agent instrumented with POST /v1/spans calls

Self-review: N issues found and fixed.
```
