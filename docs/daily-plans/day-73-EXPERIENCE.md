# Day 73 — Experience Post Plan

**Title:** Hash Collisions Happen
**Subtitle:** Walmart · OTA version mixups
**Format:** `incident` (per `docs/BLOG-FORMAT-MIX.md` — "Hash Collisions Happen" reads as a
near-miss/what-broke-and-how-we-contained-it story, not a rollout narrative, even though the
subtitle mentions OTA; the format table's incident signals — "near-miss," "what broke and how we
fixed it" — match the actual shape of this story better than the OTA→rollout mapping does. Last
10 Experience posts (days 63–72) carry exactly 1 incident (Day 66); Day 73 as incident brings that
to 2 of 10, well under the 4-of-10 diversity trigger.)
**Bridge:** Collision drill is firmware version isolation testing. Today's prompt-fingerprinter
work makes that concrete.

## Employer context used

`docs/context/resume-extracted.md` — Walmart Labs, Bengaluru, Aug 2018 – May 2021, Software
Engineer II, WeIoT SmartBuildings Platform (3 years). Two bullets, both directly attributed to
this role (not a team-scope caveat like the Agoda WhiteFalcon posts need): "7M+ sensors, tens of
millions of telemetry points/min — architected WeIoT SmartBuildings ingestion layer on Azure IoT
Hub... across 50+ global facilities" and "Fault-tolerant edge-to-cloud OTA firmware framework —
reliable config syncs and updates for millions of distributed devices under intermittent network
conditions." No scale numbers or system names beyond these two bullets.

## Structure (incident format: timeline → blast radius → root cause → fix → guardrails)

1. Set the stage: the OTA framework pushes firmware config updates to device groups scoped by
   facility, not by individual device ID directly — a device is addressed by
   `{facility_id}:{device_group}`, and the framework computes which config version a group is
   currently on from a version fingerprint (a hash of the config payload) rather than tracking an
   incrementing version number per device, because devices sync intermittently and an
   incrementing counter drifts out of order across an unreliable edge network.
2. Timeline: two config payloads for *different* device groups — one an HVAC control loop tweak,
   one an unrelated sensor calibration update — happened to hash to a version fingerprint that
   collided in the low bits of the scheme actually deployed at the time (a shorter, non-
   cryptographic hash chosen for a cheap on-device comparison, not SHA-256's collision
   resistance). One group briefly reported "already on latest," skipping the sync it should have
   applied.
3. Blast radius: contained to one facility's device group, not all 50+ facilities, because the
   version-fingerprint check was already scoped per `{facility_id}:{device_group}` — the same
   shape as today's `tenant_id` in the Redis key, not a coincidence in hindsight, a design pattern
   that keeps showing up wherever a fast-path key check needs a collision blast radius bounded by
   construction.
4. Root cause: a hash short enough for a cheap on-device comparison traded away exactly the
   collision resistance a version check needs — the same tradeoff DESIGN.md §2 makes explicit
   today by choosing SHA-256 over a faster non-cryptographic hash for prompt-fingerprinter,
   almost certainly informed by having hit this exact failure mode once already.
5. Fix and guardrails: widen the fingerprint (more bits, real hash function) and, more
   importantly, add a periodic reconciliation sync that doesn't trust the fingerprint alone
   forever — a bounded-staleness backstop, not a promise the fingerprint check itself would never
   miss again. That backstop is the direct ancestor of today's `HardTTL`: don't just make the
   fast-path check better, bound how long you'll trust it before double-checking anyway.
6. So-what: today's collision drill (tenant-scoped keys + a 30-day TTL bound) is the same two-part
   answer — narrow the blast radius by construction, then bound it in time — applied to a cache
   key check instead of a firmware version check. The lesson traveled between two completely
   different systems seven years apart because the underlying failure mode (a fast, collision-
   prone check standing in for a slow, collision-resistant one) is the same shape both times.

Gold reference read: `blog/series/experience/day-66-*.html` (most recent incident-format post, for
timeline→blast-radius→root-cause→fix structure) and the two most recent Experience posts overall
(days 71–72) for register/voice match.

## Format diversity check

Last 10 Experience posts (days 63–72): 63 deep-dive, 64 deep-dive, 65 design, 66 incident, 67
feature, 68 design, 69 design, 70 design, 71 deep-dive, 72 deep-dive. Incident count is 1 of 10.
Day 73 as `incident` brings it to 2 of 10 — under the 4-of-10 trigger.
