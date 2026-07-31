# Day 46 — Experience Blog Plan

**Title**: Replay Step 6 — Stop Before the Blast Radius
**Subtitle**: Walmart · OTA rollback · partial deploy
**Employer context**: `docs/context/resume-extracted.md` (Walmart Labs, WeIoT SmartBuildings —
no dedicated employer doc exists for Walmart yet, so this uses the "any employer" fallback per
CLAUDE.md section 1). Relevant resume lines only:
- "7M+ sensors, tens of millions of telemetry points/min: Architected WeIoT SmartBuildings
  ingestion layer on Azure IoT Hub... across 50+ global facilities."
- "Fault-tolerant edge-to-cloud OTA firmware framework — reliable config syncs and updates for
  millions of distributed devices under intermittent network conditions."

**Format**: `rollout` (per `docs/BLOG-FORMAT-MIX.md`'s signal table: "OTA" in the subtitle maps
directly to rollout — before/after topology, rollback plan, metrics that proved success. Day 45
already used `design`/`deep-dive`, so this also keeps the last-10 mix from clustering).

**Bridge**: `--stop-at-step` is OTA rollback for agents — fix before step 7 ships. Today's code
in agent-replay-engine implements that lesson.

## Angle

Anchor on the WeIoT OTA firmware framework: pushing a config or firmware update to millions of
distributed devices (HVAC controllers, sensors) across 50+ facilities under intermittent
network conditions. A bad OTA push doesn't get rolled back all-at-once — it gets rolled back in
waves, and the discipline that makes that safe is stopping the rollout *before* the wave that's
about to touch the device population you haven't validated yet, not after.

Bridge that into today's `--stop-at-step` flag: replaying a multi-step agent run has the same
shape. If step 7 is where a past run went wrong, you don't need to replay through step 7 to
learn something — you replay steps 1 through 6, inspect state, and stop. Same discipline,
different blast radius: device fleets vs. tool-call steps.

**Attribution boundary**: Akshant architected the WeIoT SmartBuildings ingestion layer and the
OTA firmware framework as a Software Engineer II on that team — this was his own build, not a
larger team's design he's describing secondhand. Keep the framing to what's in the resume: the
ingestion layer, the OTA framework, the facility/sensor scale numbers. Don't invent specific
incident timelines, device model names, or rollback tooling details beyond "waves" / staged
rollout, since the source doc doesn't include them.

**Do not invent**: scale numbers beyond "7M+ sensors", "tens of millions of telemetry
points/min", "50+ global facilities"; no fabricated outage story — this is a design/rollout
essay about staged rollback discipline, not a postmortem.

## Structure (match last 2 Experience posts' register/length)

1. Hook — the moment a rollout is *about* to touch the device population you haven't validated
   yet, and the decision to stop rather than push through
2. The WeIoT OTA lesson: millions of devices, intermittent network, why updates go out in waves
   and why "stop before the next wave" beats "roll everything back after"
3. The bridge to agent replay: `--stop-at-step` is the same wave-boundary decision, applied to
   tool-call steps instead of device batches
4. What today's code enforces: replay serves frozen responses up through step N, then halts —
   no step N+1 side effect, no re-triggering the step you already know is broken
5. One concrete analogy grounded in a physical object (e.g., a valve you close mid-pour, not a
   spill you mop up after)
6. So-what closer tied back to LensAI/TraceForge's debugging story: a debug tool that lets you
   stop is more valuable than one that only replays to the end

Kicker: `Experience · Day 46 of 150`. Max 3 sentences/paragraph. Full self-review checklist
from CLAUDE.md section 5 before publish.
