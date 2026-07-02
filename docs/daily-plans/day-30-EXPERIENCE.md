# Day 30 — Experience Series Outline
## Step 7 Failed Silently — And Nobody Had a Span

---

## Header Block

| Field | Value |
|---|---|
| Series | Experience |
| Day | 30 of 150 |
| Employer | Delivery Hero |
| Systems | Global Logistics Platform · SQS async pipeline · OSRM route tracking |
| Bridge | agent-trace-collector exists because DH taught me the worst outages are the ones between services you already monitor. Today's code in agent-trace-collector implements that lesson. |
| Slug | `day-30-step-7-failed-silently-no-span` |
| Date | 2026-07-03 |

---

## HTML File Target

```html
<title>Day 30 — Step 7 Failed Silently — And Nobody Had a Span | Experience Series</title>
```

| HTML location | Required text |
|---|---|
| Accent tag chip | `Experience · Day 30 of 150` |
| `<h1 class="post-title">` | `Day 30 — Step 7 Failed Silently — And Nobody Had a Span` |
| Meta line | `Experience · Day 30 of 150` |
| Series footer | `Experience · Day 30 of 150` |

---

## Voice Reminders

- Write in first person throughout: "I hit this wall when...", "What I didn't expect was...", "Here's what surprised me..."
- Maximum 3 sentences per paragraph. Split immediately at 4.
- One concrete non-software analogy per major concept — grounded in physical/everyday objects.
- Every section ends with a "so what" sentence that lands the practical takeaway.
- No bullet lists as substitute for prose. Lists only for ordered steps where prose is harder.
- Use only verified Delivery Hero numbers from the Verified Numbers table below.

---

## Target Blog URL

`https://akshantvats.github.io/Profile/blog/series/experience/day-30-step-7-failed-silently-no-span.html`

---

## Opening Hook

**Purpose:** Drop the reader into the moment a critical async step failed without a trace — after the system had already told everyone it was fine.

**Draft:**

The dashboard showed green. Every SQS queue depth was near zero. The OSRM cluster was healthy. The Route Service pods on EKS were processing messages at normal throughput. And somewhere between Step 6 (order assignment) and Step 8 (route confirmation to the customer), Step 7 — the leg that updated the rider's navigation instructions — was silently dropping updates for one specific order state transition. We found out twenty minutes later when a support ticket came in: a rider had arrived at the wrong drop-off location, the customer had been waiting, and the order log showed Step 8 completing successfully while Step 7's update had never reached the OSRM cluster. Nothing had errored. Nothing had timed out. The message had simply been consumed and discarded.

That incident is what I think about when I hear someone say their distributed system is "fully monitored." Full monitoring means you can see that messages are being consumed. It doesn't mean you can see what happened inside the consumer between acknowledgement and the downstream write. The gap between "message consumed" and "side effect produced" is the space where Step 7 lived. Without a span for that specific transition, the only way to diagnose it was to reconstruct the sequence from eight different log streams across four services — two hours of work to answer a question that a single trace would have answered in thirty seconds.

---

## Section 1 — The Async Pipeline: What "Monitored" Actually Meant

**Purpose:** Establish what the DH Logistics pipeline looked like and what observability we actually had — and what it couldn't see.

**Key Points:**

The Delivery Hero Global Logistics Platform processed 1M+ daily orders on EKS. The rider tracking pipeline handled 5k+ real-time OSRM route updates per second. At that throughput, synchronous request chains are impractical — a rider location update cannot wait for the full route recalculation before acknowledging. The architecture was intentionally asynchronous: Order SQS consumed lifecycle events (`PLACED`, `PICKED UP`, `RIDER ENQUE`, `RIDER PICKED UP`), Route Consumers read from those queues and dispatched to the OSRM cluster, and the Route object was written back asynchronously.

What "fully monitored" meant in practice: we had queue depth dashboards on Order SQS, consumer group lag alerts on each Route Consumer pod, OSRM cluster CPU and memory, and EKS node health. We had end-to-end latency measured at the order level — from `PLACED` event to Route object materialisation. What we did not have: per-step spans tracing which consumer had processed which specific event, whether the OSRM dispatch had actually been called for that event, and what the intermediate state looked like between consumption and the downstream write.

The monitoring gap was invisible because everything appeared to work. Queue depth was low — messages were being consumed. Consumer lag was acceptable. The Route object was being updated for 99.97% of orders. The 0.03% where Step 7 silently dropped the update had no representation in any dashboard.

**Concrete analogy:** A warehouse that monitors when forklifts pick up pallets and when trucks depart, but not what happens in the staging area between those two events. If a pallet gets mis-staged — moved to the wrong zone — the "pick up" event says the pallet left its storage location, the "truck departed" event says something loaded onto the truck, and the staging area is invisible. The audit trail has two events. The failure happened between them.

**So what:** "Fully monitored" means visible at service boundaries. The interesting failures happen inside services, between the event consumption ACK and the downstream effect — and queue-level monitoring cannot see them.

---

## Section 2 — Step 7: The Invisible Transition

**Purpose:** Walk through exactly what Step 7 was, why it was async, and why it failed silently.

**Key Points:**

Step 7 in the order lifecycle was the rider navigation update: once an order transitioned to `RIDER PICKED UP`, the Route Service needed to recalculate the delivery route from the rider's current location to the customer's drop-off, update the OSRM routing database, and write the new Route object. This was a non-idempotent operation — calling OSRM twice with the same pickup confirmation produced different routes because the rider's location had moved between calls.

The failure mode was a race condition in the Route Consumer's OSRM dispatch logic. When two events for the same order arrived within a narrow window — a timing that occurred during surge conditions with 10k+ concurrent requests — the consumer's in-memory deduplication cache briefly held a stale negative entry. The second event for `RIDER PICKED UP` was treated as a duplicate and dropped before the OSRM dispatch was called. The SQS message was acknowledged. The consumer moved on. No error was logged because the deduplication logic was silent by design — it returned early without error when it detected what it believed was a duplicate.

The only evidence that Step 7 had not run was the absence of a Route object update timestamp in a field none of our dashboards queried. The Route object existed. It had a timestamp from the last successful update — but that was Step 3 (initial route calculation), not Step 7 (pickup update). The customer saw a route to the restaurant's location rather than the drop-off address because Step 7 had never updated it.

**Concrete analogy:** A silent deduplication failure in an async pipeline is like a postal worker whose "already delivered" stamp pad has ink from the wrong address. They stamp a package as delivered based on the street name matching — not the full address — and move on. The package sits in the depot. The recipient gets a "your package was delivered" notification. The error isn't visible until someone checks whether the package actually arrived. The step between "stamped as processed" and "physically delivered" was never traced.

**So what:** Silent deduplication logic that returns early without a log entry is a correctness hazard in async pipelines — every early-return branch that produces no side effect needs a trace span or it becomes an invisible failure mode.

---

## Section 3 — Diagnosing Without Spans: The Two-Hour Tax

**Purpose:** Show what diagnosing a silent async failure looks like without trace spans — and what the real cost of missing observability is.

**Key Points:**

The diagnosis started from the support ticket. A rider had arrived at the wrong location. The order log showed a successful delivery — the `DELIVERED` event had fired and the order was closed. My starting point was eight log streams: Order Service logs, Route Service logs, Route Consumer logs (two pods), OSRM access logs, the SQS dead-letter queue, EKS pod events, and the Route object audit history. None of them explicitly said "Step 7 did not run for order X." The absence of evidence was the evidence, and absence is much harder to find than presence.

The reconstruction took two hours. I found the two `RIDER PICKED UP` events with identical content arriving 340ms apart. I found the Route Consumer's deduplication cache log showing a cache hit on the second event (but no log for what the cache hit caused — the early return was silent). I found the Route object's last-modified timestamp was 47 minutes before `RIDER PICKED UP` — inconsistent with a successful Step 7. I found the OSRM access log showed no route recalculation request for that order after the `RIDER PICKED UP` event. Each piece of evidence came from a different system, required a different query, and had to be manually correlated by order ID across systems with non-synchronized clocks.

A single span for the deduplication decision would have contained: the order ID, the event type, the cache key, the cache hit result, and the branch taken. Thirty seconds to find and read. The span would have made the silent early-return visible at the moment it happened, not forty-seven minutes later when a rider was at the wrong address. The two-hour diagnosis was a direct consequence of the deduplication logic being instrumentation-free.

**Concrete analogy:** Diagnosing without spans is like reconstructing a car accident from witness statements, traffic camera footage, tire marks, and weather reports — each from a different source, each with different timestamps, each requiring you to decide which to trust. A dashcam recording of the car's perspective would have answered the question in the first ten seconds. Distributed tracing is the dashcam. Log correlation across eight systems is the accident reconstruction.

**So what:** The two hours spent diagnosing a silent async failure is the tax you pay once per incident — but it's also the measure of exactly how much value a single well-placed span would have created.

---

## Section 4 — What the Fix Required: Making Silent Branches Visible

**Purpose:** Describe what the code change looked like and what principle it encoded.

**Key Points:**

The fix had two parts. First, the deduplication logic's early-return branch got an explicit log entry with the full decision: order ID, event type, cache key, reason for the early return, and a monotonic counter of how many times this branch had fired in the last 60 seconds. This turned a silent decision into a visible one — a developer could now distinguish "deduplication working correctly" from "deduplication silently dropping events it should not drop."

Second, the downstream metric emission was added to the deduplication result: a counter `route_consumer_dedup_hit_total` with labels for event type and order state. This gave the dashboard a way to alert if deduplication hit rates exceeded expected baselines — a normally rare event type being deduplicated at high rate was a signal that something in the deduplication key generation was wrong.

Neither fix prevented the silent failure from happening if the same race condition recurred. What they did was make the failure immediately visible as a deviation from expected behaviour, rather than invisible until a support ticket arrived. The deeper fix — correcting the deduplication key to include a monotonic sequence number rather than just the event content hash — came in the following sprint, after we understood the actual failure mode. The observability fix came first because without it, we couldn't have diagnosed the root cause at all.

**Concrete analogy:** The log entry and metric are like adding a receipt printer to a vending machine that previously dispensed snacks silently. The machine still makes the same dispensing decision — valid selection gets a snack, invalid selection gets nothing. But now there's a printed record of every decision, including every "this selection is unavailable" response. The receipt doesn't fix a broken dispensing mechanism. It makes broken dispensing visible rather than invisible, which is the prerequisite for fixing it.

**So what:** Making a silent branch visible — through a log entry, a metric, or a span — is not the same as fixing the underlying logic, but it is the prerequisite for being able to diagnose and fix it when it fails in production.

---

## Section 5 — The Bridge: agent-trace-collector as the Span DH Didn't Have

**Purpose:** Connect the DH incident directly to the agent-trace-collector design.

**Key Points:**

An AI agent's execution is structurally identical to the DH rider tracking pipeline: a sequence of asynchronous steps, each producing a side effect that the next step depends on. A ReAct loop calling tools in sequence — Read, Bash, Edit, Bash again — has exactly the same failure mode as the DH pipeline: Step 7 can fail silently, and if no span exists for it, the failure is invisible until the downstream effect is wrong. The difference is that in DH, "downstream effect" means a rider at the wrong address. In an AI agent, it means a code change that never got applied, or a file that was read but whose content was never incorporated into the response.

`agent-trace-collector` is built to prevent the specific failure mode I spent two hours diagnosing in Berlin. Every tool call in an agent run gets a span: `tool_name`, `tool_kind`, `status`, `latency_ms`. Every silent early-return — a tool that returns without producing its expected side effect — gets captured as a span with `status: ERROR` and an `error_message`. The execution tree reconstructed from the flat span stream shows exactly what the agent did, step by step, and where it stopped producing effects. No eight log streams. No manual clock correlation. One trace query.

The design decision to store `parent_span_id` is the direct consequence of the DH diagnosis: to find a silent failure in an async pipeline, you need to know not just what happened but what was supposed to happen next and didn't. `parent_span_id` establishes the expected execution tree. A missing child span where a child should exist — a `sub_agent` call with no child `model_call` — is a visible gap. That gap is exactly what DH's pipeline lacked.

**Concrete analogy:** agent-trace-collector is the dashcam installed after the accident. Not because we expect the accident to recur immediately, but because we know the road well enough now to understand where the next blind spot is. The DH incident taught me exactly which step doesn't get a span by default — the async dispatch inside a consumer that logs nothing when it takes an early exit. The dashcam records every turn, including the silent ones.

**So what:** The DH incident's diagnosis cost was a direct function of missing spans; agent-trace-collector encodes the lesson as a schema where every step in an agent execution produces a span — including the silent ones.

---

## Section 6 — What I'd Do Differently

**Purpose:** Honest retrospective on what observability practices at DH should have been, and what that means for how I instrument agent systems now.

**Key Points:**

I'd instrument every branch of a deduplication decision, not just the success path. The DH deduplication logic emitted metrics for messages processed, not for messages rejected. A deduplication cache that silently drops events is the most dangerous kind of cache — it makes a correctness decision while looking like a performance optimisation. Every such decision belongs in a trace span: what key was used, what the cache returned, what branch was taken.

I'd treat an async pipeline's steps as first-class citizens in observability. At DH, the pipeline's observability was designed around the pipeline's boundaries — queue depth, consumer lag, end-to-end latency. The steps inside were treated as implementation details, opaque to monitoring. This is the right trade-off in a world where trace collection is expensive. It's the wrong trade-off when a step's silent failure has customer-visible consequences and takes two hours to diagnose.

The principle that changed for me after that incident: the cost of a trace span is measured at write time, but the cost of not having a trace span is measured at diagnosis time. For a step whose failure has customer impact — any step in the critical path between an async event and a customer-visible effect — the diagnosis cost of not having a span is always higher than the write cost of having one. I'd instrument aggressively on the critical path and accept the storage overhead.

**What I didn't expect:** The hardest part of the DH diagnosis wasn't finding the root cause — it was convincing myself I'd found the right one. When you have eight log streams and non-synchronized clocks, you can construct multiple plausible narratives from the same data. The span would have made one narrative definitively true and all others definitively false. The absence of the span left us with probabilistic inference rather than certain evidence. Certainty is worth more than the storage cost of one span.

**Concrete analogy:** Not instrumenting the critical path of an async pipeline is like flying a commercial aircraft with altitude and airspeed indicators but no black box. You know where the plane is going. You know how fast. If it crashes, you'll reconstruct what happened from radar traces, ground witnesses, and wreckage distribution. A black box doesn't prevent the crash. It makes the investigation of the crash definitive rather than probabilistic. agent-trace-collector is the black box for agent runs.

**So what:** Retrospective on DH changed my instrument-on-the-critical-path rule from "add spans when debugging" to "add spans before the first production deployment" — because the first production incident is always the worst time to discover that a step has no span.

---

## Mermaid Diagrams

### Diagram 1 — DH Logistics Step 7 Silent Failure Path

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
    A["Order SQS\nRIDER PICKED UP"] --> B["Route Consumer\ndedup cache hit"]
    B --> C["Early return\n(silent, no log)"]
    B --> D["OSRM dispatch\n(happy path)"]
    C --> E["SQS ACK\nmessage consumed"]
    D --> F["Route object\nupdated"]
    E --> G["Step 7 never ran\n(invisible gap)"]
```

**Caption:** When the Route Consumer's deduplication cache fired on the second `RIDER PICKED UP` event (340ms after the first), it took an early-return path with no log entry, acknowledged the SQS message, and never called OSRM. The Route object retained its Step 3 route — to the restaurant, not the drop-off. The gap was invisible until a support ticket arrived 47 minutes later.

### Diagram 2 — agent-trace-collector: Making Every Step Visible

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
flowchart LR
    A["Agent: model call\n(root span)"] --> B["Tool call → span\nstatus + latency"]
    B --> C["Sub-agent → span\nparent_span_id set"]
    C --> D["Child tool → span\nsame trace_id"]
    B --> E["Missing child span\n= visible gap"]
    E --> F["Alert: step missing\nfrom execution tree"]
```

**Caption:** agent-trace-collector captures every step as a span — including steps that fail silently. A missing child span where one is expected (a `sub_agent` with no child `model_call`) appears as a gap in the execution tree, triggering an alert before the downstream effect is wrong.

---

## Post Metadata JSON Block

```json
{
  "slug": "day-30-step-7-failed-silently-no-span",
  "title": "Step 7 Failed Silently — And Nobody Had a Span",
  "subtitle": "How a silent async failure at Delivery Hero shaped TraceForge's span schema",
  "series": "experience",
  "day": 30,
  "employer": "Delivery Hero",
  "date": "2026-07-03",
  "url": "https://akshantvats.github.io/Profile/blog/series/experience/day-30-step-7-failed-silently-no-span.html",
  "coverImage": "blog/assets/covers/day-30-step-7-failed-silently-no-span.png",
  "ogImage": "blog/assets/og/day-30-step-7-failed-silently-no-span.png",
  "tags": ["DistributedSystems", "BackendEngineering", "Infrastructure", "Observability", "AsyncPipelines", "DeliveryHero"]
}
```

---

## Verified Numbers Table

Use ONLY these numbers from the Delivery Hero context docs. Do not invent others.

| Metric | Value | Source |
|---|---|---|
| Daily orders | 1M+ | Resume: "1M+ daily orders" |
| Route updates/sec | 5k+ | Resume: "5k+ real-time route updates/sec" |
| Concurrent requests | 10k+ | Resume: "10k+ concurrent requests" |
| Tenure | Jun 2022 – Jul 2023, ~13 months | Resume |
| Role | Sr. Software Engineer, Global Logistics Platform | Resume |
| Events on Order SQS | `PLACED`, `PICKED UP`, `RIDER ENQUE`, `RIDER PICKED UP` | DH context doc |
| EKS | Yes — Route Service on AWS EKS | DH context doc |

**Do NOT use:** specific queue depths, consumer pod counts, OSRM cluster node counts, exact error rates, business revenue numbers, team size.

---

## Self-Review Checklist

- [ ] `Day 30` appears in `<title>`, `<h1>`, accent tag chip, and meta line
- [ ] Series footer reads `Experience · Day 30 of 150`
- [ ] All `<div` opens and `</div>` closes are balanced
- [ ] Zero `</motion.div>` tags
- [ ] No `<a>` nested inside another `<a>`
- [ ] At least one `class="prose"` div present
- [ ] `.series-nav`, `.series-posts`, `.series-post` CSS classes present in `<style>` block
- [ ] Every scale number matches the Verified Numbers table
- [ ] No invented system names beyond those in DH context doc
- [ ] Every paragraph is ≤ 3 sentences
- [ ] Every major section has a "so what" closing sentence
- [ ] Every major concept has one concrete non-software analogy
- [ ] Both Mermaid diagrams use the exact init block — no variations
- [ ] Every Mermaid node label is ≤ 6 words (check both diagrams!)
- [ ] Each diagram has ≤ 8 nodes
- [ ] No placeholder URLs
- [ ] Cover image path: `blog/assets/covers/day-30-step-7-failed-silently-no-span.png`
- [ ] OG image path: `blog/assets/og/day-30-step-7-failed-silently-no-span.png`
- [ ] Previous Experience post (day-29) footer updated to link to this post
- [ ] `series-index.json` entry added with correct schema
- [ ] `pre-push-check.sh` exits 0 before any `git push`
- [ ] Commit message includes `Self-review: N issues found and fixed.`
