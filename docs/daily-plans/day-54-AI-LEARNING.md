# Day 54 — AI Learning Blog Plan

**Title**: Day 54 — Flame Graphs — CPU Profile for Agents
**Subtitle**: LLM wait vs tool exec vs queue
**Hook**: Wide bars are where budget died — color by dollars.
**day_index**: 54

**Format**: `deep-dive` (per `docs/BLOG-FORMAT-MIX.md`), following the GOLD post
(`day-2-continuous-batching-vllm.html`) structure: mechanism first, systems-engineering
parallel (CPU flame graphs, since the title names them directly), production failure
modes, honest gap.

**Bridge**: today's code (`pkg/report/flame.go`) renders `CostReport` as a flame-graph
timeline — box width proportional to a tool call's dollar cost, color on a heat gradient,
the single most expensive call per row marked. The post explains why a flame graph (width
= resource consumed, contiguous per-row layout) is the right visual for "where did the
money go" versus Day 53's divergence timeline (width = fixed, aligned by step index),
which answers a different question ("where did the two runs disagree").

## Angle

A CPU flame graph answers one question: across a profiled call stack, which function ate
the most wall-clock time — answered by making that function's box the widest one on
screen, stacked contiguously with its neighbors so the eye reads "biggest box" as "biggest
cost" without doing arithmetic. Brendan Gregg's flame graphs made that mapping (width =
time, not position = time) the whole insight; two functions running at different points in
the trace but taking the same time render the same width, because width was never encoding
"when," only "how much."

An agent's tool-call trace has the identical shape, with dollars standing in for
wall-clock time. A tool call that hits an expensive external API costs more than one that
reads a local cache, and that difference is invisible in Day 53's timeline — every box is
the same fixed width regardless of what the call cost, because Day 53's timeline was
built to answer a different question ("where did two agents' sequences diverge") that has
nothing to do with cost. Day 54 doesn't replace that timeline; it adds a second one that
answers the cost question the same way a CPU flame graph does: width proportional to
spend, color on a heat gradient, the widest box being the answer to "where did the budget
die" before a reader reads a single dollar figure.

Sections: the CPU-flame-graph mental model and why width (not color, not position) is the
semantically loaded dimension; why `agent-benchmark-runner`'s flame graph is two
independent per-row strips instead of aligned columns (a true flame graph's contiguous
layout, versus Day 53's aligned-by-step-index layout, and why forcing cost-weighted rows
into aligned columns would misrepresent cost); the heat-gradient color choice and the
single-peak-marker decision; production failure modes a cost flame graph surfaces that a
pass/fail badge or a divergence timeline cannot (a passing run that's quietly 10x more
expensive than a failing one); the honest gap (no live per-call cost telemetry yet —
`BuildCostReport` takes cost as an explicit parameter, same shape as Day 53's `Build`
taking tool call sequences as a parameter rather than reaching into data it doesn't have).

## Series Navigation

Previous: Day 53 — Human-Readable Benchmark Reports
Next: Day 55 — Cross-Product Metrics — LensAI × TraceForge
