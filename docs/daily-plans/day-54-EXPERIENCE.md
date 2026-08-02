# Day 54 — Experience Blog Plan

**Title**: Flame Graphs — LLM Time vs Tool Time
**Subtitle**: Walmart · HVAC control loop · latency
**Employer context**: `docs/context/resume-extracted.md` only (no dedicated Walmart context
doc exists — table in CLAUDE.md §1 falls back to resume-extracted.md for any employer
without one). Relevant lines only:
- Walmart Labs, Bengaluru, Aug 2018 – May 2021, Software Engineer II, WeIoT SmartBuildings
  Platform, 3 years.
- Architected the WeIoT SmartBuildings ingestion layer on Azure IoT Hub: 7M+ sensors,
  tens of millions of telemetry points/min.
- Engineered real-time HVAC control loops via Azure Stream Analytics, automating energy
  optimization across 50+ global facilities.
- Fault-tolerant edge-to-cloud OTA firmware framework for reliable config syncs across
  millions of distributed devices under intermittent network conditions.
- Do NOT invent specific dollar/energy figures beyond what's in resume-extracted.md — the
  post's numbers stay qualitative (which subsystem, not a fabricated kWh delta).

**Format**: `design` (per `docs/BLOG-FORMAT-MIX.md`) — a decision-narrative about *where*
to spend tuning effort, not an incident postmortem. Last-10 Experience posts lean
deep-dive/patterns/reflection (Day 51 patterns, Day 52 patterns, Day 53 deep-dive) with no
recent incident run, so `design` keeps the mix varied without forcing an artificial
incident framing onto a genuinely design-shaped anecdote.

**Bridge**: color by cost is control-loop tuning — which actuator spends the energy.
Today's code in `agent-benchmark-runner` (`pkg/report/flame.go`) implements that lesson: a
flame-graph timeline that sizes and colors each tool call by dollar cost, so the most
expensive step is visually obvious instead of requiring a reader to scan a table of
uniform-width boxes.

## Angle

At Walmart Labs, WeIoT SmartBuildings ingested telemetry from 7M+ sensors across 50+
facilities and ran HVAC control loops over Azure Stream Analytics to optimize energy use.
The naive read of "where is energy going" is per-facility or per-zone aggregate power draw
— useful for a monthly bill, useless for deciding which actuator to retune this week,
because an aggregate number is uniform where the underlying consumption never is. A
facility's energy draw isn't spread evenly across its dampers, compressors, and fans; a
handful of actuators running against a stuck setpoint or a miscalibrated sensor account
for a disproportionate share of the draw, and a flat per-zone dashboard renders that
handful the same visual size as everything else.

The fix that mattered wasn't a new sensor or a new control algorithm — it was changing
what the operator saw first: instead of a uniform grid of zone tiles, a view sized and
colored by relative energy draw, so the actuator burning the most immediately reads as the
biggest, hottest box on the screen. That's a report design decision, not a control-theory
one, and it's the same decision `pkg/report/flame.go` makes for tool-call cost: a report
that gives every step the same visual weight is optimizing for symmetry over legibility,
and the reader who wants to know "where did the budget go" needs width and color to answer
that before they read a single number.

Bridge into `agent-benchmark-runner`: `RenderFlameGraphSVG` sizes each tool-call box by
its dollar cost and colors it on a heat gradient, marking the single most expensive call
per agent run — turning "where did the budget die" into a one-glance answer the same way
a draw-weighted HVAC view turned "which actuator needs retuning" into one.

## Series Navigation

Previous: Day 53 — 14 Calls vs 9 — The Report Hiring Managers Get
Next: Day 55 — TBD
