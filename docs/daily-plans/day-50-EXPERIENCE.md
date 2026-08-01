# Day 50 — Experience Blog Plan

**Title**: Copy-Paste Debuggability
**Subtitle**: Stealth · on-call · operability
**Employer context**: `docs/context/resume-extracted.md` (general "any employer" fallback per
CLAUDE.md section 1 — no single incident/system is the anchor here; this is a synthesized
pattern across roles, which is exactly what the `patterns` format calls for). Relevant resume
lines only:
- Wayfair: "Engineered a high-throughput bulk processing framework (99.99% availability) with
  distributed rate limiting and circuit breakers, eliminating degradation and cascading
  failures under peak global load" — 20k+ suppliers, 250k+ SKU updates/supplier.
- Delivery Hero: "Designed async SQS + Kinesis pipeline decoupling order processing from
  notifications, guaranteeing sub-second delivery status updates for millions of active users
  at peak."
- 7.5 years across five companies, each with its own on-call rotation and incident tooling.

**Format**: `patterns` (per `docs/BLOG-FORMAT-MIX.md`: "README as hiring artifact" and
"synthesized patterns from multiple incidents — not a single fake outage" map directly to a
post about runbook culture across roles, not one company's postmortem. Days 48-49 already used
design/deep-dive framing; this also keeps the last-10 mix from clustering).

**Bridge**: README "debug step 7" is runbook culture — ops-friendly beats clever. Today's code
in agent-replay-engine implements that lesson.

## Angle

Anchor on a pattern repeated across every on-call rotation Akshant has been part of: the tools
that actually get used at 3am are never the cleverest ones — they're the ones with a runbook
you can copy-paste without having to remember which flag does what. A circuit breaker system
(Wayfair) or a decoupled notification pipeline (Delivery Hero) is only as good as the on-call
engineer's ability to act on it fast, half-awake, without re-deriving the mental model from
scratch. Bridge into today's code: `agent-replay-engine`'s CLI grew four separate debugging
capabilities over four days (Day 46 stop-at-step, Day 47 diff, Day 48 inject-timeout, Day 49
streaming) and none of them had been written down as an *order* until today — the same gap a
good on-call runbook closes for any production system.

**Attribution boundary**: Akshant engineered the Wayfair bulk-processing framework (circuit
breakers, rate limiting) and designed the Delivery Hero SQS/Kinesis decoupling — both `attr-box
mine`. Keep the framing to the resume's own language: "eliminating degradation and cascading
failures," "sub-second delivery status updates." Don't invent a specific page/incident
timestamp or a named on-call tool — the post is about the *pattern* of runbook culture, not a
fabricated pager story.

**Do not invent**: no fabricated incident transcript, page time, or specific runbook tool name
beyond what's in resume-extracted.md; scale numbers stay at 20k+ suppliers / 250k+ SKUs
(Wayfair) and "millions of active users" (Delivery Hero).

## Structure (match last 2 Experience posts' register/length)

1. Hook — the tool that's cleverest on a whiteboard is rarely the one that gets opened during a
   page; the one with a runbook wins
2. The pattern across roles: circuit breakers (Wayfair) and decoupled pipelines (Delivery Hero)
   both only pay off if on-call can act on them fast — a good README is part of the design, not
   an afterthought
3. The bridge to agent-replay-engine: four debugging capabilities built over four days, no
   fixed order to run them in until today
4. What today's code enforces — the seven-step runbook, plus a CI smoke test that keeps the
   README's commands honest (if the commands in the README stop working, the smoke test fails
   before a human ever tries to copy-paste them at 3am)
5. One concrete analogy grounded in a physical object (e.g., a fire extinguisher's instructions
   printed on the side, not a manual filed in a drawer)
6. So-what closer tied back to LensAI/TraceForge's debugging story: a debugging tool's value
   is capped by how fast a tired engineer can act on it, not by how many capabilities it has

Kicker: `Experience · Day 50 of 150`. Max 3 sentences/paragraph. Full self-review checklist from
CLAUDE.md section 5 before publish.
