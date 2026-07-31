# Day 49 — Experience Blog Plan

**Title**: Streaming Parser — Don't OOM the Debugger
**Subtitle**: Agoda · bounded memory · large queries
**Employer context**: `docs/context/agoda-whitefalcon-tsdb-architecture.md` + `docs/context/
resume-extracted.md` for scale numbers. Relevant lines only:
- Agoda WhiteFalcon: 1.5T–1.8T events/day, Akshant Senior Engineer ~5 months, contributed the
  cross-tier query engine extension (Redis hot tier + S3/Parquet cold tier, histogram-bucket
  quantile merge) and a new Kubernetes-tag cardinality dimension. Did NOT design WhiteFalcon,
  the RoaringBitmap engine, or the Kafka pipeline — Agoda team built those.
- Query path: Grafana → Scala query engine → Redis (hot, last 3–7 days) or Parquet/S3 (cold).

**Format**: `design` (tradeoff essay) — per `docs/BLOG-FORMAT-MIX.md`: this is genuinely an
options-table-and-honest-consequences post, not a mechanism deep-dive (Day 47 already used
`deep-dive`) or an incident. The real content is "we benchmarked streaming vs batch and the
result wasn't the clean win we expected" — that's a decision-and-tradeoff narrative, not a
single-mechanism teach.

**Bridge**: Streaming JSONL is paginated TSDB queries — never load the whole day into RAM.
Today's code in agent-replay-engine implements that lesson.

## Angle

Anchor on the WhiteFalcon query engine's bounded-memory discipline: a Grafana query spanning
the hot tier never pulls a raw day of Redis buckets into the query engine's heap — it fetches
histogram bucket counts (already aggregated) and merges bounded structures, not raw rows. The
cross-tier quantile merge Akshant built (`attr-box mine`) works specifically because the query
engine never materializes more than one tier's histogram at a time. Bridge into
`agent-replay-engine`: `traceforge replay` had the same latent problem — `ReadJSONL` pulled the
*entire* shared log file into memory before filtering to one trace, the same mistake a naive
"just SELECT * and filter in the app" query would make against WhiteFalcon.

**The honest turn**: benchmark `RunFromReader` (streaming) against `Run`+`ReadJSONL` (batch) on
a realistic shared-log shape (51 traces, ~3.7MB) and report the *actual* numbers — streaming
used ~20% less peak memory but was ~40% slower and allocated 2x more, because two single-pass
scans (mocker build, then replay) each decoding every line cost more than one `ReadJSONL` pass
with slice growth. This is not the clean "streaming wins" story a first-draft would reach for —
write the surprise, not the story you expected to tell. The real, unqualified win is
`--stop-at-step` on a large file: streaming stops reading `r` the instant the step limit hits
(measured: 65,536 bytes read out of a 1.78MB file to stop at step 1 — 3.7%), where the old batch
path always read and sorted the whole file first regardless of where `--stop-at-step` cut it off.

**Attribution boundary**: Akshant's WhiteFalcon contribution is the cross-tier query engine
extension and the Kubernetes cardinality dimension — reference the RoaringBitmap engine and
Kafka pipeline only as "the Agoda team built" context for why the query engine had to stay
bounded-memory, never as something he designed.

**Do not invent**: no fabricated production incident where WhiteFalcon actually OOMed — the
honest framing is "the query engine's design already assumes bounded memory; here's a place my
own code hadn't caught up to that discipline yet." Scale numbers stay within 1.5T–1.8T/day.

## Structure (matched to last 2 Experience posts' register/length)

1. Hook — a `traceforge replay --stop-at-step 1` call that read a whole multi-MB shared log file
   just to answer a question about the first step
2. WhiteFalcon's cross-tier query engine: how it stays bounded-memory (histogram buckets, not
   raw rows) — `attr-box mine` for the query engine extension, Agoda-team credit for
   RoaringBitmap/Kafka
3. Options table: batch `ReadJSONL` vs streaming `Scanner` — memory, allocations, wall time,
   what changes about `--stop-at-step`
4. The benchmark's honest result — streaming is not strictly better, own the ~40% slower /
   2x-allocs number before the ~20% memory win
5. Where streaming is an unqualified win — `--stop-at-step` reading 3.7% of the file instead of
   100%
6. Physical analogy — a card catalog you flip one card at a time vs one you photocopy in full
   before finding the card you needed
7. Closer tied to LensAI/TraceForge's "replay must work on laptop RAM" story

Kicker: `Experience · Day 49 of 150`. Max 3 sentences/paragraph.
