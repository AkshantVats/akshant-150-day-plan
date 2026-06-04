# Day 18 — Experience Post Outline
## "Rate Limiting at the Supplier Boundary — Not the Textbook Diagram"
### Experience · Day 18 of 150

**Series**: Experience
**Day**: 18 of 150
**Employer**: Wayfair
**Systems**: UCMS (ucms-partner-home), gst-acc-promotions, SPCS (Supplier Cost Service), PAS CORE
**Bridge**: WAL on ingestion + eBPF backpressure policy is the same "never lose the write" instinct as gst-acc-promotions durability at the supplier boundary.

**Target blog URL**: `https://akshantvats.github.io/Profile/blog/series/experience/day-18-supplier-rate-limiting.html`

---

## HTML File Target
`blog/series/experience/day-18-supplier-rate-limiting.html`

**Title tag**: `Day 18 — Rate Limiting at the Supplier Boundary — Not the Textbook Diagram | Experience Series`
**Accent chip**: `Experience · Day 18 of 150`
**H1**: `Day 18 — Rate Limiting at the Supplier Boundary — Not the Textbook Diagram`
**Meta line**: `Experience · Day 18 of 150`
**Series footer**: `Experience · Day 18 of 150`

---

## Voice Reminders (from CLAUDE.md)
- First person throughout: "I hit this wall when...", "What I didn't expect was..."
- Max 3 sentences per paragraph. Split at 4.
- One concrete analogy per major concept — grounded in physical/everyday objects
- Every section ends with a "so what" sentence
- No bullet lists as substitute for prose

---

## Opening Hook

**Goal**: Pull the reader in with the tension between the textbook diagram and reality.

Opening sentence: "The first time I saw gst-acc-promotions fall over, the on-call alert said 'p99 latency spike' — it didn't say '14 suppliers sent simultaneous batch updates.'"

**Textbook vs. reality**: The textbook diagram for rate limiting is a single box labeled "API Gateway" with an arrow flowing through a token bucket. At Wayfair, the actual problem was nothing like that box. It was 70,000 active suppliers, each with their own peak pattern, hammering a single ingestion boundary at 250,000 SKU updates per supplier in near real-time — and the "gateway" that needed a rate limiter wasn't a gateway at all.

**Concrete analogy for the opening**: Rate limiting at a busy post office — not one queue for all mail, but a separate counter per major corporate account, each with its own daily envelope allowance.

---

## Section 1 — System Topology (What Was Actually Running)

**Purpose**: Orient the reader. Don't assume they know Wayfair's architecture.

**Key points to cover**:
- UCMS (ucms-partner-home): Supplier Core, 10–35 pods autoscaled via HPA, Python FastAPI, ~1.7 RPS average but with burst patterns from supplier batch uploads
- gst-acc-promotions: 12 pods, Python FastAPI, ~0.9 RPS average — lower throughput than UCMS but latency-sensitive (0.56s average response time)
- SPCS (Supplier Cost Service): the read layer, Bigtable-backed, ~2,800 QPS average, ~4,200 peak — price reads land here
- PAS CORE: the heavy compute layer, 3,414 RPS average, 15,263 peak, 3.1s average latency — clearly spiky
- CloudSQL proxy in every service: 2–4 replicas per service, the shared statefulness behind the stateless FastAPI pods

**What to emphasize**: The variance between average and peak for PAS CORE (3,414 avg vs 15,263 peak — a 4.5x spike factor) is the context for why naive rate limiting fails. A single bucket sized for average load gets blown through instantly at peak.

**So what**: The topology tells you where the pressure concentrates before you write a line of rate-limiting code.

---

## Section 2 — The Supplier Boundary Concept

**Purpose**: Define what "supplier boundary" means and why it's the right abstraction for rate limiting.

**Key points**:
- A "supplier boundary" is not a network boundary. It's a trust and capacity boundary — each supplier has contractually different update volumes, different peak hours, and different SLAs.
- 70,000 active suppliers, peak 9am–6pm ET on weekdays. Not uniform — a furniture supplier's SKU updates cluster around catalog season; a home goods supplier spikes at holiday drops.
- The naive implementation: one shared rate limiter for all supplier traffic at the gst-acc-promotions ingestion path. This failed when a top-10 supplier by SKU count did a batch upload and consumed the entire shared bucket.
- The correct implementation: per-supplier token bucket, with capacity proportional to contracted update volume.

**Concrete analogy**: Think of a highway toll plaza. One toll booth for 70,000 cars fails. Separate lanes per vehicle class (trucks, cars, motorcycles) — each with its own throughput — is how real highways work. The supplier boundary is the lane assignment.

**What I didn't expect**: the per-supplier key wasn't just the supplier ID from the request. It was a composite key of `(supplier_id, product_type)` because the same supplier sending furniture updates vs. rug updates hit different downstream services (SPCS vs. PAS CORE) with totally different cost profiles.

**So what**: Once you name the right boundary, the bucket granularity writes itself.

---

## Section 3 — Token Bucket Per Supplier — The Design Decisions

**Purpose**: Go from concept to the actual design choices. Not the code — the decisions.

**Key points**:
- Token bucket over leaky bucket because suppliers send bursts (full catalog upload) followed by silence. Leaky bucket would throttle the burst even when the system had headroom. Token bucket absorbs the burst if the bucket was full from the idle period.
- Bucket capacity sized to 90th-percentile burst for each supplier tier (top-10, mid-tier, long-tail). Not one capacity for all.
- Refill rate tied to downstream sustained throughput — the constraint is PAS CORE's 15,263 peak RPS, not the supplier's 250k+ daily SKU updates.
- Distributed bucket state: the first version had single-node bucket state. With 10–35 UCMS pods, each pod had its own bucket. A supplier could hit all 35 pods and effectively get 35x the capacity. Redis atomic counters per supplier with a sliding window fixed this.
- The Redis key TTL: if a supplier is silent for 24 hours, their key expires. On next activity they start with a full bucket. Penalizing suppliers for being idle would be wrong.

**Concrete analogy for distributed buckets**: Imagine a bar with 35 bartenders and a per-customer tab limit. If each bartender tracks the tab independently, a determined customer can hit each bartender and drink 35x the limit. One shared tab ledger — the Redis equivalent — fixes this.

**Number to anchor on**: 250k+ SKU updates per supplier in near real-time. That's the inbound pressure each bucket had to absorb without dropping legitimate updates.

**So what**: Token buckets in distributed systems always need a shared backing store — the algorithm is the easy part.

---

## Section 4 — What Happened When the Bucket Was Empty (Drop Policy)

**Purpose**: The drop policy is where rate limiting gets expensive if you design it wrong.

**Key points**:
- First instinct: drop the request, return 429. Simple. Correct for stateless APIs.
- Wrong for this use case: a supplier's SKU update is not idempotent from the supplier's perspective. If gst-acc-promotions drops a price update with a 429, the supplier's system may not retry — and Wayfair loses price accuracy.
- The correct response: queue the update with a position marker. The bucket controls the ingest *rate*, but the update must not be lost. This is the WAL instinct applied at the HTTP boundary.
- Circuit breaker layered on top: when a supplier hit the bucket limit >3 times in 60 seconds, the circuit opened and their updates were queued with a 5-minute delay before retry. This separated "burst but legitimate" from "runaway retry loop."
- PAS CORE's 3.1s average latency was the downstream signal that opened the circuit — not just the token bucket state.

**What I didn't expect**: The circuit breaker needed its own state, separate from the token bucket. Mixing them into one data structure made the logic unreadable and the tests brittle. Two clean primitives — bucket + breaker — made the code easier to reason about, even at the cost of an extra Redis key per supplier circuit.

**So what**: Drop policy is a product decision dressed as an engineering decision. Get the product team in the room before you code the 429.

---

## Section 5 — The Durability Lesson (WAL Instinct at the HTTP Boundary)

**Purpose**: This is the bridge section — connects the Wayfair story to Day 18's code work.

**Key points**:
- At gst-acc-promotions, queued updates when the bucket was empty were not stored in memory. They went to a durable queue (Cloud Tasks or GCS object, depending on update size). If a pod restarted while holding in-memory queued updates, those updates were gone.
- This is exactly the WAL pattern. Before you tell the caller "accepted," you persist the intent to a durable medium. Only then do you say "I'll process this."
- The failure mode without durability: a supplier sends 50k SKU updates during a GCP zone incident. All pods restart. 50k updates silently lost. Price data stale by hours. Support tickets from 50k product pages showing wrong prices.
- The fix is the same whether you're writing a Go consumer for an eBPF tracer or a Python FastAPI service at a retailer: append to disk before you acknowledge.

**Bridge sentence to Day 18 code**: "The WAL I'm writing in ebpf-llm-tracer today is the same instinct — never tell the upstream 'I got it' until you've written it somewhere it can survive a crash."

**Concrete analogy**: A restaurant's order ticket system. The waiter doesn't tell the kitchen to start cooking until the ticket is pinned to the board. If the waiter trips and forgets, the ticket is still there. The ticket is the WAL.

**So what**: Durability is not a feature you add later. It's the first question you answer when designing any ingestion path.

---

## Section 6 — Numbers and Scale in Context

**Purpose**: Ground the abstract with verified numbers. No invented figures.

**Verified numbers to use** (from Wayfair architecture context docs):
- 70,000 active suppliers
- 250,000+ SKU updates per supplier in near real-time
- 20,000+ suppliers on the Global Pricing & Promotion Engine
- SPCS: ~2,800 QPS average, ~4,200 peak
- PAS CORE: ~3,414 RPS average, ~15,263 peak (4.5x spike factor)
- gst-acc-promotions: 0.56s average latency, 12 pods
- Price propagation reduced from hours to sub-seconds after the event-driven rewrite

**How to use these**: Use one number per paragraph as a grounding anchor, not a list. "When SPCS was at 4,200 QPS — its peak — a single misfiring supplier could add 300 QPS of unintended load..."

**What NOT to do**: Do not invent team sizes, specific incident dates, or additional scale numbers not in the context docs.

---

## Section 7 — What I'd Do Differently

**Purpose**: First-person reflection. Shows growth, makes the post credible.

**Key points**:
- Instrument the token bucket fill level as a metric, not just the drop rate. Knowing a supplier is at 80% bucket utilization before they hit the limit is a leading indicator. The drop count is lagging.
- Test the distributed bucket under network partition between pods and Redis before production. We found a race condition in staging that unit tests missed because they mocked Redis.
- Write the drop policy spec before the token bucket spec. The bucket parameters flow from the drop policy decision, not the other way around.

**So what**: The order of design matters as much as the design itself.

---

## Section 8 — Bridge to Day 18 Code (Closing)

**Draft closing**:
Today's ebpf-llm-tracer work is a smaller-scale version of the same problem. When Kafka backpressures, the Go consumer must choose: queue indefinitely (OOM risk), drop silently (data loss), or shed new events through a rate limiter while persisting in-flight events to a WAL. The answer is the same one I arrived at in gst-acc-promotions: rate-limit new arrivals, never lose what's already accepted. The WAL is the receipt. The token bucket is the door policy.

---

## Mermaid Diagrams

### Diagram 1 — System Topology

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
    SUP["70k Suppliers\n250k SKU updates each"]
    UCMS["UCMS\n10-35 pods HPA\nFastAPI ~1.7 RPS avg"]
    GST["gst-acc-promotions\n12 pods · 0.56s p50\nFastAPI ~0.9 RPS avg"]
    SPCS["SPCS Bigtable\n2800 avg / 4200 peak QPS"]
    PAS["PAS CORE\n3414 avg / 15263 peak RPS\n3.1s avg latency"]

    SUP -->|"price + promo updates"| UCMS
    UCMS -->|"promotion events"| GST
    GST -->|"cost lookups"| SPCS
    GST -->|"price compute"| PAS
```

### Diagram 2 — Rate Limiting State Machine at the Supplier Boundary

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
stateDiagram-v2
    [*] --> Accepting: bucket has tokens
    Accepting --> Accepting: token consumed / event processed
    Accepting --> Queued: bucket empty / event durable-queued
    Queued --> Accepting: bucket refilled / queue drained
    Accepting --> CircuitOpen: >3 bucket misses in 60s
    CircuitOpen --> Accepting: 5-min delay + bucket reset
```

---

## Post Metadata

```json
{
  "slug": "day-18-supplier-rate-limiting",
  "title": "Day 18 — Rate Limiting at the Supplier Boundary — Not the Textbook Diagram",
  "subtitle": "Wayfair · UCMS · gst-acc-promotions · supplier token bucket in production",
  "series": "experience",
  "day": 18,
  "date": "2026-06-04",
  "employer": "Wayfair",
  "systems": ["UCMS", "gst-acc-promotions", "SPCS", "PAS CORE"],
  "tags": ["RateLimiting", "TokenBucket", "DistributedSystems", "Wayfair", "SupplierPlatform"],
  "coverImage": "/blog/assets/covers/day-18-supplier-rate-limiting.png",
  "url": "/blog/series/experience/day-18-supplier-rate-limiting.html"
}
```

---

## Self-Review Checklist (before pushing)

- [ ] `Day 18` appears in `<title>`, `<h1>`, accent chip, meta line, series footer
- [ ] All scale numbers match context docs exactly (no invented figures)
- [ ] No system name invented (UCMS, gst-acc-promotions, SPCS, PAS CORE verified)
- [ ] Every paragraph ≤ 3 sentences
- [ ] At least one concrete non-software analogy per major concept
- [ ] Every section ends with a "so what" sentence
- [ ] Both Mermaid diagrams have the correct init block
- [ ] No nested `<a>` tags
- [ ] Div open/close count balanced
- [ ] No `</motion.div>` tags
- [ ] Cover image exists at `blog/assets/covers/day-18-supplier-rate-limiting.png`
- [ ] `pre-push-check.sh` exits 0
