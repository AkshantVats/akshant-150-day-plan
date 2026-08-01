# Day 52 — Experience Blog Plan

**Title**: Parallel Runs — Respect the Rate Limit
**Subtitle**: Delivery Hero · peak · concurrency caps
**Employer context**: `docs/delivery-hero-rider-tracking-system.md` (canonical topology —
Route Service + Route Consumers on EKS, OSRM cluster) + `docs/context/resume-extracted.md`
for scale numbers. Relevant lines only:
- Delivery Hero, Berlin, Jun 2022 – Jul 2023, Sr. Software Engineer, Global Logistics
  Platform. 1M+ daily orders, 5k map/route adjustments per second, 10k+ concurrent
  requests on AWS EKS at zero downtime. Async SQS + Kinesis pipeline decoupling order
  processing from notifications, eliminating cascading failures under peak load.
- Do NOT invent a specific named outage. This is a design/capacity-planning post about
  the concurrency cap decision on Route Service / Route Consumers, not a postmortem.

**Format**: `design` (tradeoff essay) — per `docs/BLOG-FORMAT-MIX.md`: the "EKS /
concurrent requests" signal in the title maps to `patterns`/`rollout`, but the actual
content here is a specific bounded-concurrency decision (options table: unbounded
fan-out vs. fixed worker pool vs. adaptive/AIMD limiting), which the doc explicitly
frames as `design` territory. Avoids being a third generic peak-EKS-incident post (see
`docs/PLAN-REALIGNMENT-RECOMMENDATIONS.md` guidance for days 8/20/82) by anchoring on the
concurrency-cap *decision*, not a scaling-under-load narrative already covered by
`ten-thousand-concurrent-requests-eks-patterns-delivery-hero.html`.

**Bridge**: the concurrency limit `agent-benchmark-runner`'s orchestrator puts on parallel
benchmark repetitions is the same discipline as capping Route Consumer concurrency during
Delivery Hero's dinner-rush peak — don't let your own fan-out become the thing that
degrades the system you're trying to measure or serve. Today's code in
`agent-benchmark-runner` (`pkg/orchestrator`, `MaxParallel`) implements that lesson.

## Angle

At Delivery Hero, Route Consumers read Order SQS and call OSRM per event; at 5k+
route updates/sec and 10k+ concurrent requests on EKS, the naive move — one goroutine (or
one pod, via unchecked HPA) per inbound event — turns a downstream dependency's own
capacity limit into *your* outage. OSRM has a bounded budget per instance; a burst of
unmetered concurrent callers doesn't get "5k/sec sustained," it gets queueing, then
timeouts, then retries stacking on top of the original burst. The fix wasn't "add more
OSRM replicas until the problem goes away" — replicas cost money and don't fix a client
that doesn't know its own concurrency. The fix was bounding concurrency at the caller:
a fixed worker pool sized to what OSRM (and the SLA around it) could actually sustain,
so peak traffic queues predictably at the edge instead of degrading unpredictably
downstream.

Bridge into `agent-benchmark-runner`: an agent benchmark that fires all N repetitions of a
task at once has the identical failure shape — it isn't testing "how does agent A behave,"
it's testing "what happens when a model provider gets N simultaneous requests from one
caller," which is a rate-limit test wearing a benchmark's clothes. `pkg/orchestrator`'s
`MaxParallel` is the same fixed-worker-pool decision as the Route Consumer fix: name the
concurrency budget explicitly instead of borrowing whatever the runtime's default fan-out
happens to be.

**Options table** (design post core): unbounded fan-out (fastest wall-clock, but the
caller becomes the rate-limit violator) vs. serial one-at-a-time (safest, but a 30-run
benchmark or a peak-hour backlog take unnecessarily long) vs. a fixed-size worker pool
(chosen — bounded, predictable, and the bound is a parameter instead of an accident).
Rejected: adaptive/AIMD-style dynamic concurrency (the textbook "better" answer) — out of
scope for both Route Consumers' first fix and Day 52's orchestrator, because a fixed pool
sized from known downstream capacity solves the actual problem without the added
complexity and failure surface of a feedback controller tuning itself in production.

## Series Navigation

Previous: Day 51 — Benchmark Agents Like Load Tests
Next: Day 53 — TBD
