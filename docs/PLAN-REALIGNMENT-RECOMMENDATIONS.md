# Plan realignment recommendations

**Audit date:** 2026-05-22  
**Scope:** `data/plan.json` days 0–150 vs resume, Wayfair pricing architecture doc, Delivery Hero rider-tracking SOt, LensAI days 0–8.

---

## Executive summary

The **first nine calendar days (0–8)** are well aligned with real employers: Agoda TSDB (0, 3, 6), Walmart IoT (4), Delivery Hero geo + EKS (5, 8), Wayfair supplier token buckets (7), and infra-ai-streaming code. Shipped Profile posts for days 5–7 match the rider-tracking and cardinality narratives.

**Gaps concentrate in days 9–150:** (1) **~24 Delivery Hero** experience slots where the title does not anchor Order SQS / Route Service / OSRM—many are agent/TraceForge essays that won't contradict topology but miss resume strength; (2) **~27 Wayfair** slots that say "Wayfair" without Delphi/Aletheia/PAS/supplier vocabulary—the pricing doc is ingested but underused; (3) **three EKS/HPA peak posts** (days 8, 20, 82) overlap; (4) **two HIGH integrity issues**—day 15 subtitles over-emphasize Kinesis vs canonical Order SQS routing plane, and day 80 invents a "stealth startup" not on the resume; (5) **plan metadata lag**—`current_day` was 6 while user reports day 8 in progress.

**Pricing system (Wayfair)** is the richest unused asset: 4k+ lines covering PAS GraphQL (~3.4k RPS), Aletheia (~21k RPS), Barter, UCMS, promotions Pub/Sub, and Pilgrim/Delphi orchestration. Rewiring ~15–20 future Wayfair experience days to named services will materially improve interview signal.

**Process fix:** enforce [`docs/context/README.md`](context/README.md) before every Experience draft (patched in CHECKLIST cross-ref below).

---

## Systems inventory

| System | Company | Stack (from context) | Resume proof |
|--------|---------|----------------------|--------------|
| WhiteFalcon TSDB | Agoda | Rust, Kafka, Ceph, Redis/S3 tiers, RoaringBitmap | 1.5T events/day, cross-tier P99 |
| Rider tracking | Delivery Hero | Order Service, Order SQS, Route Service/Consumers (EKS), OSRM, Revisit, GBQ | 5k geo events/sec, 10k concurrent, 1M+ orders/day |
| Async notifications | Delivery Hero | SQS + Kinesis decoupling (resume) | Sub-second status; **not** the map-matching hot path |
| Global pricing engine | Wayfair | GKE, Delphi, Aletheia, Barter, PAS, UCMS, Bigtable, CloudSQL, Kafka, Pub/Sub, Pilgrim | Led PAS + P&P teams, 250k SKU, sub-second propagation |
| WeIoT platform | Walmart | Azure IoT Hub, millions of sensors, Kafka | 7M+ sensors, stream analytics limits |
| Device instrumentation | BrowserStack | Native hooks, CI | Sparse plan coverage |
| infra-ai-streaming | OSS / LensAI | Rust, Kafka, ClickHouse, Grafana | Current project; Agoda cardinality bridge |

---

## Days 0–8: completed / in progress

| Day | Experience | Verdict |
|-----|------------|---------|
| 0 | Agoda 1.5T observability | **OK** |
| 1 | Design docs (deferred backlog per CHECKLIST) | **OK** — meta, not employer fiction |
| 2 | Ceph/POSIX Agoda (deferred) | **OK** |
| 3 | Cross-tier percentiles Agoda | **OK** — matches resume |
| 4 | Walmart 7M sensors | **OK** |
| 5 | DH 5k geo-events / stream shape | **OK** — aligns with rider doc + shipped post |
| 6 | Agoda cardinality / RoaringBitmap | **OK** |
| 7 | Wayfair supplier token buckets | **OK** — bridge to pricing APIs |
| 8 | DH 10k concurrent EKS | **OK** — Route Service layer per rider doc |

**Minor notes (no title changes required):**

- Day 3 AI title duplicates "Day 2" wording in plan.json—Profile CHECKLIST already flags index drift; fix in Profile repo.
- Day 5 `ai.day_index` is 5 on calendar day 5—should be 4 per CHECKLIST rule (off-by-one).
- Mark days 6–7 `done` and day 8 `today` in `plan.json` when user closes day 7.

---

## Days 9–150: prioritized change list

### High

| Day | Current title | Proposed title | Why |
|-----|---------------|----------------|-----|
| **15** | Async Pipelines That Survived Dinner Rush | **Order SQS → Route Consumers — Decoupling Map-Match from Status** | Subtitle cited "SQS/Kinesis" without Order SQS / Route Service; risks Kinesis-only fiction. Resume: async SQS+Kinesis is for **notifications**, not OSRM hot path ([`delivery-hero-rider-tracking-system.md`](delivery-hero-rider-tracking-system.md)). |
| **80** | Stealth Startup Saga: Compensating Transactions on Order State | **Route Revisions and Revisit Order System — Compensating Bad Polylines** | "Stealth startup" not on resume. Use DH Revisit Order System + Route `{ }` object from rider doc. |
| **20** | Peak Kubernetes — HPA Reacts, It Doesn't Predict | **Route Consumer Lag — Why CPU-Based HPA Failed at Lunch Rush** | Duplicates day **8** EKS peak story; shift to **consumer lag / SQS depth** scaling signal. |
| **82** | Delivery Hero Peak EKS — PDB + HPA Tuning Under OSRM Load | **OSRM Pool Saturation — PDBs When Map-Matching Ate the Error Budget** | Third EKS/HPA overlap; differentiate with **OSRM cluster** failure mode vs generic HPA. |

### Medium

| Day | Issue | Proposed direction |
|-----|-------|-------------------|
| **9** | Wayfair SKU propagation — generic event-driven | **Delphi → Aletheia feed — Sub-Second Price Visibility** (use pricing doc §Distribution) |
| **24**, **95** | Duplicate "BigQuery Streaming vs Batch" | Keep **24** as Wayfair PAS analytics (`pas-analytics` Pub/Sub); retitle **95** to **ScheduledReader TB-scale BQ slots** |
| **25**, **75** | Two Redis token-bucket stories | **75** = supplier boundary (gst-acc / UCMS); **25** = tenant gateway Lua — keep both but cross-link |
| **58**, **59** | Duplicate "TraceForge — Agents Need a Flight Recorder" | Collapse to one day; other → **TraceForge launch narrative** only |
| **60** | Semantic Cache — Wayfair Pricing Deja Vu | Good hook — add **Aletheia cache + price-change Kafka** in subtitle |
| **18** | Rate limiting supplier boundary | Add **UCMS / gst-acc-promotions** names from pricing doc |
| **78** | DH Async SQS from OSRM | **Strong** — keep; ensure copy says Order SQS not generic Kinesis |
| **81** | Wayfair SKU propagation ordering | Tie to **Kafka `pricing_refresh` 40 partitions** + versioned events |
| **96** | Leading two teams | Pull PAS + Promotions team scope from resume + pricing doc §PAS/§Promotions |
| **141** | Helm at Delivery Hero | Anchor to **Route Service EKS stack** Helm values, not generic cluster |

**Delivery Hero "weak topology" (14 days):** 30, 37, 52, 58, 59, 62, 67, 74, 101, 106, 122, 141 — agent/product themed; add one sentence in bridge tying to Order Service or Route Consumers (Low effort, Medium impact).

**Wayfair "weak pricing anchor" (16 days):** 9, 24, 25, 33, 48, 55, 56, 71, 81, 95, 96, 114, 124, 128, 138, 147 — retitle or subtitle with Delphi/Aletheia/PAS/UCMS.

### Low

- Agoda-heavy second half (43 experience mentions) — balanced but monitor duplicate cardinality/Kafka posts (days 85, 100, 105).
- BrowserStack only 3 days — acceptable.
- Netflix shadow traffic (90) — fine as external pattern, not employer fiction.

---

## Pricing doc → recommended plan days

| Pricing domain | Services | Suggested experience days |
|----------------|----------|---------------------------|
| Storefront read path | Aletheia, Barter, Basket | 9, 60, 114 (A/B reads) |
| Calculation core | Delphi, ScheduledReader | 9, 81, 147 (rollout) |
| Supplier ingress | UCMS, gst-acc-promotions, ph-ui-web | 7, 18, 75, 76 |
| Adjustments / overrides | PAS Core, PAS Bigtable, PAS CloudSQL | 25, 96, 128 |
| Orchestration / simulation | Pilgrim, Pricing Run Orchestrator, Pub/Sub simulation | 24, 95 (split), 138 |
| Promotions | PromoSvc, PromoDB, Promo Pub/Sub | 60, 114 |
| Cost aggregation | SPCS, Hydros eden-reader | 33 (SDK) → **eden-reader burst** story |

**Do not** attribute pricing platform components to Delivery Hero or Agoda.

---

## Duplicate / conflict register

| Topic | Days | Action |
|-------|------|--------|
| EKS / HPA / 10k concurrent | 8, 20, 82 | Differentiate per High table |
| BigQuery streaming vs batch | 24, 95 | Split domains |
| TraceForge flight recorder | 58, 59 | Dedupe |
| Redis token bucket | 7, 25, 75 | Clarify supplier vs gateway |
| DH OSRM / geo | 5, 23, 82, 91 | OK if angles differ (stream shape, ETA budget, pool saturation, retries) |

---

## Process rule (add to CHECKLIST)

> **Before Experience blog generation:** read [`docs/context/README.md`](context/README.md) and employer SOt (`delivery-hero-rider-tracking-system.md` and/or `docs/context/pricing-system-architecture.md`). Ask user if post predates ingested context.

---

## Applied patches (plan.json)

The following **High** edits were applied in `data/plan.json` for review:

- Day **15** — experience subtitle/bridge → Order SQS / Route Consumers framing
- Day **80** — experience title/subtitle/bridge → Revisit Order System (DH)
- Day **20** — experience title/subtitle → consumer lag HPA (dedupe day 8)
- Day **82** — experience title/subtitle → OSRM saturation angle

`data/current-day.json` → `8`.

**Not patched (document only):** Medium/Low items, day status fields, `ai.day_index` off-by-one on day 5.

---

## Metrics

| Metric | Count |
|--------|------:|
| Future days with experience posts (9–150) | ~142 |
| Flagged (any severity) | **26** unique days |
| High priority | **4** |
| Medium priority | **~22** |
| Wayfair days needing pricing vocabulary | **16** |
| DH days weak topology | **14** |

---

## Top 10 recommended changes (by day)

1. **15** — Replace Kinesis-first framing with Order SQS → Route Consumers (HIGH)  
2. **80** — Remove stealth startup; use Revisit Order System / Route revisions (HIGH)  
3. **20** — Retitle to consumer-lag scaling vs duplicate EKS post on day 8 (HIGH)  
4. **82** — Retitle to OSRM pool saturation vs third generic HPA post (HIGH)  
5. **9** — Rewire to Delphi → Aletheia sub-second propagation (MEDIUM)  
6. **95** — Split from day 24 BigQuery duplicate → ScheduledReader analytics (MEDIUM)  
7. **60** — Add Aletheia + price-change Kafka to semantic cache story (MEDIUM)  
8. **18** — Name UCMS / gst-acc-promotions in supplier rate limit post (MEDIUM)  
9. **58–59** — Deduplicate TraceForge flight-recorder titles (MEDIUM)  
10. **96** — "Leading two teams" → PAS + Promotions with pricing doc team boundaries (MEDIUM)
