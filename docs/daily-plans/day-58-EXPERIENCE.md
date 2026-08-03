# Day 58 — Experience Post Plan

**Title:** TraceForge — Agents Need a Flight Recorder
**Subtitle:** Delivery Hero · operations · postmortems
**Employer:** Delivery Hero — read `docs/delivery-hero-rider-tracking-system.md` before writing.
**Format:** `feature` (see `docs/BLOG-FORMAT-MIX.md`) — today's code is a launch rehearsal /
integration test on `agent-benchmark-runner`, not an incident.

## Bridge

Month 2 essay ties the benchmark report to Delivery Hero's postmortem format — steps,
cost, divergence. Today's code in `agent-benchmark-runner` implements that lesson: two
agents run the same task, and the divergence between their pass rates is exactly the
kind of "what happened, step by step, and where did it diverge from expected" structure
Delivery Hero's postmortems use for rider-tracking incidents (Route Service vs Route
Consumers disagreeing on state, e.g.).

## Angle

- Open on the DH postmortem habit of writing a timeline that captures *divergence*, not
  just root cause — where did two systems (or two runs) stop agreeing.
- Bring in the rider-tracking system's lifecycle contract (`PLACED` → `RIDER ENQUE` →
  `PICKED UP`) from the context doc as the concrete, real-system anchor — do not invent
  new pipeline details beyond what's in the canonical doc.
- Land on: `agent-benchmark-runner`'s divergence report is a flight recorder for agent
  runs the same way DH's SQS lifecycle events are a flight recorder for a delivery — you
  can't debug what you can't replay.
- Do NOT claim this shipped at Delivery Hero. Frame as "this is the DH habit that shaped
  how I built today's rehearsal test," matching resume-extracted.md scope (contributor,
  not sole owner, on Agoda WhiteFalcon; keep DH claims to operational patterns, not a
  specific system Akshant built there unless resume-extracted.md confirms it).

## Constraints

- Max 3 sentences per paragraph.
- One concrete analogy grounded in a physical/everyday object.
- Kicker: `Experience · Day 58 of 150`.
