# Plan A — Experience blog (Day 5 calendar · Experience 4 of N)

**Status:** Revised after user approval of fixes (2026-05-17). Plan mode only — no HTML until `implement experience blog`.

**Sources:** `data/plan.json` day 5 · user architecture diagram · CHECKLIST §B · gold: `seven-million-iot-sensors-failure-modes.html` (3× Mermaid)

---

## Metadata

| Field | Value |
|-------|--------|
| **H1** | Five Thousand Geo-Events Per Second — Shape of the Stream |
| **Subtitle** | Delivery Hero · OSRM · throughput as a schema decision |
| **Sidebar kicker** | **Experience 4 of N** (not calendar 5) |
| **Series slug** | `experience` |
| **Bridge** | OTel spans on the ingestion path today tag the same dimensions I'd use to debug a map-matching pipeline under peak dinner rush. |
| **Word target** | **1,400–1,800** (~12–14 min) |
| **Mermaid** | **3 diagrams** (see below) — no cap at 1 |

## Paths & OG

| Item | Value |
|------|--------|
| **Filename** | `five-thousand-geo-events-per-second.html` |
| **target_html** | `Profile/blog/series/experience/five-thousand-geo-events-per-second.html` |
| **Canonical** | `https://akshantvats.github.io/Profile/blog/series/experience/five-thousand-geo-events-per-second.html` |
| **`data-series-slug`** | `experience` |
| **og:image** | `https://akshantvats.github.io/Profile/blog/assets/og/five-thousand-geo-events-per-second.png` (+ `blog/assets/covers/` duplicate) |
| **Cover badge** | `EXPERIENCE SERIES` + title — no "4 of N" on PNG |

## Verified scale (use in prose + footnote table)

| Claim | Resume / post scope | Public platform context | Source |
|-------|---------------------|-------------------------|--------|
| **Geo-events / map adjustments** | **5,000+/sec** at peak (systems I owned) | Not published by DH; frame as **regional rider-tracking slice**, not global DH total | Profile README, index.html |
| **Daily orders (resume)** | **1M+** daily orders (logistics platform scope) | **~10M orders/day** globally; **3M registered riders** | [AWS EventBridge Scheduler case study](https://aws.amazon.com/solutions/case-studies/delivery-hero-sfn-case-study/) |
| **Peak orders (single day)** | — | **10.4M orders in one day** (Dec 2024 record) | [Delivery Hero Annual Report 2024](https://www.deliveryhero.com/investor-relations/) (CEO letter) |
| **Historical throughput** | — | **>1B orders/year** expected on platforms (2020) | [New Relic / DH engineering guest post](https://newrelic.com/blog/how-to-relic/how-delivery-hero-scales-for-rapid-growth) (Sep 2020) |
| **FY2024 GMV** | — | **€48.8B GMV** | DH Annual Report 2024 |
| **Middle-mile routing** | — | Up to **24%** planning savings (AWS VRP) | [AWS Supply Chain blog — DH route optimization](https://aws.amazon.com/blogs/supply-chain/delivery-hero-reduces-middle-mile-costs-with-aws-powered-route-optimization/) |

**Writing rule:** Open with **honest scope** — resume numbers describe **the rider-tracking / map-matching pipeline I built**, not entire DH Group. One paragraph cites **public 10M/day** so readers calibrate; do not imply you personally operated all 10M orders.

**Geo-event sanity check (optional sidebar, not a claim):** Sustained 5k events/s ≈ 432M events/day — plausible for **multi-market active riders × GPS Hz × (raw + matched) fan-out** on a large slice; single-node OSRM benchmarks are **~15–63 match ops/s per worker** ([OSRM #4677](https://github.com/Project-OSRM/osrm-backend/issues/4677), [match perf PR #6976](https://github.com/Project-OSRM/osrm-backend/pull/6976)) — production uses **clustered `osrm-routed`**, batching, and async queues (your diagram).

## Architecture (align with user diagram)

**Actors:** Customer, Rider  
**Order plane:** Order Service ↔ Order Data Service; Order Service → GBQ; Customer/Rider → Order Service  
**Event bus:** Order SQS — message types: `PLACED`, `PICKED UP`, `RIDER ENQUE`, `RIDER PICKED UP` (Rider also publishes here)  
**Routing plane:** Order Service + Order SQS → **Route Service** (cluster) + **Route Consumers** → **OSRM cluster** (with road graph store)  
**Outputs:** **Route JSON** (`Route: { }`) → customer/support UI; **Revisit Order System** reads route history for audit/replay  
**Analytics:** GBQ from Order Service  
**Satellite:** Order Mapping Service (ecosystem; mention briefly if not in your ownership)

**New outline section** — insert after cold open, before stream-shape:

| `id` | Section | ~words |
|------|---------|--------|
| `architecture` | **The System I Was Debugging at 8pm on a Friday** | 280 |

Narrative beats: order lifecycle events on SQS decouple **fulfillment state** from **geometry work**; Route Service vs Route Consumers split **request/response** vs **async consumption**; OSRM is stateless CPU — state lives in trip/route stores; Route JSON is the contract support and apps see; Revisit Order System is why **immutable route snapshots** matter when disputing "where was the rider?"

## Full outline (revised)

| # | `id` | Section | ~words |
|---|------|---------|--------|
| 0 | — | Cold open | 120 |
| 1 | `architecture` | System map (diagram above) | 280 |
| 2 | `scale` | Five thousand adjustments per second — what counts as an event | 200 |
| 3 | `stream-shape` | Partition keys, hot riders, dinner rush | 250 |
| 4 | `sqs-lifecycle` | SQS states → when routing work fires | 180 |
| 5 | `osrm` | OSRM cluster: match latency, radius, backpressure | 200 |
| 6 | `labels` | Labels before benchmarks (region, map rev, client) | 180 |
| 7 | `failure-modes` | Silent wrong: dupes, skew, clock skew | 220 |
| 8 | `otel-bridge` | Same dimensions on LensAI ingest today | 200 |
| 9 | `lensai` | G-03 writer / breaker / DLQ (1 paragraph + link) | 150 |
| 10 | `tradeoffs` | What we didn't do | 120 |
| 11 | `stayed` | What stayed with me | 80 |

## Mermaid specs (3 required)

### Diagram 1 — Order + routing lifecycle (flowchart TB)

Shows: Customer → Order Service; Rider → Order SQS; SQS → Route Consumers; Order Service → Route Service → OSRM; OSRM → Route JSON → UI; Order Service → GBQ; Route JSON → Revisit Order System.

### Diagram 2 — Geo-event / map-matching hot path (flowchart LR)

GPS fixes → stream (Kinesis or equivalent — label generically if needed) → Route Consumers → OSRM cluster → route state → Route JSON; dotted edge: skewed partition → lag.

### Diagram 3 — Failure / observability overlay (flowchart TD)

Duplicate GPS → double distance; partition hot spot → consumer lag; missing `map_dataset_rev` label → useless P99; tie dashed lines to metrics dimensions that mirror OTel on LensAI.

## Cross-links (canonical)

| Target | URL |
|--------|-----|
| AI Day 4 | `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-4-tensor-parallelism-kafka-partitions.html` |
| Experience 3 (IoT) | `.../experience/seven-million-iot-sensors-failure-modes.html` |
| Experience 2 | `.../experience/when-percentiles-lie-cross-tier-queries.html` |
| infra-ai-streaming | README, OBSERVABILITY.md (post-code) |

## External references (footnotes)

- [Delivery Hero Tech](https://tech.deliveryhero.com/) — platform engineering (catalog, MFE deploy, rider app cadence)
- AWS case studies (orders, EventBridge, middle-mile VRP)
- OSRM project issues on match throughput (educational contrast to clustered prod)
