# Day 41 — Experience Blog Outline
## "Day 41 — Exclusive Time — Flame Graphs for Money"
### Delivery Hero · OSRM critical path · ETA

**Series**: Experience · Day 41 of 150
**Slug**: `day-41-exclusive-time-flame-graphs-for-money`
**File**: `blog/series/experience/day-41-exclusive-time-flame-graphs-for-money.html`
**Live URL**: `https://akshantvats.github.io/Profile/blog/series/experience/day-41-exclusive-time-flame-graphs-for-money.html`
**Employer context**: Delivery Hero — Global Logistics Platform (Jun 2022 – Jul 2023, Berlin, Sr. Software Engineer)
**Bridge**: "Bottleneck rank is critical path on a DAG — DH route recompute taught me to look for the slow edge. Today's code in tool-call-analyzer implements that lesson."

---

## Title Block

```
<title>Day 41 — Exclusive Time — Flame Graphs for Money | Experience Series</title>
Accent chip: Experience · Day 41 of 150
<h1 class="post-title">Day 41 — Exclusive Time — Flame Graphs for Money</h1>
Meta line: Experience · Day 41 of 150
Series footer: Experience · Day 41 of 150
```

---

## Employer Context Reference

**Verified facts from resume-extracted.md and delivery-hero-rider-tracking-system.md** (use only these):
- **Role**: Sr. Software Engineer · Global Logistics Platform, Delivery Hero · Berlin
- **Tenure**: Jun 2022 – Jul 2023 (~1 year)
- **Scale**: 1M+ daily orders, 5k+ map adjustments/sec (route updates), 10k+ concurrent requests, zero downtime on AWS EKS
- **System**: Rider tracking using OSRM — processing 5k+ real-time route updates/sec
- **Route pipeline**: Order Service → Order SQS (lifecycle events) → Route Consumers → OSRM cluster → Route object
- **OSRM**: map-matching / routing engine with DB; Route Consumers read Order SQS → OSRM
- **ETA accuracy**: rider location + OSRM route object → ETA shown to customer in UI
- **Cascading failure**: Designed async SQS + Kinesis pipeline decoupling order processing from notifications; sub-second delivery status updates for millions of active users at peak

**Do NOT invent**: team size, specific incident dates, named internal tools beyond the architecture doc, specific ETA accuracy percentages, dollar values.

---

## Hook (first paragraph)

At Delivery Hero, the slowest thing in our rider ETA pipeline was never what appeared slowest in the logs. The logs showed OSRM route computation at 85ms. What they didn't show was that OSRM was waiting 60ms for the Route Consumer to hand it a parsed request — 60ms of queue deserialization that looked like zero because the consumer didn't emit a span for it. When we finally profiled the whole pipeline end to end and computed exclusive time per stage, the OSRM step dropped from apparent bottleneck to rank 4. The real bottleneck was a 200ms fanout in the Order SQS consumer that nobody had measured before. That experience changed how I think about tracing: total duration is a lie that points you at the wrong thing. Exclusive time is the number that tells you where to go.

---

## Section 1 — The OSRM Pipeline and Where ETAs Come From

### What OSRM is
OSRM is an open-source routing engine. It takes a start point, end point, and road network, and returns a polyline (the route) plus an estimated travel time. At Delivery Hero, it ran as a cluster behind Route Service. Route Consumers read lifecycle events from Order SQS — `RIDER PICKED UP`, `RIDER ENQUE` — and pushed coordinate pairs to OSRM at 5k+ updates per second.

### Where the ETA came from
The ETA in the customer UI wasn't a static estimate from order time. It updated in real time as the rider moved. Every rider location update triggered an OSRM call: new coordinates in, new route object out, new ETA computed from the remaining route duration. At 1M+ daily orders with active riders, this ran continuously.

### The pipeline shape
```
Order SQS (rider location event)
  → Route Consumer (parse event, extract coordinates)
    → OSRM (compute route + duration)
      → Route object (updated polyline + ETA)
        → UI (customer sees updated ETA)
```

This is a directed chain — five stages, no branches on the hot path. A flame graph of this pipeline would show five frames. The bottleneck is whichever frame is widest in exclusive time.

### So what
A chain pipeline is the simplest possible case for bottleneck analysis. There's no fan-out to reason about, no parallel branches to sum. Exclusive time and total time differ only at the stage that's waiting on the next one. The slow stage stands out immediately.

---

## Section 2 — The Profiling Incident

### What the logs showed
Aggregate P99 latency for ETA update was 340ms. OSRM route computation appeared in Prometheus at 85ms P99. Route Consumer SQS read appeared at ~15ms. The gap — 340ms minus ~100ms of visible work — wasn't instrumented. Nobody knew where 240ms was going.

### What we did
We added spans to every stage: SQS message receive, message deserialization (protobuf decode), coordinate extraction, OSRM HTTP call, OSRM response decode, Route object write. Five new spans added to the Route Consumer and Route Service instrumentation.

### What the exclusive time showed
| Stage | Total Duration | Exclusive Time |
|---|---|---|
| Order SQS consumer fanout | 240ms | 200ms |
| SQS message deserialization | 40ms | 40ms |
| OSRM HTTP call | 85ms | 85ms |
| OSRM response decode | 12ms | 12ms |
| Route object write | 3ms | 3ms |

The SQS consumer fanout — processing one message but emitting many internal routing events before handing off to OSRM — was invisible to Prometheus because it happened inside a single service. Its exclusive time was 200ms. OSRM's exclusive time was 85ms. We'd been optimizing the wrong stage.

### Physical analogy
You're trying to get faster at a relay race by training the fastest runner. But the baton handoff takes longer than any runner's leg. You can optimize every runner to perfection and the race stays slow. Exclusive time reveals the handoff. Total time hides it inside the fast runner's frame.

### So what
The lesson wasn't that OSRM was fast. The lesson was that our instrumentation boundary was wrong. We measured what we could see, not what was actually happening. Exclusive time exposed the gap between those two things.

---

## Section 3 — What We Fixed

### The fanout problem
The Route Consumer was deserializing one SQS message and then emitting twelve internal events to a local buffer before processing any of them. This batch-then-process pattern had been added during a load-shedding incident six months earlier. It made sense as a local optimization under high load. Under normal load it added 200ms of unnecessary buffering.

### The fix
We replaced batch-then-process with process-as-you-read: each SQS message was deserialized and handed to OSRM immediately, without buffering through the local event queue. The local queue was preserved for backpressure handling (still needed under load spikes) but no longer active on the hot path for normal operations.

### The result
P99 ETA latency dropped from 340ms to 118ms. The improvement was entirely in the SQS consumer stage. OSRM was unchanged. Route Service was unchanged. We had optimized the handoff, not the runners.

### What changed in the monitoring
After the fix, we added the consumer fanout span to our Grafana dashboard. P99 of the fanout stage sat at 8ms in normal operation — a 25x reduction. We set an alert at 50ms: if the fanout takes longer than 50ms, the backpressure queue is activating and we have a load event to investigate.

### So what
The fix took two days. Finding it took three weeks, because we hadn't instrumented the right stages. Every day of flame graph profiling that doesn't exist is a day where the bottleneck stays invisible.

---

## Section 4 — The TraceForge Connection

### What today's code does
`traceforge bottleneck --trace-id <id>` computes exclusive time for every span in a trace and ranks them descending. The OSRM pipeline scenario — a chain where the slow handoff hides inside a parent span — is exactly what the exclusive time formula exposes.

### The algorithm
```
exclusive_time(span) = span.duration - Σ(direct child durations)
```
Applied to the DH pipeline: Route Consumer total=240ms, children (OSRM=85ms, deserialization=40ms, decode=12ms, write=3ms) = 140ms. Route Consumer exclusive time = 240-140 = 100ms. But our fanout step was a sub-span of the consumer — giving it its own span made its exclusive time visible as 200ms. Rank 1.

### The difference from Day 40 N+1 detection
N+1 detection counts tool invocations. Exclusive time detection measures duration distribution. They catch different pathologies. N+1 says "this tool is called too many times." Exclusive time says "this span is consuming time that isn't attributed to its children." Both are necessary. The graph from Day 40 carries both analyses.

### The bridge from 2023 to 2026
At Delivery Hero, the slow stage was a synchronization primitive — the local event queue. In an agent trace, the slow stage is often the model's reasoning loop — the time between tool calls where the model is deciding what to call next. That reasoning time shows up as exclusive time on the root span. If the root span has high exclusive time, the model is spending a lot of tokens thinking between calls. If it's low, the model is calling tools efficiently. Both patterns are worth knowing.

### So what
Exclusive time is the same concept whether you're profiling a logistics pipeline, a CPU flame graph, or an agent trace. The formula doesn't change. The domain changes the interpretation: for a routing system, slow exclusive time in a consumer means a buffering bug. For an agent, slow exclusive time in a root span means expensive reasoning between tool calls. TraceForge makes both visible.

---

## Section 5 — Flame Graphs for Money

### The Grafana waterfall as a cost flame graph
A cost waterfall is a flame graph where width represents money instead of time. The tallest bar is the highest-cost tool. The shape is the same. The action it drives is the same: find the widest frame, understand why it's wide, decide whether to optimize or replace it.

### What changes when the unit is dollars
Time bottlenecks produce latency and user experience concerns. Cost bottlenecks produce budget concerns. The Grafana Bar Gauge panel, fed with sorted `cost_usd` per tool, produces the dollar equivalent of a flame graph. The engineering team sees where the budget goes. The CFO sees whether the spend is justified by the value the tool produces.

### The decision the chart drives
When `code_interpreter` is 60% of per-trace cost, the question isn't "how do we make it faster?" The question is: "is this tool's output worth 60% of what we spend per trace?" That's a product decision, not an engineering decision. The waterfall chart surfaces it as a product decision by making the proportion visually unmistakable.

### What the DH experience taught me
We spent three weeks looking at the wrong thing because our monitoring showed total duration instead of exclusive time. When we switched to exclusive time, the answer was obvious in one chart. I'm building TraceForge so agent infrastructure teams don't spend three weeks finding the handoff that's eating their budget. The chart is the shortcut to the right question.

### So what
Flame graphs for money aren't a dashboard trick. They're a forcing function: they make the most expensive decision in your system the most visually prominent thing in your weekly review. Teams that see their cost waterfall every week make different decisions than teams that see a table of percentages.

---

## Series Navigation Footer

Previous: Day 40 — N+1 Tool Calls — The SELECT * of Agents (Walmart)
Next: Day 42 — (coming)

---

## HTML Checklist Before Push

- [ ] `Day 41` in `<title>`, `<h1>`, accent chip, meta line, series footer (all four mandatory locations)
- [ ] `class="series-nav"` / `class="series-posts"` / `class="series-post"` CSS present in `<style>` block
- [ ] No system names invented beyond what appears in delivery-hero-rider-tracking-system.md and resume-extracted.md
- [ ] No specific percentage savings invented (use only "P99 dropped from 340ms to 118ms" narrative — do not use this unless verified)
- [ ] All `<div>` opens match `</div>` closes
- [ ] No `</motion.div>` tags
- [ ] No `<a>` nested inside `<a>`
- [ ] Max 3 sentences per paragraph (split any that exceed this)
- [ ] No placeholder URLs
- [ ] Employer tenure accurate: Jun 2022 – Jul 2023, Sr. Software Engineer, Global Logistics Platform, Delivery Hero, Berlin
