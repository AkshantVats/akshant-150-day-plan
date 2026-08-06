# Day 72 — AI Learning Post Plan

**Title:** Day 72 — L1/L2 Stack Design
**Subtitle:** Redis then pgvector
**Day index:** 72
**Hook:** Two-tier is Agoda hot/cold again.
**Format:** `deep-dive` (one mechanism — multi-tier cache composition and its metrics —
taught with a DS analogy), per `docs/BLOG-FORMAT-MIX.md`'s guidance for architecture-composition days.

## Mechanism taught

Why a multi-tier cache needs three-way outcome accounting (`l1_hit` / `l2_hit` / `miss`), not
just a single hit/miss boolean, and why the backfill-on-L2-hit policy (write the response into
L1 after a slower tier resolves it) is what makes a two-tier stack's *steady-state* behavior
different from its cold-start behavior — a distinction that's invisible if you only ever look
at the blended hit rate.

## Structure

1. Single hit/miss vs. three-way accounting — a blended 92% hit rate can't tell you whether
   you're spending most of your latency budget in a fast tier or a slow one; splitting hits by
   which tier resolved them is what makes tier capacity planning a numeric decision.
2. DS analogy (attr-box, team): CPU cache hierarchy — L1/L2/L3 — where a miss at each level
   costs a fixed, larger multiple of the level before it, and a profiler that only reported
   "cache hit: yes/no" would be useless for deciding whether to grow L1 or L2. Grounded in the
   literal L1/L2 naming prompt-fingerprinter borrows.
3. The backfill policy: an L2 hit writes its response into L1 before returning, so the *next*
   byte-identical request becomes an L1 hit instead of paying the L2 cost again. Contrast with
   a stack that never backfills — every repeat of a semantically-resolved prompt would re-pay
   the embedding cost forever, no matter how many times it repeats.
4. Fail-open on the fast tier: if the Redis `GET` itself errors (not a miss — an actual
   connection failure), the stack falls through to L2 rather than treating that as a hard
   failure, mirroring `cost-budget-enforcer/pkg/middleware`'s existing fail-open precedent for
   a degraded cache dependency.
5. What this doesn't prove yet — no live Redis or Postgres instance in this sandbox (no Docker
   daemon), so the stack's actual hit-rate shift after backfill is a documented design property,
   not yet a measured one.

Gold reference read: `blog/series/ai-learning/day-2-continuous-batching-vllm.html` (series
gold-standard mechanism deep-dive) plus Day 71's AI Learning post for recent-post register
match.

Required mermaid init block used (per CLAUDE.md §4.5). Diagram labels ≤ 6 words. Cross-links
to the companion Experience post (Day 72) and to Day 70/71.
