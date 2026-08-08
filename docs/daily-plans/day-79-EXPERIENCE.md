# Day 79 — Experience Post Plan

**Title:** Walmart Stream Analytics Dropped Messages — Switching to Kafka
**Subtitle:** 7M sensors exposed bounded-window limits; we owned offset recovery
**Format:** `rollout` (a cutover from one streaming substrate to another, with a before/after
topology and a rollback story — not a single-incident postmortem; per
`docs/BLOG-FORMAT-MIX.md`'s signal table, "migration", "SQS →"-shaped topics map to `rollout`, and
this is the same shape one substrate back)
**Bridge:** Normalized judge scores need durable storage with replay — ClickHouse, not in-memory
averages.

## Format diversity check

Last 10 Experience posts (Days 69–78): 69 design, 70 design, 71 deep-dive, 72 deep-dive, 73
incident, 74 design, 75 rollout, 76 feature, 77 deep-dive, 78 rollout (days 69–76's formats are
recorded verbatim in `day-76-EXPERIENCE.md`'s own diversity check plus that day's own `feature`
choice; 77 — "Agoda P99 Cannot Be Averaged", quantile-merge mechanism — is `deep-dive`; 78 —
"Decoupling SQS from OSRM" — is `rollout` per the signal table). Incident is 1 of 10, design 3 of
10, deep-dive 3 of 10 — nothing at the 4-of-10 trigger. `rollout` for Day 79 brings rollout to 3 of
10 (75, 78, 79), still under threshold, and fits the topic better than forcing a different format
onto a genuine substrate migration.

## Employer context used

`docs/context/resume-extracted.md` — Walmart Labs bullet: "7M+ sensors, tens of millions of
telemetry points/min: Architected WeIoT SmartBuildings ingestion layer on Azure IoT Hub; engineered
real-time HVAC control loops via Azure Stream Analytics automating energy optimisation across 50+
global facilities." This is the only primary-source detail for Azure Stream Analytics on this
role — the post does not invent a specific outage timeline or an exact dropped-message count beyond
what "bounded-window limits" describes generically; it stays anchored to the documented architecture
(Azure IoT Hub ingestion, Stream Analytics windowed processing, 7M+ sensors, 50+ facilities) and
frames the failure mode structurally (windowed stream processing has a bounded state window; an
ingestion burst or a late-arriving event outside that window is dropped, not queued) rather than
inventing specifics the resume doesn't support.

Continuity: this arc has three prior Walmart WeIoT posts already live — Day 40 (fan-out
amplification, N+1 tool calls), Day 46 (OTA rollback wave discipline), Day 54 (HVAC flame graphs),
Day 66 (midnight rollover / UTC boundary bug in daily telemetry rollups), Day 73 (OTA version hash
collisions). Day 79 does not re-derive the 7M-sensor scale number or re-explain Azure IoT Hub's
ingestion role — those are already established; it adds the one system this arc hasn't covered yet:
what happened when Stream Analytics' bounded processing window met a traffic pattern it couldn't
buffer, and why the team-owned fix was Kafka's replayable, offset-based log rather than a bigger
window.

## Structure (rollout format: before topology → the gap it exposed → after topology → rollback
story → metrics → bridge to today)

1. Before: Azure Stream Analytics windowed queries processing HVAC telemetry from 7M+ sensors
   across 50+ facilities — a tumbling/hopping window holds state for a bounded duration, then emits
   and discards it.
2. The gap: a burst of sensors reporting simultaneously (a facility coming back online after a
   network blip, all its sensors re-registering and back-filling telemetry at once) could push
   events past the window's retention before the query had processed them — dropped, not queued,
   because Stream Analytics' windowing model has no concept of "replay this from where you left
   off" the way a log-based system does.
3. After: migrating the ingestion path to Kafka — an append-only, offset-addressed log instead of a
   bounded processing window. A consumer that falls behind doesn't lose events, it just has a
   growing lag it can catch up from any point using its own committed offset.
4. Rollback / cutover discipline: dual-write during migration (both paths live, Stream Analytics
   authoritative), verify parity on a subset of facilities, then flip authority to the Kafka
   consumer path once offset-based recovery had been proven under a deliberately injected consumer
   restart — the same "prove the recovery path before trusting it" discipline Day 76's circuit
   breaker half-open drill already established for the same team.
5. Metrics: not a made-up incident count — the concrete, defensible claim is what changed
   structurally (bounded window with no replay → durable log with offset-based replay) and why that
   made a previously silent drop become a bounded, recoverable consumer lag instead.
6. Bridge to today's code: `model-quality-scorer`'s rollup work needs the identical property —
   `quality_scores` is a durable, queryable ClickHouse table a rollup query can re-run against at
   any time, not an in-memory running average that forgets the underlying samples the moment it's
   computed. DESIGN.md §6 already commits to this ("never pre-collapsed into a running average at
   write time") for the same reason WeIoT's Kafka migration mattered: a number you can only ever
   compute once, going forward, is much less trustworthy than one you can always recompute from the
   raw, retained facts.
7. So-what: a bounded window is a completely reasonable choice until the moment your traffic
   pattern doesn't fit inside it — and the fix is never "make the window bigger," it's "stop
   forgetting the data the moment the window closes." A replayable log and a durable per-sample
   table solve the identical problem at two very different points in the same career.

Gold reference read: `blog/series/experience/day-78-decoupling-sqs-from-osrm.html` and
`blog/series/experience/day-77-p99-per-tenant-slos.html` (two most recent Experience posts) for
register/voice/section-length match; `seven-million-iot-sensors-failure-modes.html` (existing
WeIoT gold-reference post) for established scale numbers and voice on this exact system.
