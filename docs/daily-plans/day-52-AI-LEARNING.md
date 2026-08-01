# Day 52 — AI Learning Blog Plan

**Title**: Day 52 — Statistical Rigor — N Runs, Confidence
**Subtitle**: Don't benchmark once
**Day index**: 52
**Hook**: Run 30 times; report median cost and p95 steps.

**Format**: `design` / `deep-dive` hybrid — per `docs/BLOG-FORMAT-MIX.md`'s AI Learning
table: methodology signals map to `design`/`deep-dive`. Teach the one mechanism (why one
run is an anecdote and what N runs + a confidence interval actually buy you) with the DS
analogy required by CLAUDE.md section 4.5/4.3.

**DS analogy** (attr-box, physical/everyday object): judging a benchmark from one agent
run is like judging a restaurant from one meal — maybe the kitchen had an off night,
maybe you got the best table and the fastest server. One visit gives you a data point,
not a rating. A rating needs enough visits that a bad night gets averaged out instead of
mistaken for the truth.

**Core concept**: agent runs are non-deterministic even holding the task, seed, and
prompt fixed — tool latency jitter, retries, provider-side sampling all inject variance
a single run can't separate from real behavior. Running N times and reporting a
distribution (median step count, P95 step count, pass rate with a confidence interval)
instead of one pass/fail turns "agent A looked better" into a statement with an error bar
attached. The width of that confidence interval is itself information: a 95% CI of
[0.60, 0.95] on a 10-run batch says "run more," a CI of [0.88, 0.92] on a 100-run batch
says the estimate has actually converged.

**Mermaid diagram** (≤8 nodes, labels ≤6 words): Base seed → Derive N seeds → Bounded
worker pool → N repetitions (parallel) → Per-run results → Summarize (median · P95 ·
CI) → Benchmark report.

**Required mermaid init block**: per CLAUDE.md section 4.5, exact block, no variations.

## Series Navigation

Previous: Day 51 — Benchmark Methodology for Agents
Next: Day 53 — TBD
