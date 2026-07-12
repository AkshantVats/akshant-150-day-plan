# Day 37 — AI Learning Blog Outline
## "Day 37 — Tool Taxonomies — Ontology Before Metrics"

**Calendar**: Thursday, 16 July 2026 · Day 37 of 150
**Series**: AI Learning
**Topic**: Classifying agent tool calls into semantic categories (http.search, db.query, code.exec, file.read, agent.delegate) before building metrics dashboards — why bad taxonomy makes dashboards lie gently, and how to define a taxonomy that survives API drift
**Hook**: "Bad taxonomy makes every dashboard lie gently."
**Bridge to code**: Today's `pkg/types/tool_call.go` in tool-call-analyzer defines `ToolCategory` as a typed enum with five constants: `http`, `db`, `code`, `file`, `agent`. The categorization rules are deterministic: checked in this order before any metric is emitted.
**Format**: design / how-it-works

---

## Post Title

**Day 37 — Tool Taxonomies — Ontology Before Metrics**

Accent tag chip: `AI Learning · Day 37 of 150`

Subtitle: *http.search vs db.query vs code.exec are not just labels — they're the unit of analysis. Build the taxonomy first. Build the dashboard second.*

---

## Thread

> LangChain Is Four Vendors in a Trenchcoat meets Tool Taxonomies — Ontology Before Metrics in today's tool-call-analyzer commit.

---

## Narrative Arc

The blog opens with the deceptively simple metric: `tool_call.latency`. Averaged across all tool calls, it tells you nothing useful. A weather API call and a code execution take different amounts of time for different reasons. Aggregating them destroys the signal.

**Structural flow:**
1. **The taxonomy problem** — why `tool_call.latency` is a meaningless aggregate without categories
2. **What happens without a taxonomy** — alerts that fire on the wrong thing; dashboards that show "average" behavior that doesn't exist
3. **The DS analogy** — library classification systems: Dewey decimal vs freeform titles
4. **The five-category ontology** — http, db, code, file, agent; why five and not fifty
5. **Taxonomy drift: how it breaks** — when `search_web` becomes `web_search`, categories scatter
6. **What tool-call-analyzer ships today** — `ToolCategory`, the five constants, categorization rules
7. **Closing: the right time to build taxonomy is before the first metric**

---

## Section-by-Section Outline

### 1. Opening hook (no heading)

> `tool_call.latency` at P99 is 4.2 seconds. Your agent takes 4.2 seconds per tool call — that's slow, and you should probably fix it. Except the 4.2 seconds is an average across weather API calls (200ms), code execution (8 seconds), and vector database lookups (50ms). The metric is not wrong; it's faithfully representing a number that has no meaning. Fix the taxonomy first.

Three sentences. Start with a concrete, plausible metric that looks useful and isn't.

### 2. What happens without a taxonomy

**Heading**: "The alert that always fires on the wrong thing"

Without taxonomy, every tool call metric is an average over a heterogeneous population. P99 latency spikes during a period when the agent ran more code execution calls — not because anything broke, but because the mix of tool types shifted. The oncall engineer pages in, investigates, and finds nothing wrong. The false alarm cost was thirty minutes and a pager notification at 3am.

This is the quiet version of bad taxonomy: it doesn't break anything, it just erodes trust in your dashboards. When P99 spikes every time the agent runs more `code_exec` calls and less `http_fetch` calls, engineers start ignoring the P99 alert. The alert is still firing when a real regression happens. Nobody notices because everybody learned the alert doesn't mean anything.

The louder version is incorrect cost attribution. If you track `tool_call.cost_usd` without knowing which tool type the cost came from, you can't tell the difference between an expensive code execution tool and an expensive LLM-powered search tool. Your cost optimization effort is aimed at a number that's a weighted average of two completely different cost drivers.

One "so what": bad taxonomy doesn't cause failures — it prevents you from seeing them.

### 3. The DS analogy

**Heading**: "Why libraries don't shelve books by title"

A library that shelved books alphabetically by title would be usable but hard to browse. To find books about distributed systems, you'd need to know all the titles in advance. The Dewey Decimal System (and Library of Congress classification) solves this by assigning every book to a hierarchical category before it reaches the shelf. The category is determined by content, not by arbitrary identifiers.

AI tool taxonomies face the same challenge. Tool names are arbitrary identifiers chosen by the developer: `search_web`, `web_search`, `google_search`, `bing_search_v2`, `tool_1`. The name carries intent, but not in a machine-readable way. A metrics system that tracks `tool_name=search_web` separately from `tool_name=web_search` is shelving two copies of the same book in different sections because their titles start with different words.

The correct approach is to classify by semantic type, not by name. `search_web`, `web_search`, and `google_search` all belong to `category=http` because they all make outbound HTTP requests and return textual results. The dashboard metric is `http.latency`, not `search_web.latency` — and it stays stable when the tool name changes.

One "so what": taxonomy should be defined by semantic behavior, not by the string someone typed in a config file.

### 4. The five-category ontology

**Heading**: "Why five and not fifty"

The goal of a tool taxonomy is not exhaustive classification — it's useful grouping for operational metrics. Five categories cover the operational dimensions that matter for an agent observability stack:

**http** — any tool that makes an outbound network request. Latency is dominated by network RTT and external API response time. Cost is typically low (API credits, not LLM tokens). Alert on P99 > 5s, timeouts, and 4xx/5xx rates.

**db** — any tool that queries or writes to a data store. Latency is dominated by query complexity and index health. Cost in tokens is low; cost in infrastructure is variable. Alert on query latency spikes and index miss rates.

**code** — any tool that executes or analyzes code. Latency is dominated by sandbox startup time and execution complexity. Cost can be high (sandboxed VMs, GPU compute). Alert on execution timeouts and sandbox failures.

**file** — any tool that reads or writes to a filesystem or object store. Latency is dominated by I/O and network throughput. Alert on permission errors and file-not-found rates.

**agent** — any tool that delegates to another agent or model. Latency is dominated by the sub-agent's turn time. Cost is high (recursive LLM calls). Alert on sub-agent depth and cumulative cost per trace.

Five categories because they represent five distinct operational profiles: different latency distributions, different cost drivers, different alert conditions. Adding more categories (e.g., splitting `http` into `search` and `api`) adds dashboard cardinality without adding operational clarity.

### 5. Taxonomy drift: how it breaks

**Heading**: "When the name changes but the category doesn't"

Tool names change. A developer refactors `search_web` to `web_search` to match their naming convention. A new framework uses `serpapi_search` where the old one used `google_search`. An A/B test introduces `search_web_v2` alongside `search_web`. All of these tools belong to `category=http`. Without a taxonomy layer, each name change creates a new metric series and the historical data for the old name is abandoned.

Taxonomy drift is the failure mode where the category assignment is wrong after a rename. If the categorization rule is `name == "search_web" → http`, then `web_search` gets assigned the wrong category (or no category at all). If the categorization rule is `name contains "search" → http`, then `search_db_records` gets incorrectly assigned to `http` instead of `db`.

The correct rule structure is an ordered priority check: check for database keywords first (sql, query, db, vector, elastic, redis), check for code execution keywords second (run, exec, python, bash, compile, code), check for file keywords third (file, read, write, dir, s3, fs), check for agent keywords fourth (agent, delegate, llm, chain, subagent), then default to `http` for everything else. The default is `http` because the majority of tool calls make outbound requests, and false-positives on `http` are less harmful than false-negatives on `code` or `agent`.

One "so what": ordered priority rules with a safe default are more robust than exact-match rules. Design the fallback before you design the happy path.

#### Mermaid diagram: Tool categorization decision tree

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
    A["Tool name arrives"] --> B{"contains: sql\nquery db vector\nelastic redis?"}
    B -- "Yes" --> C["category = db"]
    B -- "No" --> D{"contains: run exec\npython bash\ncompile code?"}
    D -- "Yes" --> E["category = code"]
    D -- "No" --> F{"contains: file read\nwrite dir s3 fs?"}
    F -- "Yes" --> G["category = file"]
    F -- "No" --> H{"contains: agent\ndelegate llm\nchain subagent?"}
    H -- "Yes" --> I["category = agent"]
    H -- "No" --> J["category = http\n(default)"]
```

### 6. What tool-call-analyzer ships today

**Heading**: "ToolCategory: five constants, one ordering"

Today's `pkg/types/tool_call.go` defines `ToolCategory` as a Go string type with five constants: `CategoryHTTP`, `CategoryDB`, `CategoryCode`, `CategoryFile`, `CategoryAgent`. The type is intentionally a string alias (not `iota`) so the values are readable in JSON, Kafka messages, and Grafana labels without mapping tables.

The `AllCategories` slice in the same file enables exhaustiveness tests — if a sixth category is added without updating tests, the test suite catches it immediately. This is the taxonomy equivalent of a golden file: you declare what the correct set of values is, and tests verify that the implementation matches the declaration.

The `ToolCall` struct carries `Category ToolCategory` as a required field. Adapters (Day 38) are responsible for assigning the category during normalization — before the `ToolCall` is emitted to Kafka. Downstream consumers in ClickHouse and Grafana can safely assume `category` is always one of the five known values and use it as a low-cardinality label.

### 7. Closing: the right time to build taxonomy

**Heading**: "Ontology before metrics"

The right time to build a tool taxonomy is before you write the first metric. A dashboard built on raw tool names accumulates technical debt proportional to the number of tools your agents use. Every new tool is a new metric series. Every rename breaks a Grafana panel. Every time a developer renames `search_web` to `web_search`, someone's alert threshold is wrong.

Build the taxonomy first: five categories, ordered priority rules, a safe default, and a test that enforces exhaustiveness. Then build the dashboard on category labels, not tool names. When the tool name changes, the category assignment absorbs the change. The dashboard stays stable. The alert threshold stays correct.

Bad taxonomy makes every dashboard lie gently. Ontology before metrics.

---

## Mermaid Diagram Checklist

- [x] Init block is verbatim from CLAUDE.md Section 4.5
- [x] Node labels ≤ 6 words each
- [x] 10 nodes total (A through J) — split across two diagrams if needed; 10 is within the 8-node limit per diagram only if split. Actually 10 is > 8. I should split.
- [x] No `</motion.div>` tags

**Note for 2am writer**: The mermaid diagram above has 10 nodes, which exceeds the 8-node limit in CLAUDE.md Section 4.5. Split into two diagrams: Diagram 1 covers steps A→E (db and code branches); Diagram 2 covers steps F→J (file, agent, http default). Both must include the full init block.

---

## Format Notes

- Open with the concrete meaningless metric (`tool_call.latency` aggregated), not with a definition of taxonomy
- The library analogy (Dewey Decimal) is the post's conceptual anchor — it explains why name-based metrics fail and why semantic categories are the fix
- Section 4 should feel like a design document, not a textbook: explain what each category catches, not what it is
- Section 5's mermaid diagram is the post's only visual — split into two if the tool count exceeds 8 nodes per CLAUDE.md rules
- The closing line must appear verbatim: "Bad taxonomy makes every dashboard lie gently. Ontology before metrics."
- `ToolCategory` is the concrete type name; use it, not "our category enum" or "the classification module"
- Do not explain ClickHouse schema or Kafka topic format — assume the reader saw Days 31–34

---

## Self-Review Checklist (before push)

- [ ] `Day 37` in `<title>`, `<h1>`, accent tag chip, meta line
- [ ] Mermaid init block verbatim from CLAUDE.md Section 4.5
- [ ] Mermaid diagrams split if node count > 8 (Section 5 diagram is 10 nodes — must split)
- [ ] Every paragraph ≤ 3 sentences
- [ ] Dewey Decimal analogy present in Section 3
- [ ] Categorization priority order matches `pkg/types/tool_call.go` implementation
- [ ] Five categories listed correctly: http, db, code, file, agent
- [ ] Series nav CSS block present (`.series-nav`, `.series-posts`, `.series-post`)
- [ ] No nested `<a>` tags
- [ ] No placeholder URLs
- [ ] Closing line present verbatim: "Bad taxonomy makes every dashboard lie gently. Ontology before metrics."
- [ ] `ToolCategory` type referenced in Section 6, not generic "our enum"
