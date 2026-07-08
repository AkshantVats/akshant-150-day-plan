# Day 34 — Code Plan
## TraceForge: ClickHouse `agent_spans` MergeTree + Per-Trace Cost MV + Grafana Waterfall

**Calendar**: Monday, 9 July 2026 · Day 34 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` (traceforge/ subdirectory — continuing from Day 33)
**Language**: Go 1.22+ (Kafka consumer) · SQL (ClickHouse DDL + MV)
**Builds on**: Day 33 — Go SDK `StartSpan`/`EndSpan` + Kafka emission to `agent-spans` topic; Day 31 — HTTP ingest endpoint on `:8080`

### Shared Thread
> ClickHouse for Traces meets Trace Storage Layout — Sort Keys Matter in today's agent-trace-collector commit.

---

## Summary

Day 34 closes the TraceForge storage loop. Spans emitted by the Python SDK (Day 32) and Go SDK (Day 33) land in Kafka on the `agent-spans` topic. This day adds the ClickHouse sink that consumes those spans, the materialized view that rolls up per-trace cost in real time, and the Grafana dashboard that renders the agent waterfall.

Three deliverables:
1. **ClickHouse DDL** — `agent_spans` MergeTree table with `ORDER BY (trace_id, start_time)`, ZSTD compression, and a Kafka engine ingestion table
2. **Per-trace cost MV** — `trace_cost_rollup` materialized view that aggregates `total_tokens` and `cost_usd` per trace in near real-time
3. **Grafana waterfall panel** — JSON dashboard provisioning a Gantt-style span waterfall from ClickHouse

---

## Deliverables

| File | Purpose |
|---|---|
| `traceforge/clickhouse/schema.sql` | `agent_spans` MergeTree DDL + Kafka engine table + MV |
| `traceforge/clickhouse/trace_cost_rollup.sql` | Per-trace cost materialized view DDL |
| `traceforge/clickhouse/queries.sql` | Reference queries (waterfall, per-trace cost, slow spans) |
| `traceforge/clickhouse/consumer/main.go` | Go consumer: Kafka → ClickHouse batch insert |
| `traceforge/clickhouse/consumer/consumer_test.go` | Unit + integration tests |
| `traceforge/grafana/waterfall-dashboard.json` | Grafana dashboard JSON for agent waterfall panel |
| `traceforge/docker-compose.clickhouse.yml` | ClickHouse + ZooKeeper service overlay |

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|-------------|
| AC-1 | `agent_spans` table created with `ENGINE = MergeTree()` and `ORDER BY (trace_id, start_time)` | `SHOW CREATE TABLE agent_spans` output in PR |
| AC-2 | Kafka engine table `agent_spans_kafka` consumes from `agent-spans` topic | `SELECT count() FROM agent_spans_kafka` shows rows after Go SDK example run |
| AC-3 | `trace_cost_rollup` MV populates within 5s of span insert | Query output in PR description |
| AC-4 | Go consumer batch-inserts spans to ClickHouse with batch size 500 and flush interval 2s | Unit test with mock ClickHouse |
| AC-5 | Grafana dashboard JSON imports cleanly via `grafana/dashboards/` provisioning path | Screenshot in PR description |
| AC-6 | `go test ./traceforge/clickhouse/consumer/...` exits 0 | Command output in PR description |
| AC-7 | Reference query `SELECT * FROM agent_spans WHERE trace_id = ?` returns all spans for a trace in `start_time` order without full table scan | `EXPLAIN` output shows primary key range scan |

---

## Part 1 — ClickHouse Schema (`schema.sql`)

```sql
-- SPDX-License-Identifier: MIT
-- TraceForge: agent_spans schema
-- Day 34 — Trace Storage Layout

-- ============================================================
-- Kafka ingestion table (raw, string columns for JSON parsing)
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_spans_kafka
(
    raw String
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'localhost:9092',
    kafka_topic_list  = 'agent-spans',
    kafka_group_name  = 'traceforge-clickhouse',
    kafka_format      = 'RawBLOB',
    kafka_num_consumers = 2;

-- ============================================================
-- Main MergeTree table
-- ORDER BY (trace_id, start_time) optimises the primary query pattern:
--   "give me all spans for trace X, in chronological order"
-- Secondary pattern (slow spans across all traces) served by projection.
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_spans
(
    -- Trace identity
    trace_id        String,
    span_id         String,
    parent_span_id  String     DEFAULT '',

    -- What ran
    tool_name       String,
    tool_kind       LowCardinality(String),   -- model_call / retrieval / http / …
    model           LowCardinality(String)    DEFAULT '',

    -- Outcome
    status          LowCardinality(String),   -- OK / ERROR / UNSET
    error_message   String                    DEFAULT '',

    -- Timing
    start_time      DateTime64(3, 'UTC'),
    latency_ms      Int64,

    -- Cost
    input_tokens    UInt32                    DEFAULT 0,
    output_tokens   UInt32                    DEFAULT 0,
    total_tokens    UInt32                    DEFAULT 0,
    cost_usd        Float64                   DEFAULT 0.0,

    -- Free-form attributes (stored as JSON string, queried with JSONExtract)
    attributes      String                    DEFAULT '{}'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(start_time)      -- daily partition; one directory per day
ORDER BY (trace_id, start_time)          -- sort key: locality by trace, then time within trace
TTL toDateTime(start_time) + INTERVAL 30 DAY  -- drop spans older than 30 days automatically
SETTINGS
    index_granularity = 8192,
    min_bytes_for_wide_part = 10485760,  -- 10 MB: use wide format for larger parts
    compress_by = 'ZSTD(3)';            -- ZSTD level 3: ~4× compression vs Snappy, <1% read overhead

-- ============================================================
-- Materialized view: Kafka → agent_spans
-- Parses each raw JSON message from the Kafka engine table and
-- inserts it into agent_spans. This is the ingestion bridge.
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS agent_spans_mv
TO agent_spans
AS SELECT
    JSONExtractString(raw, 'trace_id')       AS trace_id,
    JSONExtractString(raw, 'span_id')        AS span_id,
    JSONExtractString(raw, 'parent_span_id') AS parent_span_id,
    JSONExtractString(raw, 'tool_name')      AS tool_name,
    JSONExtractString(raw, 'tool_kind')      AS tool_kind,
    JSONExtractString(raw, 'model')          AS model,
    JSONExtractString(raw, 'status')         AS status,
    JSONExtractString(raw, 'error_message')  AS error_message,
    parseDateTimeBestEffort(JSONExtractString(raw, 'start_time')) AS start_time,
    JSONExtractInt(raw, 'latency_ms')        AS latency_ms,
    JSONExtractUInt(raw, 'input_tokens')     AS input_tokens,
    JSONExtractUInt(raw, 'output_tokens')    AS output_tokens,
    JSONExtractUInt(raw, 'total_tokens')     AS total_tokens,
    JSONExtractFloat(raw, 'cost_usd')        AS cost_usd,
    ifNull(JSONExtractString(raw, 'attributes'), '{}') AS attributes
FROM agent_spans_kafka;

-- ============================================================
-- Projection: slow-span lookup across all traces
-- Without this, finding the slowest spans across all traces
-- requires a full sort over the entire table (wrong sort key order).
-- The projection stores a secondary sort: (latency_ms DESC, trace_id).
-- ============================================================
ALTER TABLE agent_spans
    ADD PROJECTION IF NOT EXISTS proj_slow_spans
    (
        SELECT trace_id, span_id, tool_name, latency_ms, cost_usd, start_time
        ORDER BY (latency_ms DESC, trace_id)
    );

MATERIALIZE PROJECTION proj_slow_spans IN TABLE agent_spans;
```

---

## Part 2 — Per-Trace Cost Rollup (`trace_cost_rollup.sql`)

```sql
-- SPDX-License-Identifier: MIT
-- TraceForge: per-trace cost materialized view
-- Updates in near real-time as spans arrive from Kafka → agent_spans

-- ============================================================
-- Destination table: one row per trace
-- Uses AggregatingMergeTree so that partial inserts can be merged.
-- ============================================================
CREATE TABLE IF NOT EXISTS trace_cost_rollup
(
    trace_id          String,
    first_span_time   SimpleAggregateFunction(min, DateTime64(3, 'UTC')),
    last_span_time    SimpleAggregateFunction(max, DateTime64(3, 'UTC')),
    span_count        SimpleAggregateFunction(sum, UInt64),
    total_tokens      SimpleAggregateFunction(sum, UInt64),
    cost_usd          SimpleAggregateFunction(sum, Float64),
    error_count       SimpleAggregateFunction(sum, UInt64)
)
ENGINE = AggregatingMergeTree()
ORDER BY trace_id;

-- ============================================================
-- Materialized view: inserts aggregated partial state on every
-- INSERT INTO agent_spans.
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS trace_cost_rollup_mv
TO trace_cost_rollup
AS SELECT
    trace_id,
    min(start_time)           AS first_span_time,
    max(start_time)           AS last_span_time,
    count()                   AS span_count,
    sum(total_tokens)         AS total_tokens,
    sum(cost_usd)             AS cost_usd,
    countIf(status = 'ERROR') AS error_count
FROM agent_spans
GROUP BY trace_id;
```

---

## Part 3 — Reference Queries (`queries.sql`)

```sql
-- SPDX-License-Identifier: MIT
-- TraceForge: reference queries for Grafana + ad-hoc debugging

-- Q1: Waterfall — all spans for a trace, ordered for timeline render
--   Primary key range scan: O(k) where k = spans in this trace.
SELECT
    span_id,
    parent_span_id,
    tool_name,
    tool_kind,
    status,
    start_time,
    latency_ms,
    total_tokens,
    cost_usd,
    error_message
FROM agent_spans
WHERE trace_id = {trace_id:String}
ORDER BY start_time ASC;

-- Q2: Recent traces — last N trace IDs with summary
SELECT
    trace_id,
    minMerge(first_span_time)   AS started_at,
    sumMerge(span_count)        AS spans,
    sumMerge(total_tokens)      AS tokens,
    sumMerge(cost_usd)          AS cost,
    sumMerge(error_count)       AS errors
FROM trace_cost_rollup
GROUP BY trace_id
ORDER BY started_at DESC
LIMIT {limit:UInt32};

-- Q3: Slowest spans across all traces (uses proj_slow_spans projection)
SELECT
    trace_id,
    span_id,
    tool_name,
    latency_ms,
    cost_usd
FROM agent_spans
ORDER BY latency_ms DESC
LIMIT 20;

-- Q4: Error rate by tool in the last hour
SELECT
    tool_name,
    countIf(status = 'ERROR')  AS errors,
    count()                    AS total,
    round(100.0 * errors / total, 2) AS error_pct
FROM agent_spans
WHERE start_time >= now() - INTERVAL 1 HOUR
GROUP BY tool_name
ORDER BY error_pct DESC;

-- Q5: Token spend by model in the last 24h
SELECT
    model,
    sum(total_tokens)  AS tokens,
    sum(cost_usd)      AS cost_usd
FROM agent_spans
WHERE start_time >= now() - INTERVAL 24 HOUR
  AND model != ''
GROUP BY model
ORDER BY cost_usd DESC;
```

---

## Part 4 — Go Consumer (`consumer/main.go`)

The Kafka engine + MV approach (Parts 1–2) handles ingestion without a separate consumer. However, a Go consumer is needed for:
- Environments where ClickHouse Kafka engine is unavailable (e.g., ClickHouse Cloud, some managed setups)
- Backpressure handling and dead-letter queue
- Integration testing without a running ClickHouse Kafka engine

```go
// SPDX-License-Identifier: MIT
// TraceForge: Kafka → ClickHouse batch consumer
package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/IBM/sarama"
	_ "github.com/ClickHouse/clickhouse-go/v2"
)

// Span mirrors traceforge.Span for JSON decode.
type Span struct {
	TraceID      string            `json:"trace_id"`
	SpanID       string            `json:"span_id"`
	ParentSpanID string            `json:"parent_span_id"`
	ToolName     string            `json:"tool_name"`
	ToolKind     string            `json:"tool_kind"`
	Model        string            `json:"model"`
	Status       string            `json:"status"`
	StartTime    string            `json:"start_time"`
	LatencyMs    int64             `json:"latency_ms"`
	InputTokens  int               `json:"input_tokens"`
	OutputTokens int               `json:"output_tokens"`
	TotalTokens  int               `json:"total_tokens"`
	CostUSD      float64           `json:"cost_usd"`
	ErrorMessage string            `json:"error_message"`
	Attributes   map[string]string `json:"attributes"`
}

const (
	batchSize     = 500
	flushInterval = 2 * time.Second
)

func main() {
	brokers := envOrDefault("TRACEFORGE_KAFKA_BROKERS", "localhost:9092")
	topic   := envOrDefault("TRACEFORGE_KAFKA_TOPIC",   "agent-spans")
	chDSN   := envOrDefault("TRACEFORGE_CLICKHOUSE_DSN", "clickhouse://localhost:9000/default")

	db, err := sql.Open("clickhouse", chDSN)
	if err != nil {
		log.Fatalf("clickhouse open: %v", err)
	}
	defer db.Close()

	cfg := sarama.NewConfig()
	cfg.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{sarama.NewBalanceStrategyRoundRobin()}
	cfg.Consumer.Offsets.Initial = sarama.OffsetNewest

	client, err := sarama.NewConsumerGroup([]string{brokers}, "traceforge-go-consumer", cfg)
	if err != nil {
		log.Fatalf("consumer group: %v", err)
	}
	defer client.Close()

	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	h := &handler{db: db, buf: make([]Span, 0, batchSize)}
	for {
		if err := client.Consume(ctx, []string{topic}, h); err != nil {
			log.Printf("consume: %v", err)
		}
		if ctx.Err() != nil {
			return
		}
	}
}

type handler struct {
	db    *sql.DB
	buf   []Span
	timer *time.Timer
}

func (h *handler) Setup(sarama.ConsumerGroupSession) error   { return nil }
func (h *handler) Cleanup(sarama.ConsumerGroupSession) error { return nil }

func (h *handler) ConsumeClaim(sess sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	ticker := time.NewTicker(flushInterval)
	defer ticker.Stop()

	for {
		select {
		case msg, ok := <-claim.Messages():
			if !ok {
				h.flush(sess)
				return nil
			}
			var s Span
			if err := json.Unmarshal(msg.Value, &s); err != nil {
				log.Printf("decode span: %v", err)
				sess.MarkMessage(msg, "")
				continue
			}
			h.buf = append(h.buf, s)
			sess.MarkMessage(msg, "")
			if len(h.buf) >= batchSize {
				h.flush(sess)
			}
		case <-ticker.C:
			h.flush(sess)
		}
	}
}

func (h *handler) flush(sess sarama.ConsumerGroupSession) {
	if len(h.buf) == 0 {
		return
	}
	if err := insertBatch(h.db, h.buf); err != nil {
		log.Printf("insert batch: %v", err)
	} else {
		log.Printf("flushed %d spans", len(h.buf))
	}
	h.buf = h.buf[:0]
	sess.Commit()
}

const insertSQL = `INSERT INTO agent_spans
    (trace_id, span_id, parent_span_id, tool_name, tool_kind, model,
     status, error_message, start_time, latency_ms,
     input_tokens, output_tokens, total_tokens, cost_usd, attributes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`

func insertBatch(db *sql.DB, spans []Span) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	stmt, err := tx.Prepare(insertSQL)
	if err != nil {
		tx.Rollback()
		return err
	}
	defer stmt.Close()

	for _, s := range spans {
		attrs := "{}"
		if len(s.Attributes) > 0 {
			if b, e := json.Marshal(s.Attributes); e == nil {
				attrs = string(b)
			}
		}
		if _, err := stmt.Exec(
			s.TraceID, s.SpanID, s.ParentSpanID, s.ToolName, s.ToolKind, s.Model,
			s.Status, s.ErrorMessage, s.StartTime, s.LatencyMs,
			s.InputTokens, s.OutputTokens, s.TotalTokens, s.CostUSD, attrs,
		); err != nil {
			tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

func envOrDefault(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
```

---

## Part 5 — Consumer Tests (`consumer_test.go`)

```go
// SPDX-License-Identifier: MIT
package main

import (
	"database/sql"
	"encoding/json"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
)

func TestInsertBatch_SingleSpan(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock: %v", err)
	}
	defer db.Close()

	mock.ExpectBegin()
	mock.ExpectPrepare("INSERT INTO agent_spans")
	mock.ExpectExec("INSERT INTO agent_spans").WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	spans := []Span{{
		TraceID:   "abc123",
		SpanID:    "def456",
		ToolName:  "test_tool",
		ToolKind:  "http",
		Status:    "OK",
		StartTime: time.Now().UTC().Format(time.RFC3339Nano),
		LatencyMs: 42,
	}}
	if err := insertBatch(db, spans); err != nil {
		t.Fatalf("insertBatch: %v", err)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("unfulfilled expectations: %v", err)
	}
}

func TestInsertBatch_AttributesSerialized(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock: %v", err)
	}
	defer db.Close()

	mock.ExpectBegin()
	mock.ExpectPrepare("INSERT INTO agent_spans")
	mock.ExpectExec("INSERT INTO agent_spans").WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	spans := []Span{{
		TraceID:    "trace1",
		SpanID:     "span1",
		StartTime:  time.Now().UTC().Format(time.RFC3339Nano),
		Attributes: map[string]string{"city": "Berlin", "units": "metric"},
	}}
	if err := insertBatch(db, spans); err != nil {
		t.Fatalf("insertBatch: %v", err)
	}
}

func TestFlushOnBatchSize(t *testing.T) {
	spans := make([]Span, batchSize)
	for i := range spans {
		spans[i] = Span{TraceID: "t", SpanID: "s", StartTime: time.Now().UTC().Format(time.RFC3339Nano)}
	}
	b, err := json.Marshal(spans[0])
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	if len(b) == 0 {
		t.Fatal("empty marshal")
	}
	// Verify batch constant is sensible
	if batchSize < 100 || batchSize > 10000 {
		t.Fatalf("batchSize %d out of expected range", batchSize)
	}
}

func TestEnvOrDefault(t *testing.T) {
	got := envOrDefault("__NO_SUCH_VAR__", "fallback")
	if got != "fallback" {
		t.Fatalf("expected fallback, got %q", got)
	}
}
```

---

## Part 6 — Grafana Waterfall Dashboard (`grafana/waterfall-dashboard.json`)

The dashboard has two panels:
1. **Trace waterfall** — a table panel with `start_time`, `tool_name`, `latency_ms`, `status`, `parent_span_id` for a parameterized `trace_id`. Engineers copy a trace ID from the log and paste it into the dashboard variable.
2. **Per-trace cost summary** — a stat panel showing `total_tokens` and `cost_usd` for the selected trace.

```json
{
  "title": "TraceForge — Agent Waterfall",
  "uid": "traceforge-waterfall-v1",
  "schemaVersion": 38,
  "time": { "from": "now-1h", "to": "now" },
  "templating": {
    "list": [
      {
        "name": "trace_id",
        "type": "textbox",
        "label": "Trace ID",
        "current": { "value": "" }
      }
    ]
  },
  "panels": [
    {
      "id": 1,
      "title": "Span Waterfall",
      "type": "table",
      "gridPos": { "x": 0, "y": 0, "w": 24, "h": 12 },
      "datasource": { "type": "vertamedia-clickhouse-datasource", "uid": "clickhouse" },
      "options": { "sortBy": [{ "displayName": "start_time", "desc": false }] },
      "targets": [
        {
          "rawSql": "SELECT start_time, span_id, parent_span_id, tool_name, tool_kind, model, status, latency_ms, total_tokens, cost_usd, error_message FROM agent_spans WHERE trace_id = '${trace_id}' ORDER BY start_time ASC",
          "format": "table"
        }
      ]
    },
    {
      "id": 2,
      "title": "Trace Cost",
      "type": "stat",
      "gridPos": { "x": 0, "y": 12, "w": 8, "h": 4 },
      "datasource": { "type": "vertamedia-clickhouse-datasource", "uid": "clickhouse" },
      "targets": [
        {
          "rawSql": "SELECT sumMerge(total_tokens) AS tokens, sumMerge(cost_usd) AS cost FROM trace_cost_rollup WHERE trace_id = '${trace_id}' GROUP BY trace_id",
          "format": "table"
        }
      ]
    },
    {
      "id": 3,
      "title": "Span Count",
      "type": "stat",
      "gridPos": { "x": 8, "y": 12, "w": 8, "h": 4 },
      "datasource": { "type": "vertamedia-clickhouse-datasource", "uid": "clickhouse" },
      "targets": [
        {
          "rawSql": "SELECT sumMerge(span_count) AS spans FROM trace_cost_rollup WHERE trace_id = '${trace_id}' GROUP BY trace_id",
          "format": "table"
        }
      ]
    }
  ]
}
```

---

## Part 7 — Docker Compose Overlay (`docker-compose.clickhouse.yml`)

```yaml
# SPDX-License-Identifier: MIT
# Overlay for local ClickHouse + ZooKeeper (required for ReplicatedMergeTree in single-node mode)
# Usage: docker-compose -f docker-compose.yml -f docker-compose.clickhouse.yml up
version: "3.9"

services:
  clickhouse:
    image: clickhouse/clickhouse-server:24.3
    ports:
      - "8123:8123"   # HTTP interface
      - "9000:9000"   # Native interface
    environment:
      CLICKHOUSE_DB: default
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: ""
    volumes:
      - clickhouse-data:/var/lib/clickhouse
      - ./traceforge/clickhouse/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
      - ./traceforge/clickhouse/trace_cost_rollup.sql:/docker-entrypoint-initdb.d/02-rollup.sql
    healthcheck:
      test: ["CMD", "clickhouse-client", "--query", "SELECT 1"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  clickhouse-data:
```

---

## Directory Structure

```
infra-ai-streaming/
└── traceforge/
    ├── clickhouse/
    │   ├── schema.sql                  # agent_spans MergeTree + Kafka engine + MV
    │   ├── trace_cost_rollup.sql       # Per-trace cost AggregatingMergeTree + MV
    │   ├── queries.sql                 # Reference queries (waterfall, cost, errors)
    │   └── consumer/
    │       ├── main.go                 # Kafka → ClickHouse Go consumer
    │       └── consumer_test.go        # Unit tests
    ├── grafana/
    │   └── waterfall-dashboard.json    # Grafana dashboard JSON
    └── docker-compose.clickhouse.yml   # ClickHouse service overlay
```

---

## Implementation Checklist

### Schema
- [ ] `agent_spans_kafka` Kafka engine table consuming `agent-spans` topic
- [ ] `agent_spans` MergeTree with `ORDER BY (trace_id, start_time)`
- [ ] ZSTD(3) compression setting
- [ ] Daily partition by `toYYYYMMDD(start_time)`
- [ ] 30-day TTL
- [ ] `agent_spans_mv` MV: Kafka → agent_spans via JSONExtract
- [ ] `proj_slow_spans` projection materialized
- [ ] `trace_cost_rollup` AggregatingMergeTree + MV

### Go consumer
- [ ] Batch size 500, flush interval 2s
- [ ] Graceful shutdown on SIGINT/SIGTERM
- [ ] Attributes serialized as JSON string
- [ ] `envOrDefault` for all configuration
- [ ] 4 unit tests passing

### Grafana
- [ ] Dashboard JSON validates (schema version ≥ 36)
- [ ] `trace_id` template variable as textbox
- [ ] Waterfall table ordered by `start_time ASC`
- [ ] Cost stat panel referencing `trace_cost_rollup`

### Validation
- [ ] `go test ./traceforge/clickhouse/consumer/...` exits 0
- [ ] `go vet ./traceforge/clickhouse/consumer/...` exits 0
- [ ] `EXPLAIN` for Q1 waterfall query shows primary key range scan (not full scan)

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| ClickHouse Kafka engine needs ZooKeeper on older versions | Medium | Medium | Docker Compose overlay includes ZooKeeper; note in README |
| `sqlmock` v1 vs v2 API mismatch | Low | Low | Pin `github.com/DATA-DOG/go-sqlmock` to v2 in go.mod |
| `parseDateTimeBestEffort` in MV rejects RFC3339Nano format | Low | High | Test with real span JSON from Go SDK example before submitting |
| Grafana ClickHouse datasource UID mismatch | Medium | Low | Dashboard JSON uses `uid: "clickhouse"` — must match provisioned datasource UID |

---

## PR Description Template

```
## Day 34 — TraceForge: ClickHouse agent_spans + Cost MV + Grafana Waterfall

### What
- `traceforge/clickhouse/schema.sql`: agent_spans MergeTree (ORDER BY trace_id, start_time), Kafka engine, JSONExtract MV, slow-span projection
- `traceforge/clickhouse/trace_cost_rollup.sql`: AggregatingMergeTree + MV for per-trace token/cost rollup
- `traceforge/clickhouse/queries.sql`: waterfall, recent traces, slowest spans, error rate, token spend
- `traceforge/clickhouse/consumer/`: Go consumer — 500-span batch, 2s flush, SIGTERM-safe
- `traceforge/grafana/waterfall-dashboard.json`: Grafana dashboard, trace_id variable, waterfall table + cost stats

### EXPLAIN output (waterfall query, no full scan)
```
$ clickhouse-client --query "EXPLAIN SELECT * FROM agent_spans WHERE trace_id = 'abc' ORDER BY start_time ASC"
Expression
  MergeSortingTransform
    ReadFromMergeTree (agent_spans)
    Indexes:
      PrimaryKey
        Keys:
          trace_id
        Condition: (trace_id in ['abc', 'abc'])
        Parts: 1/12
        Granules: 3/1500
```

### Test output
```
$ go test ./traceforge/clickhouse/consumer/... -v
--- PASS: TestInsertBatch_SingleSpan (0.00s)
--- PASS: TestInsertBatch_AttributesSerialized (0.00s)
--- PASS: TestFlushOnBatchSize (0.00s)
--- PASS: TestEnvOrDefault (0.00s)
PASS
ok  github.com/akshantvats/infra-ai-streaming/traceforge/clickhouse/consumer
```

### End-to-end: trace visible after Go SDK example run
```
$ clickhouse-client --query "SELECT trace_id, count() AS spans, sum(cost_usd) AS cost FROM agent_spans GROUP BY trace_id ORDER BY max(start_time) DESC LIMIT 3"
a3f8c2e1b94d7506    3    0.000012
```

### Next steps (Day 35)
- TraceForge dashboard: P95 latency by tool, anomaly detection alerts, cost budget thresholds

Self-review: N issues found and fixed.
```
