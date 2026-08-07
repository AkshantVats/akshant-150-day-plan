# Day 73 — AI Learning Post Plan

**Title:** Day 73 — Collision Handling
**Subtitle:** TTL isolation on clash
**Day index:** 73
**Hook:** Treat like rare UUID collision — isolate blast radius.
**Format:** `deep-dive` (one mechanism — how a fast-path cache key check contains a collision it
cannot detect — taught with a DS analogy), per `docs/BLOG-FORMAT-MIX.md`'s guidance for a single
named mechanism.

## Mechanism taught

Why an exact-match cache keyed by a hash alone can never *detect* a collision (it would need to
store and compare the original input to notice, which defeats the point of a cheap key lookup),
and why the right engineering response is two independent containment mechanisms — scope the key
so a collision can't cross a boundary that matters, and bound how long a bad entry can live — not
a detection mechanism that doesn't exist.

## Structure

1. The detection problem: a hash function's whole job is to make different inputs *look* the
   same at a fixed, small size — a cache that only ever sees the hash literally cannot tell "same
   prompt" from "different prompt, same hash" apart, because that information was thrown away at
   hash time. This isn't a bug to fix; it's what a hash is.
2. DS analogy (attr-box, team): UUID collisions in a distributed ID generator. A v4 UUID is
   effectively never going to collide (122 random bits), but "essentially never" and "provably
   never" are different claims, and a system that assumes the former without a fallback for the
   latter is one rare draw away from two records silently sharing an identity. The engineering
   answer isn't "detect the collision" (also generally not possible after the fact without a
   uniqueness constraint elsewhere) — it's "scope IDs so a collision's damage is bounded, and
   don't let assumed-unique state live forever unchecked."
3. Today's two mechanisms, same shape: tenant-scoped Redis keys (`fingerprint:{tenant_id}:{fp}`)
   mean a collision under one tenant literally cannot produce a hit in another tenant's
   keyspace — not because it's unlikely, because the two tenants use different keys by
   construction. A 30-day hard TTL (`stack.HardTTL`, sourced from `semantic-cache-engine`'s own
   freshness policy, not invented fresh) means a corrupted entry self-expires and gets
   re-verified against L2 instead of persisting indefinitely.
4. Why bound-in-time and bound-in-scope are both needed, not just one: scoping alone caps *how
   many* tenants a collision can affect (exactly one) but not *how long* that one tenant keeps
   getting the wrong answer; a TTL alone caps *how long* but does nothing to stop a same-tenant
   collision from crossing prompts within that window. Composed, the two answer "how bad, for how
   long" instead of leaving either dimension unbounded.
5. What this doesn't prove: SHA-256's collision resistance is exactly why this whole scenario
   stays a drill instead of a real incident — the test seeds the *post-collision state* directly
   because forcing an actual SHA-256 collision isn't something any test (or attacker, at current
   compute) can do. The containment exists for a failure mode expected never to occur, the same
   engineering posture a distributed system takes toward any "effectively impossible" event
   whose cost, if wrong, is still worth bounding cheaply.

Gold reference read: `blog/series/ai-learning/day-2-continuous-batching-vllm.html` (series
gold-standard mechanism deep-dive) plus Day 72's AI Learning post for recent-post register match.

Required mermaid init block used (per CLAUDE.md §4.5). Diagram labels ≤ 6 words. Cross-links to
the companion Experience post (Day 73) and to Days 70–72.
