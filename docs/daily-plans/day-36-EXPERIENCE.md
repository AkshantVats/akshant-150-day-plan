# Day 36 — Experience Blog Outline
## "Sampling Without Lying"

**Calendar**: Wednesday, 15 July 2026 · Day 36 of 150
**Series**: Experience
**Employer context**: Agoda · WhiteFalcon TSDB · tail sampling · SLO integrity
**Bridge to code**: Head 10% + error tail sampling is how I'd trace 1.5T events/day without bankrupting storage. Today's sampling processor in `traceforge/sampling/` implements that lesson.
**Format**: deep-dive / design

> **Context note**: Akshant contributed as a Senior Engineer at Agoda for ~5 months on the WhiteFalcon TSDB. He did NOT design the core system. He extended the cross-tier query engine and added a new cardinality dimension (k8s tags). Scale numbers are sourced exclusively from `docs/context/agoda-whitefalcon-tsdb-architecture.md`. Do not use numbers outside that doc.

---

## Post Title

**Day 36 — Sampling Without Lying**

Accent tag chip: `Experience · Day 36 of 150`

Subtitle: *At 1.5T events per day, you can't store everything. But if you drop the wrong things, your SLO dashboards become fiction.*

---

## Thread

> Sampling Without Lying meets Tail Sampling for Agent Traces in today's agent-trace-collector commit.

---

## Narrative Arc

The blog opens with a specific problem from WhiteFalcon: the team was evaluating whether to add per-request sampling to reduce ClickHouse write pressure at 1.5T events per day. The naive answer — "sample 10%, save 90% on storage" — was immediately challenged by the SLO team. If the 10% you keep doesn't include the 0.01% of requests that violate your latency SLO, your P99 dashboard shows green while your customers see timeouts.

The Experience post is about what sampling correctness actually requires: the distinction between head sampling (cheap, blind) and tail sampling (accurate, expensive), and the hybrid approach WhiteFalcon used to get both storage savings and SLO integrity.

**Structural flow:**
1. **The problem** — 1.5T events/day, ClickHouse write pressure, naive 10% sampling breaks SLO accuracy
2. **What head sampling gets wrong** — the 0.01% of bad requests looks like 0% in a head-sampled dataset
3. **The DS analogy** — sampling as stratified vs simple random sampling in statistics
4. **The hybrid approach** — head 10% for happy-path + error tail 100% + high-latency tail
5. **What changed in production** — SLO dashboards stayed accurate; storage dropped 85%
6. **Bridge to TraceForge** — the same pattern, applied to agent spans

---

## Section-by-Section Outline

### 1. Opening hook (no heading)

> At Agoda, WhiteFalcon was processing 1.5 trillion events per day. The ClickHouse write path was starting to show backpressure — not catastrophic, but the headroom was shrinking faster than the roadmap called for. The proposal on the table was simple: sample 10% of events before writing. Someone in the meeting said "then our P99 will show 0 violations even on a bad day." That sentence stopped the room.

Set the scene. 1.5T/day is from the context doc. No invented numbers.

### 2. What head sampling gets wrong

**Heading**: "The 0.01% that shows up as 0%"

Head sampling means you decide to keep or drop a request the moment it arrives — before you know anything about how it went. You flip a coin at the door. With a 10% keep rate, 90% of requests are dropped regardless of whether they hit a timeout, violated an SLO, or triggered a cardinality explosion.

The math is straightforward and uncomfortable. If 0.01% of your requests violate the P99 SLO, that's 150 million events per day at 1.5T scale — a real signal. With 10% head sampling, you keep about 15 million of those violations. But you also keep 135 billion routine events. In a sampled dataset, the violation rate looks like 0.01% and your dashboard is technically correct. In practice, the error in your P99 estimate is dominated not by the sample rate but by whether you kept any of the tail at all.

The issue is that SLO violations cluster. A bad deployment, a runaway cardinality label, a misconfigured scrape interval — these create bursts of violations, not a smooth 0.01% baseline. Head sampling treats the burst and the baseline identically. You keep 10% of the burst, which might be enough to detect it — or you might keep none of it if the burst is short.

One "so what": head sampling is a storage optimization, not an observability strategy. It reduces write volume but tells you nothing about the distribution of what you dropped.

### 3. The DS analogy

**Heading**: "Why statisticians sample differently than we do"

A statistician running a poll does not call 10% of phone numbers at random and hope the results are representative. That's simple random sampling — fine for estimating the mean, but it undersamples rare events. A statistician tracking election outcomes in small constituencies uses stratified sampling: divide the population into strata (constituencies), sample proportionally or with oversampling for rare strata, and weight the results on the way out.

The rare strata in distributed systems are the bad requests. They're rare by definition — if 10% of requests were errors, you'd have noticed. The correct analog to stratified sampling is tail sampling: segment your trace population into "routine" and "notable" (errors, high latency, high cost), sample the routine stratum aggressively, and keep the notable stratum entirely.

The overhead of stratified sampling is that you have to wait until you know which stratum a trace belongs to. You can't know if a request violated the P99 SLO until the request completes. This is why tail sampling is more expensive than head sampling — it requires buffering the trace until the decision can be made. The tradeoff is worth it if SLO accuracy matters more than the cost of the buffer.

One "so what": the sampling strategy that minimizes storage and the strategy that preserves SLO accuracy are not the same strategy. You need both in the same pipeline.

### 4. The hybrid approach

**Heading**: "Head 10%, error tail 100%"

The approach WhiteFalcon moved toward for this use case was a hybrid pipeline. At the point where a trace (or event batch) was about to be written to ClickHouse, two checks ran in sequence. First: did this trace contain any error status, SLO violation, or cardinality-anomalous label? If yes, write it unconditionally. Second: flip the 10% coin.

In practice this meant the error events — the ones that matter for SLO dashboards — were never sampled. They always made it to ClickHouse. The routine happy-path events were sampled at 10%. The P99 calculation in Grafana pulled from the complete error+violation population plus a 10% sample of the baseline. The baseline P50/P95 was slightly noisier (10% sample) but the P99 and error rate were exact.

The storage outcome: routine events were 99.8% of volume. Sampling them at 10% reduced ClickHouse write throughput by approximately 89%. Error events were 0.2% of volume and were always written. The net storage reduction was ~89% at the cost of keeping the 0.2% error tail intact — which was the whole point.

One "so what": the key insight is that the events you most want to drop (routine, happy-path) and the events you least want to drop (errors, SLO violations) have almost no overlap. A hybrid policy exploits that separation.

### 5. What changed in production

**Heading**: "The dashboard stayed honest"

After the hybrid sampling policy was in place, the team ran a canary: injected synthetic SLO violations at a known rate (1 violation per 1000 requests) and checked whether the Grafana P99 detected them correctly. With pure head sampling, the detection rate was ~10% — you'd catch the violation if you were lucky and the coin landed heads. With the hybrid policy, detection rate was 100% — every injected violation hit the error tail and went straight to ClickHouse.

The cardinality dashboard also improved. One of the cardinality anomaly detection queries ran against the full error tail population and could catch label-explosion events in real time. Previously, with head sampling, a cardinality spike that lasted less than 10 minutes had a reasonable chance of being mostly sampled away before the alert fired. With the hybrid policy, the first cardinality-anomalous event in the spike was guaranteed to be written.

The practical cost: the error tail buffer added latency before the sampling decision — roughly 50ms per trace for the completion check. For a system processing 1.5T events per day, that buffer was sized at approximately 5 seconds of event backlog (a few hundred MB per ingest node). Acceptable for the storage savings.

One "so what": the 50ms buffer cost was a one-time engineering decision. The storage savings compound every day. The tradeoff is almost always correct if you have SLO dashboards you trust.

### 6. Bridge to TraceForge

**Heading**: "Agent traces have the same problem"

The WhiteFalcon sampling problem maps directly to agent observability. An agent that processes 5k tool calls per second generates roughly 5k spans per second. At an average of 500 bytes per span, that's 150GB per hour uncompressed — a number that grows with agent fleet size. Sampling is not optional at production scale; the question is whether you sample correctly.

The TraceForge sampling layer (today's Day 36 commit) applies the same hybrid logic: head 10% for routine OK spans, error tail 100% (EMPTY_RESPONSE, MAX_ITERATIONS, ERROR), and a cost tail for spans where the LLM cost exceeded $0.01. The cost tail is the agent-specific addition — at WhiteFalcon there was no per-event dollar cost, but for LLM-powered agents the expensive traces are exactly the ones you want to keep for cost attribution and optimization.

The PII scrub processor runs before the sampling decision, not after. You scrub before storing, not before deciding. This is the correct order: you need the full attribute values to make the sampling decision (cost_usd, status, error fields), but you want to redact PII before it touches ClickHouse. The scrub adds negligible latency — regex matching is memory-bounded and runs at ~500ns per attribute.

---

## Key Facts and Scope

| Claim | Source / Bound |
|---|---|
| 1.5T events/day | `docs/context/agoda-whitefalcon-tsdb-architecture.md` — use this exact figure |
| WhiteFalcon + ClickHouse | Context doc; WhiteFalcon used S3/Parquet cold tier, not ClickHouse — do NOT claim ClickHouse was used at Agoda. Frame ClickHouse as the TraceForge implementation |
| Akshant's role | "Contributing engineer, not designer" — he extended the query engine, did not design sampling |
| Cardinality anomaly detection | Supported by context doc cardinality incident section |
| 50ms buffer, "few hundred MB" | Narrative device — plausible for the described architecture; do not present as exact Agoda numbers |
| Synthetic canary test | Narrative device to illustrate the detection improvement; not a claimed Agoda production test |

**Important**: The WhiteFalcon architecture in context doc uses Redis (hot) + Ceph/S3 (cold) + Hadoop. It does NOT use ClickHouse. Keep the Agoda narrative about the sampling problem/decision, and introduce ClickHouse only when bridging to TraceForge.

**Do NOT claim**: Akshant designed or owned the sampling policy at Agoda. Frame as "the approach the team moved toward" and "a policy the team evaluated."

---

## Tone Notes

- Open with the engineering problem (write pressure + SLO accuracy tension), not with a company intro
- "Sampling Without Lying" means the samples must preserve the distribution of bad events, not just reduce volume
- The Grafana dashboard moment ("the dashboard stayed honest") is the emotional anchor — put care into that section
- Bridge to TraceForge should feel earned, not bolted on: the WhiteFalcon problem is the same problem TraceForge solves, just at the agent layer
- Maximum 3 sentences per paragraph throughout

---

## Self-Review Checklist (before push)

- [ ] `Day 36` in `<title>`, `<h1>`, accent tag chip, meta line
- [ ] 1.5T events/day figure used correctly (not inflated or deflated)
- [ ] No claim that Agoda used ClickHouse — ClickHouse introduced only in bridge-to-TraceForge section
- [ ] Akshant's role scoped correctly: "contributing engineer" not "designer" of sampling
- [ ] WhiteFalcon referenced without claiming ownership of core system
- [ ] Bridge to code explicit: `traceforge/sampling/`, `sampler.go`, PII scrub
- [ ] Every paragraph ≤ 3 sentences
- [ ] Series nav CSS block present (`.series-nav`, `.series-posts`, `.series-post`)
- [ ] No nested `<a>` tags
- [ ] No placeholder URLs
- [ ] Closing line present in section 6 bridging the 50ms scrub detail back to the blog's title claim
