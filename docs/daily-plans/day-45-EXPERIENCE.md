# Day 45 — Experience Blog Plan

**Title**: S3 for Traces — Compliance and Cost
**Subtitle**: Agoda · retention · cold storage
**Employer context**: `docs/context/agoda-whitefalcon-tsdb-architecture.md` (Agoda/WhiteFalcon)
**Bridge**: JSONL on MinIO is Ceph for traces — cheap bytes, replayable history. Today's code
in agent-replay-engine implements that lesson.

## Angle

Format diversity check first against the last 10 posts (see step in build routine) — pick a
format other than "incident" if incident count ≥ 4/10.

Anchor on WhiteFalcon's cold tier: Ceph sitting between pods and S3, Parquet partitioned by
datetime, compaction rolling hourly → 3-hour → daily files, and the retention/compliance
reasoning behind why hot data (last 3–7 days) lives in Redis while everything older moves to
S3/Parquet and eventually Hadoop for audit. Bridge that lesson into today's agent-replay-engine
work: trace event logs are small, numerous, append-only records — structurally identical to
the WhiteFalcon cold-tier problem at a different scale. The zstd + checksum + 30/90-day
tiering design in `pkg/export` is the same shape of decision: what lives where, for how long,
and how do you prove it wasn't corrupted in flight.

**Attribution boundary**: Akshant contributed to WhiteFalcon's cross-tier query engine and a
new cardinality dimension — he did NOT design the Ceph/S3 tiering or RoaringBitmap engine
(Agoda team's work). Keep this distinction explicit in the post.

**Do not invent**: scale numbers outside 1.5T–1.8T events/day, Agoda team member names, or a
"WhiteFalcon v2" roadmap. Use only what's in the context doc.

## Structure (match last 2 Experience posts' register/length)

1. Hook — a compliance/cost question about "where do old traces live and who can prove they
   weren't tampered with"
2. The WhiteFalcon cold-tier lesson (Ceph → S3 → Hadoop, compaction cadence, why tiering
   exists — cost AND compliance, not just cost)
3. The bridge to trace storage: same tiering shape, smaller blast radius, same discipline
4. What today's code enforces: checksums (tamper evidence), retention tiers (cost + audit
   window), zstd (cost)
5. One concrete analogy grounded in a physical object (e.g., a storage unit with a paper trail)
6. So-what closer tied back to LensAI/TraceForge's audit story

Kicker: `Experience · Day 45 of 150`. Max 3 sentences/paragraph. Full self-review checklist
from CLAUDE.md section 5 before publish.
