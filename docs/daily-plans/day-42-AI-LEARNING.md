# Day 42 — AI Learning Blog Outline
## "Day 42 — Unified Billing Events — One Envelope"
### Same ingest schema for inference and tools

**Series**: AI Learning · Day 42 of 150
**Slug**: `day-42-unified-billing-events-one-envelope`
**File**: `blog/series/ai-learning/day-42-unified-billing-events-one-envelope.html`
**Live URL**: `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-42-unified-billing-events-one-envelope.html`

---

## Title Block

```
<title>Day 42 — Unified Billing Events — One Envelope | AI Learning Series</title>
Accent chip: AI Learning · Day 42 of 150
<h1 class="post-title">Day 42 — Unified Billing Events — One Envelope</h1>
Meta line: AI Learning · Day 42 of 150
Series footer: Day 42 of 150 — Unified Billing Events — One Envelope
```

---

## Hook (first paragraph)

An agent's cost comes from two places: inference calls to a model API and tool calls to external services. In most observability setups, these land in different tables, different dashboards, and different budget owners. The inference team looks at token usage. The infrastructure team looks at tool latency. Nobody looks at a trace and sees the total spend. The join that would answer "what did this one customer request actually cost us?" doesn't exist — because the two systems never agreed on an envelope. Today's code adds a BillingEvent struct that both systems emit. tenant_id + trace_id is the join key. One envelope makes the join possible.

---

## Section 1 — Why Two Systems Can't Share a Dashboard Today

### The schema divergence problem
LensAI tracks inference: model, token_count, prompt_tokens, completion_tokens, cost_usd, latency_ms. tool-call-analyzer tracks tool calls: tool_name, vendor, span_id, duration_ms, cost_usd, trace_id. Both have cost_usd. Neither has the other's primary identifier. You can't JOIN them without a shared key that both systems populate at write time.

### The tenant visibility problem
Multi-tenant agent systems need per-tenant cost breakdowns: "how much did tenant_id T17 spend this week on inference versus tool calls?" Without a unified envelope, you run two queries, get two numbers, and add them in a spreadsheet. That's not a dashboard. That's manual accounting.

### What a unified envelope changes
A unified envelope is a single JSON schema that both systems write to the same ClickHouse table (or two tables with identical schemas). The fields that matter for cost attribution — tenant_id, trace_id, span_id, source, cost_usd — are the same regardless of whether the event came from a model API call or a web search tool. Everything else is optional context. The shared keys are what make the JOIN work.

### So what
Schema divergence between observability systems is not a data engineering problem. It's an agreement problem. Once both teams agree on the envelope — even if the extra fields differ — every dashboard, query, and alert can be written once and applied to both data sources simultaneously.

---

## Section 2 — The BillingEvent Envelope Design

### The nine fields

```json
{
  "tenant_id":    "t17",
  "trace_id":     "7f3d9a2e-1234-5678-abcd-ef0123456789",
  "span_id":      "a1b2c3d4",
  "source":       "tool",
  "tool_name":    "search_web",
  "vendor":       "openai",
  "cost_usd":     0.0031,
  "duration_ms":  380,
  "timestamp_ns": 1721234567890000000
}
```

For an inference event, `source="inference"`, `tool_name=""`, `vendor="anthropic"` (or whichever model vendor), and `cost_usd` is computed from token counts. The struct is identical. The source field tells downstream consumers which event type they're reading.

### Why source over separate tables
Separate tables feel cleaner until you need to query across them. A single table with a source discriminator column keeps every cost query as a simple `WHERE tenant_id = ? AND trace_id = ?` without UNION. ClickHouse handles the discriminator filter efficiently — it's a low-cardinality string column, not a nullable type.

### Why tenant_id matters as much as trace_id
trace_id answers "what happened in this request?" tenant_id answers "who owns this cost?" For an agent platform, tenant is the billing unit. A tenant might generate thousands of traces per day. Aggregating by tenant_id gives the invoice line item. Joining on trace_id gives the individual request breakdown. Both are necessary. Neither is sufficient alone.

### Mermaid diagram — unified envelope flow

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
graph LR
  LensAI["LensAI SDK\nsource=inference"]
  TA["tool-call-analyzer\nsource=tool"]
  ENV["BillingEvent\ntenant_id+trace_id"]
  CH["ClickHouse\nbilling_events"]
  GR["Grafana\nUnified Board"]

  LensAI -->|"emit"| ENV
  TA -->|"dual-write"| ENV
  ENV --> CH
  CH --> GR
```

### So what
The envelope doesn't eliminate the difference between inference and tool calls. It makes the difference navigable. The source field tells you which system produced the event. The shared fields let you aggregate them together. You get both: event-type detail and cross-system totals.

---

## Section 3 — Dual-Write: Fire-and-Forget

### The design constraint
tool-call-analyzer's primary write path is ClickHouse. Adding LensAI ingest as a second destination must not gate ClickHouse writes. If LensAI is down, tool spans still land in ClickHouse. If LensAI is slow, tool span writes still complete in under 50ms. The dual-write is additive, not dependent.

### Fire-and-forget in Go
```go
func Send(ev BillingEvent) {
    url := os.Getenv("LENSAI_INGEST_URL")
    if url == "" {
        return
    }
    go func() {
        body, _ := json.Marshal(ev)
        ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
        defer cancel()
        req, _ := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
        req.Header.Set("Content-Type", "application/json")
        resp, err := http.DefaultClient.Do(req)
        if err != nil {
            return
        }
        resp.Body.Close()
    }()
}
```

The goroutine carries a 2-second context deadline. If LensAI doesn't respond in 2 seconds, the goroutine exits cleanly — no leak, no blocked caller.

### Why not retry
LensAI ingest is idempotent: span_id is the dedup key. A span that fails to arrive at LensAI on the first attempt will be visible as a gap in the tenant's inference-vs-tool breakdown — but it won't produce a duplicate cost entry if a retry arrives later. The tradeoff: we accept occasional gaps at LensAI in exchange for never blocking the ClickHouse write path. For billing, gaps are visible and recoverable. Latency spikes in the write path are invisible and compounding.

### The no-op path
If `LENSAI_INGEST_URL` is unset, `Send()` returns immediately without spawning a goroutine. This makes the dual-write optional: tool-call-analyzer works in isolation (no LensAI dependency) and integrates with LensAI only when the env var is present.

### Physical analogy
Dual-write is like mailing a copy of every invoice to your accountant while the original goes to the client. The client's invoice is what matters. The accountant copy is useful for aggregation but the business doesn't stop if one gets lost in the post. You don't delay shipping the invoice to the client while waiting for confirmation that the accountant received their copy.

### So what
Fire-and-forget dual-write is the correct pattern whenever the secondary destination is observability infrastructure rather than primary business data. The primary write (ClickHouse tool spans) must always succeed. The secondary write (LensAI billing events) is best-effort. Treating them identically — both blocking, both retried — couples your tool write path to LensAI availability. That's the wrong coupling direction.

---

## Section 4 — The Unified Grafana Board

### What the board contains

```
Row 1 — Inference (LensAI datasource)
  [Stat]        Total inference cost today (filtered by $tenant_id)
  [Bar Gauge]   Cost breakdown by model
  [Time Series] Token usage over time

Row 2 — Tools (TraceForge ClickHouse datasource)
  [Bar Gauge]   Cost waterfall by tool name
  [Time Series] Exclusive time P99 trend by tool
  [Stat]        N+1 alerts fired today
```

Every panel filters on the same `$tenant_id` Grafana template variable. Switch the variable to T17 and both rows update simultaneously. The inference row shows T17's model spend. The tool row shows T17's tool spend. Total cost for T17 = stat from row 1 + stat from row 2.

### The JOIN that doesn't require a JOIN
Grafana panels from two datasources don't JOIN in the database — they JOIN in the viewer's eye. The `$tenant_id` variable makes both panels show the same tenant simultaneously. The user reads the total by adding two numbers. For most purposes (team review, budget conversation, anomaly detection), visual juxtaposition is sufficient. The SQL JOIN is needed only when you want a single number in a single query — for invoice generation, not for the weekly review dashboard.

### Mermaid diagram — unified board structure

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
graph TD
  VAR["$tenant_id\nGrafana variable"]
  R1["Row 1 — Inference\nLensAI datasource"]
  R2["Row 2 — Tools\nTraceForge datasource"]
  GR["Grafana Board"]

  VAR --> R1
  VAR --> R2
  R1 --> GR
  R2 --> GR
```

### Why generate the board as JSON in Go
Grafana dashboards are JSON files. You can click-and-drag panels or generate the JSON programmatically. For a project like TraceForge — where the board structure is deterministic (same panels, same datasource mappings, same variable) across every deployment — generating it in Go means the board is versioned alongside the code that produces the data. A change to the ClickHouse schema triggers a change to the board generator, not a manual Grafana edit.

### So what
Unified observability doesn't require a unified database. It requires a unified variable (tenant_id) and two datasources configured in the same Grafana instance. The board generator is the artifact that encodes that agreement: one command produces a ready-to-import dashboard JSON that surfaces both systems together.

---

## Section 5 — What tenant_id + trace_id Makes Possible

### The query that wasn't possible before
```sql
SELECT
    tenant_id,
    SUM(cost_usd) FILTER (WHERE source = 'inference') AS inference_cost,
    SUM(cost_usd) FILTER (WHERE source = 'tool')      AS tool_cost,
    SUM(cost_usd)                                      AS total_cost
FROM billing_events
WHERE tenant_id = 'T17'
  AND toDate(timestamp_ns / 1e9) = today()
GROUP BY tenant_id
```

This query requires both inference and tool events in the same table with the same schema. Before the unified envelope, this was two queries with a manual sum.

### The per-trace breakdown
```sql
SELECT
    trace_id,
    SUM(cost_usd) FILTER (WHERE source = 'inference') AS inference_cost,
    SUM(cost_usd) FILTER (WHERE source = 'tool')      AS tool_cost
FROM billing_events
WHERE tenant_id = 'T17'
ORDER BY (inference_cost + tool_cost) DESC
LIMIT 10
```

This surfaces the ten most expensive traces for tenant T17 today — across both systems. It shows whether the expensive traces are inference-heavy (GPT-4 calls), tool-heavy (many web searches), or balanced. That breakdown drives different optimizations.

### What changes at the product level
When every API call a tenant makes produces a BillingEvent, the invoice is a SELECT. There's no reconciliation process, no monthly aggregation job, no gap-filling script. The billing envelope is the invoice record. The unified table is the billing database. TraceForge's dual-write is the first step toward that.

### So what
tenant_id + trace_id is not metadata. It's the schema decision that converts an observability system into a billing system. The BillingEvent envelope makes that conversion possible without rebuilding either LensAI or tool-call-analyzer's primary write paths.

---

## Series Navigation Footer

Previous: Day 41 — Cost Waterfalls — CFO-Friendly Visuals
Next: Day 43 — (coming)

---

## HTML Checklist Before Push

- [ ] `Day 42` in `<title>`, `<h1>`, accent chip, meta line, series footer
- [ ] `class="series-nav"` / `class="series-posts"` / `class="series-post"` CSS present
- [ ] Mermaid init block exact (no variations) — appears twice above
- [ ] No node labels > 6 words
- [ ] All `<div>` opens match `</div>` closes
- [ ] No `</motion.div>` tags
- [ ] No `<a>` nested inside `<a>`
- [ ] Max 3 sentences per paragraph
- [ ] No placeholder URLs (`example.com`, `TODO`, `localhost`)
