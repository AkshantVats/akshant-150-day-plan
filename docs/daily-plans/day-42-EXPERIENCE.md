# Day 42 — Experience Blog Outline
## "Day 42 — One Dashboard for Inference and Tools"
### Agoda · unified telemetry · tenant view

**Series**: Experience · Day 42 of 150
**Slug**: `day-42-one-dashboard-inference-tools`
**File**: `blog/series/experience/day-42-one-dashboard-inference-tools.html`
**Live URL**: `https://akshantvats.github.io/Profile/blog/series/experience/day-42-one-dashboard-inference-tools.html`
**Employer context**: Agoda — WhiteFalcon TSDB (Senior Engineer, ~5 months)
**Bridge**: "Dual-write to LensAI is hot/cold tiering for observability — one query face, two pipelines. Today's code in tool-call-analyzer implements that lesson."

---

## Title Block

```
<title>Day 42 — One Dashboard for Inference and Tools | Experience Series</title>
Accent chip: Experience · Day 42 of 150
<h1 class="post-title">Day 42 — One Dashboard for Inference and Tools</h1>
Meta line: Experience · Day 42 of 150
Series footer: Experience · Day 42 of 150
```

---

## Employer Context Reference

**Verified facts from agoda-whitefalcon-tsdb-architecture.md and resume-extracted.md** (use only these):
- **Role**: Senior Engineer, ~5 months at Agoda
- **System**: WhiteFalcon — Agoda's in-house TSDB (Apache Druid-inspired)
- **Scale**: 1.5T events/day (resume) / 1.8T events/day (Kafka forwarder figure)
- **Hot tier**: Redis, time-windowed buckets, last 3–7 days at per-hour granularity
- **Cold tier**: Ceph → S3 (Parquet), datetime-partitioned, compacted hourly → 3-hour → daily
- **Query engine**: Scala — one query face over both tiers, histogram-based quantiles
- **Akshant's contribution**: Cross-tier query engine extension — single request spans Redis + S3 with correct histogram merge
- **Grafana**: Connected to the Scala query API as the visualization layer
- **Attribution**: Agoda team built the RoaringBitmap engine, Kafka pipeline, Rust consumers, Scala engine; Akshant extended the cross-tier query path

**Do NOT invent**: team size, specific incident dates, internal tool names beyond what's in the architecture doc, dollar values, specific business metrics.

---

## Hook (first paragraph)

WhiteFalcon had two storage tiers for the same metrics: Redis for the last 3–7 days, S3 Parquet for everything older. From a Grafana user's perspective, there was one dashboard, one query, one datasource. The Scala query engine in the middle was the piece that made that possible — it routed each time range to the right tier, fetched histogram bucket counts from both, merged them correctly, and returned a single result set. One query face, two pipelines. The user never needed to know which tier answered their question. I extended that engine to handle time ranges that crossed the hot/cold boundary — the case where neither tier alone had the full answer. That experience shaped how I think about unified observability: the user-facing interface should be singular even when the storage beneath it is plural.

---

## Section 1 — WhiteFalcon's Split Storage Problem

### What the tiers were for
WhiteFalcon's hot tier (Redis) held the last 3–7 days of metrics at per-hour granularity. This was the query load that mattered: on-call engineers, active dashboards, alerting pipelines. The Redis tier was sized for fast random access, not storage efficiency. The cold tier (Ceph → S3 Parquet) held everything older, compacted from hourly to daily granularity, partitioned by datetime for efficient range scans.

### Why two tiers create a dashboard problem
Dashboards often ask for a 14-day window. "Show me API error rate for the last two weeks." A 14-day query crosses the hot/cold boundary: days 1–7 are in Redis, days 8–14 are in S3 Parquet. Before the cross-tier query extension, a Grafana user had to split this into two manual queries with different datasource configurations and mentally stitch the charts together. That's not a dashboard. That's a research project with a time limit.

### What Agoda's Scala engine did
The Scala query engine sat between Grafana and storage. It received the full time range from Grafana, determined which tiers it needed, fetched histogram bucket counts from each in parallel, and merged them. The merge is mathematically non-trivial: quantiles (P95, P99) are not additive across datasets. You cannot compute P95 of each tier and average them. You must merge the underlying histogram bucket counts first, then compute the quantile on the merged distribution.

### Physical analogy
It's like asking a librarian for all books written between 2010 and 2020. The librarian doesn't tell you "new books are in room A, older books are in the archive — go check both." They check both and hand you a unified list. The user's query had one shape. The retrieval path had two branches. The interface absorbed the complexity.

### So what
The single-query-face design was the Agoda team's most important architectural decision for WhiteFalcon. It meant Grafana dashboards could be written without knowledge of the storage tier split. Alerts could fire on 30-day windows without anyone configuring a dual-datasource query. The complexity was real — it lived in the query engine — but it was contained there, not spread across every dashboard that consumed the data.

---

## Section 2 — The Cross-Tier Extension I Built

### The problem
Before my work, the Scala engine handled time ranges entirely within one tier: either fully in Redis (< 7 days) or fully in S3 (> 7 days). A time range from day 1 to day 14 fell through an unhandled case. In practice, engineers worked around it by querying each tier separately and adding the results — which, for quantile metrics, produced mathematically incorrect answers.

### The wrong approach I initially proposed
My first instinct was to query each tier, compute the quantile on each result, and return the higher value. This is wrong. For a P95 latency metric where the hot tier shows P95=120ms and the cold tier shows P95=95ms, returning 120ms is not the correct 14-day P95. The distributions are different shapes. You cannot take the max of two quantiles and call it the quantile of the union.

### Why storing histograms makes the correct approach possible
WhiteFalcon stored aggregations as histogram bucket counts, not as pre-computed percentiles. This is the design decision that made the cross-tier merge work. Each bucket count is additive: bucket[100ms-200ms] in Redis + bucket[100ms-200ms] in S3 = bucket[100ms-200ms] across both tiers. Merge the bucket arrays, recompute the quantile on the merged distribution, and the answer is mathematically correct.

### What I actually built
I extended the Scala query engine to detect time ranges crossing the hot/cold boundary, fetch histogram bucket counts from both Redis and S3 in parallel, add corresponding bucket counts element-wise, then compute the requested quantile on the merged result. The output to Grafana was identical in shape to a single-tier response — one time series, one data point per hour, covering the full requested range.

### So what
The implementation was three weeks of work. The user-facing change was invisible — the dashboard they already had started returning correct 14-day results. That's the right outcome for an infrastructure extension. The metric of success was not a new feature. It was the removal of an incorrect workaround that nobody knew they were relying on.

---

## Section 3 — What "One Query Face" Costs

### The complexity budget
One query face over two tiers means the query engine absorbs complexity that would otherwise be spread across every dashboard consumer. That's the right trade — centralize complexity where experts can manage it, not distribute it to every team that writes a Grafana panel. But it comes with a cost: the query engine becomes a critical shared dependency. Any bug in the cross-tier merge silently corrupts every metric that crosses the boundary.

### How we caught regressions
We added a validation query that ran every hour: for the 3-hour window straddling the hot/cold boundary (the last 3.5 days of hot tier data), we computed the same metric three ways: Redis-only, S3-only, and cross-tier merge. The cross-tier result should equal the Redis result for the hot portion and the S3 result for the cold portion, within histogram quantization error. If the cross-tier result diverged by more than 2%, the pipeline emitted an alert.

### What I learned about shared infrastructure
The more consumers depend on a piece of infrastructure, the more carefully it must be tested — not because the infrastructure is complex (complexity is manageable) but because failures are invisible by design. A dashboard showing wrong P95 values after a query engine regression doesn't crash. It just shows wrong numbers. The users don't know. The on-call engineers don't know. The alert that should have fired based on real P95 doesn't fire. Invisible failures in shared infrastructure compound silently.

### So what
One query face is the right architecture. But it requires explicit regression testing at the integration point. The correct place to validate correctness is the merge logic itself — not the downstream dashboards. Every dashboard that trusts the query engine is a test you're not writing.

---

## Section 4 — The TraceForge Connection

### What dual-write mirrors
Today's `pkg/dualwrite` in tool-call-analyzer sends each tool span's BillingEvent to LensAI's ingest endpoint after writing to ClickHouse. LensAI tracks inference. tool-call-analyzer tracks tool calls. The Grafana board joins them on `$tenant_id`. This is WhiteFalcon's architecture replayed at the product level: two pipelines, one query face (the Grafana variable), one dashboard.

### The hot/cold analogy
In WhiteFalcon, hot=Redis held recent data, cold=S3 held historical data. In TraceForge, hot=tool-call-analyzer holds tool span data (recent, granular), cold=LensAI holds inference data (the other side of the cost). The unified envelope is the histogram bucket schema equivalent — the shared format that makes merging possible. tenant_id + trace_id is the join key, the way histogram bucket boundaries are the merge key in WhiteFalcon.

### What fire-and-forget preserves
WhiteFalcon's Redis writes never gated on S3 writes completing. The hot tier received the event first; S3 compaction happened asynchronously on a configurable cadence. The system was designed so that Redis availability was independent of cold tier availability. tool-call-analyzer's dual-write follows the same principle: ClickHouse write path never waits on LensAI. If LensAI is partitioned, tool spans still land in ClickHouse. The secondary write is best-effort, the same way cold tier compaction is best-effort relative to hot tier ingest.

### The difference
WhiteFalcon's query engine actively merged the two tiers on read. TraceForge's unified board presents two data sources side by side — the merge happens in the viewer's eye via the shared Grafana variable, not in a query engine. That's a deliberate tradeoff: less infrastructure to build and maintain, at the cost of requiring a ClickHouse table join for true cross-system aggregations. For weekly reviews and budget conversations, visual juxtaposition is enough. For invoice generation, a SQL UNION on the billing_events table provides the correct aggregate.

### So what
The WhiteFalcon architecture is not tied to TSDB. The principle — two storage systems, one query interface, shared schema that makes merging possible — applies to any observability system with heterogeneous data sources. TraceForge is applying it to AI agent cost attribution. The envelope is the histogram. The Grafana variable is the query engine. The result is the same: users see one dashboard, not two.

---

## Section 5 — Building for the CFO and the On-Call Engineer Simultaneously

### Why both audiences need the same data
The on-call engineer asks: "why is trace 7f3d9a2e costing $0.04?" The CFO asks: "why did our AI bill increase 30% this week?" Both questions are answered by the same data — BillingEvent rows grouped differently. The engineer needs trace-level granularity. The CFO needs tenant-level weekly aggregation. One table, two GROUP BY clauses.

### What the Grafana board communicates
Row 1 (LensAI inference) communicates token spend to the model provider. Row 2 (TraceForge tools) communicates tool call spend to the API vendors. Both rows filtered by `$tenant_id` means a customer success manager can pull up a tenant's dashboard in a weekly review and immediately see whether their costs are inference-driven or tool-driven. That's a product conversation, not an engineering conversation — and it happens in Grafana, not a spreadsheet.

### The lesson from WhiteFalcon's Grafana integration
At Agoda, the Grafana-facing API was the same regardless of which storage tier answered the query. This meant Grafana configuration never needed to change when the team adjusted hot tier retention windows or added a new cold tier storage format. The dashboard was stable because the interface contract was stable. For TraceForge, the Grafana board generator (`traceforge board`) codifies that contract: the two datasource UIDs are configuration, the panel structure is fixed. Add a new inference model and the board still works. Switch ClickHouse clusters and only the datasource UID changes.

### So what
Unified observability is a product discipline, not a data engineering exercise. The discipline is agreeing on the envelope schema, agreeing on the join keys, and then generating the interface artifact (the Grafana board) from code — so that the agreement is machine-checkable, not a convention people forget. WhiteFalcon's query engine was that artifact for Agoda. The board generator is that artifact for TraceForge.

---

## Series Navigation Footer

Previous: Day 41 — Exclusive Time — Flame Graphs for Money (Delivery Hero)
Next: Day 43 — (coming)

---

## HTML Checklist Before Push

- [ ] `Day 42` in `<title>`, `<h1>`, accent chip, meta line, series footer (all four mandatory locations)
- [ ] `class="series-nav"` / `class="series-posts"` / `class="series-post"` CSS present in `<style>` block
- [ ] No system names invented beyond what appears in agoda-whitefalcon-tsdb-architecture.md and resume-extracted.md
- [ ] Akshant's contribution accurately scoped: cross-tier query extension, not the RoaringBitmap engine or Kafka pipeline
- [ ] Scale numbers within documented range: 1.5T–1.8T events/day, ~5 months tenure
- [ ] All `<div>` opens match `</div>` closes
- [ ] No `</motion.div>` tags
- [ ] No `<a>` nested inside `<a>`
- [ ] Max 3 sentences per paragraph (split any that exceed this)
- [ ] No placeholder URLs
- [ ] Employer tenure accurate: Senior Engineer, ~5 months, Agoda
