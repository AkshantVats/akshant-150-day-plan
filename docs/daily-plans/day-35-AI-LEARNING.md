# Day 35 — AI Learning Blog Outline
## "Day 35 — Silent Failures in Multi-Step Agents"

**Calendar**: Tuesday, 10 July 2026 · Day 35 of 150
**Series**: AI Learning
**Topic**: Empty tool results, swallowed exceptions, and max-iterations — the three ways ReAct agents fail without raising an exception
**Hook**: "Alert on zero-byte tool responses — they're the new 500."
**Bridge to code**: Today's ReAct demo agent in `traceforge/examples/react_agent/` implements all three failure modes, instrumented with TraceForge spans that surface `result_bytes: 0` and `status: EMPTY_RESPONSE`.
**Format**: deep-dive / how-it-works

---

## Post Title

**Day 35 — Silent Failures in Multi-Step Agents**

Accent tag chip: `AI Learning · Day 35 of 150`

Subtitle: *Empty tool results, swallowed exceptions, max iterations — and why your logs won't tell you which one killed the run*

---

## Thread

> The Demo Agent That Always Dies on Step 7 meets Silent Failures in Multi-Step Agents in today's agent-trace-collector commit.

---

## Narrative Arc

The blog starts not with definitions but with a symptom: a ReAct agent returns a plausible but wrong answer. No exception in the logs. No non-2xx status from the LLM. The user can't tell which step failed. This is a new category of production failure — one that HTTP monitoring was not designed to catch.

**Structural flow:**
1. **The symptom** — a wrong answer with no error signal
2. **Three silent failure modes** — empty tool response, swallowed exception, max iterations
3. **The DS analogy** — silent failures as a dropped queue message
4. **Why HTTP 500 monitoring misses these** — LLM calls succeed, tools don't surface errors
5. **What good observability looks like** — `result_bytes`, `status`, span-level cost rollup
6. **The fix TraceForge implements** — every span records tool output size and status
7. **Closing: the new class of alert**

---

## Section-by-Section Outline

### 1. Opening hook (no heading)

> Last week a colleague showed me an agent run that completed in 12 seconds, returned a five-sentence summary, and was completely wrong. No HTTP errors. No exceptions in the logs. Status 200 all the way down. The agent had reached step 7, received an empty string from a tool, and continued as if nothing happened. It spent four more LLM calls reasoning on corrupted context.

Set the scene with the failure. Do not open with definitions or theory. Three sentences.

### 2. The three silent failure modes

**Heading**: "What silence looks like"

Silent failures in multi-step agents fall into three categories. Each looks different in the logs — or rather, doesn't appear at all.

**Mode 1: Empty tool response.** The tool function returns `""` or `None`. The agent framework receives a falsy value, converts it to the string `"[empty]"` or skips the observation, and continues to the next step. The LLM sees `Observation: ` with nothing after it and generates the next Thought from incomplete context. No exception. No log line. Cost still accrues.

**Mode 2: Swallowed exception.** The tool catches its own error. Maybe it hits a timeout, wraps the error in a try/except, and returns `""` to avoid surfacing failure to the caller. From the agent's perspective, the tool ran and returned nothing. Same outcome as Mode 1, different cause. Harder to detect because the exception was valid code, not a bug.

**Mode 3: Max iterations.** The agent hits `MAX_STEPS` before producing a `finish` action. Most frameworks raise a `MaxIterationsReached` exception — but many production deployments catch that exception and return the last observation as the "answer." A 10-step agent that ran 10 steps without converging produces a response indistinguishable from a 3-step agent that converged quickly. Token cost is 3× higher; answer quality is lower.

One "so what": all three modes have the same signature from the outside — a completed run with a result. The only difference is inside the spans.

### 3. The DS analogy

**Heading**: "The dropped message problem"

In a Kafka consumer pipeline, a message that fails to deserialize has two fates. A poorly configured consumer catches the deserialization error, logs a warning at DEBUG level, and commits the offset — the message is gone, the lag stays flat, nothing alerts. A well-configured consumer puts the message on a dead-letter queue and emits a metric: `messages.deserialization_errors`.

Silent agent tool failures are the same problem at a higher abstraction. The "message" is the tool's response. The "consumer" is the agent's reasoning loop. A tool that returns `""` is a dropped message — it committed the offset (advanced to the next step) without actually processing the payload.

Dead-letter queues taught distributed systems engineers that every message must either succeed, fail loudly, or be explicitly parked. The same principle applies to agent tool calls. Every call must either return data, raise an observable error, or emit a `status: EMPTY_RESPONSE` span. There is no safe third option.

Analogy in plain terms: the agent's step-7 tool call is like a Kafka consumer that commits its offset after receiving an empty partition assignment. The lag stays at zero, the alert stays silent, and the data was never processed.

One "so what": we already solved this in distributed systems. We need to apply the same observability discipline to agent tool calls.

### 4. Why HTTP monitoring misses this

**Heading**: "All your 200s are fine"

A ReAct agent that silently fails on step 7 makes this HTTP call correctly: POST `/v1/chat/completions` → 200 OK. The LLM received the prompt, returned a valid JSON response, and the agent parsed it successfully. Every metric in a standard API monitoring stack shows green: latency within SLO, status 2xx, no retries.

The failure isn't in the HTTP layer. It's in the semantic layer — the meaning of what the LLM produced. The LLM said "call `convert_currency` with amount 28" and the tool returned nothing. The LLM doesn't know the tool returned nothing; it was never told. It received `Observation: ` with an empty value and generated a coherent-sounding continuation. The coherence is the problem — it masks the emptiness.

Prometheus scraping the OpenAI HTTP endpoint cannot observe this. The metric that matters is `tool_response_bytes`, not `http_status`. That metric does not exist in standard LLM observability tooling — which is why we're building TraceForge.

One "so what": adding more Prometheus exporters doesn't fix this. You need a layer that instruments the agent loop itself, not just the HTTP calls.

### 5. What good observability looks like

**Heading**: "Spans that tell the truth"

Every tool call in a traced agent should produce a span with at minimum:
- `tool.name` — which tool was called
- `result_bytes` — the byte length of the tool's response
- `status` — `OK`, `EMPTY_RESPONSE`, `EXCEPTION`, or `MAX_ITERATIONS`
- `cost_usd` — the LLM token cost charged to reach this step

With these four attributes, the Grafana waterfall query becomes a single `WHERE result_bytes = 0` filter. The failing step is instantly visible: one amber span among nine green ones, annotated with the tool name and the fact that it produced zero bytes of output.

The `cost_usd` attribute is equally important. Step 7 cost money — the LLM call that produced the tool invocation was real, even if the tool's response was empty. Downstream steps that reasoned on corrupted context also cost money. A per-trace cost rollup that shows "8 LLM calls, 1 empty tool response, $0.0023 wasted" is a business metric, not just a debugging aid.

#### Mermaid diagram: Traced vs untraced agent step 7

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
    subgraph UN ["Without TraceForge"]
        A["Step 7: tool call"] --> B["Observation: ''"]
        B --> C["Step 8: reason on\ncorrupted context"]
        C --> D["Final answer\n(wrong, no error)"]
    end
    subgraph TR ["With TraceForge"]
        E["Step 7: tool call\n→ span emitted"] --> F["result_bytes: 0\nstatus: EMPTY_RESPONSE"]
        F --> G["Grafana: amber span\ncost_usd: $0.0003"]
        G --> H["Alert fires:\nzero-byte response"]
    end
```

### 6. The TraceForge implementation

**Heading**: "What we shipped in today's code"

The Day 35 commit adds a ReAct agent to `traceforge/examples/react_agent/`. Every step wraps a `traceforge.start_span()` call. The span records `step`, `tool.name`, `result_bytes`, and `status` before calling `span.end()`. Step 7's tool always returns `""` — the span captures `result_bytes: 0` and sets `status: EMPTY_RESPONSE`.

The ClickHouse query for detecting silent failures across all traces becomes:

```sql
SELECT trace_id, step, tool_name, result_bytes, cost_usd
FROM agent_spans
WHERE status = 'EMPTY_RESPONSE'
  AND start_time > now() - INTERVAL 1 HOUR
ORDER BY start_time DESC
LIMIT 50;
```

This runs in under 10ms on the `agent_spans` MergeTree because `status` is a low-cardinality column that benefits from the `ORDER BY (trace_id, start_time)` primary key range scan when filtered by time window.

One "so what": the fix is not complicated. It's instrumenting what was already happening and recording it to a queryable store.

### 7. Closing: the new class of alert

**Heading**: "The zero-byte 500"

HTTP 500 is the wrong abstraction for agent failures. A well-instrumented agent never raises a 500 for a silent tool failure — the HTTP calls all succeed. The correct abstraction is a span-level status that captures the semantic health of the operation, not just its transport success.

The alert to add: `WHERE result_bytes = 0 AND status = 'EMPTY_RESPONSE'` on the `agent_spans` table, with a threshold of one occurrence in any rolling five-minute window. This is the agent equivalent of alerting on `http_requests_total{status=~"5.."} > 0`. It was always the right thing to monitor. We just didn't have spans to query.

Zero-byte tool responses are the new 500. Treat them accordingly.

---

## Mermaid Diagram Checklist

- [x] Init block is verbatim from CLAUDE.md Section 4.5
- [x] Node labels ≤ 6 words each
- [x] ≤ 8 nodes total
- [x] No `</motion.div>` tags

---

## Self-Review Checklist (before push)

- [ ] `Day 35` in `<title>`, `<h1>`, accent tag chip, meta line
- [ ] Mermaid init block verbatim from CLAUDE.md Section 4.5
- [ ] Every paragraph ≤ 3 sentences
- [ ] DS analogy (Kafka dropped message) present in Section 3
- [ ] No bullet lists substituting for prose in Sections 1–3
- [ ] Series nav CSS block present (`.series-nav`, `.series-posts`, `.series-post`)
- [ ] `result_bytes` and `status` span attributes correctly named (match Day 35 code)
- [ ] No placeholder URLs
- [ ] All SQL queries verified against Day 34 ClickHouse schema (`agent_spans`, `status` column)

---

## Format Notes

- Open with the symptom (wrong answer, no error), not a definition
- The Kafka analogy is the post's anchor — return to it in the closing paragraph
- "Zero-byte tool responses are the new 500" is the closing line — use it verbatim
- Do not explain ReAct from scratch; assume the reader saw Day 31–34 posts
- "TraceForge" is the product name; use it, not "our tool" or "the observability system"
