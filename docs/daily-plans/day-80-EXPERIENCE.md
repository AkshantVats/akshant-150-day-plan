# Day 80 — Experience Post Plan

**Title:** Route Revisions and Revisit Order System — Compensating Bad Polylines
**Subtitle:** Delivery Hero · immutable Route { } snapshots · rollback without corrupting UI
**Format:** `design` (tradeoff essay: immutable revision objects vs in-place mutation as the fix
for a bad routing output — options table, decision, rejected alternatives, consequences; per
`docs/BLOG-FORMAT-MIX.md`'s signal table, "why we chose immutable snapshots over patching in
place" is a design-decision shape, not a single-incident postmortem or a before/after topology
rollout)
**Bridge:** RouteIQ's decision engine (today's code) also never mutates a `Candidate` in place —
`Decide` picks a winner from an immutable slice of candidates and returns a new `Decision`, the
same "don't patch state in place, produce a new versioned object" discipline this post's Route
`{ }` revisions apply at the data-model layer.

## Format diversity check

Last 10 Experience posts (Days 70–79): 70 design ("Exact Match Before Fuzzy" — cache-lookup-order
tradeoff), 71 deep-dive ("Normalization Is Contract Testing" — one mechanism), 72 deep-dive
("Two-Tier Cache Metrics"), 73 incident ("Hash Collisions Happen"), 74 design ("OTel for Cache
Tiers" — instrumentation tradeoff), 75 rollout ("Wayfair's Redis Lua Token Bucket" — cutover to a
new rate-limit mechanism), 76 feature ("Circuit Breaker Half-Open State in Production"), 77
deep-dive ("Agoda P99 Cannot Be Averaged"), 78 rollout ("Decoupling SQS from OSRM"), 79 rollout
("Stream Analytics Dropped Messages — Switching to Kafka"). Incident is 1 of 10 — nowhere near the
4-of-10 trigger — but `rollout` already sits at 3 of 10 (75, 78, 79), including the two most recent
posts back-to-back. `design` for Day 80 avoids a fourth consecutive-leaning rollout and fits the
topic better: today's actual decision is "immutable revision object vs correcting a bad polyline
in place," a tradeoff choice with a clear rejected alternative, not a substrate cutover with a
before/after topology.

## Employer context used

`docs/delivery-hero-rider-tracking-system.md` (canonical topology, source of truth) — Route
Service (EKS stack) and Revisit Order System both produce the Route `{ }` object; Revisit Order
System is explicitly scoped as "audit replay / immutable snapshots into Route object." This post
does not invent a new pipeline — it stays inside the documented boundary: Route Service computes a
polyline via OSRM, Revisit Order System is the mechanism that handles what happens when that
polyline is wrong (a map-matching miss, a road closure OSRM's graph hasn't caught up to, a stale
snapshot after a rider re-routes) without corrupting what the UI is already showing a customer or
support agent mid-delivery.

`docs/context/resume-extracted.md` — Delivery Hero bullet: "1M+ daily orders · 5k map
adjustments/sec: Scaled logistics platform to 1M+ daily orders on AWS EKS (10k+ concurrent
requests, zero downtime); built end-to-end rider tracking using OSRM processing 5k+ real-time
route updates/sec." "5k map adjustments/sec" is the primary-source number this post's "bad
polyline" framing anchors to — a route recomputation at that rate is common enough that some
fraction of them will disagree with what a rider's device or a support agent's screen already
rendered, which is the concrete problem a revision system exists to solve.

Continuity: this arc has two prior DH rider-tracking posts already live —
`five-thousand-geo-events-per-second.html` (stream shape, partition skew, OSRM match quality) and
`ten-thousand-concurrent-requests-eks-patterns-delivery-hero.html` (Route Service + Route Consumers
autoscaling). Both already establish Order SQS's lifecycle events, Route Service/Route Consumers
reading from it, and OSRM producing the Route `{ }` object. Day 80 does not re-derive that
topology — it adds the one component neither prior post covered: Revisit Order System, and the
specific question of what happens to a Route `{ }` object already rendered on a screen when the
routing engine changes its mind.

## Structure (design format: the concrete problem → options considered → decision → rejected
alternatives → consequences → bridge to today)

1. The concrete problem: a Route `{ }` object (polyline, distance, revision) is already on a
   customer's or support agent's screen. Then something changes the correct answer — OSRM's
   underlying graph updates, a rider physically diverges from the computed path, a road closure
   invalidates the current polyline. Route Service (or Route Consumers, reading the same Order SQS
   lifecycle stream) now has a *new* correct route. The question: how does the system get the
   new, correct polyline in front of the UI without breaking whatever was mid-flight against the
   old one — a support agent's screen that just loaded, a client-side animation interpolating along
   the stale path, an analytics event already emitted with the prior revision's data.
2. Options considered (table):
   - **A. Mutate the existing Route object in place.** Cheapest to implement — overwrite the
     polyline field, done. Rejected: any reader holding a reference to the old object (a UI that
     fetched it a second ago, an in-flight GBQ export) now silently sees different data at the
     same identity, with no way to tell "this changed" from "this was always this." A support
     agent mid-call with a customer, reading a polyline that just changed under them without any
     signal, is the specific failure this option produces.
   - **B. Delete and recreate.** Avoids partial-mutation confusion but destroys the audit trail —
     there's no way to answer "what did we tell this customer five minutes ago" after the fact,
     which matters both for support escalations and for debugging a routing regression after it's
     already been overwritten away.
   - **C. Immutable revision objects via Revisit Order System (chosen).** Each Route `{ }` object
     is versioned; a new correct polyline is a *new* revision, not a mutation of the old one. The
     old revision stays exactly as it was for whoever already has a reference to it; a reader that
     wants "current" explicitly asks for the latest revision rather than assuming a stable object
     never changes underneath it.
3. Decision: C. Revisit Order System's "audit replay / immutable snapshots" role (per the
   canonical topology doc) is precisely this — it's the component responsible for producing a new
   Route `{ }` revision rather than patching the old one, and for making prior revisions available
   for replay when a support agent needs to reconstruct exactly what a customer saw at a given
   moment.
4. Rejected alternative revisited: option A wasn't rejected because in-place mutation is always
   wrong — it's rejected specifically because a Route object has readers with no natural way to
   detect a silent change. A field that's genuinely private and single-reader can mutate safely;
   a field surfaced to a UI, an analytics pipeline, and a support tool at once cannot, without
   either a version bump or a lot of defensive re-fetching logic pushed onto every reader.
5. Consequences: readers that want "give me whatever is current" ask for the latest revision
   explicitly rather than holding a long-lived reference and assuming it stays correct. A support
   agent reconstructing a customer complaint can replay the exact revision sequence a delivery
   went through, not just see today's final answer. The cost is real too — more objects, more
   storage, a "which revision is authoritative right now" question that has to be answered
   somewhere (Route Service, by construction: whichever revision it most recently emitted).
6. Bridge to today's code: RouteIQ's `Decide` function has the identical shape at a much smaller
   scale — it never mutates a `Candidate` to be "the winner," it returns a new `Decision` value
   built from an immutable slice of inputs. A tie-break toward the cheaper model is a deterministic
   function of the inputs, not a stateful adjustment to one of them — the same reason Revisit Order
   System produces a new revision instead of editing the old polyline: a decision that can silently
   change out from under whoever already read it is a decision nobody can fully trust.
7. So-what: "just overwrite the field" is always the cheapest first instinct, and it's wrong the
   moment more than one part of the system might be holding a reference to the value being
   overwritten. Immutable revisions cost more upfront and pay it back the first time someone needs
   to answer "what did we actually tell the customer" after the fact.

Gold reference read: `blog/series/experience/day-79-stream-analytics-to-kafka.html` and
`blog/series/experience/day-78-decoupling-sqs-from-osrm.html` (two most recent Experience posts)
for register/voice/section-length match; `five-thousand-geo-events-per-second.html` and
`ten-thousand-concurrent-requests-eks-patterns-delivery-hero.html` (existing DH gold-reference
posts) for established topology, scale numbers, and voice on this exact system.
