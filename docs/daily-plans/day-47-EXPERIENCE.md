# Day 47 — Experience Blog Plan

**Title**: Diff Two Traces — Git Blame for Agents
**Subtitle**: Delivery Hero · route divergence · A/B
**Employer context**: `docs/delivery-hero-rider-tracking-system.md` (Route Service, OSRM, Order
SQS lifecycle events, Revisit Order System's immutable Route object) + `docs/context/resume-
extracted.md` for scale numbers. Relevant resume lines only:
- "Delivery Hero · Berlin, Jun 2022–Jul 2023, Sr. Software Engineer, Global Logistics Platform"
- "1M+ daily orders · 5k map adjustments/sec: Scaled logistics platform to 1M+ daily orders on
  AWS EKS (10k+ concurrent requests, zero downtime); built end-to-end rider tracking using OSRM
  processing 5k+ real-time route updates/sec."

**Format**: `deep-dive` (per `docs/BLOG-FORMAT-MIX.md`: the mechanism — a diff algorithm — is
the hero of the post, not an incident or a rollout).

**Bridge**: First diverging span is where two drivers got different ETAs — same debugging
muscle. Today's code in agent-replay-engine implements that lesson.

## Angle

Anchor on a real class of Delivery Hero support ticket: two riders with near-identical orders
get different ETAs, and resolving the dispute means finding which OSRM routing decision first
diverged — not reading two full Route objects (polylines differ in nearly every coordinate due
to GPS jitter even when the underlying decision matched). Bridge into `pkg/diff`: it solves the
identical shape of problem for agent traces, comparing `ToolName` + `InputHash` per step instead
of raw JSON, and reporting only the first disagreement.

**Attribution boundary**: Akshant built the end-to-end rider tracking pipeline on OSRM and
scaled the platform to 1M+ daily orders on EKS — that's `attr-box mine`. The Revisit Order
System (audit-replay component per the canonical architecture doc) is referenced only as
context for why Route objects are immutable/replayable, not claimed as his own build.

**Do not invent**: no fabricated support-ticket transcript or specific dispute timeline; keep
scale numbers to what's in resume-extracted.md (1M+ daily orders, 5k+ route updates/sec, 10k+
concurrent requests).

## Structure (matched to last 2 Experience posts' register/length)

1. Hook — a support ticket that took an hour because two Route objects don't diff cleanly
2. Delivery Hero scale/role scene-setting (`attr-box mine`)
3. Why a textual diff of two routes is mostly noise (GPS jitter, timestamps)
4. The bridge to agent traces — same divergence-search shape, smaller trace
5. What today's code enforces — `pkg/diff`'s tool_name/input_hash walk, stat callout
6. Physical analogy — git bisect vs git diff ("git blame, not git diff")
7. Closer tied to LensAI/TraceForge's debugging story

Kicker: `Experience · Day 47 of 150`. Max 3 sentences/paragraph.
