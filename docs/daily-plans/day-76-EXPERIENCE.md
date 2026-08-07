# Day 76 — Experience Post Plan

**Title:** Supplier API Circuit Breakers — Half-Open State in Production
**Subtitle:** Wayfair: testing the recovery path before Black Friday, not just the trip
**Format:** `feature` (a specific operational practice added to an existing system — the manual
half-open verification step — not a single-incident timeline or a broad tradeoff essay; per
`docs/BLOG-FORMAT-MIX.md`'s table, `feature`/arc is the closest match for "here's a capability we
built and why")
**Bridge:** Fingerprint rule changes are config deploys — treat breaking normalization like opening
a circuit on live traffic.

## Continuity check — required before drafting

A gold-reference post already exists on this exact system:
`blog/series/experience/supplier-apis-and-token-buckets-wayfair-circuit-breaker.html` (cited in
`docs/BLOG-FORMAT-MIX.md`'s gold-reference table, format `design`). It already establishes:
the circuit breaker sits behind the per-supplier token bucket on the pricing submission path
(`gst-acc-promotions` → PAS → SPCS), and **the trip threshold is five consecutive timeouts, or a
50% error rate in a 30-second window** — opens to an immediate `503` on all requests.

Day 76 does **not** re-derive that threshold or invent a different one (an earlier subtitle draft
said "3 failures in 60s" — dropped in favor of the number the gold post already published, since a
reader who read both posts would notice a contradiction on the same system). What the gold post
never covers: how the circuit comes *back* — the half-open state, and specifically that it was
tested manually, on purpose, ahead of Black Friday, rather than trusted to recover unattended the
first time it mattered. Day 75 already revisited this same Wayfair pricing path (the Lua token
bucket, at 250k+ SKU scale) — Day 76 revisits the circuit breaker half of that same system, the
piece Day 75 didn't touch.

## Employer context used

`docs/context/resume-extracted.md` — Wayfair bullet: "250k+ SKU updates per supplier in near
real-time: Engineered a high-throughput bulk processing framework (99.99% availability) with
distributed rate limiting and circuit breakers, eliminating degradation and cascading failures
under peak global load" — the source for "99.99% availability" and "circuit breakers" as
Akshant's own scope, not inherited. No new scale numbers invented beyond what this bullet and the
gold-reference post already establish.

## Structure (feature format: the gap → the practice → why it's not automatic → the payoff)

1. Recap the trip condition in two sentences (link to the gold post rather than re-explaining it
   in full) — five consecutive timeouts or 50% error rate in 30s opens the breaker, `503`s
   everything, protects a pricing core that would otherwise queue unbounded behind a dying
   downstream.
2. The gap: a circuit breaker's *open* transition gets exercised constantly (every real downstream
   blip trips it) — its *half-open* transition, the one-probe-request test that decides whether to
   fully close again, gets exercised far less often, because most trips are brief. A path that
   rarely runs is a path nobody has actually watched succeed under load, which is exactly the
   failure mode a peak-traffic event (Black Friday) turns from theoretical into expensive.
3. The practice: ahead of Black Friday, deliberately forcing the breaker open (a controlled
   downstream fault injection, not a real outage) and watching the half-open probe and recovery
   run under realistic pricing-submission traffic, instead of trusting the automatic transition's
   first real test to be the one that matters most.
4. Why this isn't redundant with the breaker's own logic: the breaker's state machine is correct
   by construction (the code either lets one probe through in half-open or it doesn't) — what a
   manual drill actually tests is everything *around* that logic: does a flood of retried requests
   arrive at the exact moment the probe succeeds and immediately re-trip the breaker before it can
   stabilize, does a monitoring dashboard reflect the transition in time for someone to notice if
   it doesn't recover, does the fail-open Redis policy from Day 25/75's token bucket interact badly
   with a breaker that's simultaneously testing recovery.
5. Bridge to today's code: `prompt-fingerprinter`'s new admin `PUT /tenants/{id}/fingerprint-rules`
   endpoint changes what counts as "the same prompt" for a tenant the moment it's called — a
   normalization rule change is a config deploy with the same shape as a circuit breaker's state
   transition: correct by construction in isolation, but worth deliberately exercising (an
   integration test proving the exact scenario it changes, not just trusting the code path) before
   trusting it in production the same way a circuit breaker's recovery path gets tested before it's
   trusted for real.
6. So-what: a mechanism being provably correct and a mechanism being *exercised* are different
   claims — the second one only gets made true by deliberately running the path that matters most
   before the day it matters most, whether that's a circuit breaker's half-open probe or a
   fingerprint rule change's first real traffic.

Gold reference read: `supplier-apis-and-token-buckets-wayfair-circuit-breaker.html` (the system this
post extends) and the two most recent Experience posts (Days 74-75) for register/voice match.

## Format diversity check

Last 10 Experience posts (Days 67-75, plus today makes 11 in the window — dropping Day 66):
67 feature, 68 design, 69 design, 70 design, 71 deep-dive, 72 deep-dive, 73 incident, 74 design,
75 rollout. Design is already 4 of the last 9 published; Day 76 as `feature` keeps design from
becoming a 5th and brings feature to 2 of the last 10 — under the 4-of-10 trigger on every format,
not just incident.
