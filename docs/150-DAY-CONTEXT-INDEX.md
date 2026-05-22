# 150-day context index (chat window)

Master map for agents working in `akshant-150-day-plan` and cross-repo blog/code delivery.

## Quick links

| Resource | Path |
|----------|------|
| Context README (read first) | [`docs/context/README.md`](context/README.md) |
| Realignment audit | [`docs/PLAN-REALIGNMENT-RECOMMENDATIONS.md`](PLAN-REALIGNMENT-RECOMMENDATIONS.md) |
| Rider tracking SOt | [`docs/delivery-hero-rider-tracking-system.md`](delivery-hero-rider-tracking-system.md) |
| Rider diagram | [`docs/assets/delivery-hero-rider-tracking-architecture.png`](assets/delivery-hero-rider-tracking-architecture.png) |
| Plan data | [`data/plan.json`](../data/plan.json) |
| Current calendar day | [`data/current-day.json`](../data/current-day.json) |
| Daily checklist | [`CHECKLIST.md`](../CHECKLIST.md) |
| Shipped blogs (public) | [Profile repo](https://github.com/akshantvats/Profile) — `blog/series/experience/`, `blog/series/ai-learning/` |

---

## Resume employers (extracted)

| Employer | Role | Dates | Signature systems |
|----------|------|-------|-------------------|
| **Wayfair** | Sr. SWE III — led PAS & Pricing Promotion teams | Nov 2024 – Mar 2026 | Global pricing engine, 250k+ SKU/supplier, GCP event-driven, token buckets, circuit breakers |
| **Agoda** | Sr. SWE — WhiteFalcon TSDB | Apr 2024 – Sep 2024 | 1.5T events/day, Rust+Kafka+Ceph, cross-tier P95/P99, RoaringBitmap K8s indexing |
| **Delivery Hero** | Sr. SWE — Global Logistics | Jun 2022 – Jul 2023 | 1M+ orders/day, 5k map adjustments/sec, OSRM, EKS 10k+ concurrent, SQS+Kinesis async |
| **BrowserStack** | Sr. SWE — Device instrumentation | May 2021 – Dec 2021 | APK/IPA hooks, biometrics automation |
| **Walmart Labs** | SWE II — WeIoT SmartBuildings | Aug 2018 – May 2021 | 7M+ sensors, Azure IoT Hub, stream analytics → Kafka |
| **Current** | infra-ai-streaming (OSS) | In progress | Rust ingest → Kafka → ClickHouse → Grafana, LensAI narrative |

---

## Systems map (real → plan)

| System | Key components | Plan days that should reference it | Alignment (days 0–8) |
|--------|----------------|------------------------------------|----------------------|
| **LensAI / infra-ai-streaming** | Axum ingest, Kafka, Go consumer, ClickHouse, Grafana, WAL, rate limits | 0–8 code + AI; ongoing | **Y** — days 0–8 match repo |
| **Agoda WhiteFalcon** | Kafka, Ceph, Redis hot / S3 cold, quantile merge, RoaringBitmap | 0, 2–3, 6, 10+ Agoda experience | **Y** — 0, 3, 6 anchored |
| **Delivery Hero rider tracking** | Order Service, Order SQS, Route Service, Route Consumers, OSRM, Route object, Revisit | 5, 8, 15, 20–23, 78, 82, 86, 91+ | **Y** — 5, 8; **watch** 15 (Kinesis subtitle) |
| **Wayfair pricing platform** | Delphi, Aletheia, Barter, PAS, UCMS, promotions, Pilgrim, Bigtable, supplier APIs | 7, 9, 18, 24–25, 60, 75–76, 81, 95–96, 114+ | **Y** — day 7 token buckets |
| **Walmart IoT** | Azure IoT Hub, 7M sensors, stream analytics, Kafka migration | 4, 12, 26, 79, 92, 120, 125 | **Y** — day 4 |
| **BrowserStack** | Device farm, CI integration tests | 84, 99, 115 | **N** — underused but OK |
| **Pricing doc depth** | Full service catalog (see context file) | Under-mapped until week 10+ | **Mismatch** — many Wayfair titles generic |

---

## Calendar state (audit snapshot 2026-05-22)

| Item | Value |
|------|--------|
| User-reported progress | Days **0–7** done; **day 8** in progress |
| `current-day.json` before fix | `6` (stale) |
| `plan.json` day 6 | `today`; days 7–8 `pending` |
| Known AI index drift | CHECKLIST: `day-5` file when calendar day 5 expected `day-4`; fix in Profile, not plan repo |

---

## Process (locked)

1. Experience blog agent → `docs/context/README.md` + employer SOt doc.
2. Never publish DH routing posts without Order SQS + Route Service + OSRM vocabulary.
3. Never publish Wayfair pricing posts without at least one of: Delphi, Aletheia, PAS, supplier/UCMS, 250k SKU propagation.
4. Do not push this plan repo to public GitHub (local-only per CHECKLIST).
