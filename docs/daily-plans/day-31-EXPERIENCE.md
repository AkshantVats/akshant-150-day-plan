# Day 31 — Experience Blog Outline
## "Tool Calls Are RPCs With Marketing"
### Agoda · fan-out · retries

**Series**: Experience · Day 31 of 150
**Slug**: `day-31-tool-calls-are-rpcs-with-marketing`
**File**: `blog/series/experience/day-31-tool-calls-are-rpcs-with-marketing.html`
**Employer**: Agoda (WhiteFalcon TSDB) — cross-tier query fan-out, retry logic
**Bridge to code**: "Wrapping OpenAI today is no different from instrumenting an internal gRPC service — same span boundaries, different JSON. Today's code in agent-trace-collector implements that lesson."

---

## One-Line Summary

Every LLM tool call has a request, a response, a timeout, and a failure mode — exactly like a gRPC call — and the only thing separating them is the JSON envelope and a billing dashboard.

---

## Format Check

Before writing, count last 10 posts by format. This post is a **patterns** post — drawing structural parallels between two systems. Acceptable unless patterns count ≥ 4 of last 10.

---

## Employer Context — What to Use (MANDATORY)

Pull only from `agoda-whitefalcon-tsdb-architecture.md`:

- Cross-tier query engine: Akshant extended the Scala query engine to fan out to **both Redis (hot tier) and S3 cold tier** in a single request
- The fan-out is sequential in time but logically parallel — fetch histogram bucket counts from Redis (last 3h), fetch from S3 (hours 3–30), then merge
- Retry risk: if the cold-tier S3 fetch fails mid-flight and retries, a naive implementation double-counts histogram buckets → corrupts the P95 calculation
- The correct approach: treat each sub-request as a span with its own status, accumulate only on `OK` spans, discard on retry
- RoaringBitmap inverted index: tag-value → bitmap → series IDs — the fan-out of index lookups across tag filters (model=X AND cluster=Y) is also a set of concurrent RPC-like calls

Akshant attribution: cross-tier query extension — **he extended**, not designed. Original system by Agoda team.

Scale context allowed: 1.5T events/day, Redis hot tier (3–7 days), S3 cold tier.

Do NOT use: system names not in the doc, team member names, business logic.

---

## Core Argument

An OpenAI API call is a network call to an external service. It has:

| Property | Internal gRPC service | LLM tool call |
|---|---|---|
| Request | Protobuf message | JSON prompt |
| Response | Protobuf message | JSON completion |
| Latency | Nanoseconds to seconds | Seconds |
| Token cost | CPU cycles | USD/token |
| Failure modes | timeout, 5xx, network | timeout, rate limit, model error |
| Retry semantics | idempotent if you're careful | idempotent if you're careful |
| Tracing primitive | gRPC span with headers | HTTP span with attributes |

The span schema is identical. The "marketing" is the word "intelligence."

---

## Post Structure

### Opening hook (~3 sentences)

At Agoda, I added Kubernetes tags to WhiteFalcon's RoaringBitmap index. That meant extending the Scala query engine to fan out across two storage tiers — Redis for the last three hours, S3 for everything before that. The moment I had to handle a retry on the cold-tier fetch without corrupting the histogram merge, I realised I was writing span management code. I just didn't know it yet.

### Section 1 — The fan-out that taught me span boundaries

Walk through the WhiteFalcon cross-tier query:
- Single user request → Scala query engine fans out to Redis AND S3
- Each sub-request has its own timeout, its own error surface, its own latency
- The result is only valid when both `OK` — a partially returned result silently corrupts P95

**The bug**: first implementation retried the S3 fetch on 503 and summed the histograms twice. P95 looked fine — it was off by 8%.

**The fix**: treat each sub-request as an atomic unit. Track its status. Only merge `OK` results. Retry means a new sub-request span, not a re-run of the same one.

**So what**: this is span hygiene. It has nothing to do with AI.

### Section 2 — Now open your LLM gateway logs

An LLM tool call trace looks like this (draw from Day 31 code context):

```
trace_id: 4bf92f3577b34da6a3ce929d0e0e4736
├── model_call (root)          tool_kind=model_call   latency=2100ms  tokens=850  cost=$0.0034
│   ├── Read file.py           tool_kind=file_io       latency=12ms
│   ├── Bash: cargo test       tool_kind=code_exec     latency=4200ms
│   └── Edit main.rs           tool_kind=file_io       latency=8ms
```

The model call is the gRPC entry point. The tool calls are sub-RPCs it issues. Each has a parent span (the model call), its own `span_id`, its own latency and status. A `Bash` tool call that times out produces an ERROR span, the same way an S3 fetch that 503s produces an error sub-request.

**The difference**: nobody calls an S3 timeout "the model thinking." Everyone calls a 30-second Bash timeout "slow." Same thing.

### Section 3 — The retry double-count returns in a new form

At WhiteFalcon: retry → histogram added twice → P95 wrong.

In an agent: sub-agent retried by orchestrator → tool call emitted twice → token count doubled → cost report wrong.

The fix is the same: each attempt is its own span. First attempt: `status=ERROR`. Retry attempt: new `span_id`, new `status=OK`. Do not sum costs across the same logical operation — sum across distinct `span_id` values.

TraceForge's `parent_span_id` field exists precisely to let you reconstruct the retry chain. A query that groups by `trace_id` and sums `cost_usd` without checking for retries will overcount. The index was histograms; the agent is tokens. The shape of the bug is identical.

**So what**: the lesson from WhiteFalcon didn't need 18 months of unlearning — it transferred immediately when I needed to design the TraceForge span schema.

### Section 4 — What the bridge looks like in Go

Show the `Span` struct from Day 30 / Day 31 code — highlight that `status`, `latency_ms`, `parent_span_id` are the same fields you'd put in a gRPC span. No magic fields for "AI." No separate schema for "intelligence."

A 3-sentence comparison:
- gRPC: `metadata.Set("x-b3-traceid", ...)` + `metadata.Set("x-b3-spanid", ...)` → Zipkin
- OTel HTTP: `traceparent` header → Jaeger
- LLM tool call: `trace_id` + `span_id` in JSON body → ClickHouse via TraceForge

Same structure. Different wire format. TraceForge just adds the missing adapter.

### Section 5 — The one thing that's different

Token cost has no equivalent in standard RPC tracing. A gRPC call's "cost" is server CPU time, tracked in your infrastructure billing. An LLM call's cost is immediate, per-call, and denominated in USD.

This is the only genuinely new field: `cost_usd`. Everything else is borrowed from 10 years of distributed tracing practice.

The implication: any observability team that already runs Jaeger or Tempo can instrument LLM calls by adding one field to their existing span schema. They don't need a new platform. They need `cost_usd` and a way to populate it.

### Closing bridge to code

Day 31's agent-trace-collector wires the full pipeline: HTTP endpoint receives spans, normalises them to the canonical schema (nine fields, same as a gRPC span plus `cost_usd`), and forwards to an OTel Collector already running in the LensAI quickstart. The Collector routes to ClickHouse and back to Kafka — the same fan-out pattern WhiteFalcon used, now for agent spans instead of TSDB histograms.

**Closing sentence**: The system names changed. The span boundaries didn't.

---

## Mermaid Diagram Plan

One diagram illustrating the Agoda fan-out pattern → TraceForge parallel:

```
%%{init: {\n  'theme': 'base',\n  'themeVariables': {\n    'primaryColor': '#1e3a5f',\n    'primaryTextColor': '#f0f4f8',\n    'primaryBorderColor': '#4a90d9',\n    'lineColor': '#4a90d9',\n    'secondaryColor': '#0d2137',\n    'tertiaryColor': '#0a1a2e',\n    'background': 'transparent',\n    'nodeBorder': '#4a90d9',\n    'clusterBkg': '#0d2137',\n    'titleColor': '#f0f4f8',\n    'edgeLabelBackground': '#0d2137'\n  }\n}}%%
flowchart TD
    A["User query"] --> B["Scala query engine"]
    B --> C["Redis hot tier\n(last 3h)"]
    B --> D["S3 cold tier\n(hours 3-30)"]
    C --> E["Merge histograms\n(on both OK)"]
    D --> E
    E --> F["P95 result"]
```

Second diagram (optional if needed): agent span tree mirroring the fan-out structure.

---

## Voice Checklist (pre-draft)

- [ ] First person throughout: "I extended...", "I realised...", "I had to..."
- [ ] Max 3 sentences per paragraph
- [ ] One concrete analogy: histogram-merge bug → token double-count
- [ ] Every section ends with a "so what" sentence
- [ ] No bullet-list substitutes for prose (lists only for the comparison table in Section 1)
- [ ] No unexplained jargon: "RoaringBitmap" gets one definition sentence on first use
- [ ] "WhiteFalcon" attributed to Agoda team on first mention; Akshant's role: "I extended the query engine"
- [ ] Day 31 in `<title>`, `<h1>`, accent tag, meta line — all four locations

---

## Series Nav

Previous: Day 30 — Step 7 Failed Silently (Delivery Hero · async pipelines · visibility)
URL: `blog/series/experience/day-30-step-7-failed-silently-no-span.html`

Next: Day 32 (pending)

Retrofix Day 30 Experience post footer to link to Day 31.

---

## Self-Review Checklist (before push)

- [ ] `Day 31` in `<title>`: `Day 31 — Tool Calls Are RPCs With Marketing | Experience Series`
- [ ] `Day 31` in `<h1>`: `Day 31 — Tool Calls Are RPCs With Marketing`
- [ ] Accent tag: `Experience · Day 31 of 150`
- [ ] Meta line: `Experience · Day 31 of 150`
- [ ] Series footer: `Experience · Day 31 of 150`
- [ ] Mermaid init block exact match
- [ ] Node labels ≤ 6 words
- [ ] ≤ 8 nodes per diagram
- [ ] All Agoda facts match `agoda-whitefalcon-tsdb-architecture.md`
- [ ] No scale numbers invented (1.5T events/day max)
- [ ] HTML div balance
- [ ] No `</motion.div>` tags
- [ ] No nested `<a>` tags
- [ ] `class="prose"` present
- [ ] Series nav CSS: `.series-nav`, `.series-posts`, `.series-post`
