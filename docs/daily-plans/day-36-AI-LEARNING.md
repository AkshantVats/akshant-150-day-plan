# Day 36 — AI Learning Blog Outline
## "Day 36 — Tail Sampling for Agent Traces"

**Calendar**: Wednesday, 15 July 2026 · Day 36 of 150
**Series**: AI Learning
**Topic**: Head sampling vs tail sampling for agent traces — why always keeping errors and high-cost spans is the correct policy, and what the tradeoff costs you
**Hook**: "Head sample the happy path; tail sample the expensive path."
**Bridge to code**: Today's `traceforge/sampling/sampler.go` implements `TraceSampler` with head 10% + error tail 100% + cost tail. The load test (`cmd/load_test/main.go`) validates the policy at 5k spans/sec.
**Format**: deep-dive / how-it-works

---

## Post Title

**Day 36 — Tail Sampling for Agent Traces**

Accent tag chip: `AI Learning · Day 36 of 150`

Subtitle: *Head sample the happy path. Tail sample the expensive path. If you mix them up, your cost dashboards lie and your error dashboards lie differently.*

---

## Thread

> Sampling Without Lying meets Tail Sampling for Agent Traces in today's agent-trace-collector commit.

---

## Narrative Arc

The blog opens with the tension: agent observability at scale requires sampling, but naive sampling destroys the data you most need. A 10-step ReAct agent run costs $0.003 in LLM tokens. At 5k runs per second, that's $54k/hour in tracing cost if you store everything. But if you drop 90% of spans randomly, you also drop 90% of the errors, the expensive outliers, and the exact runs your oncall engineer needs during an incident.

**Structural flow:**
1. **The math problem** — storage cost vs observability correctness at 5k spans/sec
2. **Head sampling: fast, blind, wrong for errors** — what you lose when you sample at ingestion time
3. **Tail sampling: accurate, expensive, why** — what you need to know before you can decide
4. **The DS analogy** — commit logs and write-ahead logs: you can't prune until you know the transaction committed
5. **The hybrid policy** — head 10% + error tail 100% + cost tail ($0.01 threshold)
6. **What TraceForge ships today** — `TraceSampler`, `ScrubSpan`, load test at 5k/sec
7. **Closing: the right question to ask before sampling**

---

## Section-by-Section Outline

### 1. Opening hook (no heading)

> At 5,000 agent spans per second, storing every span unsampled costs roughly 150GB per hour in ClickHouse. At 10% head sampling, you cut that to 15GB per hour. The problem appears solved — until your oncall engineer asks why the Grafana waterfall shows no spans for the trace that triggered the PagerDuty alert at 2am. The trace had an EMPTY_RESPONSE span. You sampled it away.

Three sentences. Open with the concrete tension: cost vs correctness.

### 2. Head sampling: fast, blind, wrong for errors

**Heading**: "The coin flip at the door"

Head sampling is a decision made at ingestion time, before you know anything about the span's outcome. A span arrives at the TraceForge HTTP endpoint. You flip a coin — or more precisely, you check whether a pseudorandom float64 is below your keep rate. If yes, write it to ClickHouse. If no, discard it. Done.

The speed is the appeal. The decision is O(1) — no buffering, no state, no waiting for downstream spans to complete. You can process millions of spans per second with a single comparison. The cost in CPU is negligible; the reduction in ClickHouse write throughput is immediate and proportional to the drop rate.

The problem is that the coin doesn't know what it's flipping for. An error span, a high-cost span, and a routine OK span all look the same to the head sampler — they're just bytes arriving at a socket. The sampler drops them at the configured rate regardless of their content. If errors represent 0.1% of your spans, a 10% head sampler keeps about 0.01% of those errors. That might still be enough to detect a sustained outage. It will not be enough to find a transient error that fired once during a test run and was never reproduced.

One "so what": head sampling is correct for optimizing storage. It is wrong as the sole policy when you care about error coverage.

### 3. Tail sampling: accurate, expensive, why

**Heading**: "Wait until you know"

Tail sampling inverts the decision timing. Instead of deciding at ingestion, you buffer the span until you have enough information to classify it. For a single span, "enough information" is the span's own completion: its status, cost_usd, and error attributes are set when the span ends. For a complete trace, it's the arrival of all child spans so you can evaluate the trace as a whole.

Single-span tail sampling is practical: the decision is delayed by the span's own duration (milliseconds to seconds for LLM calls). You can buffer spans in memory for up to a few seconds and still make real-time decisions. Full-trace tail sampling requires buffering until the last span of a trace arrives — which can be tens of seconds for a long-running ReAct agent, and requires a separate buffer store (Redis, a ring buffer) sized to hold the entire in-flight population.

TraceForge today implements single-span tail sampling, not full-trace tail sampling. Each span is evaluated independently when it arrives. This misses cross-span patterns — for example, a trace where every individual span has status OK but the cumulative cost exceeds $0.10. Full-trace tail sampling is a Day 40+ feature. Today's implementation is the right first step: classify single spans by error status and individual cost, and tail-sample those.

One "so what": tail sampling is not free. You pay for correctness with buffer memory and decision latency. Design the buffer size before committing to full-trace tail sampling.

### 4. The DS analogy

**Heading**: "The write-ahead log problem"

A database write-ahead log (WAL) records every write before the write is applied to the data store. The WAL exists because you can't know if a transaction committed until it commits. Before commit, the data is provisional — the transaction might roll back, fail, or conflict. You can't prune the WAL entry until the transaction is finished.

Tail sampling has the same structure. The span is the WAL entry. You record it provisionally when it arrives. You make the keep/drop decision when the "transaction" (the span's execution) completes and the outcome attributes are set. You can't prune the span before you know its status — you'd be running head sampling in disguise.

The buffer in tail sampling plays the role of the WAL segment before a checkpoint. The checkpoint is the sampling decision. After the decision, the buffer entry is either promoted (written to ClickHouse) or discarded (equivalent to a rolled-back transaction being pruned from the WAL). The WAL is bounded because checkpoints happen frequently; the tail sampling buffer is bounded because spans complete on a known latency distribution.

Analogy in plain terms: trying to do tail sampling without a buffer is like trying to prune a WAL entry before the transaction commits. You'll sometimes prune a transaction that was about to commit, and sometimes keep one that was about to roll back. The buffer is the mechanism that makes the decision correct.

One "so what": if you don't have a buffer, you're doing head sampling and calling it tail sampling. The two are fundamentally different in what they require from your infrastructure.

### 5. The hybrid policy

**Heading**: "Head 10%, error tail 100%, cost tail $0.01"

The correct production policy is a hybrid that applies different strategies to different span populations. Think of your span stream as three overlapping sets: routine spans (status OK, cost < $0.01), error spans (status ERROR, EMPTY_RESPONSE, MAX_ITERATIONS, or error=true), and high-cost spans (cost_usd > $0.01). These sets can overlap — a high-cost span can also be an error — but in practice the overlap is small.

Head-sample the routine set aggressively. At 10% head rate, you reduce storage by 90% for the majority population. The information you lose is statistically recoverable — you can estimate P50 latency and typical cost from a 10% sample with acceptable error. You cannot estimate rare events (errors, cost outliers) from a 10% sample, which is why the error and cost sets are handled separately.

Tail-sample the error and cost sets at 100% — keep everything. These sets are small (errors are by definition rare; spans costing more than $0.01 are above your LLM's average) but they carry disproportionate signal. An error span that gets dropped is a silent failure you just made permanent. A high-cost span that gets dropped is a cost attribution gap you'll spend an hour debugging.

#### Mermaid diagram: Hybrid sampling pipeline

```
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e3a5f',
    'primaryTextColor': '#f0f4f8',
    'primaryBorderColor': '#4a90d9',
    'lineColor': '#4a90d9',
    'secondaryColor': '#0d2137',
    'tertiaryColor': '#0a1a2e',
    'background': 'transparent',
    'nodeBorder': '#4a90d9',
    'clusterBkg': '#0d2137',
    'titleColor': '#f0f4f8',
    'edgeLabelBackground': '#0d2137'
  }
}}%%
flowchart TD
    A["Span arrives\nat ingest"] --> B{"Is status\nERROR / empty?"}
    B -- "Yes" --> C["Keep: error_tail\n100% retained"]
    B -- "No" --> D{"cost_usd\n> $0.01?"}
    D -- "Yes" --> E["Keep: cost_tail\n100% retained"]
    D -- "No" --> F{"Head coin flip\n10% keep rate"}
    F -- "Keep" --> G["Write to\nClickHouse"]
    F -- "Drop" --> H["Discard\n(counter++)"]
    C --> G
    E --> G
```

One "so what": the hybrid policy makes explicit what you're willing to lose (10% of routine OK spans) and what you refuse to lose (any error, any high-cost span). That explicitness is a contract with your oncall team.

### 6. What TraceForge ships today

**Heading**: "TraceSampler + ScrubSpan + load test"

Today's `traceforge/sampling/sampler.go` implements `TraceSampler` with three decision paths matching the hybrid policy above. The `Sample()` method checks error status first (short-circuit to `error_tail`), then cost_usd against the configured threshold (short-circuit to `cost_tail`), then applies the head coin flip using `crypto/rand` for the float64. Using `crypto/rand` instead of `math/rand` eliminates seed management and avoids correlated samples in concurrent goroutines — the security-grade entropy source is fast enough for span-level decisions (~100ns per call).

`pii_scrub.go` runs before the sampling decision in the pipeline. Three regex patterns cover the common PII types in agent tool call attributes: email addresses, 10-digit phone numbers, and 16-digit payment card numbers. The scrub is applied to all attribute values before `Sample()` is called — you need the full attributes to make the cost and error decisions, but PII should not persist to ClickHouse regardless of the sampling outcome.

The load test driver (`cmd/load_test/main.go`) runs 5k spans/sec for 60 seconds against the HTTP ingest endpoint. The terminal output records throughput, P99 latency, and error rate. BENCHMARKS.md captures these numbers as a permanent record — the first time TraceForge's ingest performance is characterized against a real-throughput target.

### 7. Closing: the right question

**Heading**: "What are you willing to lose?"

The right question before designing a sampling policy is not "how much do we want to save?" It is "what are we willing to lose?" If the answer is "nothing — every span is equally important" then you don't need a sampling policy, you need cheaper storage. If the answer is "routine happy-path spans at low cost" then head sampling is the correct choice. If the answer is "never lose an error or a cost outlier" then you need the hybrid.

Most teams default to head sampling because it's simple to implement and the storage benefits are immediate. The correctness gap is invisible until an incident, when an oncall engineer discovers that the exact error span they need was sampled away at a rate that seemed reasonable six months ago. By then, the sampling policy is load-bearing infrastructure and changing it requires a migration.

Design for what you can't afford to lose, and head-sample the rest. Head sample the happy path; tail sample the expensive path.

---

## Mermaid Diagram Checklist

- [x] Init block is verbatim from CLAUDE.md Section 4.5
- [x] Node labels ≤ 6 words each
- [x] 8 nodes total (A through H)
- [x] No `</motion.div>` tags

---

## Self-Review Checklist (before push)

- [ ] `Day 36` in `<title>`, `<h1>`, accent tag chip, meta line
- [ ] Mermaid init block verbatim from CLAUDE.md Section 4.5
- [ ] Every paragraph ≤ 3 sentences
- [ ] DS analogy (WAL / checkpoint) present in Section 4
- [ ] No bullet lists substituting for prose in Sections 1–4
- [ ] Series nav CSS block present (`.series-nav`, `.series-posts`, `.series-post`)
- [ ] `crypto/rand` usage in Section 6 matches `sampler.go` implementation
- [ ] Closing line "Head sample the happy path; tail sample the expensive path." present verbatim
- [ ] No placeholder URLs
- [ ] All code references verified against Day 36 `sampler.go` (TraceSampler, Sample(), error_tail, cost_tail)

---

## Format Notes

- Open with the storage math (5k spans/sec, 150GB/hour), not with a definition of sampling
- The WAL analogy is the post's conceptual anchor — it explains *why* tail sampling needs a buffer
- Section 5's mermaid diagram is the post's only visual; make it earn its place by showing the full decision tree
- Do not explain ClickHouse schema or MergeTree — assume the reader saw Day 34
- "TraceSampler" is the concrete class name; use it, not "our sampler" or "the sampling module"
- The closing line must appear verbatim: "Head sample the happy path; tail sample the expensive path."
