# Day 80 — AI Learning Post Plan

**Title:** Day 80 of Learning LLM Inference — Multi-Objective Routing — Scalarization and Weights
**Subtitle:** Weighted sum like cost-aware load balancing
**Day index:** 80
**Hook:** Expose `RoutingWeights` per tenant in RouteIQ config.
**Format:** `deep-dive` (one mechanism — scalarization, turning a multi-objective routing decision
into a single scalar via weighted sum — taught with a cost-aware load balancing DS analogy), per
`docs/BLOG-FORMAT-MIX.md`'s "cost / routing / cache economics → design or deep-dive" signal and
"mechanism in title" rule.

## Mechanism taught

Why `U = w_q·quality − w_c·cost − w_l·latency` is a real technique with a name (linear
scalarization) and a real limitation, not just "add some numbers together and pick the biggest" —
and why the tie-break toward the cheaper model matters precisely because scalarization can produce
genuine ties that a single scalar number can't distinguish on its own.

## Structure

1. The concrete problem: RouteIQ has to pick one model per request from several candidates, each
   good on a different axis — one is higher quality but slower and pricier, one is cheap and fast
   but scores lower on today's rollup. There is no single "best" model in the way there's a single
   largest number in a list — quality, cost, and latency are three different units that can't be
   compared directly (a quality point isn't a dollar isn't a millisecond), and "best" only means
   something once you decide how much each axis matters relative to the others.
2. DS analogy (attr-box, mine): cost-aware load balancing. A naive load balancer picks the backend
   with the most free capacity — one objective, trivially comparable. A cost-aware one scores each
   backend on a weighted combination of free capacity *and* the $/request cost of routing there
   (a spot-instance backend might be cheaper but slower to provision under load) — `score = w1 ·
   capacity − w2 · cost`. Nobody thinks that's a strange thing to do to a load balancer; the same
   move — reduce several objectives to one number via a weighted sum — is scalarization, and it's
   exactly what `decision.Utility` does with quality, cost, and latency instead of capacity and
   spend.
3. Why weights, not a fixed formula: two tenants can legitimately disagree about how much latency
   matters relative to cost — a real-time customer support tenant might set `WLatency` high and
   tolerate a costlier model; a batch-report tenant might zero out `WLatency` entirely and
   optimize purely on quality-per-dollar. `WeightsForTenant`'s override map (falling back to
   `DefaultWeights` when a tenant hasn't set one) is what makes the same `Decide` function serve
   both tenants correctly without either one needing a different code path.
4. The limitation scalarization has that this post names honestly: a weighted sum can only ever
   express tradeoffs that are linear in the objectives — it can't represent "I want quality above
   0.8 no matter the cost, and only optimize cost past that." That's a *constrained* optimization
   problem, a different technique entirely (RouteIQ doesn't attempt it today; `Candidate.Validate`
   only range-checks inputs, it doesn't enforce a quality floor). Scalarization is the right tool
   when a smooth tradeoff across all three axes is genuinely what's wanted — which is RouteIQ's
   actual stated goal (DESIGN.md's arc-level framing: "was the response actually good," measured
   alongside cost and latency, not instead of them).
5. Today's code, concretely: `decision.Utility(c, w)` is the scalarization step —
   `w.WQuality*c.Quality - w.WCost*c.CostPerCall - w.WLatency*c.LatencyP99Ms`, quality rewarded,
   cost and latency penalized. `Decide` then does the part scalarization alone doesn't solve:
   because collapsing three objectives into one number can produce genuine near-ties (two models
   that are, within the weights given, practically indistinguishable), it applies a **secondary**,
   deterministic tie-break — prefer the cheaper of two candidates within `tieEpsilon` of the top
   utility — the same way a load balancer with a near-tied weighted score needs a second,
   deterministic rule (round-robin, lowest ID) rather than an unstable pick that could flap between
   two backends on every request.
6. Today's Experience post, same shape one level up: Delivery Hero's Revisit Order System never
   mutates a Route `{ }` object in place — a new correct polyline becomes a new revision. RouteIQ's
   `Decide` has the identical discipline at the decision layer: it doesn't adjust a `Candidate`'s
   fields to declare it the winner, it returns a new, separate `Decision` value computed from an
   unmodified slice of inputs. Both are instances of the same rule — a decision or a fact that
   readers might already be holding a reference to should never change silently underneath them.
7. So-what: "just weight the objectives and add them up" sounds almost too simple to name, but
   knowing it's called scalarization — and knowing exactly what it can't express (hard
   constraints, non-linear tradeoffs) — is the difference between using it deliberately, inside
   its actual domain of validity, and reaching for it by accident and being surprised when a
   tenant's real preference ("quality floor, then optimize cost") can't be expressed as any set of
   linear weights.

Gold reference read: `blog/series/ai-learning/day-2-continuous-batching-vllm.html` (series
gold-standard mechanism deep-dive) plus `day-79-score-normalization-0-1-vs-likert.html` (most
recent AI Learning post, for register match and because Day 79's own rollup output — the quality
signal — is the direct predecessor input `FromRollupRow` consumes today).

Required mermaid init block used (per CLAUDE.md §4.5). Diagram labels ≤ 6 words. Cross-links to the
companion Experience post (Day 80) and to Days 77, 78, 79.
