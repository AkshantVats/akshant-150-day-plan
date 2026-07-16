# Day 39 — Experience Blog Outline
## The Tool That Ate Your Margin

**Calendar**: Saturday, 18 July 2026 · Day 39 of 150
**Series**: Experience
**Slug**: `day-39-tool-ate-your-margin`
**Live URL**: `https://akshantvats.github.io/Profile/blog/series/experience/day-39-tool-ate-your-margin.html`

---

## Post Metadata

| Field | Value |
|---|---|
| Title | `Day 39 — The Tool That Ate Your Margin` |
| Subtitle | Agoda · cost attribution · outliers |
| Series chip | `Experience · Day 39 of 150` |
| Cover image | `blog/assets/covers/day-39-tool-ate-your-margin.png` |
| OG image | `blog/assets/og/day-39-tool-ate-your-margin.png` |
| Estimated read time | 8 min |
| Format | design + incident (hybrid) |
| Employer | Agoda (Bangkok, Apr 2024 – Sep 2024, ~5 months, Senior Engineer) |

---

## Bridge to Today's Code

> "Per-tool cost rollup is cardinality-aware billing — Finance asks the same question Platform did. Today's code in tool-call-analyzer implements that lesson."

At Agoda's WhiteFalcon TSDB, the question "which label is making our index this expensive?" has the same structure as "which tool call is eating our LLM budget?" Both ask: across a high-cardinality space of possible contributors, which specific one is responsible for the disproportionate share of cost? The ClickHouse MVs I built today answer that question for AI tool calls the same way WhiteFalcon's cardinality tooling answered it for time-series metrics.

---

## Hook

At Agoda, the WhiteFalcon indexing team didn't get a bill in dollars. Their "bill" was index memory: how many bits the RoaringBitmap inverted index consumed per metric, per label value. When a new Kubernetes label got added to a fleet metric, the index grew as the product of every existing label dimension — and the team found out when Grafana scrape latency crept up, not when the label was deployed.

The question that followed was always the same: "which label is the outlier?" Not "how big is the index?" but "what single thing is causing the most growth?" That question requires per-dimension attribution. And per-dimension attribution requires a cost model that can disaggregate.

Today's `tool_stats_1m_mv` in tool-call-analyzer is the same answer to that question, applied to AI tool calls instead of TSDB labels.

---

## Outline

### Section 1: The Attribution Problem at Agoda Scale (650 words)

- **Scale context**: 1.5T events/day flowing into WhiteFalcon
- **The index structure**: RoaringBitmap inverted index (Agoda team's design) — one bitmap per label value, mapping label value → set of series IDs that carry it
- **Why attribution is hard**: the cost of adding a label is not the bitmap's size alone. It is the bitmap's size multiplied by every other label dimension it intersects with. Adding `pod` to a metric that already has `model_id (200 values) × tenant_id (500 values)` produces 200 × 500 × 50 = 5M new series from a single label addition.
- **Akshant's contribution context**: while contributing to the cross-tier query engine, I ran cross-product analysis before adding Kubernetes infrastructure tags to the indexing layer. The analysis was manual — a spreadsheet modeling the label × series cross-products. There was no automated per-label cost attribution tool at that point; you had to estimate.
- **What happened when teams didn't run the analysis**: the cardinality incident. A `pod` label was added to a high-cardinality fleet metric by a team that did not own the metric. Prometheus scrape duration crept up over several days. The alert designed to detect stack degradation was the first to go dark — the monitoring system was consuming too much resource to watch itself reliably. No alert fired until scrape targets began failing.

**So what**: The lesson from that incident was not "don't add labels." Labels are how you slice metrics to find problems. The lesson was: you need a cost model that tells you, after the fact, which label contributed which share of index growth. Without that, cardinality controls become restrictions with no enforcement mechanism.

### Section 2: The Shape of Per-Dimension Cost (600 words)

- **What good attribution looks like**: a query that answers "of all the index memory we are consuming, what fraction came from each distinct label dimension?"
- **The ClickHouse parallel**: in WhiteFalcon, this would be a rollup over the series catalog — count of series per label value, multiplied by average bitmap memory per series. In tool-call-analyzer, the same structure is `sum(cost_usd) GROUP BY tool_name, vendor` — total spend per tool per vendor per time window.
- **Why `GROUP BY` is the attribution primitive**: any cost attribution system is fundamentally a `GROUP BY` with a cost function. The sophistication lives in how you define the cost function, not in the grouping itself.
- **The 40% alert as outlier detection**: a single tool consuming more than 40% of trace wall time is an outlier. The right threshold depends on the expected tool mix, but 40% is a strong signal for a single tool in a multi-tool agent. At Agoda, the equivalent signal was a single label contributing more than 30% of index growth week-over-week.
- **SummingMergeTree for cost rollup**: `tool_cost_rollup_mv` uses SummingMergeTree because cost sums are additive and merge-safe. ClickHouse background merges accumulate partial sums automatically. The query never needs to scan raw rows — it reads pre-summed aggregates.

**So what**: Attribution is not just reporting. It is the precondition for enforcement. You cannot cap cardinality per label until you know which label is responsible for what. You cannot optimize tool cost until you know which tool owns what fraction of the budget.

### Section 3: What Made the Agoda Incident Preventable (500 words)

- The `pod` label was added to a high-cardinality fleet metric by a team that owned the service but not the metric schema. Metric schemas were shared infrastructure.
- The cross-product analysis that would have caught this: `existing_series_count × new_label_cardinality`. For `pod` with 50 pod IDs on a metric already at 100,000 series, the new total would be 5M series. The index could hold ~10M — it would not fail immediately, but every new pod deployment would add 100,000 series silently.
- **What the Agoda team added after**: a series count budget per metric, enforced at ingest by the Rust consumer. Each metric gets a maximum series ceiling. The consumer rejects samples that would push a metric past its budget — the rejection is counted in a Prometheus counter that fires a real alert.
- **The enforcement mechanism is a counter**: `series_rejected_cardinality_budget_total{metric="...", label="..."}`. One increment per rejected sample. The alert condition is `rate(series_rejected...) > 0`. Simple, binary, actionable.
- **Attribution is a prerequisite for enforcement**: you cannot set a per-metric ceiling until you know what each metric is costing. The cross-product modeling was the attribution step that made ceiling-setting possible.

**So what**: The hardest part of cardinality enforcement was not the code. It was agreeing on who owned the metric schema. Services that emit metrics do not always pay for the index cost of their labels. The rejection counter made that cost visible to the team that added the label, not just the team running WhiteFalcon.

### Section 4: The Same Thinking Applied to AI Tools (500 words)

- **Parallel structure**: an AI agent has multiple tools. Each tool call has a cost: token spend, latency, error rate. The agent owner often does not know which tool is responsible for most of that cost.
- **`tool_cost_rollup_mv` answers the question**: "of all LLM spend in this time window, how much came from `search_web` vs `bash` vs `code_interpreter`?" Same structure as "of all index memory, how much came from `pod` vs `model_id`?"
- **The 40% duration alert is the enforcement signal**: when a single tool consumes more than 40% of trace wall time, it is the AI equivalent of a single label pushing a metric past its cardinality budget. It surfaces the outlier before it becomes a cost crisis.
- **What is different**: AI tool cost is pay-per-call and easier to model than cardinality explosion. You can estimate expected token cost per tool per call and set a ceiling. WhiteFalcon cardinality cost was harder to model because it depended on the combinatorial explosion of all other existing label dimensions.
- **The LangChain blind spot**: today's code returns `cost_usd: 0` for LangChain tool calls because LangChain does not emit token usage. This is the same problem as a team emitting metrics without labels — the data exists, but attribution is impossible until the instrumentation is added. The `model_name: "unknown"` in the ClickHouse row is the signal that the attribution gap exists.

**So what**: A zero cost entry in the attribution dashboard is not "this tool is free." It is "this tool call has no attribution data." The distinction matters: optimizing away a tool you believe is cheap because the attribution is broken is the AI equivalent of adding the `pod` label without running the cross-product analysis.

### Section 5: The Question Finance Asks (350 words)

At Agoda, when the index grew by 40% in a month, Finance asked: "what changed?" Platform could not answer without per-label attribution. The incident forced the team to reconstruct the answer retroactively — pulling audit logs, identifying which team added which label when, estimating each label's contribution.

Today, when an AI platform's monthly LLM bill grows by 40%, Finance asks the same question. If you have built `tool_cost_rollup_mv` before the growth happens, the answer takes one ClickHouse query and about 30 seconds. If you have not, it takes days of log archaeology and still may not be accurate.

Build the attribution layer before you need it. The moment you need it is the moment you have no time to build it.

---

## Series Nav (sidebar)

Previous: Day 38 — Golden Files — How Platforms Survive API Drift
Next: Day 39 — (coming)

---

## Tags for social sharing

`#DistributedSystems #BackendEngineering #Infrastructure #OSS #Observability #AIInference #Agoda`

---

## Accuracy checkpoint (verify against context docs before writing)

- Akshant's Agoda tenure: Apr 2024 – Sep 2024, ~5 months, Senior Engineer ✓ (agoda-whitefalcon-tsdb-architecture.md)
- WhiteFalcon scale: 1.5T events/day ✓ (not 2T, not 5T)
- RoaringBitmap inverted index: Agoda team's design — NOT Akshant's contribution ✓
- Akshant's contributions: cross-tier query engine, new cardinality dimension (K8s tags), 2-3 Grafana query types ✓
- Cross-product analysis before K8s tag addition: Akshant's work ✓
- Cardinality incident: `pod` label on fleet metric → scrape target failures ✓ (from context doc)
- Do NOT claim Akshant designed the Rust consumer, Kafka pipeline, or RoaringBitmap engine ✓
- Do NOT use scale numbers outside 1.5T–1.8T/day ✓
- Do NOT name Agoda team members ✓
- Do NOT reference business logic (hotel pricing, search ranking) — this was pure infra ✓
