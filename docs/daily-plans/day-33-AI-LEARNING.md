# Day 33 — AI Learning Blog Outline
## "Day 33 — Context Propagation in Polyglot Agents"

**Calendar**: Sunday, 6 July 2026 · Day 33 of 150
**Series**: AI Learning
**Topic**: W3C TraceContext — propagating trace IDs across Python and Go service boundaries
**Hook**: "Broken context = broken parent_span_id = useless waterfall."
**Bridge to code**: Today's Go SDK implements `InjectTraceContext`/`ExtractTraceContext` in `traceforge/sdk/go/traceforge/propagation.go`
**Format**: deep-dive / how-it-works

---

## Post Title

**Day 33 — Context Propagation in Polyglot Agents**

Accent tag chip: `AI Learning · Day 33 of 150`

Subtitle: *W3C tracecontext through Python and Go — or why your agent waterfall looks like a bowl of spaghetti*

---

## Thread

> SDK Wrappers meets Context Propagation in Polyglot Agents in today's agent-trace-collector Go SDK commit.

---

## Narrative Arc

The post starts with the broken waterfall — the reader knows what a trace waterfall is supposed to look like (nested, sequential, causal), and we show them why it breaks in a polyglot agent. Then we explain the W3C TraceContext spec as the solution, implement it in two languages, and close with the distributed systems analogy.

---

## Section-by-Section Outline

### 0. Opening hook (no heading — first ≤3 sentences)

> A Python agent calls a Go tool. The tool finishes in 40ms. Your Grafana dashboard shows two disconnected spans with different trace IDs, sitting on separate rows, with no visual relationship between them. The waterfall is useless.
>
> The data is there. The relationship isn't — because nothing told the Go tool which trace it was part of.

### 1. Why traces break at language boundaries

**Heading**: "The scope problem"

Within a single Python process, context propagates automatically via `contextvars.ContextVar`. The trace ID lives in the thread (or async) local state. Every function call within that process inherits the same trace ID.

The moment you make an HTTP call to a Go tool, you're leaving that process. Go has no idea what Python's context looks like. It starts a fresh span with a new, unrelated trace ID.

**Analogy**: Imagine a relay race where each runner carries a baton — but when the track crosses a national border, the customs officer takes the baton for inspection and hands the next runner a brand-new one. Each leg of the race is timed correctly, but the splits can't be assembled into a total.

One "so what": the trace ID must travel explicitly in the HTTP request, not implicitly in memory.

### 2. W3C TraceContext — the specification

**Heading**: "The `traceparent` header"

The W3C TraceContext specification (RFC 7230 compliant, widely adopted since 2020) defines a single HTTP header that carries the trace context across service boundaries:

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

Four fields, dash-separated:
1. **Version** (`00`) — always `00` in the current spec
2. **Trace ID** (32 hex chars = 128 bits) — the global conversation identifier
3. **Parent Span ID** (16 hex chars = 64 bits) — the span ID of the caller
4. **Trace flags** (`01`) — bit 0 = sampled (1 = record this trace)

Any service that reads this header and creates a new span:
- Copies the **trace ID** unchanged
- Uses the incoming **parent span ID** as its own `parent_span_id`
- Generates a fresh **span ID** for itself

One "so what": the header is the baton — the relay race works even across national borders.

### 3. Inject: writing the header on the way out

**Heading**: "The caller's job"

When the Python agent calls the Go tool over HTTP, it must inject the `traceparent` header before sending the request. In the TraceForge Python SDK (Day 32), the active span lives on a context object. The inject function reads it and writes the header:

```python
# inject_trace_context(span: Span, headers: dict) -> None
traceparent = f"00-{span.trace_id}-{span.span_id}-01"
headers["traceparent"] = traceparent
```

Three fields taken from the *caller's* span:
- `trace_id` — propagates the global conversation
- `span_id` — becomes the `parent_span_id` on the receiver's side
- Flags — always `01` (sampled)

The caller's span ID is what creates the parent-child relationship on the waterfall. Without it, the Go span appears as a root span with no parent.

### 4. Extract: reading the header on the way in

**Heading**: "The receiver's job"

The Go tool receives the request. Before processing, it extracts the `traceparent` header and creates a new span that inherits the trace ID:

```go
// ExtractTraceContext(ctx, http.Header) context.Context
parts := strings.Split(h.Get("traceparent"), "-")
// parts[1] = trace_id, parts[2] = parent_span_id
ctx, span := tf.StartSpan(ctx, "weather_lookup")
// StartSpan sees the inherited trace_id and sets parent_span_id from the header
```

The Go span gets:
- **Same `trace_id`** as the Python span — they're in the same conversation
- **`parent_span_id`** = the Python span's `span_id` — explicit parent pointer

On the waterfall, the Go span now appears nested under the Python span, connected by that pointer.

### 5. The full polyglot trace

**Heading**: "What the waterfall looks like now"

Before propagation: two disconnected spans, different trace IDs, no relationship.

After propagation: a connected waterfall showing causality:

```
[Python agent_turn — 180ms trace_id: 4bf9...]
  ├─ [Go weather_lookup — 40ms parent: a3ce...]
  └─ [Go unit_conversion — 2ms parent: a3ce...]
```

The Python span is the root. The Go spans are children. The timeline shows the Go calls happened within the Python turn. Duration adds up. You can debug the 180ms latency.

#### Mermaid diagram: context propagation flow

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
sequenceDiagram
    participant Py as Python Agent
    participant Go as Go Tool (HTTP)
    participant Col as Collector

    Py->>Py: StartSpan("agent_turn") → trace_id=4bf9, span_id=a3ce
    Py->>Go: POST /weather\ntraceparent: 00-4bf9...-a3ce...-01
    Go->>Go: ExtractTraceContext → parent=(4bf9, a3ce)
    Go->>Go: StartSpan("weather_lookup") → same trace_id, parent=a3ce
    Go->>Col: Emit span (trace_id=4bf9, parent=a3ce)
    Go-->>Py: 200 OK
    Py->>Col: Emit root span (trace_id=4bf9, no parent)
```

### 6. What breaks if you skip it

**Heading**: "The cost of a missing header"

Three failure modes, one per paragraph:

1. **Ghost spans** — spans with no parent_span_id appear as new root spans. A 100-tool agent produces 100 root spans, each in its own row. You can't tell which tool ran when or how long a full agent turn took.

2. **Wrong attribution** — if a Go service is used by ten different agents, and spans have no trace ID tying them to a specific agent turn, you can't tell which agent caused which latency spike. Debugging is guesswork.

3. **Silent cost leaks** — token count and latency are per-span. Without a trace to aggregate, you can't compute the total cost of one agent turn. Cost attribution to a business workflow is impossible.

One "so what": without propagation, you have logs, not traces. Logs are better than nothing; traces are better than logs.

### 7. Distributed systems analogy

**Heading**: "The correlation ID you've always used"

If you've built microservices, you've solved this before under a different name: the **X-Request-ID header**. Every upstream service adds a correlation ID to outbound requests; every downstream service logs it. At debugging time, you grep by correlation ID and see the whole request's journey.

W3C TraceContext is the standardized, versioned, widely-supported version of X-Request-ID. It carries more information (the parent span ID for waterfall ordering, not just a flat correlation ID), but the mental model is identical.

One "so what": if you've ever grep'd a request ID across service logs, you already understand why `traceparent` exists.

### 8. Closing: what today's code ships

**Heading**: "Three functions that complete the waterfall"

Today's Go SDK adds:
- `InjectTraceContext(ctx, http.Header)` — writes `traceparent` on every outbound HTTP call
- `ExtractTraceContext(ctx, http.Header)` — reads `traceparent` on every inbound request
- `StartSpan` respects the extracted context automatically

The Python SDK (Day 32) emits spans when `wrap_openai()` captures tool calls. The Go SDK (Day 33) propagates context when Go tools are called over HTTP. Together, any agent that uses both can produce a complete, connected waterfall — regardless of which service handles which step.

The specification is 15 pages of RFC. The implementation is under 50 lines of Go. The waterfall is the payoff.

---

## Mermaid Diagrams

Two diagrams total:
1. Sequence diagram in Section 5 (inject → extract → emit flow)
2. No second diagram needed — the section structure carries the explanation without it

Both diagrams must use the verbatim init block from CLAUDE.md Section 4.5.

---

## Key Concepts Checklist

| Concept | Where introduced |
|---|---|
| `traceparent` header format | Section 2 |
| Trace ID vs Span ID vs Parent Span ID | Section 2 |
| Inject: caller writes traceparent | Section 3 |
| Extract: receiver reads traceparent | Section 4 |
| Trace flags (`01` = sampled) | Section 2 (note: don't over-explain) |
| Ghost spans failure mode | Section 6 |
| X-Request-ID analogy | Section 7 |

---

## Tone Notes

- The reader is a backend engineer who knows what a trace waterfall is and has debugged latency before. Don't explain what a span is from scratch.
- "Polyglot" is jargon — introduce it immediately as "multiple programming languages in one system"
- Avoid "simply" and "just" — the propagation semantics are subtle; don't undersell them
- The broken waterfall is the emotional anchor. Return to it in the closing ("the waterfall is the payoff")

---

## Self-Review Checklist (before push)

- [ ] `Day 33` in `<title>`, `<h1>`, accent tag chip, meta line
- [ ] Sequence diagram uses correct mermaid init block (verbatim)
- [ ] All code snippets are illustrative — no real API keys, no localhost-only assumptions
- [ ] Paragraph length ≤ 3 sentences throughout
- [ ] No unexplained acronym: "W3C" defined on first use as "the standards body behind the web's core protocols"
- [ ] No nested `<a>` tags in the rendered HTML
- [ ] Series nav CSS block present (`.series-nav`, `.series-posts`, `.series-post`)
- [ ] Footnote or aside: link to W3C TraceContext spec (https://www.w3.org/TR/trace-context/) — only URL allowed in the post; confirm it's live before push
