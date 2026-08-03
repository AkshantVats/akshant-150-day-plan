# Day 59 — AI Learning Blog Plan

## Data quality note (read first)

`data/plan.json`'s `days[59].ai` block has `title`/`subtitle`/`hook` identical to
`days[58].ai` ("Day 58 — Month 2 Synthesis — Agents Are Distributed Systems" /
"Day 59 — Month 2 Synthesis — Agents Are Distributed Systems" — same subtitle and hook
verbatim, only the day number differs). Day 58's post with that exact title is already
live on Profile main. Publishing a near-duplicate post one day later would be a real
content-quality problem, not a numbering nuance covered by CLAUDE.md §4.9 (which is
about the Experience/AI Learning day-number match, not about two AI Learning posts
sharing a topic).

**Resolution:** use `plan.json[59].product_blog` instead, which is distinct and matches
the day's actual code ticket ("TraceForge v1 launch HN + publish product essay"):

**Title:** Day 59 — TraceForge — Agent Observability Is Distributed Tracing With Money on the Line
**Subtitle:** Collector, analyzer, replay, benchmark — Month 2 product essay

## Required reading before writing

- `day-2-continuous-batching-vllm.html` (GOLD post) for depth/structure.
- Most recent AI Learning post (Day 58) for register — but do not reuse its thesis or
  title.
- `agent-benchmark-runner/pkg/lensai/writer.go` and `OBSERVABILITY.md`'s new `source`/
  `trace_id` section (added in Day 59's code PR) for the concrete technical anchor:
  one ClickHouse table, one Grafana dashboard, two event sources discriminated by a
  single column — the "money on the line" thesis made literal.

## DS analogy

One clearinghouse ledger with a transaction-type column, not two separate ledgers that
need reconciling — same idea as the attr-box analogy pattern used in prior posts, applied
to why `source='benchmark_run'` living in the same table as `source='inference'` beats a
second table.

## Diagram requirement

Standard mermaid init block (CLAUDE.md §4.5). One flowchart showing the four TraceForge
components feeding one ClickHouse table, discriminated by `source`. Labels ≤6 words, ≤8
nodes.
