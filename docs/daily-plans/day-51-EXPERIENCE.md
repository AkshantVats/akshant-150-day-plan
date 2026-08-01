# Day 51 — Experience Blog Plan

**Title**: Benchmark Agents Like Load Tests
**Subtitle**: Agoda · k6 · methodology
**Employer context**: `docs/context/agoda-whitefalcon-tsdb-architecture.md` + `docs/context/
resume-extracted.md` for scale numbers. Relevant lines only:
- Agoda WhiteFalcon: 1.5T events/day, Akshant Senior Engineer ~5 months. Akshant's
  contribution: extended the Scala query engine for cross-tier (Redis hot + S3/Parquet
  cold) queries, solving the quantile-merge problem — histogram bucket counts merged
  across tiers, then percentiles computed once on the merged histogram. Did NOT design
  WhiteFalcon, the RoaringBitmap engine, or the Kafka pipeline.
- The wrong-vs-right approach documented in context: `P95(hot) + P95(cold) ≠ P95(both)` —
  quantiles are not additive; you must merge the underlying distributions first.

**Format**: `design` (tradeoff essay) — per `docs/BLOG-FORMAT-MIX.md`: this is a DESIGN.md
day (`code` signal maps directly to `design`), and the real content is a methodology
decision (how do you compare two agents honestly) with an options table and rejected
alternatives, not a single-mechanism deep-dive or an incident.

**Bridge**: benchmark-runner task YAML is a k6 scenario for agents — same statistical
discipline, different subject under test. Today's code in agent-benchmark-runner
implements that lesson.

## Angle

Anchor on the same statistical discipline that made the WhiteFalcon cross-tier quantile
merge correct: you cannot average percentiles computed from different distributions and
call the result a percentile — you have to merge the underlying histograms first, then
compute the statistic once. The naive mistake (`P95(A) vs P95(B)` computed independently
and eyeballed) is the same class of error as `P95(hot) + P95(cold)`: it looks like a valid
comparison because the numbers are the same shape, but the inputs weren't held constant.

Bridge into `agent-benchmark-runner`: comparing "agent A feels better than agent B" from
separately-read transcripts has the identical flaw — if the two agents didn't run against
the same task, same seed, same tools, any difference in outcome is confounded with a
difference in *scenario*, not a difference in *agent*. A k6 load test would never compare
service A's P99 under one traffic profile to service B's P99 under a different one and
call it a benchmark; the scenario (RPS, payload shape, duration) is fixed so the only
variable left is the system under test. `agent-benchmark-runner`'s task YAML does the
same job for agents: fix `task_id` + `seed` + `prompt` + `tools_allowed`, then the only
thing that can differ between two runs is the agent.

**Options table** (design post core): free-form assertion scripts vs. LLM-judge scoring
vs. a closed set of typed, deterministic success criteria — same three-way tradeoff k6
faced choosing checks (deterministic assertions) over "does this response look right"
(subjective, non-repeatable). Consequence: the criteria set is not exhaustive (no fuzzy
grading yet), same honest limitation k6 checks have against genuinely open-ended output.

## Series Navigation

Previous: Day 50 — Copy-Paste Debuggability
Next: Day 52 — TBD
