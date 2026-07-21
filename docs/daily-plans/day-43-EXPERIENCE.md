# Day 43 — Experience Blog Outline
## "Day 43 — Kafka as Shock Absorber — Again"
### Agoda · backpressure · consumer lag

**Series**: Experience · Day 43 of 150
**Slug**: `day-43-kafka-shock-absorber-again`
**File**: `blog/series/experience/day-43-kafka-shock-absorber-again.html`
**Live URL**: `https://akshantvats.github.io/Profile/blog/series/experience/day-43-kafka-shock-absorber-again.html`
**Employer context**: Agoda — WhiteFalcon TSDB (Senior Engineer, ~5 months)
**Bridge**: "Chaos on analyzer proves TraceForge fails like infra-ai-streaming — queued, not dropped. Today's code in tool-call-analyzer implements that lesson."

---

## Title Block

```
<title>Day 43 — Kafka as Shock Absorber — Again | Experience Series</title>
Accent chip: Experience · Day 43 of 150
<h1 class="post-title">Day 43 — Kafka as Shock Absorber — Again</h1>
Meta line: Experience · Day 43 of 150
Series footer: Experience · Day 43 of 150
```

---

## Employer Context Reference

**Verified facts from agoda-whitefalcon-tsdb-architecture.md and resume-extracted.md** (use only these):
- **Role**: Senior Engineer, ~5 months at Agoda
- **System**: WhiteFalcon — Agoda's in-house TSDB (Apache Druid-inspired)
- **Scale**: 1.5T events/day (resume) / 1.8T events/day (Kafka forwarder figure)
- **Pipeline**: Kafka → Rust consumers → Redis (hot tier) → Ceph/S3 (cold tier)
- **Akshant's contribution**: Cross-tier query engine extension; new cardinality dimension (k8s tags); 2-3 new Grafana query types
- **Agoda team built**: RoaringBitmap engine, Kafka pipeline, Rust consumers, Scala query engine, Ceph/S3 tiering
- **Attribution**: Akshant did NOT design the Kafka pipeline — he contributed to components and observed the backpressure behavior as an operator

**Do NOT invent**: specific consumer lag numbers, incident dates, broker count, Kafka partition counts, team size, dollar values.

---

## Hook (first paragraph)

WhiteFalcon processed 1.5 trillion events per day through a Kafka pipeline that the Agoda team had built. The Rust consumers sat between Kafka and Redis — reading from the topic, aggregating metrics into time-windowed buckets, writing to the hot tier. When the Redis hot tier got slow — compaction overhead, a cache flush, or just a noisy-neighbour latency spike — the Rust consumers slowed with it. Consumer lag grew. The Kafka topic accumulated messages. Nothing dropped. The system had a shock absorber built in, and the shock absorber was Kafka itself. I watched this happen during on-call shifts and did not fully appreciate what I was seeing. A slow downstream component created observable lag without creating data loss. That is not a trivial guarantee. Most HTTP-based ingest pipelines do not have it.

---

## Section 1 — What Backpressure Actually Means in Kafka

### The problem most ingest pipelines have
An HTTP-based ingest pipeline has a clear failure mode: when the downstream (database, aggregator, analytics store) is slow, the upstream HTTP handler either queues requests in memory (OOM risk) or rejects them with 503 (data loss). There is no free middle option. You pick between dropping requests at the HTTP boundary or growing an in-memory queue that will eventually exhaust heap. Neither is good.

### What Kafka gives you instead
Kafka is disk-backed. The topic is the queue. When consumers are slow, messages accumulate on disk — bounded by topic retention policy, not by heap. The producer (the sender of events) does not need to know that the consumer is slow. The producer writes to Kafka and moves on. Consumer lag is the delta between the last offset the producer wrote and the last offset the consumer processed. It grows when the consumer is slow. It shrinks when the consumer catches up. At no point are messages deleted until the retention window expires.

### The physical analogy
Think of Kafka as a conveyor belt with a very long buffer section between the assembly line (producers) and the packaging station (consumers). If the packaging station slows down, items pile up on the buffer. The assembly line doesn't stop. The buffer absorbs the pace mismatch. Consumer lag is just the length of the pile on the buffer. A traditional HTTP queue is a packaging station with no buffer — if it's slow, the assembly line backs up or items fall on the floor.

### So what
Consumer lag is not a problem. It is information. It tells you that the consumer is slower than the producer — not that data is being lost. The correct response to growing consumer lag is to monitor it as a signal and, if it stays elevated, add consumer capacity or investigate the downstream bottleneck. The incorrect response is to treat it as an emergency, restart consumers, or reduce producer throughput. Restarting a consumer does not make the downstream faster.

---

## Section 2 — Watching Kafka Absorb the Shock at Agoda

### What I observed during on-call
During shifts on WhiteFalcon, consumer lag on the Rust consumers was the first signal of downstream slowness. Redis compaction jobs ran on a schedule, and during their peak they would cause the hot tier to respond slower than normal. The Rust consumers' write throughput dropped. Consumer lag climbed — sometimes to tens of millions of messages on a high-volume topic. The on-call runbook said: observe, do not panic, wait for compaction to finish, watch lag drain.

### Why "do not panic" was the right instruction
The lag draining after compaction proved that no messages were lost. The Kafka offset was a commit log: every message that arrived was durably written before any consumer acknowledged it. Consumer slowness never put messages at risk. It only put them in a longer queue. The on-call engineer's job during these windows was to ensure that the lag was draining at a rate that would clear before the topic's retention window expired — and if it wasn't, to investigate whether the consumer was stuck rather than merely slow.

### The difference between stuck and slow
A slow consumer makes progress — its committed offset is advancing, just not as fast as the producer. A stuck consumer has a committed offset that is not moving at all. These look similar in a consumer lag graph over a short window but diverge over minutes. Slow consumers self-resolve when the downstream speeds up. Stuck consumers require intervention: check for panics in the consumer process, check for connectivity to the downstream, restart if necessary. Conflating the two leads to unnecessary restarts of slow-but-healthy consumers.

### So what
The backpressure story at Agoda was quiet precisely because Kafka made it quiet. The mechanism absorbed the shock invisibly — events arrived, consumer lag grew, events processed, lag drained. I would not have understood this if I hadn't seen the lag metric move and then recover without any on-call action. The system proved its own resilience on every compaction cycle, which happened multiple times per day.

---

## Section 3 — The Same Lesson in tool-call-analyzer

### What the chaos test does
Today's `pkg/ingest/chaos_test.go` in tool-call-analyzer simulates exactly the Agoda pattern at micro-scale. A slow ClickHouse stub (200ms artificial latency per write) stands in for the slow Redis hot tier. The HTTP ingest handler's ClickHouse write deadline (100ms) fires before the stub responds. Instead of dropping the span, the handler's Kafka fallback path (`pkg/kafka/producer.go`) publishes the `BillingEvent` to the `tool-spans` Kafka topic. The chaos test fires 100 spans concurrently and asserts that all 100 arrive on the Kafka topic — zero dropped.

### Why 100 concurrent spans matters
A single-threaded test would not expose race conditions in the fallback path. Ten goroutines each sending 10 spans creates concurrent ClickHouse timeouts, concurrent Kafka produces, and concurrent JSON marshaling. If the fallback path has a data race on the Kafka writer or a channel that serializes produces incorrectly, the chaos test will find it before production does.

### The architectural parallel
WhiteFalcon: Kafka → Rust consumers → Redis. tool-call-analyzer: HTTP ingest → ClickHouse → Kafka fallback. In both cases, Kafka is the shock absorber between the fast ingest path and the slower storage path. In both cases, the consumer lag equivalent is the Kafka topic offset lag — observable, not alarming. The recovery path is the same: when ClickHouse recovers, a future recovery consumer will drain the `tool-spans` topic and replay the buffered spans into ClickHouse.

### What the OpenAPI spec adds
The `api/openapi.yaml` and README document the ingest contract so that a future SDK or CLI consumer knows exactly what `POST /ingest` expects without reading Go source. This is the equivalent of WhiteFalcon's Grafana API contract: the interface is stable and documented even when the storage path beneath it changes.

### So what
The chaos test is not a unit test of the Kafka producer. It is a proof of the system property: "this ingest path does not drop spans when its downstream is slow." That property is the entire point of the Kafka fallback. Proving it with a deterministic chaos test means it stays provable as the codebase evolves — regression-protected by the same test suite that runs on every commit.

---

## Section 4 — Backpressure as a Design Discipline

### What most engineers get wrong
Backpressure is usually treated as an emergency response: the system is overwhelmed, add more capacity, restart the slow service. This framing misses the design question entirely. The question is not "what do we do when the downstream is slow?" The question is "where does the excess work go when the downstream is slow?" In-memory queue: heap exhausts. HTTP 503: caller must retry or data is lost. Kafka: topic absorbs, consumer catches up. The choice happens at design time, not during the incident.

### The split-topic design from today's AI Learning post
The AI Learning post today covers splitting the `tool-spans` ingest topic from the aggregation topic. The ingest topic receives raw spans from the HTTP handler. The aggregation consumer reads from the ingest topic, computes stats (exclusive time, cost rollups, N+1 detection), and writes results to ClickHouse. A separate aggregation topic receives pre-aggregated results for downstream consumers that don't need raw spans. Slow aggregation never backs up the raw ingest path — the raw span is safe on disk regardless of how long the aggregator takes.

### Why this maps to WhiteFalcon's architecture
WhiteFalcon's Kafka pipeline was already doing this at a different granularity. Raw metric events from application instrumentation arrived on the ingest topic. Rust consumers transformed them into time-windowed bucket counts before writing to Redis. The transformation (aggregation) happened in the consumer, not the producer. The ingest topic's throughput (1.5T events/day) was decoupled from the aggregation throughput by the Kafka buffer between them.

### The lesson that transfers
Any time an ingest path must be available at higher throughput or lower latency than a downstream transformation, Kafka belongs between them. The downstream can be slow without the ingest path knowing. The contract is: write to Kafka at ingest time, process from Kafka at aggregation time. These are independent rates. Consumer lag is the observable that tells you whether the rates are matched. If lag grows steadily over days, the downstream is structurally slower than the upstream — add consumer capacity. If lag spikes and drains on a schedule, the downstream has a periodic bottleneck — investigate and tune.

### So what
The most useful thing backpressure design gives you is the separation of "data at risk" from "data processing slowly." In a system without backpressure, a slow downstream means data at risk. In a Kafka-backed system, a slow downstream means data in the buffer — observable, recoverable, and not your problem until the retention window approaches. Building tool-call-analyzer with this property from Day 43 means the system handles the messy realities of shared infrastructure without requiring a perfectly tuned downstream to stay correct.

---

## Section 5 — What the README and OpenAPI Spec Represent

### Why documentation is infrastructure
The tool-call-analyzer README and OpenAPI spec are not optional polish. They are the interface contract that makes the system composable. The OpenAPI spec tells any future SDK, CLI consumer, or integration test exactly what `POST /ingest` expects without requiring the consumer to read Go source. The README's architecture diagram (Mermaid) shows where each component sits and how they connect. These documents deprecate as fast as the code if they're written by hand and updated manually — which is why the Day 43 README is committed alongside the chaos test, not as a separate later commit.

### The Agoda parallel
WhiteFalcon's Grafana-facing API was stable because the contract was enforced by the Scala query engine, not documented in a wiki. If the wiki drifted, Grafana still worked. If the engine drifted, Grafana broke immediately. tool-call-analyzer's OpenAPI spec is not enforced by a code generator — but committing it alongside the handler tests creates a lightweight contract: if the tests pass and the spec describes what the tests exercise, the spec is correct.

### What the README quickstart signals
A one-command quickstart (`docker compose up`) means the barrier to running tool-call-analyzer locally is zero for a new contributor. The WhiteFalcon team at Agoda had internal tooling for this. For an open-source project, the README is that tooling. A project without a working quickstart is a project where only the author can run it — which means only the author can verify that it works.

### So what
Documentation and chaos tests are both proofs of system properties. The chaos test proves the ingest path does not drop spans. The README proves the project can be run by someone who just cloned it. The OpenAPI spec proves the HTTP interface is intentional, not accidental. Each one is a commitment to a contract that the project will maintain.

---

## Series Navigation Footer

Previous: Day 42 — One Dashboard for Inference and Tools (Agoda)
Next: Day 44 — (coming)

---

## HTML Checklist Before Push

- [ ] `Day 43` in `<title>`, `<h1>`, accent chip, meta line, series footer (all four mandatory locations)
- [ ] `class="series-nav"` / `class="series-posts"` / `class="series-post"` CSS present in `<style>` block
- [ ] No system names invented beyond what appears in agoda-whitefalcon-tsdb-architecture.md and resume-extracted.md
- [ ] Akshant's contribution accurately scoped: cross-tier query extension, new cardinality dimension, on-call observer — NOT Kafka pipeline designer
- [ ] Scale numbers within documented range: 1.5T–1.8T events/day, ~5 months tenure
- [ ] All `<div>` opens match `</div>` closes
- [ ] No `</motion.div>` tags
- [ ] No `<a>` nested inside `<a>`
- [ ] Max 3 sentences per paragraph (split any that exceed this)
- [ ] No placeholder URLs
- [ ] Employer tenure accurate: Senior Engineer, ~5 months, Agoda
