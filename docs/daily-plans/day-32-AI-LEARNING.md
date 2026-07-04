# Day 32 — AI Learning Blog Outline
## "Day 32 — Tool Calling Protocols — OpenAI vs Anthropic"
### JSON schema, parallel calls, refusal handling

**Series**: AI Learning · Day 32 of 150
**Slug**: `day-32-tool-calling-protocols-openai-vs-anthropic`
**File**: `blog/series/ai-learning/day-32-tool-calling-protocols-openai-vs-anthropic.html`
**Hook**: Normalize in the adapter; never in the dashboard SQL.

---

## One-Line Summary

OpenAI and Anthropic use different JSON schemas for tool calls, different finish-reason conventions, and different parallel-call semantics — the right place to absorb those differences is a thin adapter layer, not a `CASE` expression in your ClickHouse query.

---

## Format Check

Before writing, count last 10 posts by format. This is a **design / patterns** post — comparing two protocols and deriving an abstraction. Acceptable unless design/patterns count ≥ 4 of last 10.

---

## Core Argument

The functional intent of tool calling is identical across providers: the model signals "I need external information" and returns a structured request for it. The wire format is different in three dimensions:

1. **Schema** — OpenAI puts tool calls inside `message.tool_calls[]`; Anthropic puts them inside `content[]` blocks of type `tool_use`.
2. **Parallel calls** — Both providers support multiple tool calls per turn, but the field structure differs; OpenAI assigns a `tool_call_id`, Anthropic assigns an `id` inside the content block.
3. **Finish reason** — OpenAI: `finish_reason: "tool_calls"`; Anthropic: `stop_reason: "tool_use"`.

The correct invariant: both protocols say "the model wants to call N tools." Extract that invariant into a `NormalizedToolCall` type in your adapter. Everything downstream — span emission, cost accounting, response routing — works against the normalized type.

---

## Post Structure

### Opening hook (~3 paragraphs)

The first time I wrote code that needed to handle both an OpenAI and an Anthropic response in the same pipeline, I used a `CASE` statement. "If the response has `tool_calls`, it's OpenAI. If it has `content` blocks with type `tool_use`, it's Anthropic." I put that logic in a ClickHouse materialised view.

Six months later, OpenAI shipped a response format change and the materialised view silently returned zero rows. No error — the CASE fell through to NULL and the aggregation produced zeros instead of counts. I found it during a cost review, not a test.

The lesson is obvious in retrospect: protocol differences belong in the adapter layer, not in the data layer. But "obvious in retrospect" describes most distributed systems mistakes.

### Section 1 — The two schemas side by side

Show both JSON response fragments:

**OpenAI** (`chat.completions.create` response):
```json
{
  "choices": [{
    "finish_reason": "tool_calls",
    "message": {
      "role": "assistant",
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "get_weather",
            "arguments": "{\"location\": \"Tokyo\"}"
          }
        },
        {
          "id": "call_def456",
          "type": "function",
          "function": {
            "name": "get_time",
            "arguments": "{\"tz\": \"Asia/Tokyo\"}"
          }
        }
      ]
    }
  }],
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 45
  }
}
```

**Anthropic** (`messages.create` response):
```json
{
  "stop_reason": "tool_use",
  "content": [
    {
      "type": "text",
      "text": "I'll check both for you."
    },
    {
      "type": "tool_use",
      "id": "toolu_01A",
      "name": "get_weather",
      "input": {"location": "Tokyo"}
    },
    {
      "type": "tool_use",
      "id": "toolu_01B",
      "name": "get_time",
      "input": {"tz": "Asia/Tokyo"}
    }
  ],
  "usage": {
    "input_tokens": 120,
    "output_tokens": 45
  }
}
```

Three differences visible immediately:
- Field location: `message.tool_calls[]` vs `content[]` blocks
- Arguments format: JSON string (`"arguments"`) vs parsed object (`"input"`)
- Finish signal: `finish_reason: "tool_calls"` vs `stop_reason: "tool_use"`

A fourth difference: Anthropic can include `text` blocks alongside `tool_use` blocks in the same turn. OpenAI cannot — a `tool_calls` response has no text content.

**So what**: any code that touches both providers needs to handle these four differences. The question is where that code lives.

### Section 2 — The DS analogy: protocol adapters at the network edge

In a distributed system, you don't write Kafka consumer logic that branches on "is this message from cluster A or cluster B?" You write a deserialisation adapter per source, produce a normalised internal event, and route the normalised event downstream.

The same principle applies here. An `IngressAdapter` for OpenAI produces a `NormalizedToolCall`. An `IngressAdapter` for Anthropic produces the same `NormalizedToolCall`. The cost accounting, span emission, and response routing code never sees the raw provider format.

```python
@dataclass
class NormalizedToolCall:
    id: str               # provider's call identifier
    name: str             # tool function name
    arguments: dict       # parsed JSON arguments (not a string)
    provider: str         # "openai" | "anthropic"
    model: str
    input_tokens: int
    output_tokens: int
```

The adapter is three functions: `from_openai()`, `from_anthropic()`, and `to_span()`. Nothing else needs to know about the provider.

**So what**: the adapter is the seam. Everything below the seam is provider-agnostic.

### Section 3 — Parallel calls and why they're a span problem

Both OpenAI and Anthropic allow parallel tool calls — multiple tools requested in a single model turn. The span question is: how many spans does a parallel-call turn produce?

The answer: one span per tool call, all sharing the same parent span ID (the model turn span). Token counts are divided across calls proportionally — or assigned entirely to the first call with zero for the rest. Either convention is fine; the convention needs to be consistent.

A subtle issue: the model may issue 5 parallel tool calls but only 3 matter for cost (the other 2 hit cache). If you divide tokens evenly across all 5, you misattribute cost. The correct approach: emit spans with full token counts on the model turn span and zero on the child tool call spans. Let the ClickHouse rollup sum at the trace level, not the span level.

TraceForge's `parent_span_id` field handles this: the model turn is the parent, the tool calls are children. The `agent_trace_cost` materialised view sums `cost_usd` at the trace level, so double-counting at the span level doesn't matter as long as the model turn span carries the true cost.

**So what**: parallel tool calls are a span tree, not a flat list. The tree structure (via `parent_span_id`) is what makes cost rollup correct.

### Section 4 — Refusal handling as an ERROR span

Both providers have a case where the model is asked to call a tool but declines. OpenAI returns `finish_reason: "stop"` (no `tool_calls` array). Anthropic returns `stop_reason: "end_turn"` with no `tool_use` blocks. Neither signals an error explicitly — you have to infer it from context.

The tracing question: should a refusal produce a span?

Yes — and with `status: "ERROR"`. A model that was expected to call a tool but didn't is an observable event. If you don't emit a span, the trace waterfall has a gap: the orchestrator issued a model call, the model call disappeared, and the next step in the trace has no causal parent. That's the same as a silent failure.

The convention in TraceForge: the model turn span carries `status: "ERROR"` and `error_message: "model_refused_tool_call"` when:
- The request included `tools` with `tool_choice: "required"` (OpenAI) or `tool_choice: {"type": "any"}` (Anthropic)
- The response has no tool calls

When `tool_choice` is `"auto"` and the model returns text instead of a tool call, that's a valid outcome — emit a span with `status: "OK"` and `tool_kind: "model_call"`, note the model chose not to use tools.

**So what**: refusals are observable events. A gap in the trace waterfall is worse than an explicit ERROR span.

### Section 5 — The adapter in 40 lines

Show the normalisation code:

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class NormalizedToolCall:
    id: str
    name: str
    arguments: dict
    provider: str
    model: str
    input_tokens: int
    output_tokens: int


def from_openai(response: Any) -> list[NormalizedToolCall]:
    """Extract tool calls from an OpenAI ChatCompletion response."""
    calls = []
    for choice in response.choices:
        if not (choice.message.tool_calls):
            continue
        usage = response.usage or object()
        n = len(choice.message.tool_calls)
        in_tok = getattr(usage, "prompt_tokens", 0) or 0
        out_tok = getattr(usage, "completion_tokens", 0) or 0
        for tc in choice.message.tool_calls:
            import json
            calls.append(NormalizedToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments or "{}"),
                provider="openai",
                model=response.model or "",
                input_tokens=in_tok // n,
                output_tokens=out_tok // n,
            ))
    return calls


def from_anthropic(response: Any) -> list[NormalizedToolCall]:
    """Extract tool calls from an Anthropic Messages response."""
    calls = []
    tool_blocks = [b for b in (response.content or []) if getattr(b, "type", "") == "tool_use"]
    if not tool_blocks:
        return calls
    usage = response.usage or object()
    n = len(tool_blocks)
    in_tok = getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "output_tokens", 0) or 0
    for block in tool_blocks:
        calls.append(NormalizedToolCall(
            id=block.id,
            name=block.name,
            arguments=block.input or {},
            provider="anthropic",
            model=getattr(response, "model", "") or "",
            input_tokens=in_tok // n,
            output_tokens=out_tok // n,
        ))
    return calls
```

The adapter is 40 lines with no branching in the caller. Everything downstream uses `NormalizedToolCall`.

**So what**: the entire provider difference is contained in two functions. Adding a third provider (Gemini, Mistral) means adding a third `from_*()` function — nothing else changes.

### Section 6 — What "normalize in the adapter" saves you in SQL

Without normalization, a ClickHouse query to count tool calls by provider looks like:

```sql
-- BAD: provider logic in SQL
SELECT
    CASE
        WHEN attributes['tool_call_id'] != '' THEN 'openai'
        WHEN attributes['anthropic_tool_id'] != '' THEN 'anthropic'
        ELSE 'unknown'
    END AS provider,
    count() AS calls
FROM lensai.agent_spans
GROUP BY provider;
```

With normalization:

```sql
-- GOOD: provider stored at emit time
SELECT
    attributes['traceforge.provider'] AS provider,
    count() AS calls
FROM lensai.agent_spans
GROUP BY provider;
```

The difference compounds over time. Every new provider, every response format change, every schema version bump — with normalization in the adapter, the SQL stays identical. Without it, every change is a ClickHouse migration plus a SQL rewrite.

**Closing sentence**: the hook at the top said "normalize in the adapter, never in the SQL" — that's the rule, and this post is the argument for it.

---

## Mermaid Diagram Plan

### Diagram 1 — Protocol comparison: OpenAI vs Anthropic tool call shape

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
flowchart TD
    A["OpenAI response"] --> B["message.tool_calls[ ]"]
    C["Anthropic response"] --> D["content[ ] type=tool_use"]
    B --> E["NormalizedToolCall"]
    D --> E
    E --> F["TraceForge span emit"]
    E --> G["Cost accounting"]
```

### Diagram 2 — Parallel tool calls as a span tree

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
flowchart TD
    A["Model turn span\ntool_kind=model_call\ncost_usd=0.053"] --> B["tool_call span 1\nget_weather\nparent=model_turn"]
    A --> C["tool_call span 2\nget_time\nparent=model_turn"]
    A --> D["tool_call span 3\nsearch_docs\nparent=model_turn"]
```

---

## Voice Checklist (pre-draft)

- [ ] First person: "I wrote code that...", "I put that logic in...", "I found it during..."
- [ ] Max 3 sentences per paragraph
- [ ] Kafka adapter analogy fully developed in Section 2
- [ ] Every section ends with "so what" sentence
- [ ] No bullet-list substitutes for prose (JSON examples and code blocks are different)
- [ ] All OTel / provider terms defined on first use
- [ ] Code examples compile / run as written (no pseudocode)
- [ ] `Day 32` in `<title>`, `<h1>`, accent tag, meta line — all four locations

---

## Series Nav

Previous: Day 31 — OpenTelemetry Semantics for Agents
URL: `blog/series/ai-learning/day-31-opentelemetry-semantics-for-agents.html`

Next: Day 33 (pending)

Retrofix Day 31 AI Learning post footer to link to Day 32.

---

## Self-Review Checklist (before push)

- [ ] `Day 32` in `<title>`: `Day 32 — Tool Calling Protocols — OpenAI vs Anthropic | AI Learning Series`
- [ ] `Day 32` in `<h1>`: `Day 32 — Tool Calling Protocols — OpenAI vs Anthropic`
- [ ] Accent tag: `AI Learning · Day 32 of 150`
- [ ] Meta line: `AI Learning · Day 32 of 150`
- [ ] Series footer: `Day 32 of 150 — Tool Calling Protocols — OpenAI vs Anthropic`
- [ ] Mermaid init block exact match (both diagrams)
- [ ] Node labels ≤ 6 words
- [ ] ≤ 8 nodes per diagram
- [ ] HTML div balance
- [ ] No `</motion.div>` tags
- [ ] No nested `<a>` tags
- [ ] `class="prose"` present
- [ ] Series nav CSS: `.series-nav`, `.series-posts`, `.series-post`
- [ ] JSON examples valid JSON
- [ ] Python adapter code syntactically correct
- [ ] OpenAI and Anthropic field names verified against current SDK docs
