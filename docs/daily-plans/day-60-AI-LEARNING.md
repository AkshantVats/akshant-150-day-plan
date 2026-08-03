# Day 60 — AI Learning Blog Plan

**Title:** Day 60 — Semantic Caching Economics
**Subtitle:** Threshold vs savings curve
**day_index:** 60
**Hook:** Sweep 0.88–0.96 on real prompts — plot dollars, not vibes.
**Format:** `design` / deep-dive on one mechanism (similarity threshold selection), per
`docs/BLOG-FORMAT-MIX.md` — this is the first RouteIQ-arc post, opening where the TraceForge
arc closed at Day 58/59.

## Required reading before writing

- `day-2-continuous-batching-vllm.html` (GOLD post) for depth/structure.
- Most recent AI Learning post (Day 59 — "TraceForge — Agent Observability Is Distributed
  Tracing With Money on the Line") for register, and to make the arc handoff explicit: Day 59
  closed the observability chapter, Day 60 opens the optimization/caching chapter RouteIQ
  owns.
- Today's `semantic-cache-engine/DESIGN.md` (Day 60 code) for the concrete technical anchor:
  per-tenant similarity threshold, false-positive budget, TTL/decay policy.

## Angle

- Open on the hook line: sweeping a similarity threshold from 0.88 to 0.96 against real
  prompt traffic and plotting the actual dollar tradeoff (cache-hit savings vs cost of wrong
  answers served), not an intuition about "how similar is similar enough."
- Core mechanism: as the threshold rises, cache hit rate falls (fewer near-duplicates count
  as matches) but false-positive rate also falls — the curve has a knee, and the "right"
  threshold is wherever `hit_rate * savings_per_hit - false_positive_rate * cost_per_wrong_answer`
  peaks, not a fixed constant like 0.9 picked by feel.
- DS analogy (attr-box required): a semantic cache's threshold is a hash-collision tolerance
  dial — a normal cache treats any input difference as a miss (zero tolerance, exact key
  match); a semantic cache deliberately allows near-misses to count as hits, so the tradeoff
  curve is the same shape as tuning a Bloom filter's false-positive rate against its memory
  savings, just measured in dollars instead of bits.
- Tie to the arc: Day 59 closed TraceForge (observability). Day 60 opens RouteIQ
  (routing/caching) — the thing TraceForge's benchmark/replay tooling would evaluate once
  RouteIQ ships is exactly this threshold-vs-savings curve.

## Diagram requirement

Standard mermaid init block (CLAUDE.md §4.5). One flowchart or graph showing: incoming
prompt → embedding → similarity search against cache → threshold decision (hit vs miss) →
either served-from-cache or recompute-and-store. Labels ≤6 words, ≤8 nodes.

## Constraints

- Kicker: `Day 60 of 150`.
- ai.hook opening line, attr-box DS analogy present.
- No invented benchmark numbers presented as real production data — frame any example sweep
  as an illustrative methodology (e.g., "sweeping thresholds on a synthetic prompt set"), not
  a claim of a live experiment run in this build's sandbox.
