# Day 34 — AI Learning Blog Outline
## "Day 34 — Trace Storage Layout — Sort Keys Matter"

**Calendar**: Monday, 9 July 2026 · Day 34 of 150
**Series**: AI Learning
**Topic**: ClickHouse MergeTree sort key design for trace queries — ORDER BY, ZSTD compression, projections
**Hook**: "Optimize for trace_id lookup first; global analytics second."
**Bridge to code**: Today's ClickHouse schema in `traceforge/clickhouse/schema.sql` implements `ORDER BY (trace_id, start_time)`, ZSTD compression, and a slow-span projection.
**Format**: deep-dive / systems design

---

## Post Title

**Day 34 — Trace Storage Layout — Sort Keys Matter**

Accent tag chip: `AI Learning · Day 34 of 150`

Subtitle: *Why ORDER BY (trace_id, start_time) is not obvious — and why it makes your waterfall query 500× faster*

---

## Thread

> ClickHouse for Traces meets Trace Storage Layout — Sort Keys Matter in today's ClickHouse schema commit.

---

## Narrative Arc

Most ClickHouse tutorials show `ORDER BY (timestamp)` — great for time-series dashboards, terrible for trace queries. This post explains why trace access patterns are different, how MergeTree sort keys determine I/O cost at query time, and what the correct sort key looks like for an agent span table. It ends with compression and projections as secondary wins once the primary key is right.

---

## Section-by-Section Outline

### 0. Opening hook (no heading — first ≤3 sentences)

> You've got 5 million agent spans in ClickHouse. Someone pastes a trace ID into Grafana and asks for the waterfall. If your table is `ORDER BY (start_time)`, ClickHouse reads 5 million rows. If it's `ORDER BY (trace_id, start_time)`, it reads 12.

Don't explain MergeTree yet. Let the 12-row number land.

### 1. How MergeTree sorts data on disk

**Heading**: "The filing cabinet model"

MergeTree is not a B-tree index. It's a sorted flat file. When you create a table with `ORDER BY (col_a, col_b)`, ClickHouse physically sorts every row by `(col_a, col_b)` before writing to disk. Rows with the same `col_a` and `col_b` prefix end up in consecutive disk blocks.

**Analogy**: A filing cabinet where every folder is sorted alphabetically by last name, then first name. To find all documents for "Smith, John," you walk to the S drawer, flip to Smith, then to John. You read one contiguous section. You don't open every drawer.

When you query `WHERE trace_id = 'abc'`, ClickHouse uses the sort key to binary-search for the first row where `trace_id = 'abc'`. It reads forward until `trace_id` changes. If those rows are physically adjacent — because the sort key led with `trace_id` — the read is one short seek, not a full scan.

One "so what": the sort key doesn't just affect query speed, it determines whether ClickHouse needs to read 1% of the table or 100% of it.

### 2. The wrong sort key for traces

**Heading**: "Why `ORDER BY (start_time)` fails for traces"

Almost every observability tutorial starts with `ORDER BY (start_time)`. It makes intuitive sense — traces are time-series data, and you often query by time range. For a global query like "show me all spans in the last 5 minutes," it's excellent.

For a trace waterfall query — "show me all spans for trace ID `abc`" — it's a disaster. Spans from the same trace are spread across the entire table, ordered by when they ran. Spans from trace `abc` might be at positions 1, 14,203, 891,004, and 2,003,177 in the file. ClickHouse has to read the entire table to gather them.

**Concrete numbers**: A 10-million-span table with `ORDER BY (start_time)` and a trace waterfall query reads ~10M rows. The same table with `ORDER BY (trace_id, start_time)` reads ~8 rows (the average span count per trace). That's a 1,250,000× difference in I/O.

One "so what": sort key selection is the single most impactful design decision in a ClickHouse schema — more than indexes, more than compression.

### 3. The right sort key: `(trace_id, start_time)`

**Heading**: "Optimize for the primary lookup, not the secondary"

The correct sort key for a trace store is `ORDER BY (trace_id, start_time)`. This reflects the primary access pattern: fetch all spans for a trace, in chronological order.

`trace_id` as the leading key groups all spans for the same trace into a contiguous disk block. Within that block, `start_time` orders them chronologically — exactly what Grafana needs to render a waterfall without a client-side sort.

The secondary patterns (find spans from the last hour, find the slowest spans globally) work against this sort order. ClickHouse will do a full scan for those. That's an acceptable trade-off — the primary pattern is 99% of the query load, and the secondary patterns can be served by projections (Section 5).

One "so what": a sort key is a bet on the primary access pattern. Make the bet explicitly, not by copying a tutorial.

### 4. Compression: ZSTD over Snappy

**Heading**: "The compression choice is also a sort key consequence"

Once rows are sorted by `trace_id`, adjacent rows have high redundancy: many rows share the same `trace_id`, `tool_kind` is one of five enum values, `status` is one of three. Compression algorithms exploit run-length similarity in adjacent data.

Two main options:
- **Snappy**: fast decompression, moderate compression ratio (~2×). Good when decompression CPU is a bottleneck.
- **ZSTD**: slower decompression (by ~30%), much better compression ratio (~4–6×). Good when disk I/O is the bottleneck — which it almost always is for trace data.

For agent spans, ZSTD(3) is the right choice. After sorting by `trace_id`, the `trace_id` column compresses nearly perfectly (run-length encoding of 32-char strings that repeat for every span in a trace). `tool_kind` and `status` are low-cardinality — ZSTD shrinks them aggressively. The decompression overhead is under 1% of query time at this data scale.

One "so what": the sort key made the data compressible; ZSTD capitalizes on that.

#### Mermaid diagram: sort key → disk layout → read cost

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
    A["INSERT agent spans\n(random arrival order)"] --> B["MergeTree sort\nORDER BY (trace_id, start_time)"]
    B --> C["Disk: all trace=abc spans\nadjacent, ordered by time"]
    B --> D["Disk: all trace=xyz spans\nadjacent, ordered by time"]
    C --> E["Waterfall query:\ntrace_id='abc'\n→ read 8 rows ✅"]
    D --> F["Waterfall query:\ntrace_id='xyz'\n→ read 6 rows ✅"]
    B --> G["ZSTD compression\nhigh redundancy → 4× ratio"]
```

### 5. Projections for secondary access patterns

**Heading**: "When the sort key is wrong for a query, add a projection"

A projection is a secondary copy of the table data, sorted differently, stored alongside the primary data. ClickHouse automatically uses the right projection for each query.

For the `agent_spans` table, one projection covers the common secondary pattern — finding the slowest spans across all traces for a given time window:

```sql
ALTER TABLE agent_spans
    ADD PROJECTION proj_slow_spans
    (
        SELECT trace_id, span_id, tool_name, latency_ms, cost_usd, start_time
        ORDER BY (latency_ms DESC, trace_id)
    );
```

This stores the selected columns sorted by `latency_ms DESC`. A query `ORDER BY latency_ms DESC LIMIT 20` now reads a tiny projection block instead of the full table sorted by `trace_id`.

Projections trade storage for query speed. For monitoring use cases — "find the 10 slowest tool calls in the last hour" — that's a worthwhile trade. Don't add a projection for every possible sort order; add one when a secondary pattern is frequent and expensive enough to justify the storage cost.

One "so what": projections are the escape hatch when the primary sort key is the right choice 99% of the time and a secondary pattern needs to be served efficiently for the remaining 1%.

### 6. The materialized view for cost rollup

**Heading**: "Aggregation without re-scanning: materialized views"

The `trace_cost_rollup` table uses `AggregatingMergeTree` with a materialized view. Every time spans are inserted into `agent_spans`, the MV updates the rollup table with partial aggregate state. Queries for total tokens or cost per trace read from the rollup — they never touch `agent_spans`.

This is not unique to traces. It's the standard ClickHouse pattern for any "summary by ID" query that would otherwise require a full scan:

```sql
-- Without MV: scans all spans, groups by trace_id
SELECT trace_id, sum(cost_usd) FROM agent_spans GROUP BY trace_id;

-- With MV + AggregatingMergeTree: reads pre-aggregated rows
SELECT trace_id, sumMerge(cost_usd) FROM trace_cost_rollup GROUP BY trace_id;
```

The trade-off: writes are slightly more expensive (two tables updated per INSERT), but reads are orders of magnitude cheaper for high-cardinality aggregations.

One "so what": MVs shift the aggregation cost from read time to write time — the right trade when reads vastly outnumber data volume changes.

### 7. Distributed systems analogy

**Heading**: "The card catalog in the library"

Before electronic search, libraries used card catalogs — physical drawers of index cards, sorted by author, title, and subject. To find every book by Hemingway, you went to the author drawer, found "Hemingway, Ernest," and pulled out all his cards. You didn't read every book in the library.

MergeTree's sort key is the card catalog for your data. The sort order you choose is the catalog you build. A catalog sorted by "last modified date" would make it easy to find recently added books but nearly impossible to find all books by a specific author. A catalog sorted by "author" makes author lookups trivial and date-range lookups expensive.

For traces, the author is the `trace_id`. Build the catalog for the author.

One "so what": choose your sort key by asking "what drawer do users reach for most often?" — then sort by that first.

### 8. Closing: what today's schema ships

**Heading**: "Three decisions that compound"

The `agent_spans` schema makes three compounding decisions:

1. **Sort key** `(trace_id, start_time)` → waterfall queries read 8 rows, not 5M
2. **ZSTD(3) compression** → ~4× smaller than uncompressed, ~2× smaller than Snappy, because adjacent rows share a sort key prefix
3. **`proj_slow_spans` projection** → secondary "find slowest spans" query served without a full scan

None of these is exotic. They're the straightforward application of "optimize for your primary access pattern." The failure mode is copying a generic ClickHouse schema and wondering why your trace queries are slow. The fix is always the sort key.

The Go SDK emits spans. The collector ingests them. ClickHouse stores them correctly. Grafana renders the waterfall. The trace is complete.

---

## Mermaid Diagrams

Two diagrams:
1. Sort key → disk layout → read cost flowchart (Section 4)
2. Optional: sequence diagram showing INSERT path (Kafka → MV → agent_spans → trace_cost_rollup) — include only if the post runs short

Both use the verbatim init block from CLAUDE.md Section 4.5.

---

## Key Concepts Checklist

| Concept | Where introduced |
|---|---|
| MergeTree sort = physical disk order | Section 1 |
| Sort key determines I/O, not just speed | Section 2 |
| `(trace_id, start_time)` for trace waterfall | Section 3 |
| ZSTD vs Snappy trade-off | Section 4 |
| Projections for secondary patterns | Section 5 |
| AggregatingMergeTree + MV for cost rollup | Section 6 |
| Card catalog analogy | Section 7 |

---

## Tone Notes

- Reader is a backend engineer who knows SQL and has used Postgres or MySQL. ClickHouse terms need brief definitions on first use.
- "Granule" (8192 rows) is important ClickHouse vocabulary — introduce it briefly in Section 1 but don't over-explain
- The 1,250,000× number in Section 2 is the emotional anchor. Return to it implicitly in the closing.
- Avoid "simply" — sort key choice is genuinely subtle
- Keep code blocks short (4–10 lines); the prose does the explaining

---

## Self-Review Checklist (before push)

- [ ] `Day 34` in `<title>`, `<h1>`, accent tag chip, meta line
- [ ] Flowchart diagram uses correct mermaid init block (verbatim)
- [ ] Node labels ≤ 6 words each
- [ ] ≤ 8 nodes per diagram
- [ ] Every paragraph ≤ 3 sentences
- [ ] "MergeTree" defined on first use (not assumed known)
- [ ] "ZSTD" expanded on first use: "Zstandard (ZSTD)"
- [ ] No nested `<a>` tags
- [ ] Series nav CSS block present (`.series-nav`, `.series-posts`, `.series-post`)
- [ ] No placeholder URLs or localhost links in published HTML
