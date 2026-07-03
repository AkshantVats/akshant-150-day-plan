# Day 31 — AI Learning Blog Outline
## "Day 31 — OpenTelemetry Semantics for Agents"
### Span kinds, attributes, and what to standardize now

**Series**: AI Learning · Day 31 of 150
**Slug**: `day-31-opentelemetry-semantics-for-agents`
**File**: `blog/series/ai-learning/day-31-opentelemetry-semantics-for-agents.html`
**Hook**: Align attribute names with your ClickHouse columns before v1 ships.

---

## One-Line Summary

OpenTelemetry has semantic conventions for HTTP, databases, and messaging — but not yet for agents. This post covers what OTel gives you for free, where the agent model fits, and which three attribute names to agree on before your first ClickHouse table ships.

---

## Format Check

Before writing, count last 10 posts by format. This is a **deep-dive / patterns** post — explaining a specification and its application. Acceptable unless deep-dive count ≥ 4 of last 10.

---

## Background Reading

- OTel semantic conventions: `semconv.dev` — HTTP, database, messaging specs
- OTel GenAI SIG: in-progress `gen_ai.*` conventions (LLM usage attributes)
- Day 30 TraceForge DESIGN.md: span schema already established, attribute names chosen

Key context: The OpenTelemetry GenAI SIG is actively drafting `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.system` etc. Day 31 posts should acknowledge this and explain why TraceForge uses `traceforge.*` namespace for now — pinning to a moving standard is risky before it's stable.

---

## Core Argument

OTel span semantics fall into three layers:
1. **Identity** — `trace_id`, `span_id`, `parent_span_id` (stable, universal)
2. **Classification** — `SpanKind`, `SpanStatus` (stable, universal)
3. **Domain attributes** — `http.method`, `db.system`, `gen_ai.usage.input_tokens` (domain-specific, evolving)

For agents, layers 1 and 2 are free — use them directly. Layer 3 is where you make choices today that get expensive to change later. The question is not "should I use OTel?" (yes) but "which attribute names are stable enough to put in my ClickHouse `ORDER BY`?"

---

## Post Structure

### Opening hook (~3 paragraphs)

Set the scene: you're building an agent and you want to trace it. You reach for OpenTelemetry because you already use it for your HTTP services. You find spec pages for `http.method`, `db.statement`, `messaging.system`. Then you search for `llm.` or `agent.` and find a GitHub issue with 47 comments and no resolution.

This is not a complaint. It's actually the right moment to be here — the standard is being written and your implementation choices influence it. The concrete question: which attributes do you hardcode into your ClickHouse `CREATE TABLE` today, knowing you'll be reading them in two years?

This post is the answer I arrived at while building TraceForge.

### Section 1 — What OTel gives you without any standard

**Identity layer** — universal, use directly:
- Every span has a `TraceId` (128-bit) and `SpanId` (64-bit). These are wire format, not semantic. A Jaeger instance receiving your agent spans via OTLP will reconstruct the waterfall tree from these two fields alone. No convention needed.
- `ParentSpanId` is empty for root spans. The tree structure is implicit in these three fields — no "is_root" boolean needed.

**Classification layer** — four `SpanKind` values matter for agents:
- `INTERNAL` — a step inside your own agent process (tool dispatch logic, planning loop)
- `CLIENT` — an outgoing call to an external service (LLM API, vector DB, any HTTP call)
- `SERVER` — your agent acting as a server (receiving a request from an orchestrator)
- `PRODUCER` — emitting a span to a queue (Kafka, SQS)

For a Claude Code agent: the top-level model call is `CLIENT` (your code calls the Anthropic API). The tool calls dispatched by the model are `INTERNAL` (your agent orchestrator dispatches them). A sub-agent spawn that sends work over a message queue is `PRODUCER`.

**So what**: you get the waterfall view "for free" with just `trace_id`, `span_id`, `parent_span_id`, and `SpanKind`. Jaeger and Grafana Tempo will visualise it correctly with no additional convention.

### Section 2 — The DS analogy: attributes are Kafka message headers

Kafka message headers carry arbitrary key-value pairs alongside the payload. You can add a header without changing the message schema — the consumer code that doesn't read the new header is unaffected. You remove a header the same way. Headers are the extensibility mechanism.

OTel span attributes are the same thing. A span's identity and timing are fixed in the wire format (trace_id, span_id, start_time, end_time, status). Attributes are arbitrary key-value pairs you attach. You can add `traceforge.cost.usd` to every span today without touching the consumers that only read `http.method`.

The difference: Kafka headers are opaque bytes; OTel attributes are typed (string, int, double, bool, array). And OTel has semantic conventions — agreed attribute names — so two teams independently instrumenting their LLM calls end up with comparable data.

**So what**: attributes let you evolve your instrumentation without schema migration, as long as you don't put a mutable attribute in your ClickHouse `ORDER BY`.

### Section 3 — Where the standard is today (GenAI SIG)

The OpenTelemetry GenAI SIG is drafting semantic conventions for LLM calls. The current proposal (as of mid-2026, still in-progress draft) includes:

| Attribute | Type | Meaning |
|---|---|---|
| `gen_ai.system` | string | LLM provider: `openai`, `anthropic`, `vertexai` |
| `gen_ai.request.model` | string | Requested model ID |
| `gen_ai.response.model` | string | Actual model ID used (may differ from requested) |
| `gen_ai.usage.input_tokens` | int | Prompt tokens |
| `gen_ai.usage.output_tokens` | int | Completion tokens |
| `gen_ai.operation.name` | string | `chat`, `text_completion`, `embeddings` |

This is a good start. It covers the model call span — the single LLM API invocation. What it doesn't yet cover:
- Tool calls as child spans of a model call
- Sub-agent invocations
- Tool kind taxonomy (retrieval vs code_exec vs browser)
- Cost in USD (a business attribute, not purely a technical one)

**So what**: use `gen_ai.*` for model call spans when it's stable. For everything else, use a project namespace (`traceforge.*`) until the standard catches up.

### Section 4 — The three attributes to lock in before v1

The question isn't "follow the standard" vs "use your own names." It's: which attributes are you putting in a ClickHouse `ORDER BY` or `PRIMARY KEY`? Those are the ones that hurt to rename.

In TraceForge's `lensai.agent_spans` table, the `ORDER BY` is `(started_at, trace_id, span_id)`. These are OTel identity fields — never changing.

The three mutable attributes that deserve a stable name early:

**1. `tool_kind`** (LowCardinality string in ClickHouse)
This is the column most likely to drive `GROUP BY` in cost queries: "total cost by tool category." Lock in the enum values now: `retrieval`, `code_execution`, `browser`, `file_io`, `sub_agent`, `model_call`, `unknown`. Adding values is cheap; renaming breaks queries.

**2. `model`** (string)
Every cost query has "group by model." The value format matters: use the full model ID (`claude-sonnet-4-6`, not `claude-sonnet` or `sonnet`) because you will eventually want to compare cost across patch versions of the same model family.

**3. `cost_usd`** (Float64)
The OTel GenAI SIG draft does not include cost in USD — it's considered a business attribute, not a technical one. It belongs in your namespace. TraceForge uses `traceforge.cost.usd`. Whatever you call it, it must be a ClickHouse column (not buried in an attributes map) because you'll run sum queries on it constantly.

Everything else — input_tokens, output_tokens, error_message, attributes — can live in an `Attributes` map and be promoted to columns later without breaking existing queries.

**So what**: the three stable attributes are `tool_kind`, `model`, and `cost_usd`. Everything else is a ClickHouse migration away.

### Section 5 — Practical: the span a Claude Code agent should emit

Show a complete example span in JSON matching the TraceForge schema:

```json
{
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "parent_span_id": "1234567890abcdef",
  "tool_name": "Bash",
  "tool_kind": "code_execution",
  "model": "",
  "status": "OK",
  "start_time": "2026-07-04T02:00:00.000Z",
  "latency_ms": 4200,
  "input_tokens": 0,
  "output_tokens": 0,
  "total_tokens": 0,
  "cost_usd": 0.0,
  "attributes": {
    "traceforge.bash.exit_code": "0",
    "traceforge.bash.command_preview": "cargo test --lib"
  }
}
```

And the parent model call span:

```json
{
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "1234567890abcdef",
  "parent_span_id": "",
  "tool_name": "claude-sonnet-4-6",
  "tool_kind": "model_call",
  "model": "claude-sonnet-4-6",
  "status": "OK",
  "start_time": "2026-07-04T01:59:57.500Z",
  "latency_ms": 7800,
  "input_tokens": 12400,
  "output_tokens": 850,
  "total_tokens": 13250,
  "cost_usd": 0.053,
  "attributes": {
    "gen_ai.system": "anthropic",
    "gen_ai.request.model": "claude-sonnet-4-6"
  }
}
```

Note: the model call span includes `gen_ai.*` attributes alongside `traceforge.*` because those fields are stable enough and Jaeger/Tempo already know how to display them.

### Section 6 — The ClickHouse query this unlocks

```sql
-- Cost by tool kind, last 7 days
SELECT
    tool_kind,
    count()              AS span_count,
    sum(total_tokens)    AS total_tokens,
    sum(cost_usd)        AS total_cost_usd,
    avg(latency_ms)      AS avg_latency_ms
FROM lensai.agent_spans
WHERE started_at >= now() - INTERVAL 7 DAY
GROUP BY tool_kind
ORDER BY total_cost_usd DESC;
```

Without `tool_kind` as a first-class column (not buried in an attributes JSON blob), this query either doesn't run or runs 100x slower. This is why `tool_kind` is one of the three attributes you lock in before v1.

**Closing sentence**: You can argue about attribute names — traceforge vs gen_ai, tokens vs usage — but the query above works regardless of the prefix, as long as you chose one before the table shipped.

---

## Mermaid Diagram Plan

### Diagram 1 — OTel span anatomy for an agent run

```
%%{init: {\n  'theme': 'base',\n  'themeVariables': {\n    'primaryColor': '#1e3a5f',\n    'primaryTextColor': '#f0f4f8',\n    'primaryBorderColor': '#4a90d9',\n    'lineColor': '#4a90d9',\n    'secondaryColor': '#0d2137',\n    'tertiaryColor': '#0a1a2e',\n    'background': 'transparent',\n    'nodeBorder': '#4a90d9',\n    'clusterBkg': '#0d2137',\n    'titleColor': '#f0f4f8',\n    'edgeLabelBackground': '#0d2137'\n  }\n}}%%
flowchart TD
    A["trace_id (root)"] --> B["model_call span\nSpanKind=CLIENT"]
    B --> C["file_io span\nSpanKind=INTERNAL"]
    B --> D["code_exec span\nSpanKind=INTERNAL"]
    B --> E["sub_agent span\nSpanKind=PRODUCER"]
    E --> F["child model_call\nSpanKind=CLIENT"]
```

### Diagram 2 — Attribute layers (stable vs evolving)

```
%%{init: {\n  'theme': 'base',\n  'themeVariables': {\n    'primaryColor': '#1e3a5f',\n    'primaryTextColor': '#f0f4f8',\n    'primaryBorderColor': '#4a90d9',\n    'lineColor': '#4a90d9',\n    'secondaryColor': '#0d2137',\n    'tertiaryColor': '#0a1a2e',\n    'background': 'transparent',\n    'nodeBorder': '#4a90d9',\n    'clusterBkg': '#0d2137',\n    'titleColor': '#f0f4f8',\n    'edgeLabelBackground': '#0d2137'\n  }\n}}%%
flowchart LR
    A["OTel wire format\ntrace_id · span_id"] --> B["Stable — never rename"]
    C["gen_ai.* attributes\nmodel call only"] --> D["Stable when SIG ships"]
    E["traceforge.* attributes\ntool_kind · cost_usd"] --> F["Lock in before v1"]
    G["Custom attributes\nerror · metadata"] --> H["Evolve freely"]
```

---

## Voice Checklist (pre-draft)

- [ ] First person: "I arrived at...", "I chose...", "the question I kept hitting..."
- [ ] Max 3 sentences per paragraph
- [ ] Kafka header analogy fully developed in Section 2
- [ ] Every section ends with "so what" sentence
- [ ] No bullet lists substituting for prose (the attribute table in Section 3 is a table, not a list)
- [ ] All OTel terms defined on first use (SpanKind, semantic conventions)
- [ ] ClickHouse DDL in Section 6 matches `002_agent_spans.sql` from Day 31 CODE.md

---

## Series Nav

Previous: Day 30 — ReAct Loops as Distributed Workflows
URL: `blog/series/ai-learning/day-30-react-loops-distributed-workflows.html`

Next: Day 32 (pending)

Retrofix Day 30 AI Learning post footer to link to Day 31.

---

## Self-Review Checklist (before push)

- [ ] `Day 31` in `<title>`: `Day 31 — OpenTelemetry Semantics for Agents | AI Learning Series`
- [ ] `Day 31` in `<h1>`: `Day 31 — OpenTelemetry Semantics for Agents`
- [ ] Accent tag: `AI Learning · Day 31 of 150`
- [ ] Meta line: `AI Learning · Day 31 of 150`
- [ ] Series footer: `Day 31 of 150 — OpenTelemetry Semantics for Agents`
- [ ] Mermaid init block exact match (both diagrams)
- [ ] Node labels ≤ 6 words
- [ ] ≤ 8 nodes per diagram
- [ ] HTML div balance
- [ ] No `</motion.div>` tags
- [ ] No nested `<a>` tags
- [ ] `class="prose"` present
- [ ] Series nav CSS: `.series-nav`, `.series-posts`, `.series-post`
- [ ] ClickHouse SQL in Section 6 matches DDL from Day 31 CODE.md
- [ ] OTel GenAI SIG attributes referenced as "in-progress draft" — not presented as final standard
